#!/usr/bin/env python3
# Split & clean the OCR text layer of 『中国の公案小説』 into per-chapter files.
# Source: pdftotext -raw output (correct reading order; a space between every glyph).
# The PDF stores each scanned 2-page spread twice (pairs 2,3 / 4,5 / ...); we read
# the first of each pair. A chapter can begin on the LEFT page of a spread, so we
# split that spread at the chapter-heading line (intra-spread boundary precision).
import re, os

raw = open('work/all_raw.txt', encoding='utf-8').read().split('\f')
while raw and raw[-1].strip() == '':
    raw.pop()
assert len(raw) == 451, len(raw)
OUT = 'extracted'

CJK = r'　-〿぀-ゟ゠-ヿ㐀-䶿一-鿿豈-﫿︐-︟︰-﹏＀-￯'
SPACE_BETWEEN_CJK = re.compile(rf'(?<=[{CJK}])[ \t]+(?=[{CJK}])')
BRACKETS_RE = re.compile(r'[「」『』﹁﹂﹃﹄〈〉《》【】〔〕()（）［］Jｊ]')
JUNK_RE = re.compile(r"[0-9OIlＯ-ｚ.,'\"`´′″/｜|・()（）〔〕［］\s夕ク勿ﾉりタゎχηソメィヽノ‐\-—　 ]")
SENT_END = tuple('︒。！？!?」』﹂︶﹄）〕')
ORDINALS = ['十八','十七','十六','十五','十四','十三','十二','十一',
            '十','九','八','七','六','五','四','三','二','一']

def norm(s):       return re.sub(r'\s+', '', s)
def bn(s):         return BRACKETS_RE.sub('', s)
def collapse(text):
    for _ in range(3):
        text = SPACE_BETWEEN_CJK.sub('', text)
    return text.strip()
def strip_ord(s):
    for o in ORDINALS:
        if s.startswith(o):
            return s[len(o):]
    return s
def get_lines(pdf):
    return [l for l in raw[pdf-1].splitlines() if l.strip()]

def is_running_header(line, title_norms):
    s = bn(norm(line))
    if not s:
        return True
    for t in sorted({bn(t) for t in title_norms}, key=len, reverse=True):
        if t:
            s = s.replace(t, '')
    for o in ORDINALS:
        s = s.replace(o, '')
    return JUNK_RE.sub('', s) == ''

BMAP = {'「':'[「﹁]','」':'[」﹂Jｊ]','『':'[『﹃]','』':'[』﹄]'}
# ordinals whose glyph this scan-font OCRs to other shapes (used for header stripping)
ORD_VAR = {'六':'(?:六|エハ)', '八':'(?:八|ノヽ|/ヽ)'}
def make_header_re(heading):
    m = re.match(r'^([一二三四五六七八九十]+)　(.+)$', heading)
    if not m:
        return None
    o = ORD_VAR.get(m.group(1), re.escape(m.group(1)))
    tp = ''.join(BMAP.get(c, re.escape(c)) for c in m.group(2))
    return re.compile(rf'\d{{0,3}}{o}{tp}\d{{0,3}}')   # ordinal+title only

def base_title(heading):
    return re.sub(r'^[一二三四五六七八九十]+　', '', heading)

def find_split(pdf, heading):
    """Index in get_lines(pdf) of the chapter-heading line (short line == title,
    optional leading ordinal). 0 if not found / heading at top."""
    tb = bn(norm(base_title(heading)))
    for i, l in enumerate(get_lines(pdf)):
        c = bn(collapse(l))
        if strip_ord(c) == tb and len(c) <= len(tb) + 3:
            return i
    return 0

def clean_lines(lines, title_norms, mode, header_re):
    if mode == 'list':
        while lines and is_running_header(lines[0], title_norms):
            lines = lines[1:]
        return '\n'.join(c for c in (collapse(l) for l in lines) if c)
    norm_lines = []
    for l in lines:
        c = collapse(l)
        if header_re:
            c = header_re.sub('', c)
        if c and not (len(c) <= 14 and is_running_header(c, title_norms)):
            norm_lines.append(c)
    if not norm_lines:
        return ''
    full = max(20, int(0.82 * max(len(c) for c in norm_lines)))
    paras, cur = [], ''
    for c in norm_lines:
        cur += c
        if len(c) < full and c.endswith(SENT_END):
            paras.append(cur); cur = ''
    if cur:
        paras.append(cur)
    return '\n\n'.join(paras)

