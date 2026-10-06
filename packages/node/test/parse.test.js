import assert from "node:assert/strict";
import { mkdtemp, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { test } from "node:test";

test("exports parse functions", async () => {
  const mod = await import("../src/index.js");
  assert.equal(typeof mod.parse, "function");
  assert.equal(typeof mod.parseMarkdown, "function");
});

test("uses DOCPIPE_PYTHON override", async () => {
  const dir = await mkdtemp(join(tmpdir(), "docpipe-node-"));
  const python = join(dir, "python");
  await writeFile(
    python,
    `#!/bin/sh
if [ "$5" = "markdown" ]; then
  printf 'Hello markdown'
else
  printf '{"text":"Hello json","markdown":"Hello json","pages":[{"number":1,"tables":[]}]}'
fi
`,
    { mode: 0o755 },
  );
  const original = process.env.DOCPIPE_PYTHON;
  process.env.DOCPIPE_PYTHON = python;
  try {
    const mod = await import("../src/index.js");
    const doc = await mod.parse("sample.pdf");
    const markdown = await mod.parseMarkdown("sample.pdf");
    assert.equal(doc.text, "Hello json");
    assert.equal(markdown, "Hello markdown");
  } finally {
    if (original === undefined) {
      delete process.env.DOCPIPE_PYTHON;
    } else {
      process.env.DOCPIPE_PYTHON = original;
    }
  }
});

test("passes provenance through unchanged", async () => {
  const dir = await mkdtemp(join(tmpdir(), "docpipe-node-"));
  const python = join(dir, "python");
  const payload = {
    coordinates: { backend: "pymupdf", origin: "top-left", units: "pt", bbox: "[x0, y0, x1, y1]", page_numbering: "1-based" },
    pages: [
      {
        number: 1,
        text: "Heading",
        width: 595,
        height: 842,
        blocks: [{ type: "text", text: "Heading", page: 1, kind: "text", bbox: [72, 60, 300, 82] }],
        tables: [[["Item", "Qty"], ["Widget", "2"]]],
        elements: [
          { type: "text", text: "Heading", page: 1, kind: "text", bbox: [72, 60, 300, 82] },
          {
            type: "table",
            table_id: "table-1",
            page: 1,
            bbox: [72, 100, 300, 140],
            detection: "pymupdf-find-tables",
            continued_from_previous_page: false,
            continues_on_next_page: true,
            repeated_header: false,
            rows: [
              [
                { text: "Item", page: 1, bbox: [72, 100, 200, 120] },
                { text: "Qty", page: 1, bbox: [200, 100, 300, 120] },
              ],
            ],
          },
        ],
      },
    ],
  };
  await writeFile(
    python,
    `#!/bin/sh
printf '%s' '${JSON.stringify(payload)}'
`,
    { mode: 0o755 },
  );
  const original = process.env.DOCPIPE_PYTHON;
  process.env.DOCPIPE_PYTHON = python;
  try {
    const mod = await import("../src/index.js");
    const doc = await mod.parse("sample.pdf");
    assert.deepEqual(doc, payload);
    const table = doc.pages[0].elements[1];
    assert.equal(table.table_id, "table-1");
    assert.deepEqual(table.rows[0][1].bbox, [200, 100, 300, 120]);
  } finally {
    if (original === undefined) {
      delete process.env.DOCPIPE_PYTHON;
    } else {
      process.env.DOCPIPE_PYTHON = original;
    }
  }
});
