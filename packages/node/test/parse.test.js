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
