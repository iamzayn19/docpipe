"""Deterministic PDF fixtures generated with PyMuPDF.

Each builder writes its PDF into the given directory and returns the path. Content is placed with explicit
coordinates, and blocks are drawn in a deliberately unhelpful order, so a parser that just follows the content
stream produces the wrong reading order.
"""

from pathlib import Path


def _pymupdf():
    import pymupdf

    return pymupdf


def _draw_grid(page, xs, ys):
    for x in xs:
        page.draw_line((x, ys[0]), (x, ys[-1]))
    for y in ys:
        page.draw_line((xs[0], y), (xs[-1], y))


def _write_rows(page, xs, ys, rows, size=11):
    for row_index, row in enumerate(rows):
        baseline = ys[row_index] + (ys[row_index + 1] - ys[row_index]) / 2 + size / 3
        for column_index, cell in enumerate(row):
            if cell:
                page.insert_text((xs[column_index] + 6, baseline), cell, fontsize=size)


def two_column(directory: Path) -> Path:
    """Full-width heading, then A1-A3 in the left column and B1-B3 in the right column.

    Blocks are inserted right column first, so content-stream order is B1..B3 before A1..A3.
    """
    pymupdf = _pymupdf()
    path = directory / "two-column.pdf"
    pdf = pymupdf.open()
    page = pdf.new_page()
    for index, text in enumerate(["B1", "B2", "B3"]):
        page.insert_text((330, 120 + index * 30), text, fontsize=11)
    for index, text in enumerate(["A1", "A2", "A3"]):
        page.insert_text((72, 120 + index * 30), text, fontsize=11)
    page.insert_textbox(
        pymupdf.Rect(72, 60, 523, 92),
        "Quarterly results across both columns",
        fontsize=16,
        align=0,
    )
    pdf.save(path)
    pdf.close()
    return path


def table_spanning_pages(directory: Path, *, repeated_header: bool = True) -> Path:
    """A three-column table that runs from the bottom of page 1 onto the top of page 2.

    Page 2 repeats the header when repeated_header is True. A paragraph sits below the continuation so
    tests can confirm it is not attached to the table.
    """
    pymupdf = _pymupdf()
    path = directory / ("table-repeated-header.pdf" if repeated_header else "table-no-header.pdf")
    pdf = pymupdf.open()

    first = pdf.new_page()
    xs = [72, 200, 320, 440]
    first_ys = [700, 728, 756, 784]
    _draw_grid(first, xs, first_ys)
    _write_rows(
        first,
        xs,
        first_ys,
        [["Item", "Qty", "Amount"], ["Widget", "2", "$20"], ["Gadget", "5", "$50"]],
    )
    first.insert_text((72, 810), "Page 1 footer", fontsize=9)

    second = pdf.new_page()
    second_ys = [60, 88, 116, 144]
    _draw_grid(second, xs, second_ys)
    rows = [["Gizmo", "1", "$10"], ["Doohickey", "3", "$30"]]
    if repeated_header:
        rows = [["Item", "Qty", "Amount"], *rows]
    _write_rows(second, xs, second_ys[: len(rows) + 1], rows)
    second.insert_text((72, 320), "Notes after the table", fontsize=11)

    pdf.save(path)
    pdf.close()
    return path


def table_with_mismatched_continuation(directory: Path) -> Path:
    """Page 1 ends with a three-column table. Page 2 starts with a two-column table at a different x position.

    The two tables must not be linked, because the column structure does not agree.
    """
    pymupdf = _pymupdf()
    path = directory / "table-mismatch.pdf"
    pdf = pymupdf.open()

    first = pdf.new_page()
    xs = [72, 200, 320, 440]
    ys = [700, 728, 756, 784]
    _draw_grid(first, xs, ys)
    _write_rows(first, xs, ys, [["Item", "Qty", "Amount"], ["Widget", "2", "$20"], ["Gadget", "5", "$50"]])

    second = pdf.new_page()
    xs2 = [72, 300, 440]
    ys2 = [60, 88, 116]
    _draw_grid(second, xs2, ys2)
    _write_rows(second, xs2, ys2, [["Code", "Note"], ["A-1", "Shipped"]])

    pdf.save(path)
    pdf.close()
    return path


def borderless_table(directory: Path) -> Path:
    """A table with no ruling lines, which exercises the word-alignment fallback."""
    pymupdf = _pymupdf()
    path = directory / "borderless.pdf"
    pdf = pymupdf.open()
    page = pdf.new_page()
    columns = [72, 240, 380]
    rows = [["Region", "Units", "Revenue"], ["North", "12", "900"], ["South", "7", "450"], ["West", "9", "610"]]
    for row_index, row in enumerate(rows):
        y = 120 + row_index * 22
        for column_index, cell in enumerate(row):
            page.insert_text((columns[column_index], y), cell, fontsize=11)
    pdf.save(path)
    pdf.close()
    return path
