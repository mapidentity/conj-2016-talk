#!/usr/bin/env python3
"""Build-time syntax highlighting shared by build_presenter.py (deck code
cards, REPL cards) and build_slides.py (fenced blocks in the run-sheet's slides).

HL maps a fence/label language to a function: escaped HTML with token spans
  .cm comment · .st string · .kw keyword · .bi builtin/tag · .mt meta · .at attr
  .ad diff added · .rm diff removed · .cx diff context
Languages: clojure (clj), js, bash (sh), dom (html), diff — dom colours an HTML
snippet the way DevTools does. Unknown languages fall back to plain escaping.
"""
import html, re

def esc(s): return html.escape(s, quote=False)

CLJ_BI = set("""defn defn- defmacro defonce def ns let when when-not when-let
 if if-not cond for doseq do fn fn* require binding loop recur try catch case
 swap! reset! alter-var-root with-meta vary-meta into subvec assoc assoc-in
 mapv map filter keep first second nth meta name namespace vector? keyword?
 map? seq? coll? symbol? number? string? var? fn? contains? str println
 nil? pos? some every? sort sort-by ->> -> doto slurp count range apply
 comp mapcat juxt distinct reduce quot get get-in re-find re-pattern""".split())
CLJ = re.compile(r'(;[^\n]*)|("(?:\\.|[^"\\])*")|(\^)|(:[A-Za-z0-9_.:*+!?<>=/-]+)'
                 r'|(#?[A-Za-z_][A-Za-z0-9_.*+!?<>=/\'-]*)')
def hl_clj(code):
    out, i = [], 0
    for m in CLJ.finditer(code):
        out.append(esc(code[i:m.start()])); g = m.group()
        if   m.group(1): out.append(f'<span class="cm">{esc(g)}</span>')
        elif m.group(2): out.append(f'<span class="st">{esc(g)}</span>')
        elif m.group(3): out.append(f'<span class="mt">{esc(g)}</span>')
        elif m.group(4): out.append(f'<span class="kw">{esc(g)}</span>')
        elif m.group(5) and g in CLJ_BI: out.append(f'<span class="bi">{esc(g)}</span>')
        else: out.append(esc(g))
        i = m.end()
    out.append(esc(code[i:]))
    return "".join(out)

JS_BI = set("function var let const if else return new for while do true false "
            "null undefined this typeof void break continue try catch".split())
JS = re.compile(r'(//[^\n]*)|(/\*.*?\*/)|(\'(?:\\.|[^\'\\])*\'|"(?:\\.|[^"\\])*"'
                r'|`(?:\\.|[^`\\])*`)|([A-Za-z_$][A-Za-z0-9_$]*)', re.S)
def hl_js(code):
    out, i = [], 0
    for m in JS.finditer(code):
        out.append(esc(code[i:m.start()])); g = m.group()
        if   m.group(1) or m.group(2): out.append(f'<span class="cm">{esc(g)}</span>')
        elif m.group(3): out.append(f'<span class="st">{esc(g)}</span>')
        elif m.group(4) and g in JS_BI: out.append(f'<span class="bi">{esc(g)}</span>')
        else: out.append(esc(g))
        i = m.end()
    out.append(esc(code[i:]))
    return "".join(out)

def hl_bash(code):
    # comments + the leading command word
    out = []
    for ln in code.split("\n"):
        if ln.strip().startswith("#"):
            out.append(f'<span class="cm">{esc(ln)}</span>')
        else:
            m = re.match(r'(\s*)(\S+)(.*)', ln)
            if m:
                out.append(f'{m.group(1)}<span class="bi">{esc(m.group(2))}</span>{esc(m.group(3))}')
            else:
                out.append(esc(ln))
    return "\n".join(out)

def hl_dom(code):
    # a DevTools-style HTML element line: color tags, attr names, strings.
    # Single pass over escaped text: split tags from text, then within each
    # tag highlight attrs first, tag-name last, so inserted spans never re-match.
    def tag_repl(m):
        inner = m.group(1)
        inner = re.sub(r'([a-zA-Z-]+)=("[^"]*")',
                       lambda a: f'<span class="at">{a.group(1)}</span>=<span class="st">{a.group(2)}</span>',
                       inner)
        inner = re.sub(r'^(/?)([a-zA-Z0-9-]+)',
                       lambda t: t.group(1) + f'<span class="bi">{t.group(2)}</span>', inner)
        return f'&lt;{inner}&gt;'
    return re.sub(r'&lt;(.*?)&gt;', tag_repl, esc(code))

DIFF_RE = None
def hl_diff(code):
    """Unified-diff colouring: `+` added, `-` removed, everything else context.
    Each line is a block-level span so CSS can band the changed ones."""
    out = []
    for ln in code.split("\n"):
        body = esc(ln) or " "          # keep empty lines tall
        cl = "ad" if ln.startswith("+") else "rm" if ln.startswith("-") else "cx"
        out.append(f'<span class="{cl}">{body}</span>')
    # the spans are block-level: joining with "\n" would add a second line break
    return "".join(out)

HL = {"clojure": hl_clj, "js": hl_js, "bash": hl_bash, "dom": hl_dom,
      "diff": hl_diff}
HL.update(clj=hl_clj, html=hl_dom, sh=hl_bash)

def highlight(code, lang=None):
    """Highlight `code` for `lang`; None or an unknown language → plain escaped text."""
    return HL.get(lang, esc)(code)
