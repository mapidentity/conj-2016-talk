#!/usr/bin/env python3
# Build a self-contained, print-ready (A4 landscape) presenter script for the
# Clojure/conj live-coding talk. One beat per page: projector-left, speaker-
# notes-right. Nothing in this file is talk text — everything is read from:
#
#   ../livecode-talk.md        the run-sheet: sections, spoken lines, directions.
#                              Page boundaries are `<!-- page "Title" … -->`
#                              comments (invisible in rendered markdown); the
#                              lines inside the comment say what is ON THE SCREEN
#                              for that page (see README.md, "Page markers").
#                              It also holds the bookend slides, as
#                              `<!-- slide N · name -->` … `<!-- /slide -->` blocks
#                              (build_slides.py renders them; see README.md, "Slides").
#   ../livecode-cheatsheet.md  code blocks, addressed by label (§2a, §2d#2) or by
#                              a line they contain (~"(defn tr-load!").
#   ../figures/talk/*.png      screenshots, by name (capture.cjs).
#
# Code is syntax-highlighted at build time; screenshots are embedded as resized
# base64 PNGs so the single .html is portable.
import base64, html, io, re
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent   # the talk/ directory
FIG = ROOT / "figures" / "talk"
OUT = ROOT / "livecode-presenter.html"

