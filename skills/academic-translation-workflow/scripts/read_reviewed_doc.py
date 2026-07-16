"""
Usage: python read_reviewed_doc.py <reviewed.docx> <output_reviewed.json>

Reads the translator's reviewed document back out: the segmented table
(with the Final column now filled in) and the answers written into the
Questions for Translator table. Resolves each row's effective text:
  - "default" (case-insensitive, whitespace-trimmed) -> use Proposed
  - non-empty other text -> use that as the override
  - left blank -> flagged "unresolved" (NOT silently treated as default,
    since a blank could mean "forgot to review this row" rather than
    "accepted" - surface these back to the translator rather than guessing)
  - "default" written against a row whose Proposed is ALSO blank -> flagged
    "unresolved" too (there's nothing to default to - this almost always
    means the proposed translation for that row went missing upstream, not
    a real translator decision, so it needs a human to look rather than
    silently producing an empty/wrong final row)
"""
import json
import argparse
from pathlib import Path

from docx import Document
from docx_utils import text_with_markup


def _table_header(table):
    return [c.text.strip() for c in table.rows[0].cells]


def read_reviewed(docx_path):
    doc = Document(docx_path)

    question_answers = []
    rows = []

    for table in doc.tables:
        header = _table_header(table)
        if header[:2] == ["Question", "Your Answer"]:
            for tr in table.rows[1:]:
                cells = tr.cells
                question_answers.append({
                    "question": cells[0].text.strip(),
                    "answer": cells[1].text.strip(),
                })
        elif header == ["ID", "Type", "Source (ID)", "Proposed (EN)", "Final (EN)"]:
            for tr in table.rows[1:]:
                c = tr.cells
                row_id = c[0].text.strip()
                row_type = c[1].text.strip()
                source = c[2].text.strip()
                proposed = text_with_markup(c[3]).strip()
                final_raw = text_with_markup(c[4]).strip()

                if final_raw == "":
                    status = "unresolved"
                    resolved = proposed
                elif final_raw.lower() == "default":
                    if proposed == "":
                        status = "unresolved"  # nothing to default to - likely a missing upstream translation, not a real accept
                    else:
                        status = "accepted_default"
                    resolved = proposed
                else:
                    status = "overridden"
                    resolved = final_raw

                rows.append({
                    "id": row_id,
                    "type": row_type,
                    "source": source,
                    "proposed": proposed,
                    "final": final_raw,
                    "resolved": resolved,
                    "status": status,
                })

    return {"question_answers": question_answers, "rows": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("reviewed_docx")
    parser.add_argument("output_json")
    args = parser.parse_args()

    result = read_reviewed(args.reviewed_docx)
    Path(args.output_json).write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    unresolved = [r["id"] for r in result["rows"] if r["status"] == "unresolved"]
    print(f"Wrote {len(result['rows'])} rows, {len(result['question_answers'])} question answers to {args.output_json}")
    if unresolved:
        print(f"WARNING: {len(unresolved)} row(s) left blank in Final column (treated as unresolved, NOT auto-accepted): {unresolved}")


if __name__ == "__main__":
    main()
