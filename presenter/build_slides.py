#!/usr/bin/env python3
r"""livecode-talk.md → slides.html: the bookend slides.

The slides are defined inside the run-sheet, each in a
`<!-- slide N · name -->` … `<!-- /slide -->` block placed right after the
page marker that first shows it. This file and slides-template.html (CSS +
keyboard navigation) hold only the presentation. build_presenter.py imports
`slides()` (the content) and `strip_slides()` (to keep the blocks out of the
speaker column), so deck and slides.html always agree.

Syntax (documented in README.md, "Slides"):

  <!-- slide N · name --> … <!-- /slide -->   slide N (the name is for humans)
  # / ##                  the slide heading (h1 / h2); a block may run over
                          several lines — a line ending in `\` gets a <br>
  paragraph               lines up to a blank line
  - item                  a list; indented continuation lines belong to the item
  | a | b |               a pipe table; the first row is the header when a
                          |---|---| separator row follows it
  ```diagram NAME K```   state K of the `<!-- diagram NAME · note -->` block
                          (diagram.py, DIAGRAM.md), full size; the fence body
                          stays empty. A {.flow-keys|.flow-step|.flow-auto|
                          .flow-loop|.flow-off} line before it picks how the
                          state's flows play; {.pop} pops its new parts
  ```minimap NAME K ID,…``` state K as a small you-are-here inset with those
                          parts lit, top right beside the heading, out of the
                          flow (one per slide; {.rev} / {.warn} light them green /
                          amber). The build checks that the heading leaves room
                          and narrows the inset if not; on a slide with no
                          heading it takes its own row (see fit_minimap)
  ```lang … ```           a verbatim code block, syntax-highlighted when the fence
                          names a language (clojure, html, js, bash; see highlight.py).
                          After the language: from=N numbers the lines from N in a
                          gutter; cursor=L:C bands line L and puts a caret before
                          column C (1-based, as the reader counts)
  {.repl} + ```clojure    a REPL exchange: a `user=> ` line is input (the prompt dim,
                          the form highlighted), every other line is output (muted)
  ![alt](figures/talk/NAME.png "caption")
                          a line holding only an image: a screenshot, `<figure class=
                          "shot">`. The path is relative to talk/ and must exist; the
                          caption (optional, inline markdown) may be '…' when it holds
                          a `"`; `{.cls}` at the end of the line classes the figure
                          ({.guide}: hairlines at 25% and 75% of its height,
                          from 45% of its width to the right edge).
                          Consecutive image lines are one group, side by side
                          ({.pair}, the default) or one above the other ({.stack}) —
                          on the line before. A group has ONE scale (from the PNGs'
                          pixel sizes), so its images must share one capture DPR
  {.cls .cls2}            on a line of its own: classes for the block that
                          follows (`{.steps}` renders a list as the step grid);
                          at the end of a paragraph, list item or table cell:
                          classes for that paragraph / item / cell
  **bold** `code`         inline; ==accent== ++green++ ~~strike~~ colour spans
"""
import html, re, sys
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from highlight import highlight, HL, esc
import difflib
import diagram
DIAGRAMS = {}                                        # name -> diagram.Diagram, filled by slides()

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                                   # the talk/ directory
SRC, TEMPLATE, OUT = ROOT / "livecode-talk.md", HERE / "slides-template.html", ROOT / "slides.html"

esc = lambda s: html.escape(s, quote=False)
ATTR = re.compile(r"\s*\{((?:\s*\.[\w-]+)+)\s*\}\s*$")
BR = "\x01"

IMG_LINE = re.compile(r"""^!\[([^\]]*)\]\(\s*([^\s)"']+)(?:\s+(?:"([^"]*)"|'([^']*)'))?\s*\)\s*$""")
GROUPS = ("pair", "stack")                           # the layouts of an image group

def is_image(ln):
    return bool(IMG_LINE.match(split_attr(ln)[0].strip()))

