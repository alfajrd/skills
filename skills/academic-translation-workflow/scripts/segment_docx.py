"""
Usage: python segment_docx.py <source.docx> <output_segments.json> [--client NAME]

Reads an Indonesian source .docx and produces a segments.json draft:
one row per sentence for running prose, one row per paragraph/cell for
headings/captions/list items/bibliography entries/table cells, plus any
real footnotes found.

This output is a DRAFT. Before translating, skim it for sentence-splitter
mistakes (common around abbreviations like "dkk.", "dll.", initials, or
unusual punctuation) and merge/fix rows as needed - the rest of the
pipeline just trusts whatever rows are in the JSON you hand it next.
"""
import sys
import json
import argparse
from pathlib import Path

from docx import Document
from docx_utils import iter_units, classify_paragraph, split_sentences, extract_footnotes


def build_segments(docx_path, client=None):
    doc = Document(docx_path)
    rows = []
    in_bibliography = False

    for unit_id, kind, paragraph in iter_units(doc):
        ptype = classify_paragraph(paragraph, in_bibliography)
        if ptype == "empty":
            continue
        if ptype == "heading_starts_bibliography":
            in_bibliography = True
            ptype = "heading"

        text = paragraph.text.strip()

        if kind == "table_cell_para":
            ptype = "table_cell"

        if ptype in ("body", "quote") and kind == "body_para":
            for i, sentence in enumerate(split_sentences(text)):
                rows.append({
                    "id": f"{unit_id}.s{i}",
                    "type": ptype,
                    "source": sentence,
                    "proposed": "",
                    "final": "",
                })
        else:
            # headings, captions, list items, bibliography entries, and all
            # table cells are kept as one row each - splitting them further
            # rarely makes sense and risks losing structure on rebuild.
            rows.append({
                "id": f"{unit_id}.s0",
                "type": ptype,
                "source": text,
                "proposed": "",
                "final": "",
            })

    for fid, text in extract_footnotes(docx_path):
        if not text:
            continue
        rows.append({
            "id": f"fn{fid}.s0",
            "type": "footnote",
            "source": text,
            "proposed": "",
            "final": "",
        })

    return {
        "source_file": str(Path(docx_path).name),
        "client": client,
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_docx")
    parser.add_argument("output_json")
    parser.add_argument("--client", default=None)
    args = parser.parse_args()

    segments = build_segments(args.source_docx, client=args.client)
    Path(args.output_json).write_text(
        json.dumps(segments, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Wrote {len(segments['rows'])} rows to {args.output_json}")
    type_counts = {}
    for r in segments["rows"]:
        type_counts[r["type"]] = type_counts.get(r["type"], 0) + 1
    print("Row types:", type_counts)


if __name__ == "__main__":
    main()
