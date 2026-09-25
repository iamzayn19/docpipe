import json
import subprocess
import sys

from docpipe_core import parse


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
