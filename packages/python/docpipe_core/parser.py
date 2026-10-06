from __future__ import annotations

import mimetypes
from contextlib import redirect_stderr, redirect_stdout
import importlib
import io
from pathlib import Path
from typing import Any

from .layout import link_table_fragments, order_elements
from .models import BBox, Cell, Document, Element, Page, TableBlock, TextBlock


TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".rst", ".csv", ".json", ".xml", ".html"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}

PDF_COORDINATES: dict[str, Any] = {
    "backend": "pymupdf",
    "origin": "top-left",
    "units": "pt",
    "bbox": "[x0, y0, x1, y1]",
    "page_numbering": "1-based",
}


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

    block = TextBlock(text=text, page=1)
    page = Page(number=1, text=text, elements=[block])
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
    has_bbox = False
    with fitz.open(path) as pdf:
        metadata = {k: v for k, v in (pdf.metadata or {}).items() if v}
        for index, raw_page in enumerate(pdf, start=1):
            text_blocks: list[TextBlock] = []
            for block in raw_page.get_text("blocks"):
                x0, y0, x1, y1, text, *_ = block
                if text.strip():
                    text_blocks.append(
                        TextBlock(text=text.strip(), page=index, bbox=(float(x0), float(y0), float(x1), float(y1)))
                    )
            tables = _extract_pdf_tables(raw_page, index)
            has_text_layer = bool(text_blocks)

            ocr_used = False
            if ocr == "force" or (not has_text_layer and ocr == "auto"):
                ocr_text = _ocr_pdf_page(raw_page)
                if ocr_text:
                    text_blocks = [TextBlock(text=ocr_text, page=index, kind="ocr")]
                    ocr_used = True
                elif not has_text_layer:
                    warnings.append(f"Page {index} had no extractable text and OCR produced no text.")
            if not ocr_used:
                # Text inside a detected table is represented by that table's cells, not repeated as paragraphs.
                text_blocks = [b for b in text_blocks if not _inside_any(b.bbox, tables)]

            elements = order_elements([*text_blocks, *tables])
            has_bbox = has_bbox or any(element.bbox is not None for element in elements)
            page_text = "\n\n".join(_plain_text(element) for element in elements).strip()
            pages.append(
                Page(
                    number=index,
                    text=page_text,
                    elements=elements,
                    width=float(raw_page.rect.width),
                    height=float(raw_page.rect.height),
                )
            )

    link_table_fragments(pages)
    return Document(
        source=str(path),
        mime_type=mime_type,
        pages=pages,
        metadata={"filename": path.name, **metadata},
        warnings=warnings,
        backend="pymupdf",
        coordinates=dict(PDF_COORDINATES) if has_bbox else None,
    )


def _plain_text(element: Element) -> str:
    if isinstance(element, TextBlock):
        return element.text
    return element.plain_text


def _inside_any(bbox: BBox | None, tables: list[TableBlock], tolerance: float = 1.0) -> bool:
    if bbox is None:
        return False
    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2
    for table in tables:
        if table.bbox is None:
            continue
        x0, y0, x1, y1 = table.bbox
        if x0 - tolerance <= cx <= x1 + tolerance and y0 - tolerance <= cy <= y1 + tolerance:
            return True
    return False


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


def _extract_pdf_tables(page: Any, page_number: int) -> list[TableBlock]:
    native_tables = _extract_native_pdf_tables(page, page_number)
    if native_tables:
        return native_tables
    return _extract_word_aligned_tables(page, page_number)


def _extract_native_pdf_tables(page: Any, page_number: int) -> list[TableBlock]:
    if not hasattr(page, "find_tables"):
        return []
    try:
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            result = page.find_tables()
    except Exception:
        return []

    tables: list[TableBlock] = []
    for table in getattr(result, "tables", []):
        try:
            grid = table.extract()
            layout_rows = table.rows
        except Exception:
            continue
        rows: list[list[Cell]] = []
        for row_index, values in enumerate(grid):
            cell_boxes = layout_rows[row_index].cells if row_index < len(layout_rows) else []
            row: list[Cell] = []
            for column_index, value in enumerate(values):
                box = cell_boxes[column_index] if column_index < len(cell_boxes) else None
                row.append(Cell(text=str(value or ""), page=page_number, bbox=_bbox_or_none(box)))
            rows.append(row)
        cleaned = _clean_table(rows)
        if cleaned:
            tables.append(
                TableBlock(
                    rows=cleaned,
                    page=page_number,
                    bbox=_bbox_or_none(table.bbox),
                    detection="pymupdf-find-tables",
                )
            )
    return tables


Word = tuple[float, float, float, float, str]