# ---------------------------------------------------------------- images -----
def data_uri(name, maxw=1500):
    im = Image.open(FIG / f"{name}.png").convert("RGB")
    if im.width > maxw:
        h = round(im.height * maxw / im.width)
        im = im.resize((maxw, h), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"

IMG = {}
def img(name):
    if name not in IMG:
        IMG[name] = data_uri(name)
    return IMG[name]

# ------------------------------------------------------------ highlight ------
import sys; sys.path.insert(0, str(Path(__file__).resolve().parent))
from highlight import esc, hl_clj, HL                  # shared with build_slides.py

# --------------------------------------------------------------- blocks ------
def code_block(src, lang="clojure", tag=None, cap=None, file=None):
    body = HL[lang](src.rstrip("\n"))
    pill = f'<span class="tag t-{tag.lower()}">{tag}</span>' if tag else ""
    fl = f'<span class="file">{esc(file)}</span>' if file else ""
    head = f'<div class="cbar">{pill}{fl}</div>' if (pill or fl) else ""
    capd = f'<div class="ccap">{cap}</div>' if cap else ""
    return f'<div class="code">{head}<pre>{body}</pre>{capd}</div>'

def repl_block(pairs, title="REPL"):
    rows = []
    for form, out in pairs:
        rows.append(f'<div class="rform">{hl_clj(form)}</div>')
        if out is not None:
            rows.append(f'<div class="rout"><span class="ra">=&gt;</span> {hl_clj(out)}</div>')
    return f'<div class="repl"><div class="rlbl">{title}</div>{"".join(rows)}</div>'

def slide(n, inner):
    return f'<div class="slide"><div class="sn">slide {n}</div>{inner}</div>'

def shot(name, cap=None, cls=""):
    capd = f'<figcaption>{cap}</figcaption>' if cap else ""
    return f'<figure class="shot {cls}"><img src="{img(name)}" alt="{name}">{capd}</figure>'

def note(txt):   # small caption line in the projector column
    return f'<div class="pnote">{txt}</div>'

# speaker-column pieces
def say(txt):    return f'<p class="say">{txt}</p>'
def dirn(label, txt=""):  # stage direction
    t = f' {txt}' if txt else ""
    return f'<p class="dir"><span class="dl">{label}</span>{t}</p>'
def beat(txt):   return f'<p class="beat">{txt}</p>'
def cue(txt):    return f'<p class="cue">▶ {txt}</p>'

def page(sec, title, time, marker, projector, speaker, layout="split", cls=""):
    mk = f'<span class="mk">{marker}</span>' if marker else ""
    tm = f'<span class="tm">{time}</span>' if time else ""
    head = (f'<div class="phead"><div class="pl"><span class="sec">{sec}</span>'
            f'<span class="ptitle">{title}</span></div>'
            f'<div class="pr">{mk}{tm}</div></div>')
    if layout == "full":
        return f'<section class="pg {cls}"><div class="pnum"></div>{head}<div class="full">{projector}</div></section>'
    return (f'<section class="pg {cls}"><div class="pnum"></div>{head}'
            f'<div class="beat2"><div class="projector">{projector}</div>'
            f'<div class="speaker">{speaker}</div></div></section>')

PAGES = []
def add(*a, **k): PAGES.append(page(*a, **k))


CSS = r"""
@page { size: A4 landscape; margin: 0; }
* { box-sizing: border-box; }
html, body { margin:0; padding:0; }
body { font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
       color:#1d1a26; background:#7d7a8c; counter-reset:pgc; }
.pg { position:relative; width:297mm; min-height:210mm; background:#fff;
      padding:9mm 11mm 10mm; display:flex; flex-direction:column;
      counter-increment:pgc; break-after:page; }
.pnum::after { content:counter(pgc); position:absolute; bottom:4mm; right:11mm;
      font:8pt ui-monospace,monospace; color:#c3bdd0; }
@media screen { .pg { margin:9mm auto; box-shadow:0 4px 22px rgba(0,0,0,.4); } }
@media print  { body{background:#fff;} .pg{ margin:0; box-shadow:none; } }

.phead { display:flex; justify-content:space-between; align-items:flex-end; gap:8mm;
         border-bottom:1.5px solid #e5e2ef; padding-bottom:2.5mm; margin-bottom:4.5mm; }
.sec { display:block; font:700 8.5pt ui-sans-serif,system-ui; letter-spacing:.09em;
       text-transform:uppercase; color:#6b5fd6; margin-bottom:.5mm; }
.ptitle { font-size:15.5pt; font-weight:700; letter-spacing:-.01em; line-height:1.15; }
.pr { text-align:right; white-space:nowrap; }
.mk { font:600 9pt ui-monospace,monospace; color:#fff; background:#3f3a52;
      padding:2px 7px; border-radius:5px; margin-left:6px; }
.tm { font:700 11pt ui-monospace,monospace; color:#9a93b5; margin-left:9px; }

.beat2 { display:grid; grid-template-columns:1.42fr 1fr; gap:8mm; flex:1; min-height:0; }
.projector, .speaker { min-width:0; display:flex; flex-direction:column; gap:4mm; }
.speaker { border-left:2px solid #efece4; padding-left:6mm; gap:0; }
.projector::before { content:"ON THE SCREEN"; display:block; font:700 7.5pt ui-sans-serif;
      letter-spacing:.13em; color:#bdb7ca; margin-bottom:1mm; }
.speaker::before { content:"WHAT YOU SAY / DO"; display:block; font:700 7.5pt ui-sans-serif;
      letter-spacing:.13em; color:#c7bfae; margin-bottom:2.5mm; }
.full { flex:1; }

/* --- slide card (dark, as projected) --- */
.slide { background:#16141f; color:#ece9f1; border-radius:9px; padding:7mm 8mm;
         position:relative; font-size:11pt; line-height:1.42; }
.slide .sn { position:absolute; top:3.5mm; right:5mm; font:600 7.5pt ui-monospace,monospace; color:#565070; }
.slide h1 { font-size:20pt; line-height:1.12; margin:0 0 3.5mm; letter-spacing:-.01em; }
.slide h2 { font-size:15.5pt; line-height:1.2; margin:0 0 3mm; letter-spacing:-.01em; }
.slide p { margin:0 0 2.5mm; }
.slide .ac { color:#8b7ff5; } .slide .gr { color:#34d399; }
.slide ul { margin:1mm 0 0; padding-left:5mm; display:grid; gap:1.8mm; }
.slide li::marker { color:#8b7ff5; }
.slide code { background:#211d30; color:#e0e7ff; padding:.05em .32em; border-radius:4px; font-size:.9em;
              font-family:ui-monospace,monospace; }
.slide pre { background:#211d30; padding:3mm 4mm; border-radius:6px; font:9pt/1.5 ui-monospace,monospace;
             overflow-x:auto; margin:2mm 0; color:#e0e7ff; }
/* box-drawing diagrams: rules must sit tight against their sides to read as a box */
.slide pre.diagram { line-height:1.05; font-size:8.6pt; }
/* ```diff fences: context recedes, additions get a band */
.slide pre .cx { display:block; color:#8d86a4; }
.slide pre .ad { display:block; color:#e8fff5; background:rgba(52,211,153,.12);
                 box-shadow:-4mm 0 0 rgba(52,211,153,.12), 4mm 0 0 rgba(52,211,153,.12); }
.slide pre .rm { display:block; color:#f6d9d9; background:rgba(248,113,113,.12); }
/* inline figures (```svg fences) */
.slide .figure { margin:2mm 0; }
.slide .figure svg { width:100%; height:auto; display:block; }
.slide .sub { color:#9d94b8; } .slide .big { font-size:1.12em; }
.slide .rule { border-left:4px solid #8b7ff5; padding:.5mm 0 .5mm 3.5mm; }
/* a remark on the block above — boxed, so it reads as an aside, not as body copy */
.slide .note { border-left:3px solid #8b7ff5; background:rgba(139,127,245,.10);
               border-radius:0 1.5mm 1.5mm 0; padding:1mm 2.5mm; color:#cdc5e4; font-size:.92em; }
.slide table { border-collapse:collapse; font-size:9.5pt; margin:1mm 0; }
.slide th, .slide td { text-align:left; padding:1.3mm 6mm 1.3mm 0; }
.slide th { color:#9d94b8; font-weight:600; } .slide tr+tr { border-top:1px solid #2c2740; }
.slide .strike { text-decoration:line-through; opacity:.5; }
.steps { display:grid; grid-template-columns:1fr 1fr; gap:1.4mm 6mm; font-size:9.5pt; }
.steps b { color:#8b7ff5; font-variant-numeric:tabular-nums; margin-right:2mm; }

/* --- code card (light) --- */
.code { background:#f7f6fb; border:1px solid #e6e3f0; border-radius:7px; overflow:hidden; }
.cbar { display:flex; align-items:center; gap:7px; padding:1.8mm 3mm; background:#efedf7;
        border-bottom:1px solid #e6e3f0; }
.tag { font:700 7.5pt ui-monospace,monospace; letter-spacing:.05em; padding:1.5px 6px;
       border-radius:4px; color:#fff; }
.t-type{background:#14915f;} .t-paste{background:#5b7cc7;} .t-checkout{background:#c67a1e;}
.file { font:600 8pt ui-monospace,monospace; color:#8a85a0; }
.code pre { margin:0; padding:2.6mm 4mm; font:8.6pt/1.46 ui-monospace,"JetBrains Mono",Menlo,monospace;
            white-space:pre-wrap; overflow-wrap:break-word; color:#2a2740; }
.ccap { padding:1.8mm 3mm; font-size:8.5pt; line-height:1.4; color:#6f6a82;
        border-top:1px dashed #e0dcee; background:#fbfafe; }
.cm{color:#9a94ad;font-style:italic;} .st{color:#1f7a4d;} .kw{color:#b5551f;}
.bi{color:#6b4fd0;font-weight:600;} .mt{color:#a84a8f;} .at{color:#b5551f;}

/* --- repl card (dark) --- */
.repl { background:#12131a; color:#dfe3ec; border-radius:7px; padding:2mm 4mm 2.5mm;
        font:9.3pt/1.55 ui-monospace,monospace; }
.rlbl { font:700 7.5pt ui-monospace,monospace; color:#7a86a8; letter-spacing:.1em; margin:1mm 0 2mm; }
.rform { white-space:pre-wrap; } .rout { color:#9fb0c8; white-space:pre-wrap; margin:.3mm 0 2.5mm; }
.ra { color:#5aa06f; }
.repl .cm{color:#6f7890;} .repl .st{color:#7ec699;} .repl .kw{color:#e0a06a;}
.repl .bi{color:#b7a5ff;} .repl .mt{color:#e28ac0;}
.slide pre .cm{color:#6f7890;} .slide pre .st{color:#7ec699;} .slide pre .kw{color:#e0a06a;}
.slide pre .bi{color:#b7a5ff;} .slide pre .mt{color:#e28ac0;} .slide pre .at{color:#e0a06a;}

/* --- screenshots --- */
.shot { margin:0; border:1px solid #e2ded2; border-radius:6px; overflow:hidden; background:#f6f4ef; }
.shot img { display:block; width:100%; height:auto; }
.shot.tall { text-align:center; background:#f6f4ef; }
.shot.tall img { width:auto; max-height:118mm; margin:0 auto; }
.shot.hero.tall img { max-height:150mm; }
.shot figcaption { font-size:8pt; color:#7a7568; padding:1.5mm 3mm; background:#efece3;
                   border-top:1px solid #e2ded2; }
.trip { display:grid; grid-template-columns:1fr 1fr; gap:3mm; align-items:start; }
.trip .shot { text-align:center; }
.trip .shot img { width:auto; max-height:86mm; margin:0 auto; }

.pnote { font-size:8.7pt; line-height:1.4; color:#6f6a82; padding-left:2.5mm; border-left:2px solid #e0dcee; }
.pnote b { color:#4a4560; }

/* --- speaker column --- */
.say { font-size:10.4pt; line-height:1.5; margin:0 0 2.6mm; color:#2c2820; }
.say b { color:#141109; }
.dir { font-size:9pt; line-height:1.42; margin:0 0 2.2mm; color:#6a6555; }
.dl { font:700 7pt ui-monospace,monospace; letter-spacing:.03em; text-transform:uppercase;
      color:#6b5fd6; background:#efecfa; padding:1px 5px; border-radius:4px; margin-right:5px;
      vertical-align:1px; }
.beat { font-size:9.8pt; line-height:1.45; font-style:italic; color:#8a5a1e;
        border-left:3px solid #e6b871; padding-left:4mm; margin:0 0 2.6mm; }
.cue { font-size:9.5pt; line-height:1.4; color:#127a52; margin:0 0 2.2mm; font-weight:600; }

/* --- cover + reference pages --- */
.cover { flex:1; display:flex; flex-direction:column; }
.cover h1 { font-size:33pt; line-height:1.08; letter-spacing:-.02em; margin:0 0 3mm; }
.cover h1 code { font-family:ui-monospace,monospace; font-size:.82em; background:#f0eef8;
                 padding:.02em .2em; border-radius:6px; }
.cover .csub { font-size:13pt; color:#5b5668; margin:0 0 1mm; }
.cover .cmeta { font-size:10.5pt; color:#8a85a0; margin:0 0 7mm; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:8mm; margin-top:auto; }
.legend h3, .timing h3 { font:700 9pt ui-sans-serif; letter-spacing:.08em; text-transform:uppercase;
      color:#6b5fd6; margin:0 0 3mm; border-bottom:1.5px solid #e5e2ef; padding-bottom:1.5mm; }
.legend dl { display:grid; grid-template-columns:auto 1fr; gap:2.2mm 4mm; margin:0; font-size:9.7pt; }
.legend dt { } .legend dd { margin:0; color:#4a4560; line-height:1.35; }
.timing table { border-collapse:collapse; width:100%; font-size:9.6pt; }
.timing td { padding:1.4mm 2mm; border-bottom:1px solid #efedf5; }
.timing td.t2 { text-align:right; font:600 9pt ui-monospace,monospace; color:#8a85a0; white-space:nowrap; }
.timing td.t3 { text-align:right; font:700 8.5pt ui-monospace,monospace; color:#14915f; white-space:nowrap; }
.reflist { columns:2; column-gap:9mm; font-size:9.6pt; line-height:1.5; }
.reflist p { margin:0 0 3mm; break-inside:avoid; }
.reflist b { color:#6b5fd6; }
.qa { font-size:9.7pt; line-height:1.45; }
.qa .q { font-weight:700; color:#3a3550; }
.qa p { margin:0 0 3mm; break-inside:avoid; }
.setup { font-size:10.4pt; line-height:1.5; }
.setup ol { margin:0; padding-left:6mm; } .setup li { margin:0 0 3mm; }
.setup b { color:#6b5fd6; }
.two { columns:2; column-gap:9mm; }
.two > * { break-inside:avoid; }
h4.blk { font:700 9.5pt ui-sans-serif; color:#3a3550; margin:0 0 2mm; }
"""

CSS += r"""
/* --- markdown-derived bits --- */
q { quotes: "\201C" "\201D"; }
.dir q { color:#2c2820; font-size:10pt; }
.say .dl, .beat .dl { margin-right:5px; }
.doc { font-size:10pt; line-height:1.5; }
.doc p { margin:0 0 2.6mm; } .doc ul, .doc ol { margin:0 0 2.6mm; padding-left:6mm; } .doc li { margin:0 0 1.8mm; }
.doc table { border-collapse:collapse; font-size:9.4pt; margin:0 0 3mm; }
.doc td, .doc th { text-align:left; padding:1mm 4mm 1mm 0; border-bottom:1px solid #efedf5; }
.doc code { background:#f0eef8; padding:.02em .3em; border-radius:4px; font-size:.92em; }
.doc h3 { font:700 9.5pt ui-sans-serif; color:#3a3550; margin:0 0 2mm; }
.doc .q { font-weight:700; color:#3a3550; }
.doc li, .doc p, .doc h3 { break-inside:avoid; } .doc.two > ol, .doc.two > ul { break-inside:auto; }
.trip .shot img { width:100%; }
/* `compact` page flag: a page that overflows by a few lines, kept whole */
.pg.compact .say { font-size:9.7pt; } .pg.compact .dir { font-size:8.5pt; } .pg.compact .beat { font-size:9.1pt; }
.pg.compact .repl { font-size:8.6pt; } .pg.compact .code pre { font-size:8pt; } .pg.compact .slide { font-size:10pt; }
"""
HEAD = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Where Did This &lt;div&gt; Come From? — presenter script</title>"
        f"<style>{CSS}</style></head><body>")
