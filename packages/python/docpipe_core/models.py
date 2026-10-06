from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union


BBox = tuple[float, float, float, float]


def _bbox_list(bbox: BBox | None) -> list[float] | None:
    if bbox is None:
        return None
    # Serialized to two decimal places; PDF coordinates are not meaningful beyond that precision.
    return [round(float(value), 2) for value in bbox]


def _bbox_tuple(value: Any) -> BBox | None:
    if value is None:
        return None
    x0, y0, x1, y1 = value
    return (float(x0), float(y0), float(x1), float(y1))


@dataclass
class Cell:
    text: str = ""
    page: int | None = None
    bbox: BBox | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "page": self.page, "bbox": _bbox_list(self.bbox)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Cell:
        return cls(text=data.get("text", ""), page=data.get("page"), bbox=_bbox_tuple(data.get("bbox")))


@dataclass
class TextBlock:
    text: str
    page: int
    kind: str = "text"
    bbox: BBox | None = None

    @property
    def type(self) -> str:
        return "text"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "text": self.text,
            "page": self.page,
            "kind": self.kind,
            "bbox": _bbox_list(self.bbox),
        }


@dataclass
class TableBlock:
    rows: list[list[Cell]]
    page: int
    bbox: BBox | None = None
    table_id: str = ""
    detection: str = "unknown"
    continued_from_previous_page: bool = False
    continues_on_next_page: bool = False
    repeated_header: bool = False

    @property
    def type(self) -> str:
        return "table"

    @property
    def grid(self) -> list[list[str]]:
        return [[cell.text for cell in row] for row in self.rows]

    @property
    def plain_text(self) -> str:
        return "\n".join(" | ".join(cell.text for cell in row) for row in self.rows if any(cell.text for cell in row))

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "table_id": self.table_id,
            "page": self.page,
            "bbox": _bbox_list(self.bbox),
            "detection": self.detection,
            "continued_from_previous_page": self.continued_from_previous_page,
            "continues_on_next_page": self.continues_on_next_page,
            "repeated_header": self.repeated_header,
            "rows": [[cell.to_dict() for cell in row] for row in self.rows],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TableBlock:
        return cls(
            rows=[[Cell.from_dict(cell) for cell in row] for row in data.get("rows", [])],
            page=data["page"],
            bbox=_bbox_tuple(data.get("bbox")),
            table_id=data.get("table_id", ""),
            detection=data.get("detection", "unknown"),
            continued_from_previous_page=data.get("continued_from_previous_page", False),
            continues_on_next_page=data.get("continues_on_next_page", False),
            repeated_header=data.get("repeated_header", False),
        )


Element = Union[TextBlock, TableBlock]


@dataclass
class Page:
    number: int
    text: str = ""
    elements: list[Element] = field(default_factory=list)
    width: float | None = None
    height: float | None = None

    @property
    def blocks(self) -> list[TextBlock]:
        return [element for element in self.elements if isinstance(element, TextBlock)]

    @property
    def tables(self) -> list[list[list[str]]]:
        return [element.grid for element in self.elements if isinstance(element, TableBlock)]

    def to_markdown(self) -> str:
        parts: list[str] = []
        for element in self.elements:
            if isinstance(element, TextBlock):
                if element.text.strip():
                    parts.append(element.text.strip())
            else:
                rendered = _table_to_markdown(element)
                if rendered:
                    parts.append(rendered)
        text = "\n\n".join(parts).strip() or self.text.strip()
        if not text:
            return ""
        return f"<!-- page:{self.number} -->\n\n{text}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "text": self.text,
            "width": self.width,
            "height": self.height,
            "blocks": [block.to_dict() for block in self.blocks],
            "tables": self.tables,
            "elements": [element.to_dict() for element in self.elements],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Page:
        return cls(
            number=data["number"],
            text=data.get("text", ""),
            elements=[_element_from_dict(item) for item in data.get("elements", [])],
            width=data.get("width"),
            height=data.get("height"),
        )


def _element_from_dict(data: dict[str, Any]) -> Element:
    if data.get("type") == "table":
        return TableBlock.from_dict(data)
    return TextBlock(
        text=data["text"],
        page=data["page"],
        kind=data.get("kind", "text"),
        bbox=_bbox_tuple(data.get("bbox")),
    )


def _table_to_markdown(table: TableBlock) -> str:
    grid = table.grid
    width = max((len(row) for row in grid), default=0)
    if width == 0:
        return ""
    rows = [row + [""] * (width - len(row)) for row in grid]
    if table.continued_from_previous_page and not table.repeated_header:
        # The continuation has no header of its own on this page; leave the header empty rather than invent one.
        header = [""] * width
        body = rows
    else:
        header = rows[0]
        body = rows[1:]
    separator = ["---"] * width
    rendered = [header, separator, *body]
    return "\n".join("| " + " | ".join(_escape_cell(cell) for cell in row) + " |" for row in rendered)


def _escape_cell(cell: str) -> str:
    return cell.replace("\n", " ").replace("|", "\\|").strip()


@dataclass
class Document:
    source: str
    mime_type: str
    pages: list[Page]
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    backend: str = "unknown"
    coordinates: dict[str, Any] | None = None

    @property
    def text(self) -> str:
        return "\n\n".join(page.text for page in self.pages if page.text).strip()

    @property
    def markdown(self) -> str:
        rendered = [page.to_markdown() for page in self.pages]
        return "\n\n---\n\n".join(page for page in rendered if page).strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "mime_type": self.mime_type,
            "backend": self.backend,
            "metadata": self.metadata,
            "warnings": self.warnings,
            "coordinates": self.coordinates,
            "text": self.text,
            "markdown": self.markdown,
            "pages": [page.to_dict() for page in self.pages],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Document:
        return cls(
            source=data["source"],
            mime_type=data["mime_type"],
            pages=[Page.from_dict(page) for page in data.get("pages", [])],
            metadata=data.get("metadata", {}),
            warnings=data.get("warnings", []),
            backend=data.get("backend", "unknown"),
            coordinates=data.get("coordinates"),
        )