# Horizontal whitespace, in PDF points, that separates two cells in a borderless table. Ordinary word spacing is
# well under this, so prose lines split into a single segment and are never mistaken for table rows.
CELL_GAP = 12.0


def _extract_word_aligned_tables(page: Any, page_number: int) -> list[TableBlock]:
    try:
        words = page.get_text("words")
    except Exception:
        return []
    if not words:
        return []

    # Words are grouped by visual row, not by PDF block or line: borderless tables often place each cell in its own block.
    line_groups: dict[int, list[Word]] = {}
    for word in words:
        x0, y0, x1, y1, text, *_ = word
        line_groups.setdefault(round(float(y0)), []).append((float(x0), float(y0), float(x1), float(y1), str(text)))

    candidates: list[TableBlock] = []
    current: list[list[list[Word]]] = []
    last_y: int | None = None
    for y, row in sorted(line_groups.items(), key=lambda item: item[0]):
        segments = _row_segments(row)
        if len(segments) < 2:
            continue
        if last_y is None or y - last_y <= 28:
            current.append(segments)
        else:
            _append_word_table_candidate(candidates, current, page_number)
            current = [segments]
        last_y = y
    _append_word_table_candidate(candidates, current, page_number)
    return candidates


def _row_segments(row: list[Word]) -> list[list[Word]]:
    segments: list[list[Word]] = []
    for word in sorted(row, key=lambda item: item[0]):
        if segments and word[0] - segments[-1][-1][2] < CELL_GAP:
            segments[-1].append(word)
        else:
            segments.append([word])
    return segments


def _append_word_table_candidate(candidates: list[TableBlock], rows: list[list[list[Word]]], page_number: int) -> None:
    if len(rows) < 2:
        return
    anchors = sorted({round(segment[0][0] / 24) * 24 for row in rows for segment in row})
    if len(anchors) < 2:
        return
    table_rows: list[list[Cell]] = []
    for row in rows:
        cells: list[list[Word]] = [[] for _ in anchors]
        for segment in row:
            index = min(range(len(anchors)), key=lambda i: abs(anchors[i] - segment[0][0]))
            cells[index].extend(segment)
        table_rows.append([_cell_from_words(words, page_number) for words in cells])
    cleaned = _clean_table(table_rows)
    if not cleaned:
        return
    bbox = _union([cell.bbox for row in cleaned for cell in row if cell.bbox is not None])
    candidates.append(TableBlock(rows=cleaned, page=page_number, bbox=bbox, detection="word-alignment"))


def _cell_from_words(words: list[Word], page_number: int) -> Cell:
    if not words:
        return Cell(text="", page=page_number, bbox=None)
    text = " ".join(word[4] for word in words)
    bbox = _union([(word[0], word[1], word[2], word[3]) for word in words])
    return Cell(text=text, page=page_number, bbox=bbox)


def _union(boxes: list[BBox]) -> BBox | None:
    if not boxes:
        return None
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _bbox_or_none(value: Any) -> BBox | None:
    if value is None:
        return None
    x0, y0, x1, y1 = value
    return (float(x0), float(y0), float(x1), float(y1))


def _clean_table(rows: list[list[Cell]]) -> list[list[Cell]]:
    cleaned: list[list[Cell]] = []
    for row in rows:
        cells = [_clean_cell(cell) for cell in row]
        while cells and not cells[-1].text:
            cells.pop()
        if sum(1 for cell in cells if cell.text) >= 2:
            cleaned.append(cells)
    if len(cleaned) < 2:
        return []
    width = max(len(row) for row in cleaned)
    normalized = [row + [Cell() for _ in range(width - len(row))] for row in cleaned]
    return _drop_empty_edge_columns(normalized)


def _clean_cell(cell: Cell) -> Cell:
    value = cell.text.strip()
    lines = [line.strip() for line in value.splitlines()]
    value = "\n".join(line for line in lines if not (len(line) == 1 and line.isalpha()))
    if len(value) == 1 and value.isalpha():
        value = ""
    return Cell(text=value, page=cell.page, bbox=cell.bbox)


def _drop_empty_edge_columns(rows: list[list[Cell]]) -> list[list[Cell]]:
    if not rows:
        return rows
    start = 0
    end = len(rows[0])
    while start < end and all(not row[start].text for row in rows):
        start += 1
    while end > start and all(not row[end - 1].text for row in rows):
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
    elements: list[Element] = [TextBlock(text=text, page=1, kind="ocr")] if text else []
    page = Page(number=1, text=text, elements=elements)
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
    page = Page(
        number=1,
        text=text,
        elements=[TextBlock(text=t, page=1) for t in paragraphs],
    )
    return Document(
        source=str(path),
        mime_type=mime_type,
        pages=[page],
        metadata={"filename": path.name},
        backend="python-docx",
    )
