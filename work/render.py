#!/usr/bin/env python3
# Render the bilingual study pages from data/*.json.
#
# data/*.json is the SOURCE OF TRUTH; this script generates the static HTML
# (ch<NN>-<M>-<slug>.html + index.html) from it. It is the inverse of
# work/extract_data.py, which re-derives the JSON and so doubles as a round-trip
# check (render -> extract -> the data should come back unchanged).
#
#     python3 work/render.py        # run from the repo root
#
# Output: index.html and one ch<NN>-<M>-<slug>.html per data/ch*.json. The markup
# (CSS, section skeleton) comes from the templates in the japanese-study-page
# skill: template.html (chapter pages) and index-template.html (the TOC).
#
# Stdlib only. See data/README.md for the JSON schema.
import os, re, glob, json, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
SKILL = os.path.join(ROOT, '.claude', 'skills', 'japanese-study-page')
PAGE_TEMPLATE = os.path.join(SKILL, 'template.html')
INDEX_TEMPLATE = os.path.join(SKILL, 'index-template.html')


# ---- helpers ---------------------------------------------------------------

def esc(s):
    """Escape & < > in a plain-text field. A no-op for the CJK content here, but
    it keeps output valid and round-trips (extract_data.py reads it back via
    text_content(), which un-escapes). Fields captured as raw HTML by the
    extractor (notes label/text, the index intro) are emitted verbatim instead."""
    return html.escape(s or '', quote=False)


def strip_comments(template):
    """Drop the template's authoring-guidance HTML comments so they don't leak
    into generated pages (one of them contains a literal href="..." example).
    lxml ignores comments, so this never affects the extract_data.py round-trip."""
    return re.sub(r'[ \t]*<!--.*?-->[ \t]*\n?', '', template, flags=re.DOTALL)


def fill(template, mapping):
    out = strip_comments(template)
    for key, val in mapping.items():
        out = out.replace('{{' + key + '}}', val)
    return out


# ---- ① 日语原文 / ② 汉语翻译 (ordered paragraph/quote blocks) ----------------

def render_tokens(tokens):
    """A paragraph's tokens -> ruby markup + plain runs."""
    parts = []
    for t in tokens:
        if 'base' in t:
            parts.append(f"<ruby>{esc(t['base'])}<rt>{esc(t['ruby'])}</rt></ruby>")
        else:
            parts.append(esc(t['text']))
    return ''.join(parts)


def render_blocks(blocks, indent, quote_style=''):
    """Shared layout for 原文/翻译: consecutive paragraphs are joined by <br><br>;
    白文 quotes are standalone block divs (their margin gives the spacing, so no
    <br> is needed around them — extract_data.py collapses such breaks anyway).
    `quote_style` is the inline style on the .chinese-quote div (the ② echo is
    tinted; the ① original quote is plain)."""
    style = f' style="{quote_style}"' if quote_style else ''
    lines, prev_para = [], False
    for b in blocks:
        if b['type'] == 'paragraph':
            text = render_tokens(b['tokens']) if 'tokens' in b else esc(b['text'])
            if prev_para:
                lines[-1] += '<br><br>'
            lines.append(indent + text)
            prev_para = True
        else:  # quote
            lines.append(f'{indent}<div class="chinese-quote"{style}>')
            lines.append(indent + '    ' + esc(b['text']))
            lines.append(indent + '</div>')
            prev_para = False
    return '\n'.join(lines)


# ---- ③ 語彙 / ④ 文法 / ⑤ 资料补注 / nav / footer ----------------------------

def render_vocab(rows, indent):
    return '\n'.join(
        f"{indent}<tr><td>{esc(r['word'])}</td><td>{esc(r['reading'])}</td>"
        f"<td>{esc(r['meaning'])}</td></tr>"
        for r in rows
    )


def build_vocab_bank(page):
    """The per-page practice deck: every furigana'd word (kanji -> reading) plus the
    curated 語彙 rows (word -> Chinese meaning), deduped by word, first-seen order.

    Each card is {"w","r","t"[,"m"]}: t="reading" cards quiz 漢字→かな; t="meaning"
    cards quiz word→中文释义. The ① ruby words and the ③ vocab rows are largely
    disjoint (ruby words are meaning-transparent kanji; vocab rows are kana/文语 forms),
    so most cards are one type — but if a curated word also appears as a ruby token we
    keep the meaning and promote it to a meaning card."""
    bank, by_word = [], {}
    for b in page['original']:
        if b['type'] != 'paragraph':
            continue
        for tok in b['tokens']:
            if 'base' not in tok:
                continue
            w = tok['base']
            if w in by_word:
                continue
            card = {"w": w, "r": tok['ruby'], "t": "reading"}
            by_word[w] = card
            bank.append(card)
    for row in page['vocab']['rows']:
        w = row['word']
        if w in by_word:
            by_word[w]["m"] = row['meaning']
            by_word[w]["t"] = "meaning"
        else:
            card = {"w": w, "r": row['reading'], "m": row['meaning'], "t": "meaning"}
            by_word[w] = card
            bank.append(card)
    return bank


def render_grammar(cards, indent):
    out = []
    for c in cards:
        title = f"{c['marker']} {c['title']}" if c['marker'] else c['title']
        out.append(f'{indent}<div class="grammar-card">')
        out.append(f'{indent}    <div class="grammar-title">{esc(title)}</div>')
        out.append(f'{indent}    <div class="grammar-desc">{esc(c["desc"])}</div>')
        out.append(f'{indent}</div>')
    return '\n'.join(out)


