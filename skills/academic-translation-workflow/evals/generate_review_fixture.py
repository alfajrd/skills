"""
One-off: builds evals/fixtures/mangrove_reviewed.docx - a plausible
translator-reviewed version of the mangrove.docx fixture, used by eval #2
(finalize step) so that eval doesn't depend on eval #1 having run first.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from segment_docx import build_segments
from build_review_doc import build_review_doc
from docx import Document

FIXTURES = Path(__file__).parent / "fixtures"

TRANSLATIONS = {
    "p0.s0": "Mangrove Reforestation for Coastal Abrasion Mitigation",
    "p1.s0": "Background",
    "p2.s0": "Coastal abrasion is a serious threat to Indonesia's coastal regions.",
    "p2.s1": "Mangrove reforestation is considered an effective, low-cost, nature-based solution compared to building concrete seawalls.",
    "p3.s0": "Community-based mangrove reforestation programs involving local residents have shown promising results in several provinces.",
    "p4.s0": "Results",
    "tbl0_r0_c0_p0.s0": "Location",
    "tbl0_r0_c1_p0.s0": "Area (ha)",
    "tbl0_r0_c2_p0.s0": "Success Rate",
    "tbl0_r1_c0_p0.s0": "Demak Coast",
    "tbl0_r1_c1_p0.s0": "12.5",
    "tbl0_r1_c2_p0.s0": "78%",
    "tbl0_r2_c0_p0.s0": "Indramayu Coast",
    "tbl0_r2_c1_p0.s0": "8.2",
    "tbl0_r2_c2_p0.s0": "65%",
    "p5.s0": "References",
    "p6.s0": "Prasetyo, D. (2020). Ekologi mangrove pesisir utara Jawa. Bandung: ITB Press.",
}

segments = build_segments(str(FIXTURES / "mangrove.docx"), client="universitas-sari")
rows = [{**r, "proposed": TRANSLATIONS.get(r["id"], "")} for r in segments["rows"]]

annotated = {
    "source_file": segments["source_file"],
    "client": "universitas-sari",
    "title": "Translation Brief: Mangrove Reforestation for Coastal Abrasion Mitigation",
    "topic_overview": "This article discusses mangrove reforestation as a nature-based approach to mitigating coastal abrasion in Indonesia, including *community-based* (locally organized) program results across two coastal sites.",
    "terminology": [
        {"term": "*berbasis komunitas*", "note": "Has a direct English equivalent: 'community-based'. Not italicized in the final translation since it's not a loanword."},
    ],
    "questions": [
        {"question": "Row tbl0_r1_c1_p0.s0 / tbl0_r2_c1_p0.s0: areas given in hectares (ha) with one decimal - confirm no rounding needed for the final table."},
    ],
    "rows": rows,
}

review_path = FIXTURES / "_mangrove_review_tmp.docx"
build_review_doc(annotated, str(review_path))

doc = Document(str(review_path))
for table in doc.tables:
    header = [c.text.strip() for c in table.rows[0].cells]
    if header == ["Question", "Your Answer"]:
        for tr in table.rows[1:]:
            tr.cells[1].text = "Confirmed, no rounding needed."
    elif header == ["ID", "Type", "Source (ID)", "Proposed (EN)", "Final (EN)"]:
        for tr in table.rows[1:]:
            tr.cells[4].text = "default"

out_path = FIXTURES / "mangrove_reviewed.docx"
doc.save(str(out_path))
review_path.unlink(missing_ok=True)
print(f"Wrote {out_path}")
