#!/usr/bin/env python3
# Extract the content of the bilingual study pages into structured JSON.
#
# The HTML pages (ch<NN>-<M>-<slug>.html + index.html) are the source of truth;
# this script DERIVES a machine-readable record under data/. Re-run it after
# adding/editing pages to keep data/ in sync:
#
#     python3 work/extract_data.py
#
# Output: data/index.json (book meta + TOC) and data/ch<NN>-<M>-<slug>.json
# (one per page). See data/README.md for the schema.
#
# Parsing relies only on the stable template structure shared by every page;
# uses lxml (cssselect is not installed, so we match classes with XPath).
import os, re, glob, json
import lxml.html as H

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')


# ---- small helpers ---------------------------------------------------------

def byclass(el, cls, tag='*'):
    """Descendants whose @class contains the whole token `cls`."""
    q = f".//{tag}[contains(concat(' ', normalize-space(@class), ' '), ' {cls} ')]"
    return el.xpath(q)


def has_class(el, cls):
    return cls in (el.get('class') or '').split()


def collapse(s):
    """Drop HTML-formatting whitespace (a newline + its surrounding indent).
    Intra-line text (Japanese/Chinese has no spaces) is left untouched."""
    return re.sub(r'\s*\n\s*', '', s or '')


def inline(s):
    """Collapse any whitespace run to a single space; for notes/footers."""
    return re.sub(r'\s+', ' ', s or '').strip()


def inner_html(el):
    """Element inner HTML, whitespace-collapsed but with inline tags kept (so the
    intro's <strong> survives round-tripping; text_content() would drop it)."""
    raw = H.tostring(el, encoding='unicode')
    raw = re.sub(r'^<[^>]+>', '', raw)         # opening tag
    raw = re.sub(r'</[^>]+>\s*$', '', raw)     # closing tag
    return inline(raw)


def is_quote(el):
    return el.tag == 'div' and has_class(el, 'chinese-quote')


def quote_text(el):
    return collapse(''.join(el.itertext())).strip()


def note_of(section):
    """The `※ …` .small-note inside a section, or None."""
    notes = byclass(section, 'small-note')
    return inline(notes[0].text_content()) if notes else None


def footer_lines(root):
    """<footer> inner HTML split on <br> into trimmed lines."""
    raw = H.tostring(root.xpath('.//footer')[0], encoding='unicode')
    raw = re.sub(r'</?footer>', '', raw)
    return [inline(x) for x in re.split(r'<br\s*/?>', raw) if inline(x)]


# ---- ① 日语原文 (token paragraphs) / ② 汉语翻译 (text paragraphs) -----------

def parse_original(container):
    """Ordered blocks: {type:paragraph, tokens:[{base,ruby}|{text}]} | {type:quote, text}."""
    blocks, cur = [], []

    def flush():
        if cur:
            blocks.append({"type": "paragraph", "tokens": cur.copy()})
            cur.clear()

    def add_text(s):
        s = collapse(s)
        if s:
            cur.append({"text": s})

    add_text(container.text)
    for el in container:
        if el.tag == 'ruby':
            rt = el.find('rt')
            cur.append({"base": el.text or '', "ruby": (rt.text or '') if rt is not None else ''})
            add_text(el.tail)
        elif el.tag == 'br':
            flush()
            add_text(el.tail)
        elif is_quote(el):
            flush()
            blocks.append({"type": "quote", "text": quote_text(el)})
            add_text(el.tail)
        else:  # any other inline node -> keep its text
            add_text(el.text_content())
            add_text(el.tail)
    flush()
    return blocks


def parse_translation(container):
    """Ordered blocks: {type:paragraph, text} | {type:quote, text}."""
    blocks, parts = [], []

    def flush():
        txt = ''.join(parts).strip()
        if txt:
            blocks.append({"type": "paragraph", "text": txt})
        parts.clear()

    def add(s):
        s = collapse(s)
        if s:
            parts.append(s)

    add(container.text)
    for el in container:
        if el.tag == 'br':
            flush()
            add(el.tail)
        elif is_quote(el):
            flush()
            blocks.append({"type": "quote", "text": quote_text(el)})
            add(el.tail)
        else:
            add(el.text_content())
            add(el.tail)
    flush()
    return blocks


# ---- ⑤ 资料补注 ------------------------------------------------------------

