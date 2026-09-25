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
