# Reference — conventions for the study pages

Detailed rules behind `SKILL.md`. Read this before writing content.

Pages are authored as JSON in `data/pages/` (schema in `data/README.md`) and rendered to HTML by
`work/render.py`. The HTML snippets below show what the renderer **emits**; when authoring,
put the content into the corresponding JSON fields (e.g. furigana as `{base, ruby}` tokens,
not literal `<ruby>` tags). The content rules here apply regardless of format.

## 1. Punctuation normalization (vertical → horizontal)

Source text is vertical-writing OCR. Map before rendering:

| source | → | use |
|---|---|---|
| `︑` | → | `、` |
| `︒` | → | `。` |
| `﹁ ﹂` | → | `「 」` |
| `﹃ ﹄` | → | `『 』` |
| `︵ ︶` | → | `（ ）` |
| `〔PDF p.N〕` | → | (delete) |

`scripts/normalize.py` does this (stdin → stdout). The book also uses `〝 〟` for emphasis
quotes (e.g. 〝説公案〟) — keep those as-is; if the OCR shows `″ … ″` with stray spaces, render
them as `〝…〟`.

## 2. Furigana (総ルビ)

- Give **every kanji compound** a reading — in the JSON, a `{"base": "漢字", "ruby": "かな"}`
  token (the renderer emits `<ruby>漢字<rt>かな</rt></ruby>`). Match the density of the existing
  pages (proper nouns, book/篇 titles, and single-kanji verbs/nouns all get readings).
- Group by sensible units: `<ruby>公案小説<rt>こうあんしょうせつ</rt></ruby>`, not one ruby per char.
- Verb stems: ruby the kanji only — `<ruby>用<rt>もち</rt></ruby>いる`, `<ruby>述<rt>の</rt></ruby>べる`.
- Book/篇 titles in the Japanese flow get ruby (`<ruby>中国小説史略<rt>ちゅうごくしょうせつしりゃく</rt></ruby>`);
  白文 block quotes do **not** (they sit in `.chinese-quote`).
- Kana already in the source (はなはだ, まま, ところで …) stays kana.

### Reading gotchas seen in this book
案贖→あんとく（＝案牘）· 所以→ゆえん · 寓目→ぐうもく · 躊躇→ちゅうちょ · 禅家→ぜんけ ·
求道者→ぐどうしゃ · 参究→さんきゅう · 繁昌記→はんじょうき · 都城紀勝→とじょうきしょう ·
夢梁録→むりょうろく · 古杭夢遊録→ここうむゆうろく · 酔翁談録→すいおうだんろく ·
小説開闢→しょうせつかいびゃく · 羅燁→らよう · 外題→げだい · 私情公案→しじょうこうあん ·
花判公案→かはんこうあん · 指腹為婚→しふくいこん · 枢密→すうみつ · 季子→きし ·
駈落ち→かけおち · 闕文→けつぶん · 判詞→はんし · 詼諧→かいかい · 駢語→べんご ·
清平山堂話本→せいへいさんどうわほん · 簡帖和尚→かんじょうおしょう · 公案伝奇→こうあんでんき ·
子部小説→しぶしょうせつ · 知られよう→しられよう.

## 3. 白文 (classical-Chinese) quotes & OCR correction — important

The OCR mangles dense Chinese. **Correct each quote against the canonical text** (use
WebSearch / WebFetch on 维基文库/wikisource, baidu/wikipedia) before rendering, then list
every change in 资料补注 as `底本「X」→「Y」`.

- Render the quote in the **book's Japanese-shinjitai forms** (説 為 図 学 独 etc.) with `、` between
  clauses and `。` at the end — match the existing pages, not simplified Chinese.
- Preserve the author's own editorial notes (e.g. `〔疑是夏〕`).
- If a character can't be confidently resolved (rare 篇目, garbled romaji), keep the source form
  and flag the uncertainty in the notes rather than inventing a correction.

Corrections already established (reuse for consistency):
- Lu Xun《中国小説史略》第二十七篇 包拯 quote: `堡→拯`, `三百十二→三百十六`, `己有→已有`,
  `審鳥盆鬼→審烏盆鬼`, `記握借→記拯借`, `十巻日→十巻曰`, `儘→僅`, `併称→仍称`, `藍本臭→藍本矣`.