def parse_notes(p):
    """The bulleted 资料补注 <p>: skip the 📌 header, one entry per <br> segment.
    Each entry -> {label, text}; label is the leading <strong>…</strong> if present
    (else null). `text` keeps any inline markup as a string so nothing is lost."""
    inner = H.tostring(p, encoding='unicode')
    inner = re.sub(r'^<p[^>]*>', '', inner)
    inner = re.sub(r'</p>\s*$', '', inner)
    out = []
    for seg in re.split(r'<br\s*/?>', inner):
        seg = seg.strip()
        if not seg or '📌' in seg:          # header line
            continue
        seg = re.sub(r'^[•·]\s*', '', seg)    # bullet glyph
        m = re.match(r'<strong>(.*?)</strong>\s*[:：]\s*(.*)$', seg, re.S)
        if m:
            out.append({"label": inline(m.group(1)), "text": m.group(2).strip()})
        else:
            out.append({"label": None, "text": seg})
    return out


# ---- nav -------------------------------------------------------------------

def nav_dir(el):
    href = el.get('href')
    disabled = el.tag == 'span' or has_class(el, 'disabled')
    return href, el.text_content().strip(), disabled


def parse_nav(root):
    navs = byclass(root, 'nav-bar')
    top = next(n for n in navs if has_class(n, 'top'))
    bottom = next(n for n in navs if has_class(n, 'bottom'))

    def ends(nbar):
        kids = [c for c in nbar if (c.get('class') or '')]
        return kids[0], kids[-1]           # prev, next (home sits in the middle)

    pt, nt = ends(top)
    pb, nb = ends(bottom)
    pt_h, pt_l, pt_d = nav_dir(pt); nt_h, nt_l, nt_d = nav_dir(nt)
    pb_h, pb_l, pb_d = nav_dir(pb); nb_h, nb_l, nb_d = nav_dir(nb)
    return {
        "prev": {"href": pt_h or pb_h, "label_top": pt_l, "label_bottom": pb_l, "disabled": pt_d and pb_d},
        "next": {"href": nt_h or nb_h, "label_top": nt_l, "label_bottom": nb_l, "disabled": nt_d and nb_d},
    }


# ---- a study page ----------------------------------------------------------

def parse_page(path):
    root = H.parse(path).getroot()
    fname = os.path.basename(path)
    slug = fname[:-5]
    sub = byclass(root, 'sub')[0].text_content().strip()
    footer = footer_lines(root)

    # chapter/section numbers are authoritative from the filename (ch<NN>-<M>);
    # the kanji chapter no., title and section total come from the sub or footer
    # heading "第一章 公案小説 · 第N節／全T節" (some pages omit it from .sub).
    cm = re.match(r'ch(\d+)-(\d+)', slug)
    chap_no, sec_num = int(cm.group(1)), int(cm.group(2))
    m = re.search(r'第(.+?)章\s+(.+?)\s*·\s*第\d+節／全(\d+)節', sub + ' ｜ ' + ' '.join(footer))
    chap_kanji = m.group(1) if m else None
    chap_title = m.group(2) if m else None
    sec_total = int(m.group(3)) if m else None

    grid = byclass(root, 'content-grid')[0]
    text_col = byclass(grid, 'text-col')[0]
    vocab_col = byclass(grid, 'vocab-col')[0]
    trans_sec = next(s for s in grid if has_class(s, 'section')
                     and not has_class(s, 'text-col') and not has_class(s, 'vocab-col'))
    grammar_sec = byclass(root, 'grammar-list')[0].getparent()
    notes_p = next(d for d in root.xpath('.//div')
                   if 'background-color' in (d.get('style') or '')).xpath('.//p')[0]

    vocab_rows = []
    for tr in byclass(root, 'word-table')[0].xpath('.//tbody/tr'):
        tds = tr.xpath('./td')
        if len(tds) == 3:
            vocab_rows.append({"word": tds[0].text_content().strip(),
                               "reading": tds[1].text_content().strip(),
                               "meaning": tds[2].text_content().strip()})

    cards = []
    for card in byclass(root, 'grammar-card'):
        title = byclass(card, 'grammar-title')[0].text_content().strip()
        marker = ''
        if title and 0x2460 <= ord(title[0]) <= 0x24FF:   # ①..⑳ etc.
            marker, title = title[0], title[1:].strip()
        cards.append({"marker": marker,
                      "title": title,
                      "desc": byclass(card, 'grammar-desc')[0].text_content().strip()})

    return {
        "filename": fname,
        "slug": slug,
        "chapter": {"number": chap_no, "number_kanji": chap_kanji, "title_ja": chap_title},
        "section": {"num": sec_num, "total": sec_total},
        "page_title": root.xpath('.//title')[0].text,
        "h1": root.xpath('.//h1')[0].text_content().strip(),
        "sub": sub,
        "nav": parse_nav(root),
        "original": parse_original(byclass(text_col, 'japanese-text')[0]),
        "translation": {
            "blocks": parse_translation(byclass(trans_sec, 'translation-text')[0]),
            "note": note_of(trans_sec),
        },
        "vocab": {"rows": vocab_rows, "note": note_of(vocab_col)},
        "grammar": {"cards": cards, "note": note_of(grammar_sec)},
        "notes": parse_notes(notes_p),
        "footer": footer,
    }


