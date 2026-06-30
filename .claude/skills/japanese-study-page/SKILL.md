---
name: japanese-study-page
description: Generate bilingual Japanese study-page HTML from passages of the scanned book 荘司格一『中国の公案小説』 (source text in data/ocr/NN_*.txt). Pages are authored as JSON in data/pages/ and rendered to HTML by work/render.py. Use when converting book passages into the established furigana + Chinese-translation + vocabulary + grammar study format, adding new chapter/passage pages (chNN-M-slug), or updating the study index. Output matches the existing html/ch01-*.html pages.
---

# Japanese study-page generator

Turn a passage of `data/ocr/NN_<title>.txt` into a self-contained bilingual study
page that matches the existing `html/ch01-*.html` pages.

**`data/pages/*.json` is the source of truth; the HTML is generated.** You author the
content as JSON under `data/pages/`, then run `work/render.py` to produce the static
`chNN-M-slug.html` + `index.html` in **`html/`**. Never hand-edit the
generated HTML — edit the JSON and re-render. The JSON schema is in
`data/README.md`; the markup/CSS lives in `template.html` + `index-template.html`
(this folder) and is applied by the renderer. Detailed content conventions are in
`reference.md` — **read `reference.md` before writing content** (furigana rules,
OCR-correction policy, vocab/grammar style, reading gotchas).

## When to use
- "Convert chapter N", "do the next passage", "add a study page for …".
- "Update / rebuild the index".

## Inputs & layout
- Source: `data/ocr/NN_<title>.txt` — clean Japanese prose, **vertical-form punctuation**
  (`︑ ︒ ﹁ ﹂ ﹃ ﹄ ︵ ︶`), `〔PDF p.N〕` markers, embedded **classical-Chinese (白文) quotes
  with OCR errors**.
- Output you author: `data/pages/ch<NN>-<M>-<slug>.json` (one per page) + `data/pages/index.json` (TOC).
- Schema: `data/README.md`. Examples to imitate: `data/pages/ch01-1-teigi-rojin.json` … `ch01-5…json`.
- Naming: `ch<NN>-<M>-<short-romaji-slug>` (NN = chapter ordinal, M = passage number); the
  JSON `filename` is the same stem + `.html`.
- The renderer turns the data into markup — you do **not** write `<ruby>`, tables, nav `<a>`
  tags, etc. by hand; you supply the structured fields below.

## Process

1. **Read the chapter file** `data/ocr/NN_*.txt`. Split it into passages at natural
   topic breaks — aim for ~1–3 source paragraphs each, comparable in size to existing
   pages; a passage may include one 白文 block quote. List the passages (lines → slug → title)
   before generating, so prev/next wiring is known.

2. **Create the page JSON** `data/pages/ch<NN>-<M>-<slug>.json` following the `data/README.md`
   schema (`filename, slug, chapter, section, page_title, h1, sub, nav, original,
   translation, vocab, grammar, notes, footer`). Copy a finished `data/pages/ch01-*.json` as a
   shape reference. Fill the fields per steps 3–8.

3. **① 日语原文** → the `original` blocks (an ordered list of `paragraph`/`quote` blocks):
   - Normalize vertical glyphs (pipe source through `scripts/normalize.py`, or apply the
     map in `reference.md`): `︑→、 ︒→。 ﹁﹂→「」 ﹃﹄→『』 ︵︶→（）`; drop `〔PDF p.N〕`.
   - **Furigana (総ルビ)** lives in the token shape: each kanji compound is a
     `{"base": "公案小説", "ruby": "こうあんしょうせつ"}` token; kana/okurigana/punctuation runs
     between them are `{"text": "とは、"}` tokens. The renderer emits the `<ruby>` tags. See
     `reference.md` for density + tricky readings (e.g. 案贖→あんとく, 所以→ゆえん, 羅燁→らよう).
   - A 白文 quote is its own block: `{"type": "quote", "text": "…"}` (no tokens, no furigana).
     **Correct OCR in the 白文 quotes** against canonical sources (WebSearch / Wikisource);
     store the corrected text, and record every fix for the notes (see step 7).

4. **② 汉语翻译** → `translation.blocks` (same `paragraph`/`quote` model, but paragraphs hold
   plain Chinese `text`, no tokens). Echo each 白文 quote verbatim as a `{"type":"quote","text":…}`
   block — the renderer tints it automatically; do **not** re-translate 白文. Put the
   `※ …` caption in `translation.note`.

5. **③ 語彙注釈** → `vocab.rows`, each `{"word", "reading", "meaning"}`, ONLY for words whose
   **meaning** a Chinese reader can't infer from the kanji: 和语词/訓読 words, 文语·语法 forms,
   同形异义 false-friends, variant/opaque kanji. Skip every meaning-transparent 同形词 (是非,
   判断, 提示, 禅家, 求道者, 取材, 判詞 …) — their readings already come from the ① furigana.
   `vocab.note` is the fixed general line (see `reference.md` §5).

6. **④ 文法分析** → `grammar.cards`, each `{"marker": "①", "title": "…", "desc": "…"}`. Cover
   classical/literary forms (なかろう, ～うる, ～よう, ～ず, 所以, 知られよう, etc.). `grammar.note`
   is the fixed caption.

7. **⑤ 资料补注** → `notes`, each `{"label": "…", "text": "…"}` (label may be `null`): a 本节定位
   entry, scholarly context, and an **OCR订正** entry listing every fix as `底本「X」→「Y」`.
   `text` may contain inline HTML and is emitted raw.

8. **Nav + footer** — `nav.prev`/`nav.next` are `{href, label_top, label_bottom, disabled}`
   (`href: null`, `disabled: true` at a chapter end; the renderer emits a disabled `<span>`).
   Top nav uses `label_top` (`← 上一篇` / `下一篇 →`), bottom uses `label_bottom` (descriptive,
   `← 上一篇：<title>`). `footer` is the list of `<footer>` lines:
   `第<N>章 … · 第<M>節／全<总>節 ｜ …` and `出典：荘司格一『中国の公案小説』（研文出版, 1988）`.

9. **Update `data/pages/index.json`** — add the page to its chapter's `sections`
   (`{num, href, title_ja, summary_zh}`). When a chapter is finished, give it a `chapters[]`
   entry (`head`, `note` `全 M 节 · 已完成 ✅`, `status: "done"`, its `sections`) and remove its
   `future_chapters[]` placeholder.

10. **Render + verify** (from the project root):
    - `python3 work/render.py` — writes the HTML from `data/pages/` into `html/`.
    - `python3 .claude/skills/japanese-study-page/scripts/check.py html` — must report: no residual
      vertical glyphs, all internal links resolve, `<ruby>`/`<rt>` balanced. (Old OCR forms
      legitimately appear inside the `底本「X」→「Y」` notes — that's expected.)
    - Optional round-trip sanity check: `python3 work/extract_data.py` should leave `data/pages/`
      unchanged (the renderer and extractor are inverses).

## Tips
- Generating several passages of one chapter is independent work — you can author the JSON
  files in parallel, then render once. Read `reference.md` first and keep the
  readings/quote-corrections consistent.
- Keep furigana density and section style identical to existing pages; the goal is a uniform
  series. The shared markup/CSS comes from the templates, so consistency is automatic — your
  job is consistent *content* in the JSON.
