"""
Usage: python rebuild_final_docx.py <original_source.docx> <reviewed.json> <output_final.docx>

Produces the final English deliverable by editing a copy of the ORIGINAL
source document in place: each translated paragraph/cell's runs are
replaced with the resolved English text (see docx_utils.apply_translated_text),
but paragraph-level formatting (style, alignment, spacing, numbering),
images, headers/footers, and every part of the document this pipeline never
touches are left completely alone. This is what gives exact fidelity to the
source's margins/fonts/colors/layout - we are NOT generating a new document
from scratch.

Reference-manager in-text citations (Zotero/Mendeley/EndNote "Insert
Citation" fields) are preserved as live fields rather than flattened to
plain text, as long as translation left the citation's own visible text
(e.g. "(Bhambra, 2021)") unchanged - see docx_utils.iter_field_spans /
apply_translated_text.

Row ids in reviewed.json must match ids produced by segment_docx.py against
this SAME original file (same paragraph/table structure) - that's what lets
each translated row find its way back to the exact right paragraph.
"""
import json
import argparse
from pathlib import Path

from docx import Document
from docx_utils import iter_units, apply_translated_text, write_footnotes


def parse_row_id(row_id):
    unit_id, _, suffix = row_id.rpartition(".s")
    return unit_id, int(suffix)


def rebuild(source_docx, reviewed_json_path, output_docx):
    reviewed = json.loads(Path(reviewed_json_path).read_text(encoding="utf-8"))

    by_unit = {}
    footnotes = {}
    unresolved = []
    empty_translation = []
    for row in reviewed["rows"]:
        unit_id, sent_idx = parse_row_id(row["id"])
        # Trust "resolved" (already computed correctly by read_reviewed_doc.py,
        # accounting for default/override/unresolved) as the source of truth.
        # Falling back to the raw "final" cell text here would be wrong: for
        # a default-accepted row that text is literally the word "default",
        # and writing that into the deliverable is worse than leaving the
        # paragraph untouched.
        text = row.get("resolved")
        if text is None:
            text = row.get("proposed", "")
        if row.get("status") == "unresolved":
            unresolved.append(row["id"])
        if not text:
            empty_translation.append(row["id"])
        if unit_id.startswith("fn"):
            footnotes[unit_id[2:]] = text
            continue
        by_unit.setdefault(unit_id, []).append((sent_idx, text))

    doc = Document(source_docx)
    touched = 0
    flattened_citations = {}  # unit_id -> [visible_text, ...] that lost their live field
    for unit_id, kind, paragraph in iter_units(doc):
        if unit_id not in by_unit:
            continue
        parts = [t for _, t in sorted(by_unit[unit_id])]
        final_text = " ".join(p for p in parts if p)
        if final_text:
            unmatched = apply_translated_text(paragraph, final_text)
            if unmatched:
                flattened_citations[unit_id] = unmatched
            touched += 1

    tmp_path = str(Path(output_docx).with_suffix(".tmp.docx"))
    doc.save(tmp_path)
    write_footnotes(tmp_path, output_docx, footnotes)
    Path(tmp_path).unlink(missing_ok=True)

    print(f"Rebuilt {touched} paragraph(s)/cell(s) and {len(footnotes)} footnote(s) -> {output_docx}")
    if unresolved:
        print(f"NOTE: {len(unresolved)} row(s) were unresolved: {unresolved}")
    if empty_translation:
        print(
            f"WARNING: {len(empty_translation)} row(s) have NO text at all (resolved and proposed both blank) - "
            f"those paragraphs were left in their ORIGINAL SOURCE LANGUAGE in the output, untouched: {empty_translation}. "
            f"This usually means a translation went missing upstream - check these before delivering."
        )
    if flattened_citations:
        print(
            f"WARNING: {len(flattened_citations)} paragraph(s) had a reference-manager citation field "
            f"(Zotero/Mendeley/EndNote) that could NOT be re-linked because its exact visible text no longer "
            f"appears in the translated sentence - it was written as plain (dead) text instead: {flattened_citations}. "
            f"This usually means the citation text itself got rephrased during translation - citation text should "
            f"be left byte-for-byte unchanged so the live link survives. Check these rows before delivering."
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_docx")
    parser.add_argument("reviewed_json")
    parser.add_argument("output_docx")
    args = parser.parse_args()
    rebuild(args.source_docx, args.reviewed_json, args.output_docx)


if __name__ == "__main__":
    main()
