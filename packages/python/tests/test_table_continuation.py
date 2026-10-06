import pytest

from docpipe_core import TableBlock, parse
from pdf_fixtures import table_spanning_pages, table_with_mismatched_continuation


def _tables(doc):
    return [(page.number, e) for page in doc.pages for e in page.elements if isinstance(e, TableBlock)]


def test_continued_table_is_linked_with_a_shared_id(tmp_path):
    pytest.importorskip("pymupdf")
    doc = parse(table_spanning_pages(tmp_path))

    (_, first), (_, second) = _tables(doc)
    assert first.table_id == second.table_id
    assert first.continues_on_next_page is True
    assert first.continued_from_previous_page is False
    assert second.continued_from_previous_page is True
    assert second.continues_on_next_page is False


def test_repeated_header_is_detected_and_kept_in_json(tmp_path):
    pytest.importorskip("pymupdf")
    doc = parse(table_spanning_pages(tmp_path))

    (_, _), (_, second) = _tables(doc)
    assert second.repeated_header is True
    assert second.grid[0] == ["Item", "Qty", "Amount"]


def test_rows_stay_in_their_columns_across_the_page_break(tmp_path):
    pytest.importorskip("pymupdf")
    doc = parse(table_spanning_pages(tmp_path))

    (_, first), (_, second) = _tables(doc)
    for table in (first, second):
        assert all(len(row) == 3 for row in table.rows)
    assert second.grid[1] == ["Gizmo", "1", "$10"]
    assert second.grid[2] == ["Doohickey", "3", "$30"]
    columns_first = [cell.bbox[0] for cell in first.rows[0]]
    columns_second = [cell.bbox[0] for cell in second.rows[0]]
    assert columns_first == pytest.approx(columns_second, abs=3.0)


def test_each_row_keeps_its_own_page_provenance(tmp_path):
    pytest.importorskip("pymupdf")
    doc = parse(table_spanning_pages(tmp_path))

    (_, first), (_, second) = _tables(doc)
    assert {cell.page for row in first.rows for cell in row} == {1}
    assert {cell.page for row in second.rows for cell in row} == {2}
    assert second.page == 2
    assert second.bbox[1] < 100


def test_paragraph_after_continuation_is_not_attached_to_the_table(tmp_path):
    pytest.importorskip("pymupdf")
    doc = parse(table_spanning_pages(tmp_path))

    page_two = doc.pages[1]
    assert [b.text for b in page_two.blocks] == ["Notes after the table"]
    assert all("Notes" not in cell.text for row in _tables(doc)[1][1].rows for cell in row)


def test_markdown_renders_each_fragment_with_its_own_header(tmp_path):
    pytest.importorskip("pymupdf")
    doc = parse(table_spanning_pages(tmp_path))

    assert doc.markdown.count("| Item | Qty | Amount |") == 2
    assert "| Gizmo | 1 | $10 |" in doc.markdown
    assert "| Doohickey | 3 | $30 |" in doc.markdown
    assert "| Widget | 2 | $20 |" in doc.markdown


def test_continuation_without_repeated_header_gets_an_empty_header_in_markdown(tmp_path):
    pytest.importorskip("pymupdf")
    from pdf_fixtures import table_spanning_pages as build

    doc = parse(build(tmp_path, repeated_header=False))

    (_, _), (_, second) = _tables(doc)
    assert second.continued_from_previous_page is True
    assert second.repeated_header is False
    assert second.grid[0] == ["Gizmo", "1", "$10"]
    assert "|  |  |  |\n| --- | --- | --- |\n| Gizmo | 1 | $10 |" in doc.markdown


def test_mismatched_columns_are_not_merged(tmp_path):
    pytest.importorskip("pymupdf")
    doc = parse(table_with_mismatched_continuation(tmp_path))

    (_, first), (_, second) = _tables(doc)
    assert first.table_id != second.table_id
    assert first.continues_on_next_page is False
    assert second.continued_from_previous_page is False
    assert second.grid == [["Code", "Note"], ["A-1", "Shipped"]]
