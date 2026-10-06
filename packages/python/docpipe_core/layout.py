from __future__ import annotations

from typing import Sequence

from .models import Element, Page, TableBlock


# Minimum whitespace, in PDF points, that separates two regions.
GUTTER = 10.0
# Distance from the top or bottom page edge, in PDF points, within which a table is treated as running off the page.
EDGE_MARGIN = 72.0
# Tolerance, in PDF points, when comparing column edges across pages.
COLUMN_TOLERANCE = 3.0


def order_elements(items: Sequence[Element]) -> list[Element]:
    """Return elements in reading order using recursive XY-cut over their bounding boxes.

    Vertical gutters are tried first so that columns are read top-to-bottom one at a time. A horizontal
    separator is used when no gutter divides the region, which keeps full-width headings ahead of the columns
    beneath them. Items without bounding boxes keep their original order.
    """
    if any(item.bbox is None for item in items):
        return list(items)
    return _xy_cut(list(items))


def _xy_cut(items: list[Element]) -> list[Element]:
    if len(items) < 2:
        return list(items)
    # Each attempt is (axis, minimum items per side). Axis 0 splits left/right, axis 1 splits top/bottom.
    # Requiring two items on each side for a column split stops a lone marginal item, such as a page
    # number, from being treated as a column.
    for axis, min_side in ((0, 2), (1, 1), (0, 1)):
        parts = _split(items, axis, min_side)
        if parts is not None:
            first, second = parts
            return _xy_cut(first) + _xy_cut(second)
    return sorted(items, key=lambda item: (item.bbox[1], item.bbox[0]))


def _split(items: list[Element], axis: int, min_side: int) -> tuple[list[Element], list[Element]] | None:
    low, high = axis, axis + 2
    ordered = sorted(items, key=lambda item: item.bbox[low])
    reach = ordered[0].bbox[high]
    for index in range(1, len(ordered)):
        if ordered[index].bbox[low] - reach >= GUTTER and index >= min_side and len(ordered) - index >= min_side:
            return ordered[:index], ordered[index:]
        reach = max(reach, ordered[index].bbox[high])
    return None


def link_table_fragments(pages: Sequence[Page]) -> None:
    """Assign table ids and mark tables that continue across a page break.

    Two fragments are linked only when the earlier one reaches the bottom edge of its page, the later one
    starts at the top edge, and their column count and column edges agree. Anything else stays a separate table,
    so a fragment is never merged on a guess.
    """
    counter = 0
    previous: tuple[Page, TableBlock] | None = None
    for page in pages:
        tables = [element for element in page.elements if isinstance(element, TableBlock)]
        for table in tables:
            counter += 1
            table.table_id = f"table-{counter}"

        if previous is not None and tables:
            previous_page, previous_table = previous
            candidate = tables[0]
            if _continues(previous_page, previous_table, page, candidate):
                candidate.table_id = previous_table.table_id
                candidate.continued_from_previous_page = True
                candidate.repeated_header = _same_first_row(previous_table, candidate)
                previous_table.continues_on_next_page = True

        previous = (page, tables[-1]) if tables else None


def _continues(previous_page: Page, previous: TableBlock, page: Page, candidate: TableBlock) -> bool:
    if previous.bbox is None or candidate.bbox is None or previous_page.height is None:
        return False
    if previous.bbox[3] < previous_page.height - EDGE_MARGIN:
        return False
    if candidate.bbox[1] > EDGE_MARGIN:
        return False
    if _width(previous) != _width(candidate) or not previous.rows or not candidate.rows:
        return False
    return _columns_align(previous.rows[0], candidate.rows[0])


def _columns_align(first: list, second: list) -> bool:
    for left, right in zip(first, second):
        if left.bbox is None or right.bbox is None:
            continue
        if abs(left.bbox[0] - right.bbox[0]) > COLUMN_TOLERANCE:
            return False
    return True


def _same_first_row(previous: TableBlock, candidate: TableBlock) -> bool:
    first = previous.grid[0] if previous.grid else []
    second = candidate.grid[0] if candidate.grid else []
    return bool(first) and any(first) and first == second


def _width(table: TableBlock) -> int:
    return max((len(row) for row in table.rows), default=0)
