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