TAIL = "</body></html>"

# ============================================================ SOURCES ========
import shlex, textwrap
SRC_TALK  = ROOT / "livecode-talk.md"
SRC_CHEAT = ROOT / "livecode-cheatsheet.md"
import build_slides                              # the run-sheet's slide blocks

# ------------------------------------------------------- markdown inline -----
def md_inline(s):
    """The subset of inline markdown the run-sheet uses → HTML.
    `code` (with \" unescaped inside), **bold**, *em*, **[stage marker]** pills,
    "spoken" → <q>. Unpaired quotes (a quote that runs across paragraphs) are
    rendered as curly quotes as-is."""
    codes = []
    def stash(m):
        codes.append(f'<code>{esc(m.group(1).replace(chr(92)+chr(34), chr(34)))}</code>')
        return f"\x00{len(codes)-1}\x00"
    s = re.sub(r'`([^`]+)`', stash, s)
    s = esc(s)
    s = re.sub(r'"([^"]+)"', r'<q>\1</q>', s)
    s = s.replace('"', '&ldquo;') if s.count('"') == 1 and s.startswith('"') else s.replace('"', '&rdquo;')
    s = re.sub(r'\*\*\[(.+?)\]\*\*', r'<span class="dl">\1</span>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<i>\1</i>', s)
    s = re.sub(r'\x00(\d+)\x00', lambda m: codes[int(m.group(1))], s)
    return s

