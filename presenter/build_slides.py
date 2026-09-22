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
  ```lang … ```           a verbatim code block, syntax-highlighted when the fence
                          names a language (clojure, html, js, bash; see highlight.py)
  {.cls .cls2}            on a line of its own: classes for the block that
                          follows (`{.steps}` renders a list as the step grid);
                          at the end of a paragraph, list item or table cell:
                          classes for that paragraph / item / cell
  **bold** `code`         inline; ==accent== ++green++ ~~strike~~ colour spans
"""
import html, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from highlight import highlight, HL

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                                   # the talk/ directory
SRC, TEMPLATE, OUT = ROOT / "livecode-talk.md", HERE / "slides-template.html", ROOT / "slides.html"

esc = lambda s: html.escape(s, quote=False)
ATTR = re.compile(r"\s*\{((?:\s*\.[\w-]+)+)\s*\}\s*$")
BR = "\x01"

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
    """→ [(kind, classes, payload)] with kind in heading|para|list|table|code|svg."""
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
            lang = ln[3:].strip() or None
            if lang == "svg":                        # inline figure, passed through verbatim
                i += 1
                body = take(lambda l: not l.startswith("```"))
                i += 1                               # closing fence
                blocks.append(("svg", c, body))
                continue
            if lang and lang not in HL: raise SystemExit(f"{SRC.name}: unknown fence language {lang!r} (known: {', '.join(sorted(HL))})")
            i += 1
            body = take(lambda l: not l.startswith("```"))
            i += 1                                   # closing fence
            blocks.append(("code", c, (lang, body)))
        elif ln.startswith("#"):
            level = len(ln) - len(ln.lstrip("#"))
            i += 1
            body = [ln.lstrip("#").strip()] + take(lambda l: l.strip() and not l.startswith(("#", "- ", "|", "```")))
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
            body = take(lambda l: l.strip() and not l.startswith(("```", "|")) and not ATTR.fullmatch(l))
            blocks.append(("para", c, body))
    return blocks

def render_block(kind, classes, payload):
    if kind == "heading":
        level, body = payload
        return f"<h{level}>{text(body)}</h{level}>"
    if kind == "para":
        body = list(payload)
        body[-1], tail = split_attr(body[-1])
        return f"<p{cls(classes + tail)}>{text(body)}</p>"
    if kind == "svg":
        return f'<div{cls(["figure"] + classes)}>' + "\n".join(payload) + "</div>"
    if kind == "code":
        lang, body = payload
        return f"<pre{cls(classes)}><code>{highlight(chr(10).join(body), lang)}</code></pre>"
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

# ------------------------------------------------------------------ slides ---
BLOCK = re.compile(r"^<!-- slide (\d+) · (.*?) -->[ \t]*\n(.*?)^<!-- /slide -->[ \t]*$\n?", re.M | re.S)

def strip_slides(text):
    """The run-sheet without its slide blocks (what the deck's speaker column parses)."""
    return BLOCK.sub("", text)

def slides():
    """→ {n: (name, inner_html)} for every `<!-- slide N · name -->` block in the run-sheet."""
    src = SRC.read_text(encoding="utf-8")
    found = list(BLOCK.finditer(src))
    if not found: raise SystemExit(f"{SRC}: no `<!-- slide N · name -->` … `<!-- /slide -->` blocks")
    if len(re.findall(r"^<!-- slide ", src, re.M)) != len(found): raise SystemExit(f"{SRC.name}: a `<!-- slide` block is missing its `<!-- /slide -->`")
    out = {}
    for m in found:
        body = m.group(3).split("\n")
        n = int(m.group(1))
        if n in out: raise SystemExit(f"{SRC.name}: slide {n} defined twice")
        inner = "\n".join("  " + render_block(*b) for b in parse_blocks(body))
        out[n] = (m.group(2), inner)
    expect = list(range(1, len(out) + 1))
    if sorted(out) != expect: raise SystemExit(f"{SRC.name}: slide numbers {sorted(out)} are not {expect}")
    return out

def page():
    secs = []
    for n, (name, inner) in sorted(slides().items()):
        on = " on" if n == 1 else ""
        secs.append(f'<!-- {n} · {name} -->\n<section class="slide{on}">\n{inner}\n</section>')
    shell = TEMPLATE.read_text(encoding="utf-8")
    banner = "<!-- GENERATED from the slide blocks in livecode-talk.md by presenter/build_slides.py — edit the run-sheet, not this file -->\n"
    return banner + shell.replace("{{SLIDES}}", "\n\n".join(secs))

if __name__ == "__main__":
    OUT.write_text(page(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT.parent)} ({len(slides())} slides)")
