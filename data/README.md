# `data/` — source content of the study pages

Machine-readable content of the bilingual study pages — 原文 furigana, 汉语翻译,
語彙注釈, 文法分析, 资料补注, and the TOC — decoupled from the CSS/markup.

**`data/*.json` is the source of truth.** Edit the JSON here, then render the
HTML from it; don't hand-edit the generated `../ch*.html` / `../index.html`.

## Render

```sh
python3 work/render.py            # run from the repo root
```

`render.py` reads each `data/ch*.json` + `data/index.json` and writes the
self-contained `../ch*.html` + `../index.html`, reusing the markup templates in
`.claude/skills/japanese-study-page/` (`template.html` for pages,
`index-template.html` for the TOC). It prints a one-line per-file summary and
needs only the Python stdlib.

**Vocab practice (no new authoring).** The renderer also derives a per-page
practice deck (`build_vocab_bank`) and embeds it as JSON in a `<script>` for the
🎴 单词练习 multiple-choice self-test: every ① furigana word becomes a *reading*
card (漢字→かな) and every ③ `vocab.rows` entry a *meaning* card (词→中文释义).
Progress is stored in a **Supabase (Postgres) database** with **per-user accounts**
(email/password): each answered question is recorded via the `record_attempt` RPC,
each reader's hardest words show atop ③ 語彙注釈 (`#user-hard`) with their 正确率, and
`index.html` runs a cross-lesson 错题复习. **You author nothing extra; new pages get
it automatically.** The added markup (auth bar, practice section) lives outside
`.content-grid` and avoids the extractor's classes, so `extract_data.py` round-trips
unchanged. **Database setup + schema live in [`db/`](../db/) — see `db/README.md`.**
`work/export_words.py` regenerates `db/words_seed.sql` (the catalog of all words)
from the same bank; re-run it when lesson content changes.

## Verify / re-import

```sh
python3 work/extract_data.py      # re-derive data/ from the HTML
```

`extract_data.py` is the inverse of the renderer: it parses `ch*.html` +
`index.html` back into `data/<name>.json` (needs `lxml`). Use it to **import
legacy hand-authored HTML** into `data/`, or as a **round-trip check** — after
`render.py`, re-running it should leave `data/` byte-for-byte unchanged.

## Files

- `index.json` — book metadata + table of contents.
- `ch<NN>-<M>-<slug>.json` — one per study page (currently `ch01-1` … `ch01-5`).

## Per-page schema (`ch<NN>-<M>-<slug>.json`)

| field | meaning |
|-------|---------|
| `filename`, `slug` | source HTML file name / name without `.html` |
| `chapter` | `{number, number_kanji, title_ja}` (e.g. `1` / `"一"` / `"公案小説"`) |
| `section` | `{num, total}` — this passage's number and the chapter's passage count |
| `page_title` | `<title>` text |
| `h1`, `sub` | page heading and subtitle line (kept verbatim, emoji included) |
| `nav.prev` / `nav.next` | `{href, label_top, label_bottom, disabled}`; `href` is `null` when disabled |
| `original` | **① 日语原文** as ordered blocks (see below) |
| `translation` | `{blocks, note}` — **② 汉语翻译** (see below) + its `※` note |
| `vocab` | `{rows:[{word, reading, meaning}], note}` — **③ 語彙注釈** |
| `grammar` | `{cards:[{marker, title, desc}], note}` — **④ 文法分析** (`marker` = leading ①②… ) |
| `notes` | **⑤ 资料补注**: `[{label, text}]`; `label` is the bold lead-in or `null`; `text` keeps inline markup |
| `footer` | `<footer>` lines (split on `<br>`) |

### `original` — token blocks

An ordered list mixing two block types so furigana and 白文 quotes interleave
exactly as on the page:

```jsonc
"original": [
  { "type": "paragraph", "tokens": [
      { "base": "公案小説", "ruby": "こうあんしょうせつ" },   // a <ruby> (kanji + reading)
      { "text": "とは、" },                                    // plain run between ruby
      { "base": "犯罪", "ruby": "はんざい" }
  ] },
  { "type": "quote", "text": "拯字希仁、以進士官至礼部侍郎、…" }  // a 白文 block quote (no furigana)
]
```

A source paragraph that contains an inline 白文 quote is split into
`paragraph → quote → paragraph`; rendering the blocks back in order reproduces the
page (the quote is a block element either way). `<br><br>` marks a paragraph break.

### `translation` — text blocks

Same block model, but paragraphs hold plain Chinese text (no tokens). 白文 quotes
are echoed verbatim, not re-translated:

```jsonc
"translation": {
  "blocks": [
    { "type": "paragraph", "text": "所谓“公案小说”，是以犯罪…" },
    { "type": "quote",     "text": "拯字希仁，以进士官至礼部侍郎，…" }
  ],
  "note": "※ 上引鲁迅…"
}
```

## Index schema (`index.json`)

```jsonc
{
  "book": { "title", "author", "publisher", "year",
            "page_title", "h1", "sub", "intro", "footer": [ … ] },
  "chapters": [
    { "number": 1, "number_kanji": "一", "title_ja": "公案小説",
      "head": "第一章 公案小説", "note": "全 5 节 · 已完成 ✅",
      "status": "done",                       // "done" | "in_progress"
      "sections": [ { "num", "href", "title_ja", "summary_zh" }, … ] }
  ],
  "future_chapters": [ { "number_kanji": "二", "title_ja": "公案小説の系譜" }, … ]
}
```

`book.intro` keeps inline HTML (e.g. `<strong>…</strong>`) and is emitted raw, like
`notes[].text`. `chapters[].head`/`note` and `sections[].*` are plain text. The
"後続章節 待补充" block's heading/blurb are fixed boilerplate in `index-template.html`,
not stored here.