def split_attr(s):
    """'text {.a .b}' → ('text', ['a', 'b']); no attribute → (s, [])."""
    m = ATTR.search(s)
    return (s[:m.start()], m.group(1).replace(".", " ").split()) if m else (s, [])

def cls(classes):
    return f' class="{" ".join(classes)}"' if classes else ""

def inline(s):
    codes = []
    def stash(m):
        codes.append(f"<code>{esc(m.group(1))}</code>")
        return f"\x00{len(codes) - 1}\x00"
    s = re.sub(r"`([^`]+)`", stash, s)
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s, flags=re.S)
    s = re.sub(r"==(.+?)==", r'<span class="accent">\1</span>', s, flags=re.S)
    s = re.sub(r"\+\+(.+?)\+\+", r'<span class="green">\1</span>', s, flags=re.S)
    s = re.sub(r"~~(.+?)~~", r'<span class="strike">\1</span>', s, flags=re.S)
    s = re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], s)
    return s.replace(BR, "<br>")

def text(lines):
    """Join a block's lines: a trailing `\\` becomes <br>, otherwise a soft break."""
    joined = "\n".join(l.strip() for l in lines)
    return inline(re.sub(r"\\(\n|$)", BR, joined))

# ------------------------------------------------------------------ blocks ---
def parse_blocks(lines):
    """→ [(kind, classes, payload)] with kind in heading|para|list|table|code|svg|shots|diagram|minimap."""
    blocks, pending, i = [], [], 0
    def take(pred):
        nonlocal i
        got = []
        while i < len(lines) and pred(lines[i]):
            got.append(lines[i]); i += 1
        return got
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1; continue
        if ATTR.fullmatch(ln):                       # `{.big}` on its own line
            pending += split_attr(ln)[1]; i += 1; continue
        c, pending = pending, []
        if ln.startswith("```"):
            lang = ln[3:].strip() or None                # the whole info string, for the special fences
            if lang and lang.split()[0] in ("diagram", "minimap"):   # a state of a run-sheet diagram
                kind, one_line = lang.split()[0], lang.endswith("```")   # ```diagram arch 5``` on one line is fine too
                args = lang.rstrip("`").split()[1:]
                usage = "```diagram NAME K```" if kind == "diagram" else "```minimap NAME K ID,ID…```"
                if len(args) < 2 or not args[1].isdigit() or (kind == "diagram" and len(args) > 2):
                    raise SystemExit(f"{SRC.name}: {ln.strip()!r}: want {usage}")
                i += 1
                if not one_line:
                    if any(l.strip() for l in take(lambda l: not l.startswith("```"))):
                        raise SystemExit(f"{SRC.name}: {ln.strip()!r}: the fence body stays empty (the diagram is its `<!-- diagram {args[0]} -->` block)")
                    i += 1                           # closing fence
                ids = [x for x in re.split(r"[,\s]+", " ".join(args[2:])) if x]
                blocks.append((kind, c, (args[0], int(args[1])) + ((ids,) if kind == "minimap" else ())))
                continue
            if lang == "svg":                        # inline figure, passed through verbatim
                i += 1
                body = take(lambda l: not l.startswith("```"))
                i += 1                               # closing fence
                blocks.append(("svg", c, body))
                continue
            lang, opts = fence_info(lang)
            if lang and lang not in HL: raise SystemExit(f"{SRC.name}: unknown fence language {lang!r} (known: {', '.join(sorted(HL))})")
            i += 1
            body = take(lambda l: not l.startswith("```"))
            i += 1                                   # closing fence
            blocks.append(("code", c, (lang, body, opts)))
        elif ln.startswith("![") and not is_image(ln):
            raise SystemExit(f"{SRC.name}: {ln.strip()!r}: an image line is ![alt](path \"caption\") {{.cls}} and nothing else (no ] in the alt)")
        elif is_image(ln):                           # a group of screenshots: consecutive image lines
            figs = []
            while i < len(lines) and is_image(lines[i]):
                body, fc = split_attr(lines[i].strip())
                m = IMG_LINE.match(body.strip())
                figs.append((m[2], m[1], m[3] if m[3] is not None else m[4], fc))
                i += 1
            blocks.append(("shots", c, figs))
        elif ln.startswith("#"):
            level = len(ln) - len(ln.lstrip("#"))
            i += 1
            body = [ln.lstrip("#").strip()] + take(lambda l: l.strip() and not l.startswith(("#", "- ", "|", "```")) and not is_image(l))
            blocks.append(("heading", c, (level, body)))
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                first = lines[i][2:]; i += 1
                cont = take(lambda l: l.strip() and l[0].isspace())
                items.append([first] + cont)
            blocks.append(("list", c, items))
        elif ln.startswith("|"):
            blocks.append(("table", c, take(lambda l: l.startswith("|"))))
        else:
            body = take(lambda l: l.strip() and not l.startswith(("```", "|")) and not ATTR.fullmatch(l) and not is_image(l))
            blocks.append(("para", c, body))
    return blocks