# (filenum, filename, heading, start_pdf, mode)
SECTIONS = [
    ('01','01_公案小説.txt','一　公案小説',6,'prose'),
    ('02','02_公案小説の系譜.txt','二　公案小説の系譜',10,'prose'),
    ('03','03_龍図公案.txt','三　龍図公案',34,'prose'),
    ('04','04_龍図公案百則.txt','四　「龍図公案」百則',74,'prose'),
    ('05','05_龍図公案の研究.txt','五　「龍図公案」の研究',114,'prose'),
    ('06','06_百家公案.txt','六　百家公案',134,'prose'),
    ('07','07_律条公案.txt','七　律条公案',158,'prose'),
    ('08','08_律条公案四十二則.txt','八　「律条公案」四十二則',186,'prose'),
    ('09','09_皇明諸司廉明奇判公案伝.txt','九　皇明諸司廉明奇判公案伝',204,'prose'),
    ('10','10_皇明諸司公案.txt','十　皇明諸司公案',238,'prose'),
    ('11','11_明鏡公案.txt','十一　明鏡公案',266,'prose'),
    ('12','12_詳情公案.txt','十二　詳情公案',290,'prose'),
    ('13','13_詳刑公案.txt','十三　詳刑公案',316,'prose'),
    ('14','14_海剛峯先生居官公案伝.txt','十四　海剛峯先生居官公案伝',336,'prose'),
    ('15','15_明代公案小説の内容と成立.txt','十五　明代公案小説の内容と成立',370,'prose'),
    ('16','16_明代公案小説における僧尼説話.txt','十六　明代公案小説における僧尼説話',384,'prose'),
    ('17','17_本朝桜陰比事と中国の公案小説.txt','十七　「本朝桜陰比事」と中国の公案小説',400,'prose'),
    ('18','18_清代の公案小説.txt','十八　清代の公案小説',416,'prose'),
    ('19','19_類似説話一覧.txt','類似説話一覧',430,'list'),
    ('20','20_関連篇目.txt','関連篇目',440,'list'),
    ('21','21_あとがき.txt','あとがき',446,'prose'),
    ('22','22_索引・奥付.txt','索引・奥付（巻末索引・著者紹介・奥付）',450,'list'),
]
LAST_PDF = 450
os.makedirs(OUT, exist_ok=True)
starts = [s[3] for s in SECTIONS]

def title_norms_for(heading):
    b = base_title(heading)
    return {norm(heading), norm(b), norm(b.replace('「','').replace('」',''))}

manifest = []
for i, (num, fname, heading, start, mode) in enumerate(SECTIONS):
    nxt = starts[i+1] if i+1 < len(SECTIONS) else None
    tnorms, hre = title_norms_for(heading), make_header_re(heading)
    own_split = find_split(start, heading)
    # ordered list of (pdf, lines) blocks for this section
    blocks = [(start, get_lines(start)[own_split:])]
    last_full = (nxt - 2) if nxt else LAST_PDF
    for pdf in range(start + 2, last_full + 1, 2):
        blocks.append((pdf, get_lines(pdf)))
    if nxt:                                   # this section's tail on next opener spread
        nsplit = find_split(nxt, SECTIONS[i+1][2])
        if nsplit > 0:
            blocks.append((nxt, get_lines(nxt)[:nsplit]))
    parts = [f'　　{heading}', '']
    for pdf, lines in blocks:
        body = clean_lines(lines, tnorms, mode, hre)
        parts.append(f'〔PDF p.{pdf}〕')
        if body:
            parts.append(body)
        parts.append('')
    open(os.path.join(OUT, fname), 'w', encoding='utf-8').write('\n'.join(parts).rstrip() + '\n')
    manifest.append((fname, blocks[0][0], blocks[-1][0]))

# front matter (cover p1 is image-only -> inject known bookplate text) + title page + TOC
cover = ('　　中国の公案小説\n\n荘司格一　著\n\n研文出版\n\n'
         '（注：本PDFの1ページ目は画像のみでテキスト層がないため、上記は標題紙記載の書誌情報。）\n')
fm = ['　　前付（表紙・標題紙・目次）', '', cover]
for pdf in (2, 4):
    fm.append(f'〔PDF p.{pdf}〕')
    fm.append(clean_lines(get_lines(pdf), set(), 'list', None))
    fm.append('')
open(os.path.join(OUT, '00_前付.txt'), 'w', encoding='utf-8').write('\n'.join(fm).rstrip() + '\n')
manifest.insert(0, ('00_前付.txt', 1, 4))

for fname, s, e in manifest:
    c = len(open(os.path.join(OUT, fname), encoding='utf-8').read())
    print(f'{fname:36s} p{s:>3}..p{e:<3}  {c:>7} chars')
