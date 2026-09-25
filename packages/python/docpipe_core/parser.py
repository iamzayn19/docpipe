from __future__ import annotations

import mimetypes
from contextlib import redirect_stderr, redirect_stdout
import importlib
import io
from pathlib import Path
from typing import Any

from .models import Document, Page, TextBlock


TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".rst", ".csv", ".json", ".xml", ".html"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


class DocpipeError(RuntimeError):
    pass


def parse(path: str | Path, *, ocr: str = "auto") -> Document:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    if source.is_dir():
        raise IsADirectoryError(source)

    suffix = source.suffix.lower()
    mime_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"

    if suffix == ".pdf":
        return _parse_pdf(source, mime_type, ocr=ocr)
    if suffix == ".docx":
        return _parse_docx(source, mime_type)
    if suffix in IMAGE_SUFFIXES:
        return _parse_image(source, mime_type, ocr=ocr)
    if suffix in TEXT_SUFFIXES:
        return _parse_text(source, mime_type)

    return _parse_text(source, mime_type, fallback=True)


def _parse_text(path: Path, mime_type: str, *, fallback: bool = False) -> Document:
    warnings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
        warnings.append("Decoded file as latin-1 after utf-8 failed.")
    if fallback:
        warnings.append(f"Unknown extension {path.suffix!r}; parsed as text.")

    page = Page(number=1, text=text, blocks=[TextBlock(text=text, page=1)])
    return Document(
        source=str(path),
        mime_type=mime_type,
        pages=[page],
        metadata={"filename": path.name},
        warnings=warnings,
        backend="text",
    )


def _parse_pdf(path: Path, mime_type: str, *, ocr: str) -> Document:
    fitz = _load_pymupdf()

    pages: list[Page] = []
    warnings: list[str] = []
    with fitz.open(path) as pdf:
        metadata = {k: v for k, v in (pdf.metadata or {}).items() if v}
        for index, raw_page in enumerate(pdf, start=1):
            blocks: list[TextBlock] = []
            for block in raw_page.get_text("blocks"):
                x0, y0, x1, y1, text, *_ = block
                if text.strip():
                    blocks.append(
                        TextBlock(
                            text=text.strip(),
                            page=index,
                            bbox=(float(x0), float(y0), float(x1), float(y1)),
                        )
                    )
            page_text = "\n\n".join(block.text for block in blocks)
            if ocr == "force" or (not page_text and ocr == "auto"):
                ocr_text = _ocr_pdf_page(raw_page)
                if ocr_text:
                    page_text = ocr_text
                    blocks = [TextBlock(text=ocr_text, page=index, kind="ocr")]
                elif not page_text:
                    warnings.append(f"Page {index} had no extractable text and OCR produced no text.")
            pages.append(Page(number=index, text=page_text, blocks=blocks, tables=_extract_pdf_tables(raw_page)))

    return Document(
        source=str(path),
        mime_type=mime_type,
        pages=pages,
        metadata={"filename": path.name, **metadata},
        warnings=warnings,
        backend="pymupdf",
    )


def _ocr_pdf_page(page: object) -> str:
    try:
        import pytesseract  # type: ignore[import-not-found]
        from PIL import Image  # type: ignore[import-not-found]
    except Exception:
        return ""
    fitz = _load_pymupdf()

    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    mode = "RGBA" if pix.alpha else "RGB"
    image = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
    return pytesseract.image_to_string(image).strip()


def _extract_pdf_tables(page: Any) -> list[list[list[str]]]:
    native_tables = _extract_native_pdf_tables(page)
    if native_tables:
        return native_tables
    return _extract_word_aligned_tables(page)


def _extract_native_pdf_tables(page: Any) -> list[list[list[str]]]:
    if not hasattr(page, "find_tables"):
        return []
    try:
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            result = page.find_tables()
    except Exception:
        return []

    tables: list[list[list[str]]] = []
    for table in getattr(result, "tables", []):
        try:
            rows = table.extract()
        except Exception:
            continue
        cleaned = _clean_table(rows)
        if cleaned:
            tables.append(cleaned)
    return tables