def render_block(kind, classes, payload):
    if kind == "heading":
        level, body = payload
        return f"<h{level}{cls(classes)}>{text(body)}</h{level}>"
    if kind == "para":
        body = list(payload)
        body[-1], tail = split_attr(body[-1])
        return f"<p{cls(classes + tail)}>{text(body)}</p>"
    if kind == "svg":
        return f'<div{cls(["figure"] + classes)}>' + "\n".join(payload) + "</div>"
    if kind in ("diagram", "minimap"):
        name = payload[0]
        if name not in DIAGRAMS: raise SystemExit(f"{SRC.name}: no `<!-- diagram {name} · … -->` … `<!-- /diagram -->` block")
        if kind == "diagram":
            return f'<div{cls(["figure", "ax-fig"] + classes)}>' + DIAGRAMS[name].svg(payload[1]) + "</div>"
        _, k, ids, width = payload
        return f'<div{cls(["ax-mini"] + classes)} style="--ax-mini-w:{width:g}">' + DIAGRAMS[name].mini(k, ids) + "</div>"
    if kind == "code":
        return code_html(classes, *payload)
    if kind == "shots":
        return shots_html(classes, payload)
    if kind == "list":
        items = []
        for it in payload:
            it = list(it)
            it[-1], tail = split_attr(it[-1])
            items.append((text(it), tail))
        if "steps" in classes:
            inner = "\n".join(f"    <div{cls(t)}>{h}</div>" for h, t in items)
            return f'<div{cls(classes)}>\n{inner}\n  </div>'
        inner = "\n".join(f"    <li{cls(t)}>{h}</li>" for h, t in items)
        return f"<ul{cls(classes)}>\n{inner}\n  </ul>"
    if kind == "table":
        rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in payload]
        header = len(rows) > 1 and all(re.fullmatch(r":?-+:?", c) for c in rows[1])
        out = []
        for k, row in enumerate(rows):
            if header and k == 1: continue
            tag = "th" if header and k == 0 else "td"
            cells = []
            for c in row:
                c, t = split_attr(c)
                cells.append(f"<{tag}{cls(t)}>{inline(c)}</{tag}>")
            out.append("    <tr>" + "".join(cells) + "</tr>")
        return f'<table{cls(["void"] + classes)}>\n' + "\n".join(out) + "\n  </table>"
    raise SystemExit(f"{SRC.name}: unknown block {kind!r}")

# ------------------------------------------------------------ code fences ---
FENCE_OPTS = ("from", "cursor")
FENCE_FLAGS = ("inline",)                    # ```diff inline: see inline_diff

