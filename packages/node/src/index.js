import { execFile } from "node:child_process";

function runDocpipe(args) {
  const python = process.env.DOCPIPE_PYTHON || "python3";
  return new Promise((resolve, reject) => {
    execFile(python, ["-m", "docpipe_core.cli", ...args], { maxBuffer: 100 * 1024 * 1024 }, (error, stdout, stderr) => {
      if (error) {
        error.stderr = stderr;
        reject(error);
        return;
      }
      resolve(stdout);
    });
  });
}

export async function parse(path, options = {}) {
  const ocr = options.ocr || "auto";
  const stdout = await runDocpipe([path, "--format", "json", "--ocr", ocr]);
  return JSON.parse(stdout);
}

export async function parseMarkdown(path, options = {}) {
  const ocr = options.ocr || "auto";
  return runDocpipe([path, "--format", "markdown", "--ocr", ocr]);
}