def blocks_of(lines):
    """Group markdown lines into blocks: ('quote'|'list'|'table'|'para', lines)."""
    out, cur = [], []
    def flush():
        if cur: out.append(list(cur)); cur.clear()
    item = re.compile(r'^(?:[-*]|\d+\.)\s')
    for ln in lines:
        if not ln.strip(): flush(); continue
        if cur and item.match(ln) and not item.match(cur[0]): flush()   # list right after a paragraph
        cur.append(ln)
    flush()
    typed = []
    for b in out:
        t = ("quote" if b[0].startswith(">") else
             "list"  if re.match(r'^(\s*[-*]|\s*\d+\.)\s', b[0]) else
             "table" if b[0].startswith("|") else "para")
        typed.append((t, b))
    return typed

def list_items(b):
    """Split a list block into items (each a joined string, marker stripped)."""
    items = []
    for ln in b:
        m = re.match(r'^(?:[-*]|(\d+)\.)\s+(?:\[ \]\s+)?(.*)$', ln)
        if m:
            items.append([m.group(1), m.group(2)])
        else:
            items[-1][1] += " " + ln.strip()
    return items

PILL = re.compile(r'^\*\*\[(.+?)\]\*\*\s*')          # **[stage marker]** …
BOLD_LEAD = re.compile(r'^\*\*([^*\[]{1,28}?)\*\*:?\s+')  # **TYPE (1)**: … / **TYPE** …