def fence_info(info):
    """'clojure from=17 cursor=21:8' → ('clojure', {'from': 17, 'cursor': (21, 8)})."""
    words = (info or "").split()
    lang, opts = (words[0] if words else None), {}
    for w in words[1:]:
        if w in FENCE_FLAGS: opts[w] = True; continue
        k, eq, v = w.partition("=")
        if not eq or k not in FENCE_OPTS:
            raise SystemExit(f"{SRC.name}: fence ```{info}: unknown option {w!r} (known: {', '.join([k + '=' for k in FENCE_OPTS] + list(FENCE_FLAGS))})")
        if k == "from" and v.isdigit(): opts[k] = int(v)
        elif k == "cursor" and re.fullmatch(r"\d+:\d+", v): opts[k] = tuple(int(x) for x in v.split(":"))
        else: raise SystemExit(f"{SRC.name}: fence ```{info}: want from=N / cursor=LINE:COL, got {w!r}")
    if lang == "diff" and set(opts) - {"inline"}: raise SystemExit(f"{SRC.name}: fence ```{info}: a diff takes no from= / cursor=")
    if "inline" in opts and lang != "diff": raise SystemExit(f"{SRC.name}: fence ```{info}: `inline` is for ```diff fences")
    return lang, opts

SPAN = re.compile(r"<span[^>]*>|</span>")

def html_lines(h):
    """Highlighted HTML → one self-contained string per source line: a span that runs
    across a line break is closed at the end of the line and reopened on the next."""
    out, open_ = [], []
    for ln in h.split("\n"):
        head = "".join(open_)
        for m in SPAN.finditer(ln):
            if m[0].startswith("</"): open_.pop()
            else: open_.append(m[0])
        out.append(head + ln + "</span>" * len(open_))
    return out

def at_column(h, col, mark):
    """Insert `mark` before the col-th visible character (1-based) of an HTML line."""
    i = n = 0
    while i < len(h):
        if h[i] == "<": i = h.index(">", i) + 1; continue
        if n == col - 1: return h[:i] + mark + h[i:]
        i = h.index(";", i) + 1 if h[i] == "&" else i + 1
        n += 1
    if n == col - 1: return h + mark
    raise SystemExit(f"{SRC.name}: cursor= column {col} is past the end of its line ({n} characters)")

def inline_diff(body):
    """```diff inline: a `-` line followed by a `+` line whose change only adds characters
    (or only removes them) becomes ONE row, the change marked in place (.ins / .del) and
    nothing padded, so every column stays put. The sign goes; where the context lines
    carry unified diff's leading space, a space takes its place, so the row lines up with
    them. A pair that changes more keeps its two lines (the build prints a note), and
    every other line renders as a plain ```diff does."""
    ctx = [l for l in body if l and l[0] not in "+-"]
    pad = " " if ctx and all(l.startswith(" ") for l in ctx) else ""
    rows, k = [], 0
    while k < len(body):
        ln = body[k]
        if ln.startswith("-") and k + 1 < len(body) and body[k + 1].startswith("+"):
            a, b = ln[1:], body[k + 1][1:]
            ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
            if {op for op, *_ in ops} - {"equal"} in ({"insert"}, {"delete"}):
                row = "".join(esc(a[i1:i2]) if op == "equal"
                              else f'<span class="ins">{esc(b[j1:j2])}</span>' if op == "insert"
                              else f'<span class="del">{esc(a[i1:i2])}</span>'
                              for op, i1, i2, j1, j2 in ops)
                rows.append(f'<span class="ch">{pad}{row}</span>')
                k += 2
                continue
            print(f"  note: ```diff inline: {ln.strip()!r} → {body[k + 1].strip()!r} does more than add or remove — kept as two lines")
        rows.append(HL["diff"](ln))
        k += 1
    return "".join(rows)                             # block spans, as hl_diff joins them

