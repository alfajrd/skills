"""
Shared helpers for the academic-translation-workflow skill.

Design notes (read this before modifying):
- Paragraphs are visited in true document order (body paragraphs AND table
  cells, interleaved correctly) via `iter_block_items`. Each visited unit gets
  a stable string ID derived purely from document structure/position, so the
  SAME ids can be re-derived by re-opening the ORIGINAL, untouched source file
  later during reconstruction. Do not switch to python-docx's separate
  `.paragraphs` / `.tables` lists elsewhere in this skill - they don't
  preserve interleaving order and would desync the ids.
- Footnotes live in a separate OOXML part (word/footnotes.xml) that
  python-docx does not model, so they're handled by direct XML access via
  zipfile + lxml, not through the Document object.
- Italics are expressed with a lightweight `*term*` markup (like Markdown)
  inside any "proposed" / "final" string, rather than character offsets.
  This is far easier for an LLM to produce reliably. `runs_from_markup`
  turns that markup into actual italic runs.
"""
import re
import zipfile
import shutil
from lxml import etree

from docx.oxml.ns import qn
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# --- Document-order traversal -------------------------------------------------

def _iter_block_items(parent_elm, parent):
    for child in parent_elm.iterchildren():
        if child.tag == qn('w:p'):
            yield Paragraph(child, parent)
        elif child.tag == qn('w:tbl'):
            yield Table(child, parent)


def iter_units(document):
    """Yield (id, kind, paragraph) for every translatable unit in document order.

    kind is one of: 'body_para', 'table_cell_para'.
    id looks like 'p3' for body paragraph #3 (0-indexed over body paragraphs
    only), or 'tbl0_r1_c2_p0' for the 1st paragraph of the cell at row1/col2
    of the 1st top-level table. One level of table nesting only (nested
    tables inside a cell are skipped - known limitation, flag for manual
    review if encountered).
    """
    p_idx = 0
    t_idx = 0
    for item in _iter_block_items(document.element.body, document):
        if isinstance(item, Paragraph):
            yield f"p{p_idx}", "body_para", item
            p_idx += 1
        elif isinstance(item, Table):
            for r_idx, row in enumerate(item.rows):
                for c_idx, cell in enumerate(row.cells):
                    for cp_idx, cell_para in enumerate(cell.paragraphs):
                        yield f"tbl{t_idx}_r{r_idx}_c{c_idx}_p{cp_idx}", "table_cell_para", cell_para
            t_idx += 1


# --- Paragraph classification --------------------------------------------------

BIBLIOGRAPHY_HEADINGS = re.compile(
    r'daftar\s+pustaka|bibliograf|^references$', re.IGNORECASE
)
LIST_TEXT_RE = re.compile(r'^([•●\-\*]|\d+[.)])\s+')


def classify_paragraph(paragraph, in_bibliography):
    """Return one of: empty, heading, heading_starts_bibliography, caption,
    quote, list_item, bibliography, body."""
    text = paragraph.text.strip()
    if not text:
        return "empty"
    style = (paragraph.style.name or "").lower() if paragraph.style else ""
    if "heading" in style or "title" in style:
        if BIBLIOGRAPHY_HEADINGS.search(text):
            return "heading_starts_bibliography"
        return "heading"
    if "caption" in style:
        return "caption"
    if "quote" in style:
        return "quote"
    if "list" in style or LIST_TEXT_RE.match(text):
        return "list_item"
    if in_bibliography:
        return "bibliography"
    return "body"


# --- Sentence splitting (heuristic - Claude should sanity-check output) -------

_ABBREVIATIONS = {
    "dr", "prof", "ir", "drs", "dra", "h", "hj", "sh", "se", "si", "mm", "msi",
    "ma", "md", "dkk", "dll", "dst", "yth", "no", "jl", "st", "al", "vol",
    "hal", "cf", "vs", "tbk", "pt", "cv",
}

_SENTENCE_BOUNDARY_RE = re.compile(
    r'(?<=[.!?])\s+(?=[A-Z0-9"“‘(])'
)


def split_sentences(text):
    """Heuristic sentence splitter tuned for Indonesian academic prose.
    Not perfect around abbreviations/decimals - segment_docx.py's output
    (segments.json) should be reviewed and fixed up (merge stray splits)
    before translation proceeds, rather than trusted blindly.
    """
    text = text.strip()
    if not text:
        return []
    protected = re.sub(r'(?<=\d)\.(?=\d)', '', text)  # protect decimals
    parts = _SENTENCE_BOUNDARY_RE.split(protected)

    sentences = []
    buf = ""
    for part in parts:
        buf = f"{buf} {part}".strip() if buf else part
        m = re.search(r'\b([A-Za-z]+)\.\s*$', buf)
        if m and m.group(1).lower() in _ABBREVIATIONS:
            continue  # likely an abbreviation, not a real sentence end - keep accumulating
        sentences.append(buf)
        buf = ""
    if buf:
        sentences.append(buf)
    return [s.replace('', '.').strip() for s in sentences if s.strip()]


# --- Writing translated text back into a paragraph, with *italic* markup ------

_MARKUP_RE = re.compile(r'\*([^*]+)\*')


