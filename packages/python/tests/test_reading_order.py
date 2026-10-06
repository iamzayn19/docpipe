import pytest

from docpipe_core import TextBlock, parse
from docpipe_core.layout import order_elements
from pdf_fixtures import two_column


def _texts(elements):
    return [e.text for e in elements if isinstance(e, TextBlock)]


def _box(x0, y0, x1, y1, text):
    return TextBlock(text=text, page=1, bbox=(x0, y0, x1, y1))


def test_two_columns_are_not_interleaved(tmp_path):
    pytest.importorskip("pymupdf")
    doc = parse(two_column(tmp_path))

    texts = _texts(doc.pages[0].elements)
    assert texts == [
        "Quarterly results across both columns",
        "A1",
        "A2",
        "A3",
        "B1",
        "B2",
        "B3",
    ]


def test_full_width_heading_precedes_both_columns(tmp_path):
    pytest.importorskip("pymupdf")
    doc = parse(two_column(tmp_path))

    texts = _texts(doc.pages[0].elements)
    assert texts[0] == "Quarterly results across both columns"


def test_markdown_follows_the_same_order_as_json(tmp_path):
    pytest.importorskip("pymupdf")
    doc = parse(two_column(tmp_path))

    json_order = [b["text"] for b in doc.to_dict()["pages"][0]["elements"]]
    markdown_lines = [line for line in doc.markdown.splitlines() if line.strip()]
    markdown_order = [line for line in markdown_lines if not line.startswith("<!--")]
    assert markdown_order == json_order


def test_page_text_follows_reading_order(tmp_path):
    pytest.importorskip("pymupdf")
    doc = parse(two_column(tmp_path))

    assert doc.pages[0].text.split("\n\n") == [
        "Quarterly results across both columns",
        "A1",
        "A2",
        "A3",
        "B1",
        "B2",
        "B3",
    ]


def test_xy_cut_reads_left_column_before_right_column():
    left = [_box(72, 100, 200, 115, "A1"), _box(72, 130, 200, 145, "A2")]
    right = [_box(330, 100, 460, 115, "B1"), _box(330, 130, 460, 145, "B2")]

    ordered = order_elements(right + left)

    assert _texts(ordered) == ["A1", "A2", "B1", "B2"]


def test_xy_cut_keeps_full_width_heading_above_columns():
    heading = _box(72, 40, 523, 70, "Heading")
    left = [_box(72, 100, 200, 115, "A1"), _box(72, 130, 200, 145, "A2")]
    right = [_box(330, 100, 460, 115, "B1"), _box(330, 130, 460, 145, "B2")]

    ordered = order_elements([*right, heading, *left])

    assert _texts(ordered) == ["Heading", "A1", "A2", "B1", "B2"]


def test_xy_cut_keeps_stacked_paragraphs_top_to_bottom():
    blocks = [_box(72, 300, 523, 320, "third"), _box(72, 100, 523, 120, "first"), _box(72, 200, 523, 220, "second")]

    assert _texts(order_elements(blocks)) == ["first", "second", "third"]


def test_marginal_item_is_not_treated_as_a_column():
    body = [_box(72, 100, 500, 115, "body one"), _box(72, 130, 500, 145, "body two")]
    header_right = [_box(480, 30, 520, 45, "header")]

    ordered = order_elements([*body, *header_right])

    assert _texts(ordered) == ["header", "body one", "body two"]


def test_items_without_bbox_keep_their_order():
    blocks = [TextBlock(text="b", page=1), TextBlock(text="a", page=1)]

    assert order_elements(blocks) == blocks