def code_html(classes, lang, body, opts):
    """A fenced block. {.repl}: `user=> ` lines are input, the rest output. from= / cursor=:
    each line becomes a block span (a gutter number; the cursor line banded, a caret)."""
    if opts.get("inline"):
        return f"<pre{cls(classes)}><code>{inline_diff(body)}</code></pre>"
    if "repl" in classes:
        rows = [f'<span class="rp">user=&gt;</span> {highlight(l[7:], lang)}' if l.startswith("user=> ")
                else f'<span class="ro">{highlight(l, lang)}</span>' for l in body]
        inner = "\n".join(rows)
    elif opts:
        first = opts.get("from", 1)
        lines = html_lines(highlight("\n".join(body), lang))
        last = first + len(lines) - 1
        cur_line, cur_col = opts.get("cursor", (None, None))
        if cur_line is not None and not first <= cur_line <= last:
            raise SystemExit(f"{SRC.name}: cursor= line {cur_line} is outside the block's lines {first}–{last}")
        rows = []
        for k, h in enumerate(lines):
            n = first + k
            if n == cur_line: h = at_column(h, cur_col, '<span class="caret"></span>')
            gut = f'<span class="gut">{n:>{len(str(last))}}</span>' if "from" in opts else ""
            rows.append(f'<span class="ln{" cur" if n == cur_line else ""}">{gut}{h or " "}</span>')
        inner = "".join(rows)                        # block spans: a "\n" between them would double the break
    else:
        inner = highlight("\n".join(body), lang)
    return f"<pre{cls(classes)}><code>{inner}</code></pre>"

# ------------------------------------------------------------ screenshots ---
# An image group's look lives in slides-template.html (`.shots`); this writes only its
# shape, from the PNGs' pixel sizes: one scale for the whole group, so a pair or a stack
# shows equal app pixels at equal size (its images must share one capture DPR).
#   group:  --hw  its height over its width, in PNG px (stack: Σh / max w; pair: max h / Σw)
#           --kx / --ky  the gaps across / down; --kc  the caption rows
#   figure: --wa / --wb  its PNG width over the group's width / height
def image_size(src):
    p = ROOT / src
    if not p.is_file(): raise SystemExit(f"{SRC.name}: image {src!r} not found (a path relative to {ROOT.name}/)")
    with Image.open(p) as im: return im.size

def shots_html(classes, figs):
    layout = [k for k in classes if k in GROUPS]
    if len(layout) > 1: raise SystemExit(f"{SRC.name}: an image group is {{.pair}} or {{.stack}}, not both")
    kind = "stack" if len(figs) == 1 else (layout[0] if layout else "pair")
    sizes = [image_size(src) for src, *_ in figs]
    ncap = sum(1 for f in figs if f[2])
    if kind == "stack":
        W, H, kx, ky, kc = max(w for w, _ in sizes), sum(h for _, h in sizes), 0, len(figs) - 1, ncap
    else:
        W, H, kx, ky, kc = sum(w for w, _ in sizes), max(h for _, h in sizes), len(figs) - 1, 0, min(ncap, 1)
    out = []
    for (src, alt, cap, fcls), (w, h) in zip(figs, sizes):
        capd = f"<figcaption>{inline(cap)}</figcaption>" if cap else ""
        out.append(f'    <figure{cls(["shot"] + fcls)} style="--wa:{w / W:.5f};--wb:{w / H:.5f}">'
                   f'<span class="frame"><img src="{html.escape(src)}" width="{w}" height="{h}" alt="{html.escape(alt)}"></span>'
                   f"{capd}</figure>")
    extra = [k for k in classes if k not in GROUPS]
    return (f'<div{cls(["shots", kind] + extra)} style="--hw:{H / W:.5f};--kx:{kx};--ky:{ky};--kc:{kc}"><div class="grp">\n'
            + "\n".join(out) + "\n  </div></div>")

