import assert from "node:assert/strict";
import { test } from "node:test";

test("exports parse functions", async () => {
  const mod = await import("../src/index.js");
  assert.equal(typeof mod.parse, "function");
  assert.equal(typeof mod.parseMarkdown, "function");
});
