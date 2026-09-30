#!/usr/bin/env python3
r"""One architecture diagram ("the map") that grows with the talk, authored once in the run-sheet.

The run-sheet holds the diagram once, as a `<!-- diagram NAME · note -->` …
`<!-- /diagram -->` block whose body is one ```text fence in the DSL below
(the full reference, with examples: DIAGRAM.md). A slide block shows it with an
empty fence: ```diagram NAME K``` draws state K full size, ```minimap NAME K ID,…```
draws state K as a small you-are-here inset with those parts lit (build_slides.py
places it beside the heading).

Every state is drawn from the SAME geometry (the final, full diagram): an
element is simply absent before its first state, so nothing ever moves and a
hard cut between two map slides shows only what changed. The viewBox is the
canvas, identical for every state. States are keyed to the talk's sections, not
to git branches: there is no branch chip.

This file holds structure and metrics (font sizes, paddings: they decide box
sizes); diagram.css holds the look (colours, weights, dashes); diagram.js plays
the flows. Arrowheads are drawn as paths — no <marker> ids, which collide
between slides of one page.

DSL — one statement per line, `#` starts a comment:

  canvas WxH
  step K "caption" [summary] [hide:ID,ID…] [+CLS:ID,ID…]
        a state (`state` is accepted too), numbered in talk order (the map is keyed
        to talk sections, not to git branches). The caption is the map slide's
        heading and the SVG's aria-label. hide: removes elements at this state only
        (a region id hides everything inside it); +CLS: adds class ax-CLS to those
        ids at this state; summary: a recap state, which marks nothing as new
  region ID lane|store|band "CAPTION" X,Y WxH [cap=tl|br] [capx=X]
  node ID "LABEL" X,Y WxH [mono] [list] [sub=TEXT] [valign=top]
        a box. `row` / `cell` lines after it are its parts (ID.PART):
  row  PART "TEXT" [mono]        stacked rows (title = the node's label, if any)
  cell PART "TEXT"               a left-to-right pipeline under the title
  note ID "TEXT" X,Y [mono] [anchor=start|middle|end] [size=N]
  edge ID A -> B ["LABEL"] [via …] [ws|gap|human] [seg=N] [t=F] [below|left|over] [mono|sans]
        A/B = NODE[.PART][:SIDE[=COORD]], SIDE in l r t b; COORD pins the point
        along that side (absolute y for l/r, x for t/b). `--` = no arrowhead,
        `<->` = both. via: x=N turn at x=N · y=N turn at y=N · X,Y a point.
  pill ID on EDGE "TEXT" >|< [t=F] [dy=N]      a message riding on an edge
  mark ID shield|cross|q "TEXT" X,Y [anchor=start|middle|end] [lbl=below|above] [lxy=X,Y]
        lxy= puts the label's baseline at X,Y (e.g. a shield in a tight door, its words beside it)
  key  ID new|fwd|rev|ws|warn "TEXT" X,Y
  flow ID [fwd|rev|warn] @S[-E] [lands=ID[,ID…]] : ITEM, ITEM, … [| ITEM, …]
    ITEM = EDGE[<] ["MSG"]  |  EDGE[<] at ID[+ID…]  |  NODE.PART[+ID…]
        a message travelling hop by hop over existing edges, in order. `<` runs
        a hop against the edge's drawn direction (B → A). "MSG" rides along as a
        pill beside the wire, on a side and stretch clear of boxes and words; a
        static pill on that edge with the same text and direction (its twin)
        steps aside while that hop runs and is back when it ends. Without a twin
        the pill stays where it arrived until the flow ends, and print shows it
        there. A row or cell in the list (NODE.PART) is a station: the token is
        inside that box, and the part lights for a beat (STATION_MS), in order.
        `+ID…` after it is a beat: those rows, cells, nodes, notes, marks or edges
        light with it (a mark pulses where it has room, then its words stay lit, or,
        without words, it keeps a ring: _pulse). `EDGE at ID+ID…` is a waypoint: the token
        stops on the hop where it passes the first id (a mark or a box within
        WAYPOINT_NEAR of the route), the ids light for WAYPOINT_MS, then it goes on.
        `|` starts a leg: a deliberate restart elsewhere (the token goes in, and
        comes out a moment later (diagram.js: LEG) at the next leg's first door; no jump warning).
        fwd (default) = violet, page → code and the dev machinery · rev =
        green, code → page · warn = amber, a bypass. Unlike a part, a bare @S
        means state S ONLY (a flow is a moment); S- is from S on. Print numbers
        the hops (A1, A2 … B1 … when a state has several flows); a door-to-door
        hop too short to hold a number beside it is not numbered, nor is a station
        or a waypoint. lands= names the boxes or rows where the flow's effect shows
        (the highlighted span, the opened buffer): they light up in the flow's colour
        while the path stays lit.
  swap ID @K : out ID,ID… ; in ID,ID…
        an animated replacement in state K (one state): the out parts (on screen in
        the state before K, gone in K by their own range) are still there when K
        arrives and retire when the swap plays; the in parts (on screen in K, not in
        the state before) appear only then. Nodes, rows, edges, pills, notes, marks;
        either list may be left out. Flows and swaps are a state's animations: they
        play in the order written, one per `a`, on one progress line. The static
        picture (print, the deck, a minimap) is the END state; an out node's label
        stays there as a struck-through cue.
        How a slide plays them is the slide's business: {.flow-auto} (default),
        {.flow-keys} (= {.flow-step}: only the a / p keys), {.flow-loop},
        {.flow-off} on the line before the fence (diagram.js, DIAGRAM.md).

  every element also takes
    @S  @S-E  @S-E,K…             visible from S on / S..E / several ranges
    +S:CLS  +S-:CLS  +S-E:CLS     class ax-CLS at S / from S on / S..E
    S:TEXT  S-E:TEXT              the label from S on / during S..E

State classes of an element at state K: ax-cast (K is the first state),
ax-new (first visible at K), ax-old (visible before K), ax-changed (a label range
or a class starts at K), plus the rule classes above. A `summary` step marks no deltas.
In a state with a swap, its parts also carry ax-swap-out / ax-swap-in (diagram.js drives them;
without the script they show the swap's end state).
"""
import html, math, re, shlex
from pathlib import Path

esc = lambda s: html.escape(s, quote=True)

try:
    from PIL import ImageFont
    _F = {}
    def text_w(s, px, mono=False, bold=False):
        f = "/usr/share/fonts/truetype/dejavu/DejaVuSans%s%s.ttf" % ("Mono" if mono else "", "-Bold" if bold else "")
        if (f, px) not in _F: _F[(f, px)] = ImageFont.truetype(f, px)
        return _F[(f, px)].getlength(s)
except Exception:                                    # no PIL: a conservative estimate
    def text_w(s, px, mono=False, bold=False): return len(s) * px * (0.61 if mono else 0.64)

def line_w(s, px, mono=False, bold=True):
    """Like text_w, for slide text that may hold emoji (a heading): an emoji is set in the
    colour-emoji font at ~1.25em, which DejaVu does not have (it would measure .6em)."""
    w = 0.0
    for ch in s:
        o = ord(ch)
        if o in (0xFE0F, 0x200D): continue               # presentation selector, joiner: no advance
        w += 1.25 * px if o >= 0x1F000 or 0x2600 <= o <= 0x27BF else text_w(ch, px, mono, bold)
    return w

# ---- metrics (layout, not look). DejaVu is wider than the stage laptop's system-ui,
# so a label that fits here fits there.
# Projector sizes at 1920x1080, where 1 unit = 1 screen px: box labels 36 (monospace 34,
# which reads as large), rows 32, and nothing that carries words below 28 — cells,
# edge labels, pills, captions, marks, keys. Only the print-only hop numbers sit at 26,
# the floor. The layout is sized for these: cut words, never shrink them.
FS = dict(node=36, mono=34, sub=26, row=32, cell=28, edge=28, emono=28, pill=28, cap=28, note=28, mark=28, key=28,
          mpill=30, hopnum=26)
PAD, TITLE_H, CELL_H, CELL_GAP, PILL_H, HEAD_L, HEAD_W = 14, 52, 44, 28, 42, 19, 9.5
MPILL_H, HOPNUM_R = 46, 21                           # the moving message pill; the print-only hop number
MARK_R = 17                                          # a mark's glyph (shield, cross, ?)
NUM_MSG_GAP = 56                                     # a hop number keeps this far (centre to box) from another message's pill
NUM_MARK_GAP = 10                                    # … and this much further from a mark's glyph than from words: "2 ✕" must not read as one
FLOW_KINDS = ("fwd", "rev", "warn")
# One hop's travel time. Speed stays within ~25 px per 60 Hz frame at the peak of the cosine
# ease (longer hops take longer, up to 1.8 s); a hop too short to show motion (the 20 px
# dispatch) is a 450 ms beat; a hop that carries a message lasts ≥ 1.2 s, so it can be read.
MSG_MIN_MS = 1200
STATION_MS = 450                                     # a flow's station: the part lights for this beat, the token inside the box
WAYPOINT_MS = 600                                    # a waypoint's beat: longer, the token stands still on the wire meanwhile
WAYPOINT_NEAR = 24                                   # a waypoint's first id lies this close to its hop's route, or the build stops
BEAT_KINDS = ("row", "cell", "node", "mark", "note", "edge")   # what may light with a station or a waypoint
PULSE, PULSE_MIN = 1.25, 1.1                        # a mark in a beat pulses up to 1.25×; below 1.1 it would not read: it keeps still
PULSE_CLEAR = 4                                      # what a pulse or a ring keeps from anything else drawn, strokes included
RING_GAP, RING_MIN, RING_W = 8, 5, 3.5               # a mark without words keeps a ring 8 units out, or as far as room allows, down to 5
GLYPH_INK = dict(shield=1.8, cross=1.5, q=1.5)       # how far a glyph's stroke reaches past its outline (a shield: its mitred corners)
SWAP_MS = 1800                                       # a swap: strike, retire, draw in (the phases: diagram.js)
SWAP_KINDS = ("node", "row", "edge", "pill", "note", "mark")
def hop_ms(length, msg=False):
    ms = 450 if length < 100 else min(1800, max(600, 400 + 0.8 * length))
    return round(max(ms, MSG_MIN_MS) if msg else ms)
def boxes_hit(a, b):
    """Do two (x, y, w, h) boxes overlap?"""
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]
def grow(b, m): return (b[0] - m, b[1] - m, b[2] + 2 * m, b[3] + 2 * m)
def _box_gap(a, b):
    """The clear distance between two (x, y, w, h) boxes; overlapping: minus how deep."""
    dx = max(b[0] - a[0] - a[2], a[0] - b[0] - b[2]); dy = max(b[1] - a[1] - a[3], a[1] - b[1] - b[3])
    return math.hypot(max(dx, 0), max(dy, 0)) if dx > 0 or dy > 0 else max(dx, dy)
def _box_dist_pt(b, p):
    """The distance from point p to box b (0 inside it)."""
    return math.hypot(max(b[0] - p[0], 0, p[0] - b[0] - b[2]), max(b[1] - p[1], 0, p[1] - b[1] - b[3]))
