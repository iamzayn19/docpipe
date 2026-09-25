from __future__ import annotations

import argparse
import json
import sys

from .parser import DocpipeError, parse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="docpipe", description="Parse documents to Markdown or JSON.")
    parser.add_argument("path", help="File to parse")
    parser.add_argument("--format", choices=["json", "markdown", "text"], default="json")
    parser.add_argument("--ocr", choices=["auto", "force", "off"], default="auto")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        doc = parse(args.path, ocr=args.ocr)
    except (DocpipeError, OSError) as exc:
        print(f"docpipe: {exc}", file=sys.stderr)
        return 1

    if args.format == "markdown":
        print(doc.markdown)
    elif args.format == "text":
        print(doc.text)
    else:
        indent = 2 if args.pretty else None
        print(json.dumps(doc.to_dict(), ensure_ascii=False, indent=indent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
