from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TextBlock:
    text: str
    page: int
    kind: str = "text"
    bbox: tuple[float, float, float, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Page:
    number: int
    text: str = ""
    blocks: list[TextBlock] = field(default_factory=list)
    tables: list[list[list[str]]] = field(default_factory=list)

    def to_markdown(self) -> str:
        parts = [block.text.strip() for block in self.blocks if block.text.strip()]
        text = "\n\n".join(parts).strip() or self.text.strip()
        if not text:
            return ""
        return f"<!-- page:{self.number} -->\n\n{text}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "text": self.text,
            "blocks": [block.to_dict() for block in self.blocks],
            "tables": self.tables,
        }


@dataclass
class Document:
    source: str
    mime_type: str
    pages: list[Page]
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    backend: str = "unknown"

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
            "text": self.text,
            "markdown": self.markdown,
            "pages": [page.to_dict() for page in self.pages],
        }