def _seg_dist(p, a, b):
    """The distance from point p to the segment a–b."""
    L2 = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
    t = max(0.0, min(1.0, ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / (L2 or 1)))
    return math.dist(p, (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
_ID = r"[A-Za-z][\w-]*(?:\.[\w-]+)?"
# one item of a flow's hop list: ID[+ID…][<] ["MSG"] [at ID[+ID…]], then `,`, `|` (a new leg) or the end
_HOP = re.compile(rf"""\s*({_ID})((?:\s*\+\s*{_ID})*)(<?)\s*(?:"([^"]*)"|'([^']*)')?\s*(?:\bat\s+({_ID}(?:\s*\+\s*{_ID})*))?\s*(,|\||\#.*$|$)""")
_ids = lambda s: [i for i in re.split(r"\s*\+\s*", s or "") if i]

class Item:
    """One item of a flow: a hop over edge `eid` (rev: against its direction; msg: its message; at: a
    waypoint's ids), or a station `eid` (a row or cell; plus: what lights with it). leg: its leg (`|`)."""
    __slots__ = ("eid", "rev", "msg", "plus", "at", "leg")
    def __init__(self, eid, rev, msg, plus, at, leg):
        self.eid, self.rev, self.msg, self.plus, self.at, self.leg = eid, rev, msg, plus, at, leg
    def ids(self):
        """Every id this item names: its edge or part, and what lights with it."""
        return [self.eid] + self.plus + self.at
    def __repr__(self): return f"{self.eid}{'<' if self.rev else ''}"

def polylen(pts): return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
def at_len(pts, s):
    """The point at arc length s along a polyline."""
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b)
        if s <= L or b == pts[-1]:
            f = 0 if L == 0 else max(0.0, min(1.0, s / L))
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        s -= L
    return pts[-1]

def parse_ranges(s):
    """'3' → from 3 on · '3-9' → 3..9 · '3-' → from 3 on · '3-15,17' → 3..15 and 17 (in a list, a bare K is K only)."""
    parts, out = s.split(","), []
    for p in parts:
        m = re.fullmatch(r"(\d+)(-(\d*))?", p)
        if not m: raise ValueError(f"bad range {s!r}")
        a = int(m[1])
        b = (None if len(parts) == 1 else a) if m[2] is None else (int(m[3]) if m[3] else None)
        out.append((a, b))
    return out

class El:
    def __init__(self, kind, id, label=""):
        self.kind, self.id, self.label = kind, id, label
        self.vis, self.cls, self.labels, self.opts, self.parts = [(0, None)], [], [], {}, []

    def on(self, k): return any(a <= k and (b is None or k <= b) for a, b in self.vis)
    def text(self, k):
        t = self.label
        for a, b, s in self.labels:
            if a <= k and (b is None or k <= b): t = s
        return t

class Diagram:
    def __init__(self, name, src):
        self.name = name
        self.W, self.H = 1760, 840
        self.steps, self.rules, self.hides = {}, {}, {}
        self.els, self.order = {}, []
        last = None
        for n, raw in enumerate(src.splitlines(), 1):
            try:
                if re.match(r"\s*flow\s", raw):         # hops are a comma list: parsed on the raw line
                    self._flow(raw); continue
                if re.match(r"\s*swap\s", raw):         # so are a swap's parts
                    self._swap(raw); continue
                toks = shlex.split(raw, comments=True)
                if toks: last = self._stmt(toks, last)
            except Exception as e:
                raise SystemExit(f"diagram {name}, line {n}: {e}\n  {raw}")
        if not self.steps: raise SystemExit(f"diagram {name}: no steps")
        self.first = min(self.steps)
        self._layout()
        self._check()

    # ------------------------------------------------------------ parsing ---
    def _common(self, toks, el):
        rest = []
        for t in toks:
            if t.startswith("@"): el.vis = parse_ranges(t[1:])
            elif m := re.fullmatch(r"\+(\d+)(-(\d*))?:([\w-]+)", t):
                a = int(m[1]); b = a if not m[2] else (int(m[3]) if m[3] else None)
                el.cls.append((a, b, m[4]))
            elif m := re.fullmatch(r"(\d+)(-(\d*))?:(.*)", t, re.S):
                a = int(m[1]); b = None if not m[2] else (int(m[3]) if m[3] else None)
                el.labels.append((a, b, m[4]))
            elif "=" in t and not re.fullmatch(r"[xy]=-?[\d.]+", t):
                k, _, v = t.partition("="); el.opts[k] = v
            else: rest.append(t)
        return rest

    def _add(self, el):
        if el.id in self.els: raise ValueError(f"{el.id} defined twice")
        self.els[el.id] = el; self.order.append(el)
        return el

    @staticmethod
    def _xy(t): return tuple(float(v) for v in t.split(","))
    @staticmethod
    def _wh(t): return tuple(float(v) for v in t.split("x"))

    def _stmt(self, t, last):
        kw = t[0]
        if kw == "canvas":
            self.W, self.H = map(int, t[1].split("x")); return last
        if kw == "chip" or (kw in ("step", "state") and any(r.startswith("branch=") for r in t[3:])):
            raise ValueError("the branch chip is gone: the map is keyed to talk sections, not git branches "
                             "(delete the `chip` line and every `branch=`)")
        if kw in ("step", "state"):
            k = int(t[1])
            if k in self.steps: raise ValueError(f"state {k} defined twice")
            self.steps[k] = {"caption": t[2] if len(t) > 2 else ""}
            for r in t[3:]:
                if r == "summary": self.steps[k]["summary"] = True
                elif r.startswith("hide:"): self.hides[k] = r[5:].split(",")
                elif m := re.fullmatch(r"\+([\w-]+):([\w.,-]+)", r):
                    self.rules.setdefault(k, []).append((m[1], m[2].split(",")))
                else: raise ValueError(f"step: unknown {r!r}")
            return last
        if kw == "region":
            el = El("region", t[1], t[3]); el.rkind = t[2]
            rest = self._common(t[4:], el)
            el.x, el.y = self._xy(rest[0]); el.w, el.h = self._wh(rest[1])
            return self._add(el)
        if kw == "node":
            el = El("node", t[1], t[2])
            rest = self._common(t[3:], el)
            el.x, el.y = self._xy(rest[0]); el.w, el.h = self._wh(rest[1])
            el.mono, el.list = "mono" in rest, "list" in rest
            return self._add(el)
        if kw in ("row", "cell"):
            if not last or last.kind != "node": raise ValueError(f"{kw} must follow a node")
            el = El(kw, f"{last.id}.{t[1]}", t[2]); el.parent = last
            rest = self._common(t[3:], el)
            el.mono = "mono" in rest or kw == "cell"
            if last.parts and last.parts[0].kind != kw: raise ValueError("a node has rows or cells, not both")
            last.parts.append(el); self._add(el)
            return last
        if kw == "note":
            el = El("note", t[1], t[2]); rest = self._common(t[3:], el)
            el.x, el.y = self._xy(rest[0]); el.mono = "mono" in rest
            return self._add(el)
        if kw == "edge":
            el = El("edge", t[1]); el.a, arrow, el.b = t[2], t[3], t[4]
            if arrow not in ("->", "<->", "--"): raise ValueError(f"edge wants A -> B, got {t[2:5]}")
            el.head, el.both = arrow != "--", arrow == "<->"
            rest = self._common(t[5:], el)
            el.via, el.flags, i = [], set(), 0
            while i < len(rest):
                r = rest[i]
                if r == "via":
                    i += 1
                    while i < len(rest) and (re.fullmatch(r"[xy]=-?[\d.]+", rest[i]) or re.fullmatch(r"-?[\d.]+,-?[\d.]+", rest[i])):
                        v = rest[i]
                        el.via.append((v[0], float(v[2:])) if v[0] in "xy" else ("pt", self._xy(v))); i += 1
                    continue
                if r in ("ws", "gap", "human", "below", "left", "over", "mono", "sans"): el.flags.add(r)
                elif not el.label: el.label = r
                else: raise ValueError(f"edge: unknown token {r!r}")
                i += 1
            return self._add(el)
        if kw == "pill":
            el = El("pill", t[1], t[4]); el.on_edge = t[3]
            if t[2] != "on": raise ValueError("pill ID on EDGE \"TEXT\" >|<")
            rest = self._common(t[5:], el)
            el.dir = 1 if ">" in rest else -1
            return self._add(el)
        if kw == "mark":
            el = El("mark", t[1], t[3]); el.mkind = t[2]
            rest = self._common(t[4:], el); el.x, el.y = self._xy(rest[0])
            return self._add(el)
        if kw == "key":
            el = El("key", t[1], t[3]); el.kkind = t[2]
            rest = self._common(t[4:], el); el.x, el.y = self._xy(rest[0])
            return self._add(el)
        raise ValueError(f"unknown statement {kw!r}")

    def _flow(self, raw):
        m = re.fullmatch(r"\s*flow\s+([\w-]+)((?:\s+[^\s:]+)*)\s+:\s*(.*?)\s*", raw)
        if not m: raise ValueError('flow ID [fwd|rev|warn] @S[-E] [lands=ID[,ID…]] : EDGE[<] ["MSG"], …')
        el = El("flow", m[1]); el.fkind, el.vis, el.hops, el.lands = "fwd", None, [], []
        for t in m[2].split():
            if t in FLOW_KINDS: el.fkind = t
            elif t.startswith("lands="):
                el.lands = t[6:].split(",")
                if not all(el.lands): raise ValueError(f"flow {el.id}: lands={t[6:]}: an empty id (lands=ID[,ID…], no spaces)")
            elif t.startswith("@"):
                el.vis = []
                for p in t[1:].split(","):                # a bare S is S only: a flow is a moment, not a part
                    r = re.fullmatch(r"(\d+)(-(\d*))?", p)
                    if not r: raise ValueError(f"flow {el.id}: bad range {t!r}")
                    a = int(r[1]); el.vis.append((a, a if not r[2] else (int(r[3]) if r[3] else None)))
            else: raise ValueError(f"flow {el.id}: unknown {t!r} (fwd|rev|warn, @S[-E], lands=ID[,ID…])")
        if el.vis is None: raise ValueError(f"flow {el.id}: which state? add @S")
        body, pos, leg = m[3], 0, 0
        while pos < len(body):
            h = _HOP.match(body, pos)
            if not h or h.end() == pos: raise ValueError(f"flow {el.id}: can't read a hop at {body[pos:]!r}")
            msg = h[4] if h[4] is not None else h[5]
            if msg is not None and h[6]:
                raise ValueError(f"flow {el.id}: {h[1]} has a message and a waypoint: a hop with `at` takes no message")
            el.hops.append(Item(h[1], h[3] == "<", msg, _ids(h[2]), _ids(h[6]), leg))
            pos = h.end()
            if h[7] == "|":                               # a new leg: a deliberate restart elsewhere
                leg += 1
                if not body[pos:].strip() or body[pos:].lstrip().startswith(("|", ",", "#")):
                    raise ValueError(f"flow {el.id}: an empty leg after `|` (ITEM, … | ITEM, …)")
            elif h[7] != ",": break
            elif not body[pos:].strip() or body[pos:].lstrip().startswith(("|", ",", "#")):
                raise ValueError(f"flow {el.id}: nothing after a `,` (hops are separated by commas)")
        if body[pos:].strip(): raise ValueError(f"flow {el.id}: left over {body[pos:]!r} (hops are separated by commas, legs by `|`)")
        if not el.hops: raise ValueError(f"flow {el.id}: no hops")
        self._add(el)

    def _swap(self, raw):
        """swap ID @K : out ID,ID… ; in ID,ID…  (either list may be left out)"""
        usage = "swap ID @K : out ID,ID… ; in ID,ID…"
        m = re.fullmatch(r"\s*swap\s+([\w-]+)\s+@(\S+)\s*:\s*(.*?)\s*", raw.split("#", 1)[0])
        if not m: raise ValueError(f"want {usage}")
        if not re.fullmatch(r"\d+", m[2]): raise ValueError(f"swap {m[1]}: @{m[2]}: a swap is one moment of one state, @K")
        el = El("swap", m[1]); el.k = int(m[2]); el.vis = [(el.k, el.k)]; el.out, el.inn = [], []
        seen = set()
        for chunk in m[3].split(";"):
            c = re.fullmatch(r"\s*(out|in)\s+([\w.,\s-]+?)\s*", chunk)
            if not c: raise ValueError(f"swap {el.id}: can't read {chunk.strip()!r} (want {usage})")
            if c[1] in seen: raise ValueError(f"swap {el.id}: `{c[1]}` twice")
            seen.add(c[1])
            ids = [i for i in re.split(r"[,\s]+", c[2]) if i]
            (el.out if c[1] == "out" else el.inn).extend(ids)
        if not el.out and not el.inn: raise ValueError(f"swap {el.id}: nothing to swap (want {usage})")
        self._add(el)

    def hop_ends(self, eid, rev):
        """→ (from node, to node) of a hop, as base node ids (a station: its node, twice)."""
        e = self.els[eid]
        if e.kind in ("row", "cell"): return e.parent.id, e.parent.id
        a, b = (e.b, e.a) if rev else (e.a, e.b)
        base = lambda s: s.split(":")[0].split(".")[0]
        return base(a), base(b)

    # ------------------------------------------------------------- layout ---
    def _layout(self):
        """Part geometry, computed once from ALL parts (absent ones keep their slot)."""
        for nd in (e for e in self.order if e.kind == "node" and e.parts):
            if nd.parts[0].kind == "row":
                top = nd.y + (TITLE_H if nd.label else 0)
                rh = (nd.y + nd.h - top - (8 if nd.label else 0)) / len(nd.parts)
                for i, p in enumerate(nd.parts):
                    p.x, p.y, p.w, p.h = nd.x + 6, top + i * rh, nd.w - 12, rh
            else:
                x, cy = nd.x + PAD + 2, nd.y + nd.h - CELL_H / 2 - PAD
                for p in nd.parts:
                    p.w = text_w(p.label, FS["cell"], True) + 26
                    p.x, p.y, p.h = x, cy - CELL_H / 2, CELL_H
                    x += p.w + CELL_GAP
                if x - CELL_GAP > nd.x + nd.w - PAD:
                    print(f"  warning: diagram {self.name}: cells of {nd.id} overflow by {x - CELL_GAP - (nd.x + nd.w - PAD):.0f}px")

    def rect(self, path):
        el = self.els.get(path)
        if not el or el.kind not in ("node", "row", "cell", "region"): raise SystemExit(f"diagram {self.name}: no box {path!r}")
        return el.x, el.y, el.w, el.h

    def _check(self):
        for e in self.order:
            if e.kind == "edge":
                for end in (e.a, e.b): self.rect(end.split(":")[0])
                for a, _ in e.vis:
                    for end in (e.a, e.b):
                        nd = self.els[end.split(":")[0]]
                        if not nd.on(a) and nd.kind != "region": print(f"  warning: diagram {self.name}: edge {e.id} is on at {a}, its end {nd.id} is not")
            if e.kind == "pill" and e.on_edge not in self.els: raise SystemExit(f"diagram {self.name}: pill {e.id} on unknown edge {e.on_edge}")
            if e.kind == "node" and not e.parts and e.label:
                for t in [e.label] + [s for _, _, s in e.labels]:
                    need = text_w(t, FS["mono" if e.mono else "node"], e.mono) + 16
                    if need > e.w: print(f"  warning: diagram {self.name}: {e.id} label {t!r} needs {need:.0f} > {e.w:.0f}")
            if e.kind == "row":
                for t in [e.label] + [s for _, _, s in e.labels]:
                    need = text_w(t, FS["row"], e.mono) + 16
                    if need > e.w: print(f"  warning: diagram {self.name}: {e.id} row {t!r} needs {need:.0f} > {e.w:.0f}")
        for k, ids in list(self.hides.items()) + [(k, [i for _, l in r for i in l]) for k, r in self.rules.items()]:
            for i in ids:
                if i not in self.els: raise SystemExit(f"diagram {self.name}: step {k} names unknown {i!r}")
        self._check_swaps()
        for f in (e for e in self.order if e.kind == "flow"):
            name = f"diagram {self.name}: flow {f.id}"
            for it in f.hops:
                el = self.els.get(it.eid)
                named = it.ids()
                if len(set(named)) < len(named):               # a beat lights each id once (as lands= does)
                    raise SystemExit(f"{name}: {it.eid}: {next(i for i in named if named.count(i) > 1)} named twice in one item")
                for i in it.plus + it.at:                      # what lights with a station or a waypoint
                    b = self.els.get(i)
                    if not b or b.kind not in BEAT_KINDS:
                        raise SystemExit(f"{name}: {it.eid}: {i!r} can't light in a beat (a {', '.join(BEAT_KINDS)})")
                if el and el.kind in ("row", "cell"):          # a station: the token is inside that box
                    if it.rev or it.msg or it.at: raise SystemExit(f"{name}: station {it.eid} takes no `<`, no message and no `at`")
                    continue
                if not el or el.kind != "edge": raise SystemExit(f"{name}: {it.eid!r} is not an edge (nor a row or cell: a station)")
                if it.plus:
                    raise SystemExit(f"{name}: {it.eid}+{'+'.join(it.plus)}: `+` joins what lights with a station (NODE.PART+ID…); "
                                     f"on a hop, name a waypoint: {it.eid} at {'+'.join(it.plus)}")
                if it.at:
                    w = self.els[it.at[0]]
                    if w.kind not in ("mark", "node", "row", "cell", "note"):
                        raise SystemExit(f"{name}: {it.eid} at {it.at[0]}: a waypoint is a mark or a box the token passes, not a {w.kind}")
            states = [s for s in self.steps if f.on(s)]
            if not states: print(f"  warning: {name} plays in no state")
            for i in f.lands:
                if i not in self.els or self.els[i].kind not in ("node", "row", "cell"):
                    raise SystemExit(f"{name}: lands={i} is not a box or a row")
            if len(set(f.lands)) < len(f.lands): raise SystemExit(f"{name}: lands= names an id twice")
            for s in states:
                hid, seq = self.hidden(s), self.anims(s)
                pos = seq.index(f)
                why = lambda i: next((f" (swap {a.id}, which plays {'after' if j > pos else 'before'} it, "
                                      f"{'brings it in' if i in a.in_all else 'retires it'})"
                                      for j, a in enumerate(seq) if a.kind == "swap" and i in a.out_all + a.in_all), "")
                for i in f.lands:
                    if not self.on_at(self.els[i], s, pos, hid):
                        raise SystemExit(f"{name} plays at state {s}, but lands={i} is not on screen there{why(i)}")
                for it in f.hops:
                    if not self.on_at(self.els[it.eid], s, pos, hid):
                        raise SystemExit(f"{name} plays at state {s}, but its {'station' if '.' in it.eid else 'edge'} {it.eid} is not on screen there{why(it.eid)}")
                    for i in it.plus + it.at:
                        if not self.on_at(self.els[i], s, pos, hid):
                            raise SystemExit(f"{name} plays at state {s}, but {i} (in the beat of {it.eid}) is not on screen there{why(i)}")
                    if it.at:                                   # the waypoint lies on the route: the token stops where it passes it
                        d, _ = self.waypoint(it, s)
                        if d > WAYPOINT_NEAR:
                            raise SystemExit(f"{name}: {it.eid} at {it.at[0]}: in state {s}, {it.at[0]} is {d:.0f} units from the "
                                             f"hop's route (at most {WAYPOINT_NEAR}): a waypoint is something the token passes")
                for a in seq[pos + 1:]:
                    if a.kind == "swap" and (gone := [i for it in f.hops for i in it.ids() if i in a.out_all]):
                        print(f"  warning: {name} plays at state {s} before swap {a.id} and uses what it retires "
                              f"({', '.join(gone)}); print draws the end state, so those hops are numbered beside wires it does not draw")
            for a, b in zip(f.hops, f.hops[1:]):
                if b.leg != a.leg: continue                     # a new leg is a restart elsewhere: no jump
                if self.hop_ends(a.eid, a.rev)[1] != self.hop_ends(b.eid, b.rev)[0]:
                    print(f"  warning: {name}: {a!r} ends at {self.hop_ends(a.eid, a.rev)[1]}, "
                          f"but {b!r} leaves from {self.hop_ends(b.eid, b.rev)[0]} (the token jumps; `|` if it restarts on purpose)")

    def centre(self, el, k):
        """Where an element is, as one point: a box's centre, a mark's glyph, a note's words."""
        if el.kind == "mark": return el.x, el.y
        if el.kind == "note":
            fs = int(el.opts.get("size", FS["note"])); tw = text_w(el.text(k), fs, el.mono, bold=True)
            anc = el.opts.get("anchor", "start")
            x0 = el.x - tw / 2 if anc == "middle" else el.x - tw if anc == "end" else el.x
            return x0 + tw / 2, el.y - fs * .3
        return el.x + el.w / 2, el.y + el.h / 2

    def waypoint(self, it, k):
        """A hop's waypoint → (distance of its first id from the route, arc length where the token stops: the
        route's point nearest to it)."""
        pts = self.route(self.els[it.eid]); pts = pts[::-1] if it.rev else pts
        c = self.centre(self.els[it.at[0]], k)
        best, acc = None, 0.0
        for a, b in zip(pts, pts[1:]):
            L = math.dist(a, b)
            t = max(0.0, min(1.0, ((c[0] - a[0]) * (b[0] - a[0]) + (c[1] - a[1]) * (b[1] - a[1])) / (L * L or 1)))
            d = math.dist((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])), c)
            if best is None or d < best[0] - 1e-9: best = (d, acc + t * L)
            acc += L
        return best

    # ------------------------------------------------------------- swaps ---
    def anims(self, k):
        """State k's animations, its flows and swaps, in the order written: one per `a`."""
        return [e for e in self.order if e.kind in ("flow", "swap") and e.on(k)]

    def on_at(self, el, k, pos, hid):
        """Is el on screen in state k when the state's animation number pos starts (pos past
        the last: at rest after them all)? A swap from pos on has not played yet: its out parts
        are still there, its in parts not yet. Otherwise el's own range decides."""
        for a in self.anims(k)[pos:]:
            if a.kind == "swap":
                if el.id in a.out_all: return True
                if el.id in a.in_all: return False
        return self.visible(el, k, hid)

    def _closure(self, ids, k, hid):
        """ids plus what goes with them in state k: a node's rows, an edge's pills."""
        out = []
        for i in ids:
            el = self.els[i]; out.append(i)
            if el.kind == "node": out += [p.id for p in el.parts if self.visible(p, k, hid)]
            if el.kind == "edge": out += [p.id for p in self.order if p.kind == "pill" and p.on_edge == i and self.visible(p, k, hid)]
        return list(dict.fromkeys(out))

    def _check_swaps(self):
        """A swap's parts, and the pictures before and after it → sw.prev, sw.out_all, sw.in_all
        (the parts with their rows and pills), sw.keep (an out edge's end that stays: its line
        retracts into it; '-': both ends go, it fades), self.roles[K] (ax-swap-out / ax-swap-in)."""
        self.roles = {}
        base = lambda s: s.split(":")[0].split(".")[0]
        for sw in (e for e in self.order if e.kind == "swap"):
            K, name = sw.k, f"diagram {self.name}: swap {sw.id} @{sw.k}"
            if K not in self.steps: raise SystemExit(f"{name}: no state {K} (states: {sorted(self.steps)})")
            prev = max((s for s in self.steps if s < K), default=None)
            if prev is None: raise SystemExit(f"{name}: state {K} is the first one; a swap starts from the state before it")
            hk, hp = self.hidden(K), self.hidden(prev)
            ids = sw.out + sw.inn
            for i in ids:
                el = self.els.get(i)
                if not el or el.kind not in SWAP_KINDS: raise SystemExit(f"{name}: {i!r} is not a {', '.join(SWAP_KINDS)}")
                if ids.count(i) > 1: raise SystemExit(f"{name}: {i} is listed twice")
            for i in sw.out:
                if not self.visible(self.els[i], prev, hp):
                    raise SystemExit(f"{name}: out {i} is not on screen in state {prev}: a swap retires parts that are built already")
                if self.visible(self.els[i], K, hk):
                    raise SystemExit(f"{name}: out {i} is still on screen in state {K} by its own range: end it at {prev} (the swap is what removes it)")
            for i in sw.inn:
                if not self.visible(self.els[i], K, hk): raise SystemExit(f"{name}: in {i} is not on screen in state {K}")
                if self.visible(self.els[i], prev, hp):
                    raise SystemExit(f"{name}: in {i} is on screen already in state {prev}: a swap brings in only what state {K} adds")
            sw.prev, sw.out_all, sw.in_all = prev, self._closure(sw.out, prev, hp), self._closure(sw.inn, K, hk)
            for i in sw.out_all:
                if self.visible(self.els[i], K, hk): raise SystemExit(f"{name}: {i} goes with out {self.els[i].on_edge if self.els[i].kind == 'pill' else ''}, but is on screen in state {K} by its own range: end it at {prev}")
            for i in sw.in_all:
                if self.visible(self.els[i], prev, hp): raise SystemExit(f"{name}: {i} comes with the in parts, but is on screen already in state {prev}")
            for i in sw.out_all:                      # the before picture draws an out part with state K's words and classes
                el = self.els[i]
                if el.text(prev) != el.text(K):       # its words would change on the cut, just before it retires
                    raise SystemExit(f"{name}: out {i} says {el.text(prev)!r} in state {prev} but {el.text(K)!r} in the "
                                     f"before picture of state {K}: extend its label range to {K}")
                if (c0 := sorted(self.classes(el, prev))) != (c1 := sorted(self.classes(el, K))):   # maybe on purpose
                    print(f"  warning: {name}: out {i} has classes {' '.join(c0) or 'none'} in state {prev} but "
                          f"{' '.join(c1) or 'none'} in the before picture of state {K}: its look changes on the cut")
            roles = self.roles.setdefault(K, {})
            for i, r in [(i, "out") for i in sw.out_all] + [(i, "in") for i in sw.in_all]:
                if i in roles: raise SystemExit(f"{name}: {i} is in another swap of state {K} already")
                roles[i] = r
            gone = lambda s: s.split(":")[0] in sw.out_all or base(s) in sw.out_all
            sw.keep = {i: "-" if gone(e.a) and gone(e.b) else "b" if gone(e.a) else "a"
                       for i in sw.out_all if (e := self.els[i]).kind == "edge"}
            for e in self.order:                      # a wire of a retiring box that ends with the state before: it would vanish on the cut
                if (e.kind == "edge" and e.id not in sw.out_all and (gone(e.a) or gone(e.b))
                        and self.visible(e, prev, hp) and not self.visible(e, K, hk)):
                    print(f"  warning: {name}: edge {e.id} to what it retires is on screen in state {prev}, but not when state {K} arrives: "
                          f"it vanishes on the cut instead of retiring with the swap (add it to out)")
        for K in self.roles:                          # no wire hangs from nothing, before or after any swap
            hid, seq = self.hidden(K), self.anims(K)
            for pos in range(len(seq) + 1):
                on = lambda el: self.on_at(el, K, pos, hid)
                when = f"after {seq[pos - 1].kind} {seq[pos - 1].id}" if pos else "as it arrives"
                for e in (e for e in self.order if e.kind == "edge" and on(e)):
                    for end in (e.a, e.b):
                        nd = self.els[end.split(":")[0]]
                        if nd.kind != "region" and not on(nd):
                            raise SystemExit(f"diagram {self.name}: state {K}, {when}: edge {e.id} hangs from {nd.id}, which is not on screen "
                                             f"(swap the edge together with its end)")

    # ------------------------------------------------------------ routing ---
    def anchor(self, spec, other):
        path, _, side = spec.partition(":")
        side, _, coord = side.partition("=")
        x, y, w, h = self.rect(path)
        if not side:
            ox, oy, ow, oh = self.rect(other.split(":")[0])
            if ox >= x + w: side = "r"
            elif ox + ow <= x: side = "l"
            elif oy >= y + h: side = "b"
            else: side = "t"
        c = float(coord) if coord else None
        return side, {"l": (x, c if c is not None else y + h / 2), "r": (x + w, c if c is not None else y + h / 2),
                      "t": (c if c is not None else x + w / 2, y), "b": (c if c is not None else x + w / 2, y + h)}[side]

    def route(self, e):
        sa, P = self.anchor(e.a, e.b)
        sb, Q = self.anchor(e.b, e.a)
        if not e.via:                                  # snap straight: slide an unpinned end to line up
            ap, bp = "=" in e.a, "=" in e.b
            ax, ay, aw, ah = self.rect(e.a.split(":")[0]); bx, by, bw, bh = self.rect(e.b.split(":")[0])
            if sa in "tb" and sb in "tb":
                if not bp and bx + 6 <= P[0] <= bx + bw - 6: Q = (P[0], Q[1])
                elif not ap and ax + 6 <= Q[0] <= ax + aw - 6: P = (Q[0], P[1])
            elif sa in "lr" and sb in "lr":
                if not bp and by + 6 <= P[1] <= by + bh - 6: Q = (Q[0], P[1])
                elif not ap and ay + 6 <= Q[1] <= ay + ah - 6: P = (P[0], Q[1])
        pts, cur, d = [P], P, "h" if sa in "lr" else "v"
        for kind, v in e.via:
            if kind == "pt":
                d = "v" if abs(v[0] - cur[0]) < .5 else "h"
                cur = v; pts.append(cur); d = "h" if d == "v" else "v"
            elif kind == "x":
                if d != "h": raise SystemExit(f"diagram {self.name}: edge {e.id}: x={v} needs a horizontal run")
                cur = (v, cur[1]); pts.append(cur); d = "v"
            else:
                if d != "v": raise SystemExit(f"diagram {self.name}: edge {e.id}: y={v} needs a vertical run")
                cur = (cur[0], v); pts.append(cur); d = "h"
        qd = "h" if sb in "lr" else "v"
        if d == qd:
            if d == "h" and abs(cur[1] - Q[1]) > .5:
                mx = (cur[0] + Q[0]) / 2; pts += [(mx, cur[1]), (mx, Q[1])]
            elif d == "v" and abs(cur[0] - Q[0]) > .5:
                my = (cur[1] + Q[1]) / 2; pts += [(cur[0], my), (Q[0], my)]
        else:
            pts.append((Q[0], cur[1]) if d == "h" else (cur[0], Q[1]))
        pts.append(Q)
        out = [pts[0]]
        for p in pts[1:]:
            if math.dist(p, out[-1]) > .5: out.append(p)
        return out

    # ------------------------------------------------------------- states ---
    def hidden(self, k):
        hid = set()
        for i in self.hides.get(k, []):
            el = self.els[i]; hid.add(i)
            if el.kind == "region":
                for o in self.order:
                    if o.kind in ("node", "note", "mark", "key", "region") and o is not el:
                        ox, oy = o.x, o.y
                        ow, oh = getattr(o, "w", 0), getattr(o, "h", 0)
                        if el.x <= ox and ox + ow <= el.x + el.w and el.y <= oy and oy + oh <= el.y + el.h: hid.add(o.id)
            if el.kind == "node": hid |= {p.id for p in el.parts}
        for o in self.order:                          # parts of hidden nodes, edges of hidden ends, pills of hidden edges
            if o.kind in ("row", "cell") and o.parent.id in hid: hid.add(o.id)
        for o in self.order:
            if o.kind == "edge" and any(end.split(":")[0].split(".")[0] in hid or end.split(":")[0] in hid for end in (o.a, o.b)): hid.add(o.id)
        for o in self.order:
            if o.kind == "pill" and o.on_edge in hid: hid.add(o.id)
        return hid

    def visible(self, el, k, hid):
        if el.id in hid or not el.on(k): return False
        if el.kind in ("row", "cell") and not self.visible(el.parent, k, hid): return False
        return True

    def first_seen(self, el):
        return min((s for s in self.steps if el.on(s)), default=None)

    def classes(self, el, k):
        c = [f"ax-{cls}" for a, b, cls in el.cls if a <= k and (b is None or k <= b)]
        return c + [f"ax-{cls}" for cls, ids in self.rules.get(k, []) if el.id in ids]

    def state(self, el, k):
        f = self.first_seen(el)
        summary = self.steps[k].get("summary")
        c = ["ax-cast" if k == self.first else "ax-new" if f == k and not summary else "ax-old"]
        role = self.roles.get(k, {}).get(el.id)
        if role: c.append(f"ax-swap-{role}")                # a swap's part: diagram.js drives it
        if k != self.first and f != k and not summary:
            # changed = its words or its role differ from the last state it was on screen
            prev = max((s for s in self.steps if s < k and self.visible(el, s, self.hidden(s))), default=None)
            # only ADDITIONS count: new words, or a role it did not have. A temporary highlight
            # that ends is not news — marking it would spend the one "look here" signal on noise.
            if prev is not None and (any(a == k for a, _, _ in el.labels)
                                     or set(self.classes(el, k)) - set(self.classes(el, prev))):
                c.append("ax-changed")
        return " ".join(dict.fromkeys(c + self.classes(el, k)))

    # -------------------------------------------------------------- flows ---
    def _obstacles(self, k, vis):
        """What a moving pill or a hop number must not cover at state k → (node boxes,
        [(word box, element id)]): edge labels, pills, marks, notes, keys and region
        captions."""
        nodes, words = [], []
        for el in self.order:
            if el.kind in ("row", "cell", "flow") or not vis(el): continue
            if el.kind == "node": nodes.append((el.x, el.y, el.w, el.h))
            elif el.kind == "edge":
                lab = self._elabel(el, k)
                if lab:
                    _, tx, ty, anc, fs, mono, tw, bx = lab
                    words.append(((bx - 6, ty - fs * .82, tw + 12, fs * 1.14), el.id))
            elif el.kind == "pill": words.append((self._pill_box(el, k), el.id))
            elif el.kind == "mark":
                words.append(((el.x - MARK_R - 1, el.y - MARK_R - 2, 2 * MARK_R + 2, 2 * MARK_R + 4), el.id))
                ml = self._mark_label(el, k)
                if ml: words.append((ml[4], el.id))
            elif el.kind == "note":
                fs = int(el.opts.get("size", FS["note"])); tw = text_w(el.text(k), fs, el.mono)
                anc = el.opts.get("anchor", "start")
                words.append(((el.x - (tw / 2 if anc == "middle" else tw if anc == "end" else 0), el.y - fs * .8, tw, fs), el.id))
            elif el.kind == "key": words.append(((el.x, el.y - FS["key"] * .6, 48 + text_w(el.text(k), FS["key"]), FS["key"] * 1.2), el.id))
            elif el.kind == "region": words.append((self._cap_box(el, k), el.id))
        return nodes, words

    @staticmethod
    def _normal(pts, s):
        """The unit normal of the polyline at arc length s (left of travel in screen coordinates)."""
        for a, b in zip(pts, pts[1:]):
            l = math.dist(a, b)
            if s <= l or b == pts[-1]: return ((a[1] - b[1]) / (l or 1), (b[0] - a[0]) / (l or 1))
            s -= l

    def _track(self, e, k, pts, pw, nodes, words):
        """Where a hop's message pill rides → (smin, smax, dx, dy), or None. It rides beside
        the wire (never on it: the wire may carry static pills), offset (dx, dy), on one
        segment, and only over the stretch [smin, smax] of the hop (arc length) where it
        covers no box and no word. It keeps pace with the token there, waits at smin before
        and stays at smax after. Longest clear stretch wins; the side away from the edge's
        own label and the offset closest to the wire break ties."""
        lab = self._elabel(e, k)
        lab_box = None
        if lab:
            _, tx, ty, anc, fs, mono, tw, bx = lab
            lab_box = (bx - 6, ty - fs * .82, tw + 12, fs * 1.14)
        best, s0 = None, 0.0
        for a, b in zip(pts, pts[1:]):
            Ls = math.dist(a, b)
            horiz = abs(a[1] - b[1]) < .5
            near = MPILL_H / 2 + 8 if horiz else pw / 2 + 12
            far = MPILL_H / 2 + PILL_H / 2 + 6 if horiz else pw / 2 + 12 + 60   # clears a static pill on the wire
            for side in (-1, 1):
                for d in (near, far):
                    dx, dy = (0.0, side * d) if horiz else (side * d, 0.0)
                    run, top = None, None
                    n = max(1, int(Ls // 2))
                    for j in range(n + 1):
                        s = s0 + Ls * j / n
                        c = at_len(pts, s)
                        r = (c[0] + dx - pw / 2, c[1] + dy - MPILL_H / 2, pw, MPILL_H)
                        ok = (0 <= r[1] and r[1] + r[3] <= self.H and 0 <= r[0] and r[0] + r[2] <= self.W
                              and not any(boxes_hit(grow(r, 6), o) for o in nodes)
                              and not any(boxes_hit(grow(r, 4), o) for o in words))
                        if ok: run = (run[0], s) if run else (s, s)
                        if (not ok or j == n) and run:
                            if not top or run[1] - run[0] > top[1] - top[0]: top = run
                            run = None
                    if not top: continue
                    score = top[1] - top[0] - (d - near) * .6
                    if lab_box:                          # the label's side of this segment loses a tie
                        lc = (lab_box[0] + lab_box[2] / 2, lab_box[1] + lab_box[3] / 2)
                        along = (min(a[0], b[0]) - 40 <= lc[0] <= max(a[0], b[0]) + 40) if horiz else (min(a[1], b[1]) - 40 <= lc[1] <= max(a[1], b[1]) + 40)
                        if along and (lc[1] - a[1] if horiz else lc[0] - a[0]) * side > 0: score -= 40
                    if not best or score > best[0]: best = (score, top[0], top[1], dx, dy)
            s0 += Ls
        return best[1:] if best else None

    def _place_num(self, pts, w, nodes, words, taken, foreign=(), focus=None):
        """Where a hop's number badge (w × 2R) sits → ((x, y), tier): the free spot closest
        to its own line (on it is best), towards `focus` (an arc length: the hop's own
        message pill when it has one, else the middle of the hop). Tier 1 is clear of
        boxes and words; tier 2 clear of words but over a box's border band (never a box's
        middle); tier 3 the middle of the hop, whatever it covers (the build warns). In
        tiers 1 and 2 it also keeps NUM_MSG_GAP from `foreign`, the pills of OTHER messages:
        on a wire that carries several, a number beside the wrong one pairs with it."""
        L, R = polylen(pts), HOPNUM_R
        focus = L / 2 if focus is None else focus
        cores = [grow(n, -14) for n in nodes]
        def gap(p, o):
            return math.hypot(max(o[0] - p[0], 0, p[0] - o[0] - o[2]), max(o[1] - p[1], 0, p[1] - o[1] - o[3]))
        def free(p, boxes):
            b = grow((p[0] - w / 2, p[1] - R, w, 2 * R), 4)
            return (0 <= b[0] and b[0] + b[2] <= self.W and 0 <= b[1] and b[1] + b[3] <= self.H
                    and not any(boxes_hit(b, o) for o in boxes) and not any(boxes_hit(b, t) for t in taken)
                    and all(gap(p, o) >= NUM_MSG_GAP for o in foreign))
        cands = []
        n = max(1, int(L // 6))
        for s in [focus] + [L * i / n for i in range(n + 1)]:
            (x, y), (nx, ny) = at_len(pts, s), self._normal(pts, s)
            for off in range(-126, 127, 6):
                cands.append((abs(off) + .08 * abs(s - focus) - s * 1e-4, x + nx * off, y + ny * off))   # a tie goes towards the arrival
        cands.sort()
        best = None                                          # (cost, point, tier): a border band costs 45 px of distance
        for cost, x, y in cands:
            if best and cost >= best[0]: break
            if free((x, y), nodes + words): best = min(best or (1e9,), (cost, (x, y), 1)); break
            if (not best or cost + 45 < best[0]) and free((x, y), cores + words): best = (cost + 45, (x, y), 2)
        return (best[1], best[2]) if best else (at_len(pts, L / 2), 3)

    def _flows(self, k, hid):
        """→ (glow layer, moving layer, print layer) for the animations of state k: its flows,
        and its swaps as markers in the same order (diagram.js drives the swapped parts).
        Everything here is hidden until diagram.js runs a flow; the print layer (numbered
        hops, and the messages that have no static pill) shows in print and reduced motion.
        Each flow is placed against what is on screen when it plays (a swap before it has
        played, one after it has not)."""
        seq = self.anims(k)
        if not seq: return [], [], []
        plan, parked = [], []                  # parked: boxes of messages without a twin (they stay, and print)
        for f in (a for a in seq if a.kind == "flow"):
            pos = seq.index(f)
            vis = lambda el, pos=pos: self.on_at(el, k, pos, hid)
            nodes, words = self._obstacles(k, vis)
            words += [(b, a.id) for a in seq[:pos] if a.kind == "swap" for b in self._cue_boxes(a, k)]
            pills = [p for p in self.order if p.kind == "pill" and vis(p)]
            hops = []
            for n, it in enumerate(f.hops):
                eid, rev, msg = it.eid, it.rev, it.msg
                e = self.els[eid]
                leg = n > 0 and it.leg != f.hops[n - 1].leg      # the first item of a new leg
                if e.kind in ("row", "cell"):          # a station: no route, a beat inside the box
                    hops.append(dict(eid=eid, station=True, ms=STATION_MS, msg=None, plus=it.plus, leg=leg)); continue
                pts = self.route(e)[::-1] if rev else self.route(e)
                L = polylen(pts)
                hop = dict(eid=eid, pts=pts, L=L, msg=msg, ms=hop_ms(L, bool(msg)), twin=None, track=None, leg=leg,
                           at=(self.waypoint(it, k)[1], it.at) if it.at else None)
                if msg:
                    twin = next((p for p in pills if p.on_edge == eid and p.text(k) == msg and p.dir == (-1 if rev else 1)), None)
                    pw = text_w(msg, FS["mpill"], True, bold=True) + 34
                    tr = self._track(e, k, pts, pw, nodes, [b for b, i in words if not twin or i != twin.id] + parked)
                    if not tr:
                        print(f"  warning: diagram {self.name}: flow {f.id}: no clear spot for {msg!r} beside {eid} at state {k}; it rides on the wire")
                        tr = (L / 2, L / 2, 0.0, 0.0)
                    hop.update(twin=twin, pw=pw, track=tr)
                    if not twin:
                        c = at_len(pts, tr[1])
                        hop["park"] = (c[0] + tr[2], c[1] + tr[3])
                        parked.append((hop["park"][0] - pw / 2, hop["park"][1] - MPILL_H / 2, pw, MPILL_H))
                hops.append(hop)
            halos = [grow(self._glyph_box(m, pad=GLYPH_INK[m.mkind]), NUM_MARK_GAP) for m in self.order if m.kind == "mark" and vis(m)]
            plan.append((f, hops, nodes, words, pills, halos))
        glows, movers, nums = [], [], []
        taken = list(parked)
        parked_msgs = [(b, h["msg"]) for h, b in zip((h for p in plan for h in p[1] if "park" in h), parked)]
        for a in seq:
            if a.kind == "swap": movers.append(self._swap_marker(a))
        for fi, (f, hops, nodes, words, pills, halos) in enumerate(plan):
            # every message on screen when it plays, by its words: the static pills, and the parked ones
            msgs = [(self._pill_box(p, k), p.text(k)) for p in pills] + parked_msgs
            g, mv, nm, n = [], [], [], 0
            for hop in hops:
                leg = ' data-leg="1"' if hop["leg"] else ""
                if hop.get("station"):
                    w = f' data-with="{" ".join(hop["plus"])}"' if hop["plus"] else ""
                    mv.append(f'<g class="ax-hop ax-station" data-part="{hop["eid"]}"{w}{leg} data-ms="{hop["ms"]}"/>'); continue
                pts, msg = hop["pts"], hop["msg"]
                d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
                g.append(f'<path class="ax-hglow" d="{d}"/>')
                attrs = f'data-edge="{hop["eid"]}" data-pts="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" data-ms="{hop["ms"]}"' + leg
                if hop["at"]:                          # a waypoint: the token stops at arc length data-at while the ids light
                    attrs += f' data-at="{hop["at"][0]:.1f}" data-with="{" ".join(hop["at"][1])}" data-wms="{WAYPOINT_MS}"'
                body = ""
                if msg:
                    s1, s2, dx, dy = hop["track"]; w = hop["pw"]
                    attrs += f' data-smin="{s1:.1f}" data-smax="{s2:.1f}" data-off="{dx:.1f},{dy:.1f}"'
                    if hop["twin"]: attrs += f' data-pill="{hop["twin"].id}"'
                    body = self._msg_pill("ax-mpill", msg, w)
                    if "park" in hop:                   # print: the message where the animation leaves it
                        px, py = hop["park"]
                        nm.append(self._msg_pill("ax-hopnum ax-hopmsg", msg, w, f' transform="translate({px:.1f} {py:.1f})"'))
                mv.append(f'<g class="ax-hop" {attrs}>{body}</g>')
                if hop["L"] < 3 * HOPNUM_R: continue              # too short to hold its number beside it (a door-to-door hop)
                n += 1
                lbl = (chr(65 + fi) if len(plan) > 1 else "") + str(n)
                w = max(2 * HOPNUM_R, text_w(lbl, FS["hopnum"], bold=True) + 16)
                foreign = [b for b, t in msgs if t != msg]
                focus = None                                # a hop with a static twin is numbered beside that pill
                if hop["twin"]:
                    tb = self._pill_box(hop["twin"], k); tc = (tb[0] + tb[2] / 2, tb[1] + tb[3] / 2)
                    focus = min((hop["L"] * i / 200 for i in range(201)), key=lambda s: math.dist(at_len(pts, s), tc))
                (x, y), tier = self._place_num(pts, w, nodes, [b for b, _ in words] + halos, taken, foreign, focus)
                b = (x - w / 2, y - HOPNUM_R, w, 2 * HOPNUM_R)
                taken.append(b)
                hit = [i for o, i in words if boxes_hit(b, o)] + [f"box {j}" for j, o in enumerate(nodes) if boxes_hit(b, o)]
                if (tier > 1 and hit) or tier == 3:
                    print(f"  warning: diagram {self.name}: state {k}, flow {f.id}: number {lbl} ({hop['eid']}) found no clear spot"
                          + (f", it covers {', '.join(hit)}" if hit else ", it sits mid-hop"))
                nm.append(f'<g class="ax-hopnum" transform="translate({x:.1f} {y:.1f})"><rect x="{-w / 2:.1f}" y="{-HOPNUM_R}" width="{w:.1f}" height="{2 * HOPNUM_R}" rx="{HOPNUM_R}"/>'
                          f'<text y="{FS["hopnum"] * .36:.1f}" text-anchor="middle" font-size="{FS["hopnum"]}">{lbl}</text></g>')
            head = f'class="{{}} ax-f-{f.fkind}" data-flow="{f.id}"'
            glows.append(f'<g {head.format("ax-flow-under")}>' + "".join(g) + "</g>")
            # the token first, the pills after: a message's words ride above its own token
            movers.append(f'<g {head.format("ax-flow")}' + (f' data-lands="{" ".join(f.lands)}"' if f.lands else "") + '>'
                          '<g class="ax-token"><circle class="ax-tglow" r="26"/><circle class="ax-tglow2" r="15"/><circle class="ax-tdot" r="8"/></g>'
                          + "".join(mv) + "</g>")
            nums.append(f'<g {head.format("ax-flow-nums")}>' + "".join(nm) + "</g>")
        # the moving layer in the order written: diagram.js reads the sequence from it
        order = {a.id: j for j, a in enumerate(seq)}
        movers.sort(key=lambda m: order[re.search(r'data-(?:flow|swap)="([^"]+)"', m)[1]])
        return glows, movers, nums

    def _swap_marker(self, sw):
        """A swap for diagram.js: its time, its parts (an out edge with the end its line retracts
        into: a, b, or - when both ends go and it fades)."""
        out = " ".join(f"{i}:{sw.keep[i]}" if i in sw.keep else i for i in sw.out_all)
        return (f'<g class="ax-swap" data-swap="{sw.id}" data-ms="{SWAP_MS}" data-out="{out}" '
                f'data-in="{" ".join(sw.in_all)}"/>')

    def _label_at(self, el, k):
        """A node's label → (text, x, baseline y, anchor, font size, mono), or None: where _node draws it."""
        lbl = el.text(k)
        if not lbl: return None
        x, y, w, h = el.x, el.y, el.w, el.h
        fs = FS["mono" if el.mono else "node"]
        if el.parts:
            if el.parts[0].kind == "cell" or el.list: return lbl, x + PAD + 4, y + TITLE_H / 2 + fs * .36, "start", fs, el.mono
            return lbl, x + w / 2, y + TITLE_H / 2 + fs * .36, "middle", fs, el.mono
        if el.opts.get("sub"): return lbl, x + w / 2, y + h / 2 - 2, "middle", fs, el.mono
        ty = y + TITLE_H / 2 + fs * .36 if el.opts.get("valign") == "top" else y + h / 2 + fs * .36
        return lbl, x + w / 2, ty, "middle", fs, el.mono

    def _strike(self, el, k):
        """A line through a node's label → (path d, the words' box), or None."""
        la = self._label_at(el, k)
        if not la: return None
        lbl, tx, ty, anc, fs, mono = la
        tw = text_w(lbl, fs, mono)
        x0 = tx - tw / 2 if anc == "middle" else tx - tw if anc == "end" else tx
        sy = ty - fs * .3
        return f"M{x0 - 8:.1f},{sy:.1f} L{x0 + tw + 8:.1f},{sy:.1f}", (x0 - 10, ty - fs * .82, tw + 20, fs * 1.14)

    def _cue_boxes(self, sw, k):
        return [st[1] for i in sw.out if self.els[i].kind == "node" and (st := self._strike(self.els[i], k))]

    def _cues(self, sw, k):
        """The static cue of a swap (print, the deck: its end state): an out node's label, struck
        through, where the node was. Hidden on the projector (diagram.css)."""
        out = []
        for i in sw.out:
            el = self.els[i]
            st = self._strike(el, k) if el.kind == "node" else None
            if not st: continue
            lbl, tx, ty, anc, fs, mono = self._label_at(el, k)
            out.append(f'<g class="ax-swap-cue" data-swap="{sw.id}"><text class="ax-swap-cue-t{" ax-mono" if mono else ""}" x="{tx:.1f}" y="{ty:.1f}" '
                       f'text-anchor="{anc}" font-size="{fs}">{esc(lbl)}</text><path class="ax-swap-strike" d="{st[0]}"/></g>')
        return out

    @staticmethod
    def _msg_pill(cls, msg, w, extra=""):
        return (f'<g class="{cls}"{extra}><rect x="{-w / 2:.1f}" y="{-MPILL_H / 2:.1f}" width="{w:.1f}" height="{MPILL_H}" rx="{MPILL_H / 2:.1f}"/>'
                f'<text y="{FS["mpill"] * .36:.1f}" text-anchor="middle" font-size="{FS["mpill"]}">{esc(msg)}</text></g>')

    # ---------------------------------------------------------- rendering ---
    def svg(self, k):
        if k not in self.steps: raise SystemExit(f"diagram {self.name}: no state {k} (states: {sorted(self.steps)})")
        hid, out = self.hidden(k), []
        swaps = [a for a in self.anims(k) if a.kind == "swap"]
        outs = {i for a in swaps for i in a.out_all}
        # on screen in state k: its own parts, and what its swaps retire (there until they play)
        vis = lambda el: self.visible(el, k, hid) or el.id in outs
        # z-order: regions, flow glows, edge lines, travelling tokens and message pills,
        # static pills, edge labels, nodes (+parts), notes, marks, keys, print-only swap
        # cues and hop numbers. A token passes UNDER the boxes (a message goes in) and under
        # every word (a label or a pill it crosses stays readable).
        glows, movers, nums = self._flows(k, hid)
        for el in self.order:
            if el.kind == "region" and vis(el): out.append(self._region(el, k))
        out += glows
        edges = [el for el in self.order if el.kind == "edge" and vis(el)]
        edges.sort(key=lambda e: "over" in e.flags)
        for el in edges: out.append(self._edge(el, k))
        out += movers
        for el in self.order:
            if el.kind == "pill" and vis(el): out.append(self._pill(el, k))
        out += [lab for lab in (self._edge_label(el, k) for el in edges) if lab]
        for el in self.order:
            if el.kind == "node" and vis(el): out.append(self._node(el, k, vis))
        for el in self.order:
            if el.kind == "note" and vis(el): out.append(self._note(el, k))
            if el.kind == "mark" and vis(el): out.append(self._mark(el, k))
            if el.kind == "key" and vis(el): out.append(self._key(el, k))
        for a in swaps: out += self._cues(a, k)
        out += nums
        aria = esc(f"{self.name}, state {k}: {self.steps[k]['caption']}")
        return (f'<svg class="ax ax-{self.name}" data-step="{k}" viewBox="0 0 {self.W} {self.H}" '
                f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{aria}">\n  ' + "\n  ".join(out) + "\n</svg>")

    def mini(self, k, ids):
        """State k as a you-are-here inset → SVG: the regions, boxes and edges of the map from
        the same geometry (so it is aligned with the full map), no words, no marks, no flows;
        `ids` (regions, nodes, rows, cells or edges) are lit. The look is diagram.css's
        `svg.axm`; the slide template places and sizes it (strokes don't scale with it)."""
        if k not in self.steps: raise SystemExit(f"diagram {self.name}: minimap: no state {k} (states: {sorted(self.steps)})")
        if not ids: raise SystemExit(f"diagram {self.name}: minimap of state {k} lights nothing (```minimap {self.name} {k} ID,ID…```)")
        hid = self.hidden(k)
        vis = lambda el: self.visible(el, k, hid)
        for i in ids:
            el = self.els.get(i)
            if not el or el.kind not in ("region", "node", "row", "cell", "edge"):
                raise SystemExit(f"diagram {self.name}: minimap of state {k}: {i!r} is not a region, node, row, cell or edge")
            if not vis(el): raise SystemExit(f"diagram {self.name}: minimap of state {k}: {i!r} is not on screen in that state")
        lit = lambda el: " axm-lit" if el.id in ids else ""
        rect = lambda cls, el, rx: (f'<rect class="{cls}{lit(el)}" data-ax="{el.id}" x="{el.x:.1f}" y="{el.y:.1f}" '
                                    f'width="{el.w:.1f}" height="{el.h:.1f}" rx="{rx}"/>')
        out = [rect(f"axm-region axm-r-{el.rkind}", el, 22 if el.rkind != "band" else 16)
               for el in self.order if el.kind == "region" and vis(el)]
        edges = sorted((el for el in self.order if el.kind == "edge" and vis(el)), key=lambda e: e.id in ids)
        for el in edges:                                 # thin, no heads: which boxes talk, not how
            d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in self.route(el))
            out.append(f'<path class="axm-edge{lit(el)}" data-ax="{el.id}" d="{d}"/>')
        for el in self.order:
            if el.kind == "node" and vis(el):
                out.append(rect("axm-node", el, 12))
                out += [rect(f"axm-part axm-{p.kind}", p, 7) for p in el.parts if p.id in ids and vis(p)]
        aria = esc(f"{self.name}, state {k}: {self.steps[k]['caption']} (here: {', '.join(self._say(self.els[i], k) for i in ids)})")
        return (f'<svg class="axm axm-{self.name}" data-step="{k}" viewBox="0 0 {self.W} {self.H}" '
                f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{aria}">' + "".join(out) + "</svg>")

    def _say(self, el, k):
        """An element's name for a screen reader: its words, not its id."""
        if el.kind == "edge":
            return el.text(k) or " → ".join(self._say(self.els[s.split(":")[0]], k) for s in (el.a, el.b))
        if el.kind in ("row", "cell"):               # a box without words is named by its rows: the row alone
            return f"{self._say(el.parent, k)} {el.text(k)}" if el.parent.text(k) else el.text(k)
        if el.kind == "node" and not el.text(k) and el.parts: return el.parts[0].text(k)
        return el.text(k) or el.id

    def _cap(self, el, k):
        """A region caption → (text, tx, ty, anchor, width, plate x)."""
        x, y, w, h = el.x, el.y, el.w, el.h
        txt = el.text(k)
        if el.opts.get("cap", "tl") == "tl": tx, ty, anc = float(el.opts.get("capx", x + 26)), y + FS["cap"] * .36, "start"   # a legend on the top border
        else: tx, ty, anc = x + w - 22, y + h - 18, "end"
        tw = text_w(txt, FS["cap"], bold=True) + len(txt) * 3.5          # CSS letter-spacing: 3.5px
        return txt, tx, ty, anc, tw, (tx - 10 if anc == "start" else tx - tw - 10)

    def _cap_box(self, el, k):
        txt, tx, ty, anc, tw, bx = self._cap(el, k)
        return (bx, ty - FS["cap"] * .8, tw + 16, FS["cap"] * 1.05)

    def _region(self, el, k):
        x, y, w, h = el.x, el.y, el.w, el.h
        txt, tx, ty, anc, tw, bx = self._cap(el, k)
        return (f'<g class="ax-region ax-r-{el.rkind} {self.state(el, k)}" data-ax="{el.id}">'
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{22 if el.rkind != "band" else 16}"/>'
                f'<rect class="ax-capbg" x="{bx:.1f}" y="{ty - FS["cap"] * .8:.1f}" width="{tw + 16:.1f}" height="{FS["cap"] * 1.05:.1f}"/>'
                f'<text class="ax-cap" x="{tx:.1f}" y="{ty:.1f}" text-anchor="{anc}" font-size="{FS["cap"]}">{esc(txt)}</text></g>')

    def _node(self, el, k, vis):
        x, y, w, h = el.x, el.y, el.w, el.h
        cls = "ax-node" + (" ax-mono" if el.mono else "") + (" ax-list" if el.list else "")
        s = [f'<g class="{cls} {self.state(el, k)}" data-ax="{el.id}">',
             f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="12"/>']
        lbl = el.text(k)
        fs = FS["mono" if el.mono else "node"]
        if el.parts:
            if lbl:
                if el.parts[0].kind == "cell" or el.list:
                    s.append(f'<text class="ax-label" x="{x + PAD + 4:.1f}" y="{y + TITLE_H / 2 + fs * .36:.1f}" font-size="{fs}">{esc(lbl)}</text>')
                else:
                    s.append(f'<text class="ax-label" x="{x + w / 2:.1f}" y="{y + TITLE_H / 2 + fs * .36:.1f}" text-anchor="middle" font-size="{fs}">{esc(lbl)}</text>')
            shown = [p for p in el.parts if vis(p)]
            if el.parts[0].kind == "cell":
                for a, b in zip(shown, shown[1:]):          # the pipeline arrow spans any absent cell's slot
                    x1, x2, cy = a.x + a.w + 5, b.x - 5, a.y + a.h / 2
                    new = self.first_seen(b) == k or self.first_seen(a) == k
                    s.append(f'<g class="ax-pipe{" ax-new" if new and k != self.first else ""}"><path d="M{x1:.1f},{cy:.1f} L{x2 - 9:.1f},{cy:.1f}"/>'
                             f'<path class="ax-head" d="M{x2:.1f},{cy:.1f} L{x2 - 11:.1f},{cy - 6:.1f} L{x2 - 11:.1f},{cy + 6:.1f} Z"/></g>')
            for i, p in enumerate(el.parts):
                if not vis(p): continue
                pc = f"ax-part ax-{p.kind}" + (" ax-mono" if p.mono else "")
                t = p.text(k)
                if p.kind == "cell":
                    s.append(f'<g class="{pc} {self.state(p, k)}" data-ax="{p.id}"><rect x="{p.x:.1f}" y="{p.y:.1f}" width="{p.w:.1f}" height="{p.h:.1f}" rx="8"/>'
                             f'<text x="{p.x + p.w / 2:.1f}" y="{p.y + p.h / 2 + FS["cell"] * .36:.1f}" text-anchor="middle" font-size="{FS["cell"]}">{esc(t)}</text></g>')
                else:
                    sep = "" if el.list or i == 0 else f'<path class="ax-sep" d="M{p.x + 10:.1f},{p.y:.1f} H{p.x + p.w - 10:.1f}"/>'
                    tx, anc = (p.x + PAD + 6, "start") if el.list else (p.x + p.w / 2, "middle")
                    s.append(f'<g class="{pc} {self.state(p, k)}" data-ax="{p.id}">{sep}<rect class="ax-hit" x="{p.x + 3:.1f}" y="{p.y + 3:.1f}" width="{p.w - 6:.1f}" height="{p.h - 6:.1f}" rx="7"/>'
                             f'<text x="{tx:.1f}" y="{p.y + p.h / 2 + FS["row"] * .36:.1f}" text-anchor="{anc}" font-size="{FS["row"]}">{esc(t)}</text></g>')
        else:
            sub = el.opts.get("sub")
            if sub:
                s.append(f'<text class="ax-label" x="{x + w / 2:.1f}" y="{y + h / 2 - 2:.1f}" text-anchor="middle" font-size="{fs}">{esc(lbl)}</text>'
                         f'<text class="ax-sub" x="{x + w / 2:.1f}" y="{y + h / 2 + FS["sub"] + 2:.1f}" text-anchor="middle" font-size="{FS["sub"]}">{esc(sub)}</text>')
            elif lbl:
                ty = y + TITLE_H / 2 + fs * .36 if el.opts.get("valign") == "top" else y + h / 2 + fs * .36
                s.append(f'<text class="ax-label" x="{x + w / 2:.1f}" y="{ty:.1f}" text-anchor="middle" font-size="{fs}">{esc(lbl)}</text>')
        if self.roles.get(k, {}).get(el.id) == "out" and (st := self._strike(el, k)):
            s.append(f'<path class="ax-swap-strike" d="{st[0]}"/>')     # drawn while it retires (diagram.js)
        s.append("</g>")
        return "".join(s)

    def _edge(self, el, k):
        pts = self.route(el)
        line = list(pts)
        def pull(a, b, by):
            L = max(math.dist(a, b), 1e-6); return (b[0] - (b[0] - a[0]) / L * by, b[1] - (b[1] - a[1]) / L * by)
        heads = []
        if el.head: heads.append(self._head(pts[-2], pts[-1])); line[-1] = pull(pts[-2], pts[-1], HEAD_L - 3)
        if el.both: heads.append(self._head(pts[1], pts[0])); line[0] = pull(pts[1], pts[0], HEAD_L - 3)
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in line)
        kinds = " ".join(f"ax-k-{f}" for f in ("ws", "gap", "human") if f in el.flags)
        s = [f'<g class="ax-edge {kinds} {self.state(el, k)}" data-ax="{el.id}">']
        if "over" in el.flags: s.append(f'<path class="ax-halo" d="{d}"/>')
        # the wire's underlay (a highlighter band on a new edge); diagram.css decides when it shows
        s.append(f'<path class="ax-glow" d="{d}"/>')
        s.append(f'<path class="ax-line" d="{d}"/>' + "".join(f'<path class="ax-head" d="{h}"/>' for h in heads))
        s.append("</g>")
        return "".join(s)

    def _edge_label(self, el, k):
        """An edge's words, in a layer of their own above the travelling tokens: a message
        passes under a label, never over it. The group carries the edge's classes and
        data-ax, so every edge rule (new, warn, lit …) styles both halves alike."""
        lab = self._elabel(el, k)
        if not lab: return ""
        lbl, tx, ty, anc, fs, mono, tw, bx = lab
        on = next((r for r in self.order if r.kind == "region" and r.rkind == "band" and r.on(k)
                   and r.x <= bx and bx + tw <= r.x + r.w and r.y <= ty - fs and ty <= r.y + r.h), None)
        kinds = " ".join(f"ax-k-{f}" for f in ("ws", "gap", "human") if f in el.flags)
        return (f'<g class="ax-edge ax-elab {kinds} {self.state(el, k)}" data-ax="{el.id}">'
                f'<rect class="ax-lbg{" ax-on-band" if on else ""}" x="{bx - 6:.1f}" y="{ty - fs * .82:.1f}" width="{tw + 12:.1f}" height="{fs * 1.14:.1f}" rx="5"/>'
                f'<text class="ax-elabel{" ax-mono" if mono else ""}" x="{tx:.1f}" y="{ty:.1f}" text-anchor="{anc}" font-size="{fs}">{esc(lbl)}</text></g>')

    def _elabel(self, el, k, pts=None):
        """An edge label's geometry → (text, tx, ty, anchor, font size, mono, width, left x), or None."""
        lbl = el.text(k)
        if not lbl: return None
        pts = pts or self.route(el)
        segs = list(zip(pts, pts[1:]))
        i = int(el.opts["seg"]) if "seg" in el.opts else max(range(len(segs)), key=lambda j: math.dist(*segs[j]))
        (x1, y1), (x2, y2) = segs[i]
        t = float(el.opts.get("t", .5))
        px, py = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        mono = "mono" in el.flags or ("sans" not in el.flags and (lbl[:1] in "\"(`*<:" or " -g" in lbl or "!" in lbl or lbl.startswith(("/", "data-"))))
        fs = FS["emono" if mono else "edge"]
        if abs(y1 - y2) < .5:
            ty = py + (fs + 10 if "below" in el.flags else -12)
            tx, anc = px, "middle"
        else:
            tx, anc, ty = (px - 12, "end", py + 8) if "left" in el.flags else (px + 12, "start", py + 8)
        tw = text_w(lbl, fs, mono, bold=True)
        bx = tx - tw / 2 if anc == "middle" else tx - tw if anc == "end" else tx
        return lbl, tx, ty, anc, fs, mono, tw, bx

    @staticmethod
    def _head(a, b):
        L = max(math.dist(a, b), 1e-6); ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        bx, by = b[0] - ux * HEAD_L, b[1] - uy * HEAD_L
        return (f"M{b[0]:.1f},{b[1]:.1f} L{bx - uy * HEAD_W:.1f},{by + ux * HEAD_W:.1f} "
                f"L{bx + uy * HEAD_W:.1f},{by - ux * HEAD_W:.1f} Z")

    def _pill_box(self, el, k):
        """A static pill's bounding box (x, y, w, h): the same arithmetic as _pill."""
        s = self._pill(el, k)
        m = re.search(r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="([\d.]+)"', s)
        return tuple(float(v) for v in m.groups())

    def _pill(self, el, k):
        pts = self.route(self.els[el.on_edge])
        segs = list(zip(pts, pts[1:]))
        if "seg" in el.opts:
            (x1, y1), (x2, y2) = segs[int(el.opts["seg"])]
            t = float(el.opts.get("t", .5)); px, py = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
            ux, uy = (x2 - x1), (y2 - y1)
        else:
            total = sum(math.dist(*s) for s in segs); want = total * float(el.opts.get("t", .5))
            for (x1, y1), (x2, y2) in segs:
                L = math.dist((x1, y1), (x2, y2))
                if want <= L or (x2, y2) == pts[-1]:
                    f = want / L if L else 0; px, py = x1 + (x2 - x1) * f, y1 + (y2 - y1) * f; ux, uy = x2 - x1, y2 - y1; break
                want -= L
        L = max(math.hypot(ux, uy), 1e-6); ux, uy = ux / L * el.dir, uy / L * el.dir
        dy = float(el.opts.get("dy", 0))
        if abs(uy) < .5: py += dy
        else: px += dy
        t = el.text(k)
        tw = text_w(t, FS["pill"], True)
        w, h = tw + 40, PILL_H
        x0, y0 = px - w / 2, py - h / 2
        # the triangle sits on the leading side and points along the flow
        if abs(uy) < .5:
            lead = x0 + w - 16 if ux > 0 else x0 + 16
            tx = x0 + 11 + tw / 2 if ux > 0 else x0 + w - 11 - tw / 2
            tri = f"M{lead + 6 * ux:.1f},{py:.1f} L{lead - 6 * ux:.1f},{py - 7:.1f} L{lead - 6 * ux:.1f},{py + 7:.1f} Z"
        else:
            lead, tx = x0 + w - 16, x0 + 11 + tw / 2
            tri = f"M{lead:.1f},{py + 7 * uy:.1f} L{lead - 7:.1f},{py - 6 * uy:.1f} L{lead + 7:.1f},{py - 6 * uy:.1f} Z"
        return (f'<g class="ax-pill {self.state(el, k)}" data-ax="{el.id}"><rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{h / 2:.1f}"/>'
                f'<path class="ax-tri" d="{tri}"/><text x="{tx:.1f}" y="{py + FS["pill"] * .35:.1f}" text-anchor="middle" font-size="{FS["pill"]}">{esc(t)}</text></g>')

    def _note(self, el, k):
        fs = int(el.opts.get("size", FS["note"]))
        t, anc, st = el.text(k), el.opts.get("anchor", "start"), self.state(el, k)
        plate = ""
        if t:                                   # a plate for the words, as edge labels have; diagram.css decides when it shows
            tw = text_w(t, fs, el.mono, bold=True)
            x0 = el.x - tw / 2 if anc == "middle" else el.x - tw if anc == "end" else el.x
            plate = (f'<rect class="ax-tbg ax-note-bg {st}" data-ax="{el.id}" x="{x0 - 6:.1f}" y="{el.y - fs * .82:.1f}" '
                     f'width="{tw + 12:.1f}" height="{fs * 1.14:.1f}" rx="5"/>')
        return (plate + f'<text class="ax-note{" ax-mono" if el.mono else ""} {st}" data-ax="{el.id}" x="{el.x:.1f}" y="{el.y:.1f}" '
                f'text-anchor="{anc}" font-size="{fs}">{esc(t)}</text>')

    @staticmethod
    def _shield(x, y, r):
        """A shield's outline of radius r (the glyph: MARK_R) → path d."""
        q = r / 15
        return (f"M{x:.1f},{y - 15 * q:.1f} L{x + 12 * q:.1f},{y - 10 * q:.1f} L{x + 12 * q:.1f},{y + q:.1f} "
                f"Q{x + 12 * q:.1f},{y + 11 * q:.1f} {x:.1f},{y + 16 * q:.1f} Q{x - 12 * q:.1f},{y + 11 * q:.1f} {x - 12 * q:.1f},{y + q:.1f} L{x - 12 * q:.1f},{y - 10 * q:.1f} Z")

    @staticmethod
    def _glyph_box(el, r=MARK_R, pad=0.0):
        """A mark's glyph of radius r → its box (x, y, w, h), grown by pad."""
        if el.mkind == "shield":
            q = r / 15; b = (el.x - 12 * q, el.y - 15 * q, 24 * q, 31 * q)
        else: b = (el.x - r, el.y - r, 2 * r, 2 * r)
        return grow(b, pad)

    def beat_marks(self, k):
        """The marks a flow of state k lights in a beat (they pulse where they have room, then keep a ring, or their words lit)."""
        return {i for f in self.anims(k) if f.kind == "flow" for it in f.hops for i in it.plus + it.at if self.els[i].kind == "mark"}

    def _ink(self, k, skip):
        """Everything drawn at state k but the mark `skip` and the wires it sits on → [(box, id)], each box
        with its stroke (the widest it takes: a landed box's rim, a lit plate's): what that mark's pulse and
        ring keep clear of. A wire is a box per segment, as wide as its line (a new one: its highlighter band)."""
        hid, out = self.hidden(k), []
        me = self.els[skip]
        for el in self.order:
            if el.kind in ("row", "cell", "flow", "swap") or el is me or not self.visible(el, k, hid): continue
            if el.kind == "node": out.append((grow((el.x, el.y, el.w, el.h), 2.5), el.id))
            elif el.kind == "edge":
                lab = self._elabel(el, k)
                if lab:
                    _, tx, ty, anc, fs, mono, tw, bx = lab
                    out.append(((bx - 6, ty - fs * .82, tw + 12, fs * 1.14), el.id))
                pts = self.route(el)
                if any(_seg_dist((me.x, me.y), a, b) < MARK_R for a, b in zip(pts, pts[1:])): continue   # the wire it sits on
                hw = 9 if "ax-new" in self.state(el, k).split() else 3
                out += [((min(a[0], b[0]) - hw, min(a[1], b[1]) - hw, abs(a[0] - b[0]) + 2 * hw, abs(a[1] - b[1]) + 2 * hw), el.id)
                        for a, b in zip(pts, pts[1:])]
            elif el.kind == "pill": out.append((grow(self._pill_box(el, k), 1.5), el.id))
            elif el.kind == "mark":
                out.append((self._glyph_box(el, pad=GLYPH_INK[el.mkind]), el.id))
                ml = self._mark_label(el, k)
                if ml: out.append((grow(self._mark_plate(ml), 1.5), el.id))
            elif el.kind == "note" and el.text(k):
                fs = int(el.opts.get("size", FS["note"])); tw = text_w(el.text(k), fs, el.mono, bold=True)
                anc = el.opts.get("anchor", "start")
                x0 = el.x - tw / 2 if anc == "middle" else el.x - tw if anc == "end" else el.x
                out.append((grow((x0 - 6, el.y - fs * .82, tw + 12, fs * 1.14), 1.5), el.id))
            elif el.kind == "key": out.append(((el.x, el.y - FS["key"] * .6, 48 + text_w(el.text(k), FS["key"]), FS["key"] * 1.2), el.id))
            elif el.kind == "region":
                out.append((self._cap_box(el, k), el.id))
                x, y, w, h, hw = el.x, el.y, el.w, el.h, 2
                out += [((x - hw, y - hw, w + 2 * hw, 2 * hw), el.id), ((x - hw, y + h - hw, w + 2 * hw, 2 * hw), el.id),
                        ((x - hw, y - hw, 2 * hw, h + 2 * hw), el.id), ((x + w - hw, y - hw, 2 * hw, h + 2 * hw), el.id)]
        return out

    @staticmethod
    def _mark_plate(ml):
        """A mark's words (_mark_label) → the plate under them (x, y, w, h), as _mark draws it."""
        return (ml[4][0] - 6, ml[2] - FS["mark"] * .82, ml[4][2] + 12, FS["mark"] * 1.14)

    def _pulse(self, el, k):
        """A mark that lights in a beat of state k → ((origin x, y), scale, ring radius or None).
        The pulse scales the glyph about a point of its own — its centre, the middle of an edge, a corner — up
        to PULSE×, as far as keeps PULSE_CLEAR from everything else drawn, strokes included (_ink), or, from
        what is closer than that already at rest, no closer than it is. The point that allows the largest
        pulse wins (the centre on a tie); below PULSE_MIN the mark keeps still. A mark without words keeps a
        ring after its beat, in the glyph's shape: RING_GAP units out, or as far as keeps PULSE_CLEAR, down to
        RING_MIN (closer, it would merge with the glyph: no ring). A mark with words lights them instead
        (diagram.css), and a mark with neither room nor words is a warning: nothing would show it fire."""
        ink = [b for b, _ in self._ink(k, el.id)]
        ml = self._mark_label(el, k)
        if ml: ink.append(grow(self._mark_plate(ml), 1.5))       # its own words: their plate, lit in the beat
        round_ = el.mkind != "shield"
        g = self._glyph_box(el, pad=GLYPH_INK[el.mkind])        # the glyph with its stroke
        R0 = MARK_R + GLYPH_INK[el.mkind]
        def gap(o, k_, org):                                     # how far the glyph scaled k_ about org is from box o
            if round_:
                cx, cy = org[0] + (el.x - org[0]) * k_, org[1] + (el.y - org[1]) * k_
                return _box_dist_pt(o, (cx, cy)) - R0 * k_
            return _box_gap(o, (org[0] + (g[0] - org[0]) * k_, org[1] + (g[1] - org[1]) * k_, g[2] * k_, g[3] * k_))
        rest = [gap(o, 1, (el.x, el.y)) for o in ink]
        need = [min(PULSE_CLEAR, d) - 1e-6 for d in rest]
        cx, cy = (el.x, el.y) if round_ else (g[0] + g[2] / 2, g[1] + g[3] / 2)
        xs, ys = (g[0], cx, g[0] + g[2]), (g[1], cy, g[1] + g[3])
        origins = [(cx, cy)] + [(x, y) for y in ys for x in xs if (x, y) != (cx, cy)]
        best = ((cx, cy), 1.0)
        for org in origins:
            for step in range(int(round((PULSE - 1) * 100)), 0, -1):
                k_ = 1 + step / 100
                if k_ <= best[1]: break
                if all(gap(o, k_, org) >= n for o, n in zip(ink, need)): best = (org, k_); break
        org, sc = best if best[1] >= PULSE_MIN else ((cx, cy), 1.0)
        ring = None
        if not ml:
            for r in range(MARK_R + RING_GAP, MARK_R + RING_MIN - 1, -1):
                if round_: ok = all(_box_dist_pt(o, (el.x, el.y)) - (r + RING_W / 2) >= PULSE_CLEAR - 1e-6 for o in ink)
                else: ok = all(_box_gap(o, self._glyph_box(el, r, RING_W / 2 + .3)) >= PULSE_CLEAR - 1e-6 for o in ink)   # +.3: its mitres
                if ok: ring = r; break
        if sc == 1 and ring is None and not ml:
            print(f"  warning: diagram {self.name}: state {k}: {el.id} lights in a beat, but has no room to pulse or to keep a ring, "
                  f"and no words to light: nothing shows it fire")
        return org, sc, ring

    def _mark(self, el, k):
        x, y = el.x, el.y
        if el.mkind == "shield":
            q = MARK_R / 15
            g = (f'<path class="ax-glyph" d="{self._shield(x, y, MARK_R)}"/>'
                 f'<path class="ax-tick" d="M{x - 5 * q:.1f},{y + q:.1f} L{x - q:.1f},{y + 5 * q:.1f} L{x + 6 * q:.1f},{y - 4 * q:.1f}"/>')
        elif el.mkind == "cross":
            g = (f'<circle class="ax-glyph" cx="{x:.1f}" cy="{y:.1f}" r="{MARK_R}"/>'
                 f'<path class="ax-tick" d="M{x - 7:.1f},{y - 7:.1f} L{x + 7:.1f},{y + 7:.1f} M{x + 7:.1f},{y - 7:.1f} L{x - 7:.1f},{y + 7:.1f}"/>')
        else:
            g = (f'<circle class="ax-glyph" cx="{x:.1f}" cy="{y:.1f}" r="{MARK_R}"/>'
                 f'<text class="ax-q" x="{x:.1f}" y="{y + FS["mark"] * .36:.1f}" text-anchor="middle" font-size="{FS["mark"]}">?</text>')
        ml, lbl = self._mark_label(el, k), ""
        if ml:
            px, py, pw, ph = self._mark_plate(ml)
            lbl = (f'<rect class="ax-tbg" x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" height="{ph:.1f}" rx="5"/>'
                   f'<text x="{ml[1]:.1f}" y="{ml[2]:.1f}" text-anchor="{ml[3]}" font-size="{FS["mark"]}">{esc(ml[0])}</text>')
        pulse = ""
        if el.id in self.beat_marks(k):                    # a flow lights it: its pulse (origin, scale) and the ring it keeps (diagram.js)
            (ox, oy), sc, r = self._pulse(el, k)
            if sc > 1: pulse = f' data-o="{ox:.1f},{oy:.1f}" data-k="{sc:.2f}"'
            if r: g += (f'<path class="ax-mring" d="{self._shield(x, y, r)}"/>' if el.mkind == "shield"
                        else f'<circle class="ax-mring" cx="{x:.1f}" cy="{y:.1f}" r="{r}"/>')
        return f'<g class="ax-mark ax-m-{el.mkind} {self.state(el, k)}" data-ax="{el.id}"{pulse}>{g}{lbl}</g>'

    def _mark_label(self, el, k):
        """A mark's words → (text, x, y, anchor, box), or None."""
        t = el.text(k)
        if not t: return None
        x, y, pos = el.x, el.y, el.opts.get("lbl")
        if "lxy" in el.opts:
            (lx, ly), anc = self._xy(el.opts["lxy"]), el.opts.get("anchor", "start")
        elif pos in ("below", "above"):
            ly = y + MARK_R + 8 + FS["mark"] if pos == "below" else y - MARK_R - 10
            anc = el.opts.get("anchor", "middle")
            lx = x - 12 if anc == "start" else x + 12 if anc == "end" else x
        else:
            end = el.opts.get("anchor") == "end"
            lx, ly, anc = (x - MARK_R - 8 if end else x + MARK_R + 8), y + FS["mark"] * .36, ("end" if end else "start")
        tw = text_w(t, FS["mark"], True)
        x0 = lx - tw / 2 if anc == "middle" else lx - tw if anc == "end" else lx
        return t, lx, ly, anc, (x0, ly - FS["mark"] * .8, tw, FS["mark"] * 1.05)

    def _key(self, el, k):
        x, y = el.x, el.y
        sw = (f'<rect class="ax-sw" x="{x:.1f}" y="{y - 13:.1f}" width="36" height="26" rx="7"/>' if el.kkind == "new"
              else f'<path class="ax-sw" d="M{x:.1f},{y:.1f} H{x + 36:.1f}"/>')
        return (f'<g class="ax-key ax-key-{el.kkind} {self.state(el, k)}" data-ax="{el.id}">{sw}'
                f'<text x="{x + 48:.1f}" y="{y + FS["key"] * .36:.1f}" font-size="{FS["key"]}">{esc(el.text(k))}</text></g>')

# ------------------------------------------------------------ run-sheet ---
BLOCK = re.compile(r"^<!-- diagram ([\w-]+)(?: · (.*?))? -->[ \t]*\n(.*?)^<!-- /diagram -->[ \t]*$\n?", re.M | re.S)

def strip(text):
    """The run-sheet without its diagram blocks (the deck's speaker column never sees the DSL)."""
    return BLOCK.sub("", text)

def diagrams(src):
    out = {}
    for m in BLOCK.finditer(src):
        body = m.group(3)
        fence = re.search(r"^```\w*\n(.*?)^```", body, re.M | re.S)
        out[m.group(1)] = Diagram(m.group(1), fence.group(1) if fence else body)
    return out

if __name__ == "__main__":
    import sys
    src = Path(sys.argv[1]).read_text(encoding="utf-8")
    outdir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
    css = (Path(__file__).resolve().parent / "diagram.css").read_text(encoding="utf-8")
    for name, d in diagrams(src).items():
        for k in sorted(d.steps):
            svg = d.svg(k).replace("<svg ", "<svg ", 1)
            # standalone SVG: inline the look so the file renders on its own
            svg = svg.replace('role="img"', 'role="img" style="background:#16141f"', 1).replace(">\n", f"><style>{css}</style>\n", 1)
            (outdir / f"{name}-{k:02d}.svg").write_text(svg, encoding="utf-8")
        print(name, "states", sorted(d.steps), f"viewBox 0 0 {d.W} {d.H}")