def speaker_html(lines):
    """Run-sheet markdown for one page → the speaker column (say / dir / beat)."""
    html_parts, open_quote = [], False
    def para(text, pill=None):
        nonlocal open_quote
        spoken = text.startswith('"') or open_quote
        if text.count('"') % 2 == 1: open_quote = not open_quote
        cls = "say" if spoken else "dir"
        pl = f'<span class="dl">{md_inline(pill)}</span>' if pill else ""
        return f'<p class="{cls}">{pl}{md_inline(text)}</p>'
    for t, b in blocks_of(lines):
        if t == "quote":
            html_parts.append(f'<p class="beat">{md_inline(" ".join(l.lstrip("> ").strip() for l in b))}</p>')
        elif t == "list":
            for num, text in list_items(b):
                m = BOLD_LEAD.match(text)
                if m: html_parts.append(para(text[m.end():], m.group(1)))
                elif num: html_parts.append(para(text, num))
                else: html_parts.append(para(text))
        else:
            text = " ".join(l.strip() for l in b)
            m = PILL.match(text) or BOLD_LEAD.match(text)
            if m: html_parts.append(para(text[m.end():], m.group(1)))
            else: html_parts.append(para(text))
    return "".join(html_parts)

def doc_html(lines, qa=False):
    """Run-sheet markdown → a reference page (real lists, tables, checklists)."""
    out = []
    for t, b in blocks_of(lines):
        if t == "quote":
            out.append(f'<p class="beat">{md_inline(" ".join(l.lstrip("> ").strip() for l in b))}</p>')
        elif t == "table":
            rows = [r for r in b if not re.match(r'^\|\s*-', r)]
            trs = []
            for i, r in enumerate(rows):
                cells = [md_inline(c.strip()) for c in r.strip().strip("|").split("|")]
                tag = "th" if i == 0 else "td"
                trs.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
            out.append(f'<table>{"".join(trs)}</table>')
        elif t == "list":
            items = list_items(b)
            if qa:
                for _, text in items:
                    m = re.match(r'^\*\*"(.+?)"\*\*\s*(.*)$', text)
                    q, a = (m.group(1), m.group(2)) if m else ("", text)
                    out.append(f'<p><span class="q">{md_inline(q)}</span> {md_inline(a)}</p>')
            else:
                ordered = items[0][0] is not None
                check = "☐ " if re.match(r'^\s*[-*]\s+\[ \]', b[0]) else ""
                lis = "".join(f"<li>{check}{md_inline(t)}</li>" for _, t in items)
                out.append(f"<ol>{lis}</ol>" if ordered else f"<ul>{lis}</ul>")
        elif b[0].startswith("#"):
            out.append(f'<h3>{md_inline(b[0].lstrip("# "))}</h3>')
        else:
            out.append(f'<p>{md_inline(" ".join(l.strip() for l in b))}</p>')
    return "".join(out)