- 『酔翁談録』: `羅嘩→羅燁`, `小説開間→小説開闢`; drop a spurious leading `言` before 石頭孫立.
- 私情公案/花判公案: `星毒→星可`, `該諧→詼諧`, `餅語→駢語`, `閥文→闕文`, `花判とよ（れ→花判とよばれ`.
- General OCR slips: small-kana (`でぁる→である`), `己/已`, `日/曰`, `鳥/烏`, stray fullwidth `Ｃ`.

## 4. 汉语翻译

- Translate the Japanese prose into natural Chinese. Keep terms-of-art (公案, 判詞, 花判 …).
- Echo each 白文 quote verbatim as a `quote` block in `translation.blocks` (the renderer tints
  it, `background:#f3efe2;`); do not re-translate 白文 — note this in `translation.note`. A short
  modern-Chinese gist of a long/hard quote can go in 资料补注 instead.

## 5. 語彙注釈 (vocabulary table)

The table is a **meaning aid for Chinese readers**, not a reading list — every kanji already carries
furigana in ①, so a word earns a row only when its *meaning* cannot be guessed from the kanji.

- **Add a row only for** words whose meaning a Chinese reader can't infer from the characters:
  和语词/訓読 words in kana or kun-yomi (うかがう, はなはだ, ふるい, あらまし, まま見られる, ところで),
  文语·语法 forms (～にすぎぬ, ～ではなかろう, 見うる, よびうる, ～としてよい, 知られよう),
  同形异义 false-friends (所以→ゆえん “缘由”≠“因此”; 体裁→たいさい “外观/样式”), and
  variant/opaque kanji whose sense is misleading or non-standard (案贖＝案牘, 外題, 闕文, 駢語).
- **Skip every meaning-transparent 同形词**, common or not — anything a Chinese reader reads straight
  off the kanji: 是非, 判断, 提示, 禅家, 求道者, 文意, 取材, 大同小異, 以来, 庶民, 実態, 官府,
  話本, 判詞, 枢密, 子部小説 … Their readings still appear on the ① furigana, so nothing is lost.
- `.small-note` is one fixed general line, **not** a per-word skip list:
  `※ 本表仅收录中文读者较难推断的词汇（和语词、文语/语法形式、同形异义词等）；其义可由汉字直接推知的同形词已省略，读音见原文振假名。`
- Columns: 词 / 读音(平假名) / 中文释义.
- **Layout**: ① 原文 and ③ 語彙 share a two-column row (`.content-grid` → `.text-col` / `.vocab-col`);
  ③ renders to the **right** of the text. ② 翻译 and ④ 文法 stay full-width below; the grid stacks to a
  single column on screens ≤900px. See `template.html` (`.content-grid`).

## 6. 文法分析 (grammar cards)

- Number with circled digits ① ② ③ …; title = the pattern, desc = a quoted example from the
  passage + a concise Chinese explanation.
- Prioritize classical/literary residue: `～なかろう`, `～うる(得る)`, 推量 `～よう/であろう`,
  中止 `～ず`, `所以(ゆえん)`, `知られよう`, `～ながらも`, 漢文訓読調 引用 `～と述べる/と記している`,
  passive `～られる`, `～にすぎぬ`, `～もうなずける`, `～はもとより`.
- ~6–10 cards per passage (fewer for short closing passages).

## 7. Per-page boilerplate

- `<title>`: `日语学习：<topic> ·『中国の公案小説』第<N>章<circled-M> · 学术日语解析`
- `.sub`: `第<N>章 <chaptername> · 第<M>節／全<总>節 ｜ 日语原文（総ルビ付き）· 汉语翻译 · 单词注释 · 语法分析`
- Footer line 2: `出典：荘司格一『中国の公案小説』（研文出版, 1988）· 第<N>章`
- Nav active link: `<a class="nav-link" href="…">← 上一篇</a>` / `下一篇 →`;
  disabled end: `<span class="nav-link disabled">← 已是第一篇</span>` / `下一篇 →` /
  `已是本章最后一篇`.

## 8. index.html

- Finished chapter = its own `.chapter-block` with a `.chapter-head`, a `.chapter-note`
  (`全 M 节 · 已完成 ✅`), and a `.toc-list` of `<a class="toc-card">` rows
  (`.toc-num` / `.toc-ja` Japanese title / `.toc-zh` one-line Chinese summary).
- Not-yet-done chapters live as `.future-chip`s in the 待补充 block; remove a chip when its
  chapter is completed.
- Chapter order follows `data/ocr/README.txt` (一…十八 + 附録).
