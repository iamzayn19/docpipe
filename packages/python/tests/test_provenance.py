import json

import pytest

from docpipe_core import Document, TableBlock, TextBlock, parse
from docpipe_core import parser
from pdf_fixtures import borderless_table, table_spanning_pages, two_column


def _pdf(tmp_path, builder):
    pytest.importorskip("pymupdf")
    return builder(tmp_path)


def _elements(doc, page=0):
    return doc.pages[page].elements


def test_text_blocks_have_page_number_and_bbox(tmp_path):
    doc = parse(_pdf(tmp_path, two_column))

    texts = [e for e in _elements(doc) if isinstance(e, TextBlock)]
    assert texts, "expected text blocks from the fixture"
    for block in texts:
        assert block.page == 1
        assert block.bbox is not None
        x0, y0, x1, y1 = block.bbox
        assert 0 <= x0 < x1 <= doc.pages[0].width
        assert 0 <= y0 < y1 <= doc.pages[0].height


def test_page_dimensions_and_coordinate_contract_are_exposed(tmp_path):
    doc = parse(_pdf(tmp_path, two_column))

    assert doc.pages[0].width == 595.0
    assert doc.pages[0].height == 842.0
    assert doc.coordinates == {
        "backend": "pymupdf",
        "origin": "top-left",
        "units": "pt",
        "bbox": "[x0, y0, x1, y1]",
        "page_numbering": "1-based",
    }


def test_table_block_has_page_and_bbox(tmp_path):
    doc = parse(_pdf(tmp_path, table_spanning_pages))

    table = next(e for e in _elements(doc) if isinstance(e, TableBlock))
    assert table.page == 1
    assert table.bbox == pytest.approx((72.0, 700.0, 440.0, 784.0), abs=1.0)
    assert table.detection == "pymupdf-find-tables"


def test_table_cells_retain_page_and_bbox(tmp_path):
    doc = parse(_pdf(tmp_path, table_spanning_pages))

    table = next(e for e in _elements(doc) if isinstance(e, TableBlock))
    widget = table.rows[1][0]
    assert widget.text == "Widget"
    assert widget.page == 1
    assert widget.bbox == pytest.approx((72.0, 728.0, 200.0, 756.0), abs=1.0)
    amount = table.rows[1][2]
    assert amount.text == "$20"
    assert amount.bbox[0] == pytest.approx(320.0, abs=1.0)


def test_borderless_table_cells_have_bbox_from_word_positions(tmp_path):
    doc = parse(_pdf(tmp_path, borderless_table))

    table = next(e for e in _elements(doc) if isinstance(e, TableBlock))
    assert table.detection == "word-alignment"
    assert table.grid[1] == ["North", "12", "900"]
    for row in table.rows:
        for cell in row:
            assert cell.page == 1
            assert cell.bbox is not None


def test_text_inside_a_table_is_not_repeated_as_paragraphs(tmp_path):
    doc = parse(_pdf(tmp_path, table_spanning_pages))

    paragraph_texts = [b.text for b in doc.pages[0].blocks]
    assert "Widget" not in paragraph_texts
    assert "Page 1 footer" in paragraph_texts


def test_non_pdf_sources_report_no_bbox_and_no_coordinates(tmp_path):
    path = tmp_path / "note.txt"
    path.write_text("Hello", encoding="utf-8")

    doc = parse(path)

    assert doc.coordinates is None
    assert doc.pages[0].elements[0].bbox is None
    assert doc.pages[0].elements[0].page == 1


def test_provenance_serializes_and_deserializes_losslessly(tmp_path):
    doc = parse(_pdf(tmp_path, table_spanning_pages))

    payload = json.loads(json.dumps(doc.to_dict()))
    restored = Document.from_dict(payload)

    assert restored.to_dict() == doc.to_dict()
    restored_table = next(e for e in restored.pages[0].elements if isinstance(e, TableBlock))
    original_table = next(e for e in doc.pages[0].elements if isinstance(e, TableBlock))
    assert restored_table.rows[1][0].bbox == original_table.rows[1][0].bbox


def test_json_exposes_type_page_and_bbox_for_text_blocks(tmp_path):
    payload = parse(_pdf(tmp_path, two_column)).to_dict()

    block = payload["pages"][0]["elements"][0]
    assert block["type"] == "text"
    assert block["page"] == 1
    assert isinstance(block["bbox"], list) and len(block["bbox"]) == 4


def test_legacy_json_fields_are_still_present(tmp_path):
    payload = parse(_pdf(tmp_path, table_spanning_pages)).to_dict()

    page = payload["pages"][0]
    assert set(["number", "text", "blocks", "tables"]).issubset(page)
    assert page["tables"][0][0] == ["Item", "Qty", "Amount"]
    assert all(block["type"] == "text" for block in page["blocks"])


def test_word_fallback_does_not_turn_prose_into_a_table(tmp_path):
    pymupdf = pytest.importorskip("pymupdf")
    path = tmp_path / "prose.pdf"
    pdf = pymupdf.open()
    page = pdf.new_page()
    prose = (
        "The quick brown fox jumps over the lazy dog while the committee reviews the annual budget "
        "and considers several amendments proposed by members of the finance working group this quarter."
    )
    page.insert_textbox(pymupdf.Rect(72, 72, 523, 300), prose, fontsize=11)
    pdf.save(path)
    pdf.close()

    doc = parse(path)

    assert [e.type for e in doc.pages[0].elements] == ["text"]
    assert doc.pages[0].tables == []


def test_parser_module_still_exposes_block_types():
    assert parser.TextBlock is TextBlock