# ------------------------------------------------------------ run-sheet ------
SEC_RE = re.compile(r'^## (§\d+) · (.+?) \((\d+:\d+)–(\d+:\d+)\)\s*(?:→\s*`([^`]+)`|—\s*(.+))?')
PAGE_RE = re.compile(r'<!--\s*page\s+"([^"]+)"((?:\s+(?:@\S+|\[[^\]]+\]|compact))*)\s*\n?(.*?)-->', re.S)

def parse_talk():
    text = build_slides.strip_slides(SRC_TALK.read_text(encoding="utf-8"))   # slide blocks are not speech
    title = re.match(r'# (.+?)(?: — .*)?$', text.split("\n", 1)[0]).group(1)
    # split into H2 sections
    parts = re.split(r'^## ', text, flags=re.M)
    sections = []
    for part in parts[1:]:
        heading, _, body = part.partition("\n")
        sections.append((heading.strip(), body.strip("\n").rstrip("-").rstrip("\n")))
    return title, sections

def talk_pages(heading, body):
    """One § section → list of page dicts (title, time, marker, items, speaker-md)."""
    m = SEC_RE.match("## " + heading)
    sec_id, sec_title, t0, t1, step, other = m.groups()
    sec_label = f"{sec_id} · {sec_title}"
    default_marker = step or (other.split(",")[0].strip() if other else "demo")
    pages, pos, pending_pre = [], 0, ""
    matches = list(PAGE_RE.finditer(body))
    if not matches:
        raise SystemExit(f"{sec_id}: no <!-- page … --> markers")
    pre = body[:matches[0].start()]
    for i, pm in enumerate(matches):
        title, attrs, items = pm.group(1), pm.group(2), pm.group(3)
        time = (re.search(r'@(\S+)', attrs) or [None, None])[1]
        marker = (re.search(r'\[([^\]]+)\]', attrs) or [None, None])[1]
        end = matches[i+1].start() if i+1 < len(matches) else len(body)
        chunk = body[pm.end():end]
        if i == 0: chunk = pre + chunk
        pages.append(dict(sec=sec_label, title=title, time=time or (t0 if i == 0 else ""),
                          marker=marker, compact=" compact" in attrs, items=[l.strip() for l in items.splitlines() if l.strip()],
                          md=chunk.splitlines(), default_marker=default_marker))
    return sec_id, sec_title, t0, default_marker, pages

# ------------------------------------------------------------ cheatsheet -----
LABEL_RE = re.compile(r'^\*\*(§\d+[a-z]?′?)\s+(TYPE|PASTE|CHECKOUT|PASTE/CHECKOUT)\b(.*)')
FILE_RE = re.compile(r'`([\w./-]+\.(?:clj|cljs|js|css|edn))`')

