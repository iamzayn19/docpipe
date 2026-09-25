#!/usr/bin/env node
import { parse, parseMarkdown } from "./index.js";

const [path, format = "json"] = process.argv.slice(2);

if (!path) {
  console.error("Usage: docpipe-js <path> [json|markdown]");
  process.exit(1);
}

try {
  if (format === "markdown") {
    process.stdout.write(await parseMarkdown(path));
  } else {
    console.log(JSON.stringify(await parse(path), null, 2));
  }
} catch (error) {
  console.error(error.stderr || error.message);
  process.exit(1);
}