def _extract_word_aligned_tables(page: Any) -> list[list[list[str]]]:
    try:
        words = page.get_text("words")
    except Exception:
        return []
    if not words:
        return []

    line_groups: dict[tuple[int, int, int], list[tuple[float, str]]] = {}
    for word in words:
        x0, y0, _x1, _y1, text, block_no, line_no, *_ = word
        line_groups.setdefault((int(block_no), int(line_no), round(float(y0))), []).append((float(x0), str(text)))

    candidates: list[list[list[str]]] = []
    current: list[list[tuple[float, str]]] = []
    last_y: int | None = None
    for key, row in sorted(line_groups.items(), key=lambda item: item[0][2]):
        y = key[2]
        sorted_row = sorted(row, key=lambda item: item[0])
        if len(sorted_row) < 2:
            continue
        if last_y is None or y - last_y <= 28:
            current.append(sorted_row)
        else:
            _append_word_table_candidate(candidates, current)
            current = [sorted_row]
        last_y = y
    _append_word_table_candidate(candidates, current)
    return candidates


def _append_word_table_candidate(candidates: list[list[list[str]]], rows: list[list[tuple[float, str]]]) -> None:
    if len(rows) < 2:
        return
    anchors = sorted({round(x / 24) * 24 for row in rows for x, _ in row})
    if len(anchors) < 2:
        return
    table: list[list[str]] = []
    for row in rows:
        cells = [""] * len(anchors)
        for x, text in row:
            index = min(range(len(anchors)), key=lambda i: abs(anchors[i] - x))
            cells[index] = f"{cells[index]} {text}".strip()
        table.append(cells)
    cleaned = _clean_table(table)
    if cleaned:
        candidates.append(cleaned)


def _clean_table(rows: list[list[Any]]) -> list[list[str]]:
    cleaned: list[list[str]] = []
    for row in rows:
        cells = [_clean_table_cell(cell) for cell in row]
        while cells and not cells[-1]:
            cells.pop()
        if sum(1 for cell in cells if cell) >= 2:
            cleaned.append(cells)
    if len(cleaned) < 2:
        return []
    width = max(len(row) for row in cleaned)
    normalized = [row + [""] * (width - len(row)) for row in cleaned]
    return _drop_empty_edge_columns(normalized)


def _clean_table_cell(cell: Any) -> str:
    value = str(cell or "").strip()
    lines = [line.strip() for line in value.splitlines()]
    value = "\n".join(line for line in lines if not (len(line) == 1 and line.isalpha()))
    if len(value) == 1 and value.isalpha():
        return ""
    return value


def _drop_empty_edge_columns(rows: list[list[str]]) -> list[list[str]]:
    if not rows:
        return rows
    start = 0
    end = len(rows[0])
    while start < end and all(not row[start] for row in rows):
        start += 1
    while end > start and all(not row[end - 1] for row in rows):
        end -= 1
    trimmed = [row[start:end] for row in rows]
    if not trimmed or len(trimmed[0]) < 2:
        return []
    return trimmed


def _parse_image(path: Path, mime_type: str, *, ocr: str) -> Document:
    if ocr == "off":
        page = Page(number=1)
        return Document(
            source=str(path),
            mime_type=mime_type,
            pages=[page],
            metadata={"filename": path.name},
            warnings=["OCR disabled; image text was not extracted."],
            backend="image",
        )
    try:
        import pytesseract  # type: ignore[import-not-found]
        from PIL import Image  # type: ignore[import-not-found]
    except Exception as exc:
        raise DocpipeError(
            "Image OCR requires Pillow and pytesseract. Install with: pip install 'docpipe-core[ocr]'"
        ) from exc

    with Image.open(path) as image:
        text = pytesseract.image_to_string(image).strip()
    page = Page(number=1, text=text, blocks=[TextBlock(text=text, page=1, kind="ocr")] if text else [])
    return Document(
        source=str(path),
        mime_type=mime_type,
        pages=[page],
        metadata={"filename": path.name},
        warnings=[] if text else ["OCR produced no text."],
        backend="pytesseract",
    )


def _load_pymupdf():
    try:
        return importlib.import_module("pymupdf")
    except Exception:
        try:
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                return importlib.import_module("fitz")
        except Exception as exc:
            raise DocpipeError(
                "PDF parsing requires PyMuPDF. Install with: pip install 'docpipe-core[pdf]'"
            ) from exc


def _parse_docx(path: Path, mime_type: str) -> Document:
    try:
        import docx  # type: ignore[import-not-found]
    except Exception as exc:
        raise DocpipeError(
            "DOCX parsing requires python-docx. Install with: pip install 'docpipe-core[docx]'"
        ) from exc

    document = docx.Document(path)
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    text = "\n\n".join(paragraphs)
    page = Page(number=1, text=text, blocks=[TextBlock(text=t, page=1) for t in paragraphs])
    return Document(
        source=str(path),
        mime_type=mime_type,
        pages=[page],
        metadata={"filename": path.name},
        backend="python-docx",
    )