def parse_cheatsheet():
    blocks, label, tag, file, order = [], None, None, None, {}
    lines = SRC_CHEAT.read_text(encoding="utf-8").split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("## "):
            label = tag = file = None
        m = LABEL_RE.match(ln)
        if m:
            label, tag = m.group(1), m.group(2).split("/")[0]
        # the file a block belongs to: the last path named in the label or the
        # prose before it — "(same file)" labels and "in `tr-load!`" inherit it
        fm = FILE_RE.search(ln) if not ln.startswith("```") else None
        if fm: file = fm.group(1)
        if ln.startswith("```"):
            lang = ln[3:].strip() or "bash"
            j = i + 1; code = []
            while j < len(lines) and not lines[j].startswith("```"):
                code.append(lines[j]); j += 1
            n = order[label] = order.get(label, 0) + 1
            blocks.append(dict(label=label, n=n, lang=lang, code=textwrap.dedent("\n".join(code)), tag=tag, file=file))
            i = j
        i += 1
    return blocks

CHEAT = parse_cheatsheet()
def cheat_block(ref):
    """§2a → first block under that label; §2d#2 → second; ~text → the first block containing text."""
    if ref.startswith("~"):
        needle = ref[1:]
        for b in CHEAT:
            if needle in b["code"]: return b
        raise SystemExit(f"cheatsheet: no code block containing {needle!r}")
    label, _, n = ref.partition("#")
    for b in CHEAT:
        if b["label"] == label and b["n"] == int(n or 1): return b
    raise SystemExit(f"cheatsheet: no block {ref}")

def repl_pairs(code):
    """A cheatsheet block with `;; =>` lines → [(form, output)] for repl_block."""
    pairs, form, out = [], [], None
    for ln in code.split("\n"):
        if ln.startswith(";; =>"):
            out = ln[5:].strip()
        elif ln.startswith(";;") and out is not None:
            out += "\n" + ln[2:].lstrip(" ")[0:]  # continuation line of the output
        elif not ln.strip() and form:
            pairs.append(("\n".join(form), out)); form, out = [], None
        else:
            if out is not None: pairs.append(("\n".join(form), out)); form, out = [], None
            form.append(ln)
    if form: pairs.append(("\n".join(form), out))
    return pairs

# ---------------------------------------------------------------- slides -----
def parse_slides():
    """The bookend slides, from the run-sheet's slide blocks via build_slides (never
    from slides.html, which is itself generated from them)."""
    out = {}
    for n, (_name, inner) in build_slides.slides().items():
        inner = inner.strip()                    # build_slides never indents inside <pre>
        inner = (inner.replace('class="accent"', 'class="ac"').replace('class="green"', 'class="gr"')
                      .replace(' class="void"', ''))
        out[int(n)] = inner
    return out
SLIDES = parse_slides()

# ------------------------------------------------------- screen items --------
def screen_html(items):
    parts = []
    for line in items:
        kind, _, rest = line.partition(" ")
        if kind == "shots":                     # shots NAME "cap" | NAME "cap"  (side by side)
            inner = "".join(shot(t[0], md_inline(t[1]) if len(t) > 1 else None)
                            for t in (shlex.split(part) for part in rest.split(" | ")))
            parts.append(f'<div class="trip">{inner}</div>'); continue
        toks = shlex.split(line)
        kind, args = toks[0], toks[1:]
        cap = lambda k=1: md_inline(args[k]) if len(args) > k else None
        if kind == "code":
            b = cheat_block(args[0])
            opts = dict(a.split("=", 1) for a in args[1:] if "=" in a)
            caps = [a for a in args[1:] if "=" not in a]
            parts.append(code_block(b["code"], lang=b["lang"], tag=opts.get("tag", b["tag"]),
                                    file=opts.get("file", b["file"]), cap=md_inline(caps[0]) if caps else None))
        elif kind == "repl":
            pairs = [p for ref in args for p in repl_pairs(cheat_block(ref)["code"])]
            parts.append(repl_block(pairs))
        elif kind == "slide":
            parts.append(slide(int(args[0]), SLIDES[int(args[0])]))
        elif kind == "shot":
            cls = " ".join(a for a in args[2:] if a in ("tall", "hero"))
            parts.append(shot(args[0], cap(), cls))
        elif kind == "dom":
            parts.append(code_block(args[0], lang="dom", cap=cap()))
        elif kind == "bash":
            parts.append(code_block(args[0], lang="bash", tag="CHECKOUT", cap=cap()))
        elif kind == "note":
            parts.append(note(md_inline(args[0])))
        else:
            raise SystemExit(f"page marker: unknown screen item {kind!r}")
    return "".join(parts)

# ============================================================ ASSEMBLE ========
TITLE, SECTIONS = parse_talk()
by_name = {h: b for h, b in SECTIONS}
def section(name):
    for h, b in SECTIONS:
        if h.startswith(name): return b.split("\n")
    raise SystemExit(f"run-sheet: no section starting with {name!r}")

