import json
import subprocess
import sys

import pytest

from docpipe_core import parse
from docpipe_core import parser


def test_parse_text_file(tmp_path):
    path = tmp_path / "note.txt"
    path.write_text("Hello\n\nWorld", encoding="utf-8")

    doc = parse(path)

    assert doc.backend == "text"
    assert doc.text == "Hello\n\nWorld"
    assert "<!-- page:1 -->" in doc.markdown


def test_cli_json(tmp_path):
    path = tmp_path / "note.txt"
    path.write_text("Hello", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "docpipe_core.cli", str(path), "--format", "json"],
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(result.stdout)
    assert payload["text"] == "Hello"
    assert payload["pages"][0]["number"] == 1


def test_cli_pdf_json_is_not_prefixed_by_pymupdf_warnings(tmp_path):
    pymupdf = pytest.importorskip("pymupdf")
    path = tmp_path / "sample.pdf"
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Invoice total: $42.00")
    pdf.save(path)
    pdf.close()

    result = subprocess.run(
        [sys.executable, "-m", "docpipe_core.cli", str(path), "--format", "json"],
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(result.stdout)
    assert result.stdout.lstrip().startswith("{")
    assert payload["backend"] == "pymupdf"
    assert "Invoice total" in payload["text"]


def test_pdf_force_ocr_replaces_existing_text_layer(tmp_path, monkeypatch):
    pymupdf = pytest.importorskip("pymupdf")
    path = tmp_path / "text-layer.pdf"
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "bad text layer")
    pdf.save(path)
    pdf.close()

    monkeypatch.setattr(parser, "_ocr_pdf_page", lambda page: "clean ocr text")

    doc = parse(path, ocr="force")

    assert doc.text == "clean ocr text"
    assert doc.pages[0].blocks == [parser.TextBlock(text="clean ocr text", page=1, kind="ocr")]


def test_pdf_extracts_tables_into_json_and_markdown(tmp_path):
    pymupdf = pytest.importorskip("pymupdf")
    path = tmp_path / "table.pdf"
    pdf = pymupdf.open()
    page = pdf.new_page()
    xs = [72, 180, 320, 430]
    ys = [72, 108, 144, 180]
    for x in xs:
        page.draw_line((x, ys[0]), (x, ys[-1]))
    for y in ys:
        page.draw_line((xs[0], y), (xs[-1], y))
    rows = [
        ["Qty", "Service", "Total"],
        ["1", "Web Design", "$500"],
        ["2", "Hosting", "$40"],
    ]
    for row_index, row in enumerate(rows):
        for column_index, cell in enumerate(row):
            page.insert_text((xs[column_index] + 8, ys[row_index] + 22), cell)
    pdf.save(path)
    pdf.close()

    doc = parse(path)

    assert doc.pages[0].tables
    assert ["Qty", "Service", "Total"] in doc.pages[0].tables[0]
    assert ["1", "Web Design", "$500"] in doc.pages[0].tables[0]
    assert "| Qty | Service | Total |" in doc.markdown