# ---------------------------------------------------------------- minimap ---
# A ```minimap``` inset sits top right, beside the heading and out of the flow
# (slides-template.html, `.ax-mini`), so the body doesn't move (on a slide with no
# heading it takes its own row instead: see fit_minimap). It must neither run
# into the heading's words nor reach down into the body. The slide geometry that
# decides both, in em of the slide's base font, as slides-template.html sets it
# (keep these in step with it). 16:9 is the tightest case — a wider screen only adds
# width, and on a 4:3 one the larger top padding moves heading and inset alike.
SLIDE_W   = (100 - 2 * 4) / 1.875        # .slide's 4vw side padding over body's 1.875vw font: 49.07em
MINI_DROP = .8                           # .ax-mini's top is calc(4vh - .8em): .8em above the heading
GAP       = .9                           # .slide's flex gap: where the body starts below the heading
HEAD      = {1: (2.6, 1.15), 2: (1.9, 1.2)}   # h1 / h2: font size (em), line height
CLEAR     = dict(words=.8, body=.2)      # room the inset keeps to the heading's words / to the body

def mini_sizes():
    """The inset's widest and narrowest width (em), from the template: sizes are its look."""
    tpl = TEMPLATE.read_text(encoding="utf-8")
    got = [re.search(rf"--ax-mini-{k}:\s*([\d.]+)", tpl) for k in ("max", "min")]
    if not all(got): raise SystemExit(f"{TEMPLATE.name}: no --ax-mini-max / --ax-mini-min (the minimap's widths, in em)")
    return tuple(float(g[1]) for g in got)

def heading_em(level, body):
    """→ (widest line, number of lines) of a heading, in em of the slide's base font. Measured
    in DejaVu Sans Bold — what system-ui is here, and no narrower font on the stage laptop
    would make it wider — with emoji at 1.25em and `code` in mono."""
    size = HEAD.get(level, HEAD[2])[0]
    joined = "\n".join(l.strip() for l in body)
    lines = [re.sub(r"\s+", " ", seg).strip() for seg in re.split(r"\\(?:\n|$)", joined) if seg.strip()]
    def w(line):
        px, out = 100.0, 0.0
        for j, part in enumerate(re.split(r"`([^`]+)`", line)):
            out += (diagram.line_w(part, px * .92, mono=True) + .7 * .92 * px if j % 2      # `code`: .92em mono, .35em padding a side
                    else diagram.line_w(re.sub(r"\*\*|==|\+\+|~~", "", part), px))
        return out / px * size
    return max((w(l) for l in lines), default=0.0), len(lines)

def fit_minimap(n, blocks, aspect):
    """→ (width in em, alone) of the inset on slide n, whose blocks start with it: as wide as
    the heading row's height lets it be without reaching the body (at most --ax-mini-max),
    narrower beside a long heading, down to --ax-mini-min — below that the build warns.
    On a slide that starts without a heading (a full-bleed screenshot) it is `alone`: it
    takes its own row at the top, as wide as beside a one-line h2, and the body starts
    below it (the template's `.ax-alone`; the build prints a `note:`)."""
    mx, mn = mini_sizes()
    head = blocks[1] if len(blocks) > 1 and blocks[1][0] == "heading" else None
    if not head:
        size, lh = HEAD[2]
        w = min(mx, (size * lh + MINI_DROP + GAP - CLEAR["body"]) * aspect)
        print(f"  note: slide {n}: no heading — the minimap takes its own row at the top ({w:.2f}em), the body starts below it")
        return round(w, 2), True
    words, lines = heading_em(*head[2])
    size, lh = HEAD.get(head[2][0], HEAD[2])
    row = size * lh * lines
    by_height = (row + MINI_DROP + GAP - CLEAR["body"]) * aspect
    by_words = SLIDE_W - words - CLEAR["words"]
    w = min(mx, by_height, by_words)
    if w < mn:
        why = (f"the heading is {words:.1f}em wide and leaves {max(by_words, 0):.1f}em beside it" if by_words < mn
               else f"the heading row leaves room for only {by_height:.1f}em")
        print(f"  warning: slide {n}: no room for the minimap — {why}; it needs {mn:g}em "
              f"(shorten the heading, or drop the inset). Drawn at {mn:g}em, overlapping.")
        w = mn
    elif by_words < min(mx, by_height):
        print(f"  note: slide {n}: minimap narrowed to {w:.2f}em beside the heading ({min(mx, by_height):.2f}em would touch it)")
    return round(w, 2), False

