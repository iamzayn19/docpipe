# Docpipe

Docpipe turns messy documents into clean Markdown and structured JSON from Python, Node.js, and Ruby.

It is local-first by default: digital PDFs are read as text, scanned/image inputs can use OCR when optional OCR tools are installed, and every result preserves page-level structure for search, RAG, citations, and app ingestion.

## Packages

- Python: `docpipe-core`
- Node.js: `@iamzayn19/docpipe`
- Ruby: `docpipe`

The Python package is the engine. The Node and Ruby packages are thin wrappers around the Python CLI so all three ecosystems produce the same JSON shape.
Set `DOCPIPE_PYTHON=/path/to/python` when the Python engine is installed in a virtualenv instead of the system `python3`.

## Features

- PDF text extraction with optional PyMuPDF support
- PDF table extraction into JSON and Markdown tables
- OCR fallback for image files when `pytesseract` and Tesseract are installed
- DOCX extraction when `python-docx` is installed
- Plain text and Markdown support
- Markdown and JSON output
- Page numbers, text blocks, tables, metadata, warnings, and parser backend details
- Citation-ready provenance: page numbers and bounding boxes for text blocks and table cells, with ordered reading across multi-column pages and table continuation across page breaks
- CLI, Python API, Node API, and Ruby API

## Python

```bash
pip install docpipe-core
docpipe invoice.pdf --format markdown
docpipe invoice.pdf --format json
```

```python
from docpipe_core import parse

doc = parse("invoice.pdf")
print(doc.markdown)
print(doc.pages[0].text)
```

## Node.js

```bash
npm install @iamzayn19/docpipe
```

```js
import { parse } from "@iamzayn19/docpipe";

const doc = await parse("invoice.pdf");
console.log(doc.markdown);
```

## Ruby

```bash
gem install docpipe
```

```ruby
require "docpipe"

doc = Docpipe.parse("invoice.pdf")
puts doc.markdown
```

## Citation-ready output

Every block in `pages[].elements` carries its source location, so generated answers can be traced back to the exact region of the PDF:

```json
{
  "type": "text",
  "text": "A1",
  "page": 1,
  "kind": "text",
  "bbox": [72.0, 108.18, 85.45, 123.29]
}
```

Tables keep provenance per cell:

```json
{
  "type": "table",
  "table_id": "table-1",
  "page": 2,
  "bbox": [72.0, 60.0, 440.0, 144.0],
  "detection": "pymupdf-find-tables",
  "continued_from_previous_page": true,
  "continues_on_next_page": false,
  "repeated_header": true,
  "rows": [
    [
      { "text": "Item", "page": 2, "bbox": [72.0, 60.0, 200.0, 88.0] },
      { "text": "Qty", "page": 2, "bbox": [200.0, 60.0, 320.0, 88.0] }
    ]
  ]
}
```

Bounding box conventions:

- `bbox` is `[x0, y0, x1, y1]`.
- The origin is the top-left of the page, with y increasing downward.
- Units are PDF points (1/72 inch), reported in `coordinates`. Use `pages[].width` and `pages[].height` to normalize.
- Page numbers are 1-based.
- `bbox` is `null` when the source has no layout (plain text, DOCX, OCR of images). Those sources report `page: 1` for compatibility, so check `bbox` before treating a location as real.
- Boxes come only from the PDF parser and are never estimated. Table cell boxes are the ruled cell rectangles when the table has ruling lines. For borderless tables they are the union of the cell's words, and `detection` says which method was used.

How the output is built: `pages[].elements` is the single ordered source for both JSON and Markdown. Reading order comes from a recursive XY-cut over block boxes. Vertical gutters are split first, so columns are read top to bottom one at a time. Full-width headings are read before the columns below them. Text inside a detected table is represented by the table's cells and is not repeated as paragraphs.

Tables that run across a page break are not merged on a guess. Two fragments are linked only when the first reaches the bottom of its page, the second starts at the top, and their column count and column edges agree. Linked fragments share a `table_id`, and `repeated_header` records whether the continuation repeats the header. Markdown renders each fragment as its own table. A continuation without a repeated header gets an empty header row rather than an invented one.

`pages[].blocks` and `pages[].tables` are kept for compatibility. They are views over `elements`.

Provenance supports RAG citations, source highlighting, traceability, extraction validation, and linking an answer back to the exact PDF region. It only locates text the parser found, so it does not validate the parser's own reading.

## Optional OCR

For OCR support:

```bash
pip install "docpipe-core[ocr]"
```

Install the native Tesseract binary too:

```bash
brew install tesseract
```

## Release

See [RELEASE.md](./RELEASE.md).