talk_secs = [talk_pages(h, b) for h, b in SECTIONS if h.startswith("§")]

# cover: legend is the deck's own; the map and the recovery rule come from the run-sheet
decision = section("The one design decision")
rec = [b for t, b in blocks_of(decision) if t == "para" and b[0].startswith("**Recovery")]
screen_rule = [b for t, b in blocks_of(decision)                 # the section's leading rule,
               if t == "para" and b[0].startswith("**")          # however it happens to be worded
               and not b[0].startswith("**Recovery")]
if not screen_rule:
    raise SystemExit("run-sheet: 'The one design decision' has no leading **bold** rule paragraph")
screen_rule_text = " ".join(l.strip() for l in screen_rule[0])
if screen_rule_text.endswith(":"):                      # drop a sentence that introduces a list we don't show
    screen_rule_text = screen_rule_text[:screen_rule_text.rfind(". ") + 1]
rows = "".join(f'<tr><td>{sid} · {md_inline(stitle)}</td><td class="t2">{t0}</td><td class="t3">{esc(dm)}</td></tr>'
               for sid, stitle, t0, dm, _ in talk_secs[1:])
COVER = f"""<div class="cover">
  <h1>{md_inline(TITLE)}</h1>
  <p class="csub">A source inspector for server-rendered Hiccup — built live, from a bare webserver up.</p>
  <p class="cmeta">Presenter script · generated from livecode-talk.md and livecode-cheatsheet.md</p>
  <div class="grid2">
    <div class="legend">
      <h3>How to read this script</h3>
      <dl>
        <dt><span class="tag t-type">SLIDE</span></dt><dd>The few lines that carry the idea, on the projector — fragments, not files.</dd>
        <dt><span class="tag t-checkout">CHECKOUT</span></dt><dd>Git lands the step: <code>git switch -f step-N</code>. The watcher reloads, the browser refreshes itself.</dd>
        <dt style="color:#6b5fd6;font-weight:700;">pill</dt><dd>A stage direction: the editor, the browser, a slide, a demo cue.</dd>
        <dt style="color:#8a5a1e;font-style:italic;">beat</dt><dd>A design note from the run-sheet. The talk lives in these.</dd>
      </dl>
      <p style="font-size:9.3pt;color:#6f6a82;line-height:1.4;margin:4mm 0 0;">{md_inline(" ".join(l.strip() for l in rec[0]))}</p>
    </div>
    <div class="timing">
      <h3>The map (section → end tag)</h3>
      <table>{rows}</table>
      <p style="font-size:8.8pt;color:#8a85a0;margin:3mm 0 0;line-height:1.4;">{md_inline(screen_rule_text)}</p>
    </div>
  </div>
</div>"""
PAGES.append(page("", "", "", "", COVER, "", layout="full"))
PAGES.append(page("Before doors", "Stage setup", "", "checklist",
                  f'<div class="doc setup two">{doc_html(section("Stage setup"))}</div>', "", layout="full"))

for sid, stitle, t0, dm, pages in talk_secs:
    for pg in pages:
        marker = pg["marker"]
        if not marker:
            sl = [i for i in pg["items"] if i.startswith("slide ")]
            marker = f"slide {sl[0].split()[1]}" if sl else pg["default_marker"]
        add(pg["sec"], md_inline(pg["title"]), pg["time"], marker, screen_html(pg["items"]), speaker_html(pg["md"]),
            cls="compact" if pg["compact"] else "")

back = ""
for name in ("The hard gate", "Cuts if running long", "Stretch if running short", "Rehearsal checklist"):
    back += f"<h3>{esc(name)}</h3>" + doc_html(section(name))
PAGES.append(page("Backstage", "The hard gate, cuts, and recovery", "", "reference", f'<div class="doc setup two">{back}</div>', "", layout="full"))
qa = section("Likely Q&A")
items = [b for t, b in blocks_of(qa) if t == "list"][0]
starts = [i for i, l in enumerate(items) if re.match(r'^- ', l)]
half = starts[len(starts)//2 + (len(starts) % 2)]
for k, chunk in enumerate((items[:half], items[half:]), 1):
    PAGES.append(page("Backstage", f"Likely Q&A ({'I'*k})", "", "reference", f'<div class="doc qa two">{doc_html(chunk, qa=True)}</div>', "", layout="full"))

htmls = HEAD + "".join(PAGES) + TAIL
OUT.write_text(htmls, encoding="utf-8")
print(f"wrote {OUT} · {len(PAGES)} pages · {len(htmls)/1024:.0f} KB · {len(IMG)} images embedded")