def text_with_markup(container):
    """Inverse of apply_translated_text: read a paragraph (or a table cell,
    which may hold multiple paragraphs) back out as a plain string, but
    re-encode any italic run as `*text*`. This is what lets "italic-ness"
    survive the round trip through Word - a translator who accepts a row
    as-is, or who types their own override and hits Ctrl+I in Word, ends up
    with the same *markup* representation that apply_translated_text expects
    on the way back in. Consecutive runs sharing the same italic state are
    merged first so a span split across multiple runs (e.g. by spellcheck)
    doesn't turn into several adjacent *fragments*.
    """
    paragraphs = container.paragraphs if hasattr(container, "paragraphs") else [container]
    out = []
    for p in paragraphs:
        merged = []
        for r in p.runs:
            if not r.text:
                continue
            italic = bool(r.italic)
            if merged and merged[-1][1] == italic:
                merged[-1][0] += r.text
            else:
                merged.append([r.text, italic])
        for text, italic in merged:
            out.append(f"*{text}*" if italic else text)
    return "".join(out)


def apply_translated_text(paragraph, text):
    """Replace a paragraph's runs with `text`, preserving the paragraph's
    first run's character formatting (font/size/color/bold/etc.) as the base
    style, and rendering `*term*` spans as italic runs. Paragraph-level
    formatting (alignment, style, numbering, spacing) is untouched since we
    never touch paragraph-level XML, only its runs.
    """
    base_rpr = None
    if paragraph.runs:
        r = paragraph.runs[0]._r
        rpr = r.find(qn('w:rPr'))
        if rpr is not None:
            base_rpr = etree.tostring(rpr)

    for r in list(paragraph.runs):
        r._r.getparent().remove(r._r)

    pieces = _MARKUP_RE.split(text)  # alternating: plain, italic, plain, italic, ...
    for i, piece in enumerate(pieces):
        if piece == "":
            continue
        run = paragraph.add_run(piece)
        if base_rpr is not None:
            run._r.insert(0, etree.fromstring(base_rpr))
        if i % 2 == 1:  # odd index = came from inside *...*
            run.italic = True


# --- Footnotes (word/footnotes.xml is not modeled by python-docx) -------------

_FOOTNOTES_PART = "word/footnotes.xml"


def extract_footnotes(docx_path):
    """Return [(footnote_id:str, text:str), ...] for real footnotes
    (skips separator/continuation placeholders ids 0/1)."""
    results = []
    with zipfile.ZipFile(docx_path) as z:
        if _FOOTNOTES_PART not in z.namelist():
            return results
        xml = z.read(_FOOTNOTES_PART)
    root = etree.fromstring(xml)
    for fn in root.findall(f'{W_NS}footnote'):
        fid = fn.get(f'{W_NS}id')
        if fid in ("0", "1", "-1"):
            continue
        texts = [t.text or "" for t in fn.iter(f'{W_NS}t')]
        results.append((fid, "".join(texts).strip()))
    return results


def write_footnotes(src_path, dst_path, id_to_text):
    """Copy src_path to dst_path, replacing footnote body text for each
    footnote id present in id_to_text (a dict of footnote_id -> new text,
    may contain *italic* markup). Runs within a footnote paragraph are
    collapsed to a single run (formatting of the original first run is kept),
    same approach as apply_translated_text."""
    if not id_to_text:
        if src_path != dst_path:
            shutil.copyfile(src_path, dst_path)
        return

    with zipfile.ZipFile(src_path) as zin:
        names = zin.namelist()
        if _FOOTNOTES_PART not in names:
            if src_path != dst_path:
                shutil.copyfile(src_path, dst_path)
            return
        data = {n: zin.read(n) for n in names}

    root = etree.fromstring(data[_FOOTNOTES_PART])
    for fn in root.findall(f'{W_NS}footnote'):
        fid = fn.get(f'{W_NS}id')
        if fid not in id_to_text:
            continue
        paras = fn.findall(f'{W_NS}p')
        if not paras:
            continue
        target_p = paras[0]
        runs = target_p.findall(f'{W_NS}r')
        base_rpr = None
        if runs:
            rpr = runs[0].find(f'{W_NS}rPr')
            if rpr is not None:
                base_rpr = etree.tostring(rpr)
        for r in runs:
            target_p.remove(r)

        pieces = _MARKUP_RE.split(id_to_text[fid])
        for i, piece in enumerate(pieces):
            if piece == "":
                continue
            new_r = etree.SubElement(target_p, f'{W_NS}r')
            if base_rpr is not None:
                rpr_el = etree.fromstring(base_rpr)
                if i % 2 == 1:
                    it = rpr_el.find(f'{W_NS}i')
                    if it is None:
                        etree.SubElement(rpr_el, f'{W_NS}i')
                new_r.append(rpr_el)
            elif i % 2 == 1:
                rpr_el = etree.SubElement(new_r, f'{W_NS}rPr')
                etree.SubElement(rpr_el, f'{W_NS}i')
            t_el = etree.SubElement(new_r, f'{W_NS}t')
            t_el.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
            t_el.text = piece

    data[_FOOTNOTES_PART] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)

    with zipfile.ZipFile(dst_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, content in data.items():
            zout.writestr(name, content)