def render_notes(notes, indent):
    """• bulleted entries joined by <br>; the 📌 header lives in the template.
    label/text are emitted raw (the extractor captures them as HTML fragments)."""
    out = []
    for n in notes:
        if n['label']:
            out.append(f"{indent}• <strong>{n['label']}</strong>：{n['text']}")
        else:
            out.append(f"{indent}• {n['text']}")
    return '<br>\n'.join(out)


def render_nav(d, which):
    label = esc(d['label_top'] if which == 'top' else d['label_bottom'])
    if d['disabled']:
        return f'<span class="nav-link disabled">{label}</span>'
    return f'<a class="nav-link" href="{esc(d["href"])}">{label}</a>'


def render_footer(lines, indent):
    return '<br>\n'.join(indent + esc(l) for l in lines)


# ---- a study page ----------------------------------------------------------

def render_page(page, template):
    nav = page['nav']
    return fill(template, {
        'PAGE_TITLE': esc(page['page_title']),
        'H1': esc(page['h1']),
        'SUB': esc(page['sub']),
        'NAV_TOP_PREV': render_nav(nav['prev'], 'top'),
        'NAV_TOP_NEXT': render_nav(nav['next'], 'top'),
        'NAV_BOTTOM_PREV': render_nav(nav['prev'], 'bottom'),
        'NAV_BOTTOM_NEXT': render_nav(nav['next'], 'bottom'),
        'JAPANESE_TEXT': render_blocks(page['original'], ' ' * 12),
        'TRANSLATION': render_blocks(page['translation']['blocks'], ' ' * 16,
                                     'margin: 0.6rem 0; background: #f3efe2;'),
        'TRANSLATION_NOTE': esc(page['translation']['note']),
        'VOCAB_ROWS': render_vocab(page['vocab']['rows'], ' ' * 20),
        'VOCAB_NOTE': esc(page['vocab']['note']),
        'GRAMMAR_CARDS': render_grammar(page['grammar']['cards'], ' ' * 12),
        'GRAMMAR_NOTE': esc(page['grammar']['note']),
        'NOTES': render_notes(page['notes'], ' ' * 8),
        'FOOTER': render_footer(page['footer'], ' ' * 8),
        # raw JSON inside <script>; CJK content can't contain "</script>"
        'VOCAB_BANK_JSON': json.dumps(build_vocab_bank(page), ensure_ascii=False),
        'PAGE_SLUG': esc(page['slug']),
    })


# ---- index.html ------------------------------------------------------------

def render_chapter_blocks(chapters):
    out = []
    for ch in chapters:
        out.append('    <div class="chapter-block">')
        out.append(f'        <div class="chapter-head">{esc(ch["head"])}</div>')
        out.append(f'        <div class="chapter-note">{esc(ch["note"])}</div>')
        out.append('        <div class="toc-list">')
        for s in ch['sections']:
            out.append(f'            <a class="toc-card" href="{esc(s["href"])}">')
            out.append(f'                <div class="toc-num">{s["num"]}</div>')
            out.append('                <div class="toc-body">')
            out.append(f'                    <div class="toc-ja">{esc(s["title_ja"])}</div>')
            out.append(f'                    <div class="toc-zh">{esc(s["summary_zh"])}</div>')
            out.append('                </div>')
            out.append('            </a>')
        out.append('        </div>')
        out.append('    </div>')
    return '\n'.join(out)


def render_future_chips(future, indent):
    return '\n'.join(
        f'{indent}<span class="future-chip"><span class="num">{esc(c["number_kanji"])}</span>'
        f'{esc(c["title_ja"])}</span>'
        for c in future
    )


def render_index(idx, template):
    book = idx['book']
    return fill(template, {
        'PAGE_TITLE': esc(book['page_title']),
        'H1': esc(book['h1']),
        'SUB': esc(book['sub']),
        'INTRO': book['intro'],            # raw: keeps inline markup (<strong>)
        'CHAPTER_BLOCKS': render_chapter_blocks(idx['chapters']),
        'FUTURE_CHIPS': render_future_chips(idx['future_chapters'], ' ' * 12),
        'FOOTER': render_footer(book['footer'], ' ' * 8),
    })


# ---- main ------------------------------------------------------------------

def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def write(name, text):
    with open(os.path.join(ROOT, name), 'w', encoding='utf-8') as f:
        f.write(text)


def load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


def main():
    page_tpl = read(PAGE_TEMPLATE)
    index_tpl = read(INDEX_TEMPLATE)

    idx = load('index.json')
    write('index.html', render_index(idx, index_tpl))
    print(f"index.html          chapters={len(idx['chapters'])} "
          f"future={len(idx['future_chapters'])}")

    for path in sorted(glob.glob(os.path.join(DATA, 'ch*.json'))):
        page = load(os.path.basename(path))
        write(page['filename'], render_page(page, page_tpl))
        nq = sum(1 for b in page['original'] if b['type'] == 'quote')
        print(f"{page['filename']:<28} vocab={len(page['vocab']['rows'])} "
              f"bank={len(build_vocab_bank(page))} "
              f"grammar={len(page['grammar']['cards'])} quotes={nq} "
              f"notes={len(page['notes'])}")


if __name__ == '__main__':
    main()