# ------------------------------------------------------------------ slides ---
BLOCK = re.compile(r"^<!-- slide (\d+) · (.*?) -->[ \t]*\n(.*?)^<!-- /slide -->[ \t]*$\n?", re.M | re.S)

def strip_slides(text):
    """The run-sheet without its slide blocks (what the deck's speaker column parses)."""
    return diagram.strip(BLOCK.sub("", text))

def slides():
    """→ {n: (name, inner_html)} for every `<!-- slide N · name -->` block in the run-sheet."""
    src = SRC.read_text(encoding="utf-8")
    DIAGRAMS.clear(); DIAGRAMS.update(diagram.diagrams(src))
    found = list(BLOCK.finditer(src))
    if not found: raise SystemExit(f"{SRC}: no `<!-- slide N · name -->` … `<!-- /slide -->` blocks")
    if len(re.findall(r"^<!-- slide ", src, re.M)) != len(found): raise SystemExit(f"{SRC.name}: a `<!-- slide` block is missing its `<!-- /slide -->`")
    out = {}
    for m in found:
        body = m.group(3).split("\n")
        n = int(m.group(1))
        if n in out: raise SystemExit(f"{SRC.name}: slide {n} defined twice")
        try:
            blocks = parse_blocks(body)
            inner = slide_html(n, blocks)
        except SystemExit as e:                      # say which slide
            msg = str(e).removeprefix(f"{SRC.name}: ")
            raise SystemExit(f"{SRC.name}: slide {n}: {msg.removeprefix(f'slide {n}: ')}") from None
        out[n] = (m.group(2), inner)
    expect = list(range(1, len(out) + 1))
    if sorted(out) != expect: raise SystemExit(f"{SRC.name}: slide numbers {sorted(out)} are not {expect}")
    return out

def slide_html(n, blocks):
    """Slide n's blocks → its inner HTML. A minimap goes first, out of the flow (in it on a
    slide with no heading: see fit_minimap)."""
    minis = [b for b in blocks if b[0] == "minimap"]
    if len(minis) > 1: raise SystemExit(f"{len(minis)} minimaps (one per slide)")
    if minis:                                        # first in the section: see the template
        blocks = minis + [b for b in blocks if b[0] != "minimap"]
        _, c, (name, k, ids) = minis[0]
        if name not in DIAGRAMS: raise SystemExit(f"no `<!-- diagram {name} · … -->` … `<!-- /diagram -->` block")
        width, alone = fit_minimap(n, blocks, DIAGRAMS[name].W / DIAGRAMS[name].H)
        blocks[0] = ("minimap", c + ["ax-alone"] * alone, (name, k, ids, width))
    return "\n".join("  " + render_block(*b) for b in blocks)

def page(found=None):
    secs = []
    for n, (name, inner) in sorted((found or slides()).items()):
        on = " on" if n == 1 else ""
        secs.append(f'<!-- {n} · {name} -->\n<section class="slide{on}">\n{inner}\n</section>')
    shell = TEMPLATE.read_text(encoding="utf-8")
    banner = "<!-- GENERATED from the slide blocks in livecode-talk.md by presenter/build_slides.py — edit the run-sheet, not this file -->\n"
    shell = (shell.replace("/*{{DIAGRAM_CSS}}*/", (HERE / "diagram.css").read_text(encoding="utf-8"))
                  .replace("/*{{DIAGRAM_JS}}*/", (HERE / "diagram.js").read_text(encoding="utf-8")))
    return banner + shell.replace("{{SLIDES}}", "\n\n".join(secs))

if __name__ == "__main__":
    found = slides()                                 # once: diagram and minimap warnings print once
    OUT.write_text(page(found), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT.parent)} ({len(found)} slides)")