# ---- index.html ------------------------------------------------------------

def parse_index(path):
    root = H.parse(path).getroot()
    sub = byclass(root, 'sub')[0].text_content().strip()
    h1 = root.xpath('.//h1')[0].text_content().strip()

    m = re.search(r'(.+?)\s*著（(.+?)[,，]\s*(\d{4})）', sub)
    bm = re.search(r'『(.+?)』', h1)
    footer = footer_lines(root)

    chapters, future = [], []
    for block in byclass(root, 'chapter-block'):
        if byclass(block, 'toc-list'):
            head = byclass(block, 'chapter-head')[0].text_content().strip()
            hm = re.match(r'第(.+?)章\s+(.+)$', head)
            note = byclass(block, 'chapter-note')[0].text_content().strip()
            sections = []
            for a in byclass(block, 'toc-card', tag='a'):
                sections.append({
                    "num": int(byclass(a, 'toc-num')[0].text_content().strip()),
                    "href": a.get('href'),
                    "title_ja": byclass(a, 'toc-ja')[0].text_content().strip(),
                    "summary_zh": byclass(a, 'toc-zh')[0].text_content().strip(),
                })
            chapters.append({
                "number": int(re.match(r'ch(\d+)-', sections[0]["href"]).group(1)) if sections else None,
                "number_kanji": hm.group(1) if hm else None,
                "title_ja": hm.group(2) if hm else head,
                "head": head,
                "note": note,
                "status": "done" if ('已完成' in note or '✅' in note) else "in_progress",
                "sections": sections,
            })
        elif byclass(block, 'future-list'):
            for chip in byclass(block, 'future-chip'):
                kanji = byclass(chip, 'num')[0].text_content().strip()
                title = chip.text_content().strip()
                if title.startswith(kanji):
                    title = title[len(kanji):].strip()
                future.append({"number_kanji": kanji, "title_ja": title})

    return {
        "book": {
            "title": bm.group(1) if bm else None,
            "author": m.group(1).strip() if m else None,
            "publisher": m.group(2).strip() if m else None,
            "year": int(m.group(3)) if m else None,
            "page_title": root.xpath('.//title')[0].text,
            "h1": h1,
            "sub": sub,
            "intro": inner_html(byclass(root, 'intro')[0]),
            "footer": footer,
        },
        "chapters": chapters,
        "future_chapters": future,
    }


# ---- main ------------------------------------------------------------------

def write(name, obj):
    with open(os.path.join(DATA, name), 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    os.makedirs(DATA, exist_ok=True)

    idx = parse_index(os.path.join(ROOT, 'index.html'))
    write('index.json', idx)
    print(f"index.json          chapters={len(idx['chapters'])} future={len(idx['future_chapters'])}")

    for path in sorted(glob.glob(os.path.join(ROOT, 'ch*.html'))):
        page = parse_page(path)
        write(page['slug'] + '.json', page)
        nq = sum(1 for b in page['original'] if b['type'] == 'quote')
        print(f"{page['slug']+'.json':<28} vocab={len(page['vocab']['rows'])} "
              f"grammar={len(page['grammar']['cards'])} quotes={nq} "
              f"notes={len(page['notes'])}")


if __name__ == '__main__':
    main()
