# DIAGRAM.md: the map DSL

The talk has one architecture diagram, "the map". It is written once in the
run-sheet, and each slide shows one **state** of it. Every state is drawn from
the same geometry, which is the finished diagram. An element is absent until its
first state, so nothing ever moves: a hard cut between two map slides changes only
what was added. States follow the talk's **sections**, not git branches. There is
no branch chip.

Who holds what:

| file | holds |
| --- | --- |
| `../livecode-talk.md` | the content: the `<!-- diagram … -->` block (geometry, labels, states, flows) and the slides that show it |
| `diagram.py` | structure and metrics: parsing, routing, font sizes, and the build checks |
| `diagram.css` | the look of `svg.ax` (the map) and `svg.axm` (the minimap): colours, weights and dashes |
| `diagram.js` | playing the flows in `slides.html` on the `a` / `p` keys, and the progress line under them (the deck never runs it) |
| `slides-template.html` | where a map or minimap sits on a projector slide, and how big it is |
| `build_presenter.py` | the same for the deck's slide cards |

## The block

The block goes in the run-sheet, outside every slide block; the talk keeps it in
the appendix section "The map (diagram source)", at the end. Its body is one
` ```text ` fence:

````text
<!-- diagram arch · what we build: one more piece per section -->
```text
canvas 1760x870
step 1 "the starting world"
…
```
<!-- /diagram -->
````

- The name (`arch`) is how slides refer to the diagram.
- The note after ` · ` is for humans.
- Rendered markdown shows the fence as a code block.
- The deck's speaker column never sees the block: `build_slides.strip_slides()`
  removes it, together with the slide blocks.

## Showing it on a slide

Put these fences inside a `<!-- slide N · name -->` block. Their bodies stay empty.
The one-line form, ` ```diagram arch 5``` `, works too.

````text
{.flow-step}
```diagram arch 5
```

```minimap arch 5 watcher,e-poll
```
````

### ` ```diagram NAME K``` `: the full map

This draws state K at full size. It fills all the room below the heading, so every
map slide lays out the same way: at 1080p that is 1766×879 px for a 1760×870
canvas, so one unit is one screen pixel. The class line before the fence sets how
the state's flows play (see "Flows" below). `{.pop}` can be added to that line.

Give every map slide a one-line `##` heading (the talk's is `## 🗺 caption`). The
map fills what the heading leaves, so only then is it drawn at the same place and
scale on every map slide, and a cut from one state to the next moves nothing. A
`#` heading, or one that wraps, makes the map smaller on that slide.

### ` ```minimap NAME K ID,ID…``` `: the you-are-here inset

This draws state K small, in the free space at the right of the heading row, with
the listed parts filled in the map's highlighter ink, so "here" on a code slide
looks like "new" on a map slide.

- **The IDs** name regions (zones), nodes, rows, cells (`node.part`) or edges, and
  each must be on screen in state K. They are separated by commas, and spaces
  after the commas are fine.
- **Colour:** `{.rev}` on the line before the fence lights the parts green (code →
  page, the overlay's emerald). `{.warn}` lights them amber (a bypass). Without
  either, they are violet.
- **What it draws:** the same geometry as the map, so it lines up with the full map:
  zones, boxes, and thin edges without arrowheads. It draws no words, marks, pills
  or flows. Its strokes are screen pixels, so they don't vanish at 1/5 scale. Its
  `aria-label` names the lit parts by their words (`tr-load! wrap`,
  `/dev/ws → inspector.js`), not by their ids.
- **Placement:** top right, starting 0.8em above the heading's top edge and
  ending at the slide's right padding. It is out of the flow, and the build puts
  it first in the section wherever the fence was written. So the heading and the
  body sit exactly where they would without it, and a minimap never shifts a slide.
- **Size:** `build_slides.py` works out the width and writes it on the inset
  (`--ax-mini-w`, in em):
  - it is as wide as the heading row allows without reaching the body: about
    9.1em (327 px at 1080p) beside a one-line h1, and about 7.6em (275 px) beside
    an h2;
  - it is never wider than `--ax-mini-max` (10em);
  - beside a long heading it narrows, keeping 0.8em from the heading's words, down
    to `--ax-mini-min` (6.5em). The build prints a `note:` when it narrows the
    inset. If even the minimum doesn't fit, it prints a `warning:` and draws the
    inset at the minimum width, overlapping the heading. The fix is to shorten
    the heading or drop the inset.
  - The two limits live in `slides-template.html`, and the build reads them from
    there.
  - The heading is measured in DejaVu Sans Bold, with emoji at 1.25em. That is the
    font Chromium uses for `system-ui` in this container, and it is wider than the
    stage laptop's `system-ui` is likely to be, so a heading that fits here fits on
    stage.
- **In the deck:** the slide card shows the inset top right, below the "slide N"
  label, at 2.1 mm per em of its projector width (about 19 mm), with thinner
  strokes. The deck's CSS in `build_presenter.py` sets this.
- **Limit:** one minimap per slide.

## The DSL

There is one statement per line, and `#` starts a comment. Coordinates are canvas
units: 1 unit is 1 px at 1080p. Quoted text uses `"…"` or `'…'`.

Type sizes are fixed in `diagram.py` for the projector, in those units: box labels
36 (monospace 34), rows 32, and 28 for everything else that carries words (cells,
edge labels, pills, captions, marks, keys). Only the print-only hop numbers are 26,
the floor. The layout is sized for these: cut words, never shrink them.

```text
canvas WxH
step K "caption" [hide:ID,ID…] [+CLS:ID,ID…] [summary]
region ID lane|store|band "CAPTION" X,Y WxH [cap=tl|br] [capx=X]
node ID "LABEL" X,Y WxH [mono] [list] [sub=TEXT] [valign=top]
  row  PART "TEXT" [mono]
  cell PART "TEXT"
note ID "TEXT" X,Y [mono] [anchor=start|middle|end] [size=N]
edge ID A -> B ["LABEL"] [via …] [ws|gap|human] [seg=N] [t=F] [below|left|over] [mono|sans]
pill ID on EDGE "TEXT" >|< [t=F] [seg=N] [dy=N]
mark ID shield|cross|q "TEXT" X,Y [anchor=…] [lbl=below|above] [lxy=X,Y]
key  ID new|fwd|rev|ws|warn "TEXT" X,Y
flow ID [fwd|rev|warn] @S[-E] [lands=ID] : EDGE[<] ["MSG"], EDGE[<] ["MSG"], …
```

### The statements

- **`canvas WxH`**: the viewBox. It is the same for every state. The default is
  1760×840.
- **`step K "caption"`**: a state. `state` is accepted as a synonym.
  - K is any integer. States are ordered by K, and the lowest K is the cast, where
    everything is drawn equal.
  - The caption becomes the SVG's `aria-label`; the talk also uses it as the map
    slide's heading.
  - `hide:ID,…` removes elements in this state only. A region id hides everything
    inside it, a node id hides its parts, and edges and pills of hidden ends go too.
  - `+CLS:ID,…` adds class `ax-CLS` to those ids in this state.
  - `summary` marks no deltas (the final view).
  - `branch=` and `chip` are gone. The build rejects them with a message saying so.
- **`region`**: a process or zone. There are three kinds:
  - `lane`: a process box;
  - `store`: dotted, for the files;
  - `band`: dashed and tinted, like DEV ONLY.

  The caption sits on the top border (`cap=tl`, with `capx=` for its x) or at
  the bottom right (`cap=br`).
- **`node`**: a box.
  - `mono` sets the label in monospace.
  - `list` makes the rows a left-aligned list under the label.
  - `sub=` adds a second, smaller line.
  - `valign=top` puts the label at the top of a tall box.
- **`row` / `cell`**: the parts of the node written just above. Their id is
  `node.PART`.
  - Rows stack.
  - Cells form a left-to-right pipeline under the title, with arrows between them.
    An absent cell keeps its slot, so a cell added later appears without anything
    moving.
  - A node has rows or cells, not both.
- **`note`**: free text.
- **`edge ID A -> B`**: a connection.
  - `->` draws one arrowhead, `<->` two, `--` none.
  - An end is `NODE[.PART][:SIDE[=COORD]]`. SIDE is `l`, `r`, `t` or `b`. COORD
    pins the point along that side: an absolute y for `l`/`r`, an absolute x for
    `t`/`b`. An unpinned end slides so that the edge runs straight when it can.
  - `via` adds turns: `x=N` turns at x=N, `y=N` turns at y=N, `X,Y` goes through a
    point. The route is orthogonal.
  - **Kinds:**
    - `ws`: a dashed socket wire;
    - `gap`: an amber dashed open question;
    - `human`: dotted footsteps, a manual step.
  - **The label:**
    - it sits on the longest segment, or on segment `seg=N`, at fraction `t=`;
    - `below` puts it under a horizontal segment, `left` to the left of a vertical
      one;
    - `over` draws the edge above the others, with a halo;
    - `mono` / `sans` force the label's font. A label that looks like code is
      monospace by default.
- **`pill`**: a message on an edge: `>` points along the edge, `<` against it.
  `t=` is the fraction of the whole route, `seg=` picks a segment, and `dy=` offsets
  it sideways.
- **`mark`**:
  - `shield`: a trust boundary, like `origin-ok?`;
  - `cross`: something lost, like "structure gone";
  - `q`: a question.

  `lbl=below|above` or `anchor=` place its words, and `lxy=X,Y` puts them at an
  exact baseline, for a shield in a tight doorway.
- **`key`**: a legend entry with a swatch: `new`, `fwd` (violet), `rev` (green),
  `ws` or `warn`.
- **`flow`**: a message that travels. See "Flows" below.

### What every element also takes

| suffix | meaning |
| --- | --- |
| `@S` | on screen from state S on |
| `@S-E` | on screen in states S through E |
| `@S-E,K,…` | several ranges; in a list, a bare K means K only |
| `+S:CLS` | class `ax-CLS` in state S only |
| `+S-:CLS` | class `ax-CLS` from S on |
| `+S-E:CLS` | class `ax-CLS` in S through E |
| `S:TEXT` | the label from S on |
| `S-E:TEXT` | the label in S through E, e.g. `11-11:'Load buffer'` |

**Classes the look defines:** `warn` (amber, dashed: a bypass), `ghost` (an
outline: not built yet), `fallback` (dashed and thinner), `human`, `new`, `fwd`
(violet) and `rev` (green). `fwd` and `rev` colour a loop's direction: in the final
view, and in any state whose new parts run code → page (state 9 gives its cursor
path `+rev:`). On a new part `rev` wins over the violet new tint, so the part is
highlighted in green ink: hue is the meaning, the highlighter is the newness.

**State classes the generator adds:**
- `ax-cast`: the first state; everything is drawn equal.
- `ax-new`: first on screen in this state, for exactly one state. It is drawn with
  the highlighter: boxes, rows, cells, pills, edge labels, a zone's caption and
  a note's or mark's words are filled with light ink and lettered dark and bold;
  a new wire is drawn in the ink over a translucent band (`.ax-glow`, the path
  `diagram.py` emits under every edge's line; hidden unless the look shows it).
  Words without a plate of their own (notes, mark labels) get one (`.ax-tbg`),
  also hidden unless the look shows it. A part that comes back after an absence, or an old part the
  state is about, is not new by itself: give it `+K-K:new` (the talk does this for
  you and F5 in state 11, the typed `(load-file …)` in state 2, and the
  tr-load! → views wire in state 8).
- `ax-old`: on screen in an earlier state.
- `ax-changed`: a label range or a class starts in this state. Only additions
  count. The new words are highlighted (the box, row or label plate takes the
  ink), the wire is not; a changed role with a look of its own (`warn`,
  `fallback`) keeps that look, with its words in bold.

**Colour meaning:**
- violet: page → code, and the dev machinery;
- green: code → page;
- amber: danger or a bypass.

A new gap stays amber: hue is the meaning, and the highlighter shows the
newness (amber ink under a new `cross`/`q` mark or gap). The loops are wires,
never filled, so a filled violet part always means "new here" and a violet wire
always means page → code.
Violet and green differ in hue only (the same weight and dash): they stay apart for
deuteranopia, protanopia and tritanopia, but not in greyscale, where the pills'
words and the arrowheads carry the direction. A dash means a socket, a bypass or a
fallback, never a direction.

## Flows

A flow is a message that travels the map hop by hop. What moves, and in which
state, is content, so it is written in the block:

```text
flow ID [fwd|rev|warn] @S[-E] [lands=ID] : EDGE[<] ["MSG"], EDGE[<] ["MSG"], …
```

- **Hops** are existing edge ids, taken in order. Each hop follows the edge's
  routed path.
- **`EDGE<`** runs a hop against the edge's drawn direction, B → A. Use it for
  `--` socket wires, and for the way back from a lookup (`e-resolve, e-resolve<`).
- **`"MSG"`** is a message that rides beside the wire as a pill, never on it.
  - The generator picks the side and the stretch where the pill covers no box and
    no word, and there the pill keeps pace with the token.
  - A static pill on the same edge with the same text and direction is the
    message's **twin**. The twin steps aside while its hop runs.
  - A message **without a twin** stays where it arrived until the flow ends, and
    print shows it there.
- **Kind** sets the colour: `fwd` is violet (the default), `rev` is green, `warn`
  is amber.
- **`@S`** means state S **only**: a flow is a moment, not a part. Use `@S-E` for
  a range and `@S-` for "from S on".
- **`lands=ID`** names the box or row where the flow's effect shows: the
  highlighted span, the opened buffer, the reloaded page. It lights up in the
  flow's colour when the token arrives.
- **Several flows in one state** play in the order they are written, one per press
  of `a`. Split a story where the speaker wants to pause.

### How a slide plays them

Navigation never plays a flow: → / Space / PageDown / a click always go to the next
slide, and ← / PageUp to the previous one, whatever is playing. The flows have their
own two keys, on any slide with flows (either case; Ctrl/Cmd/Alt+`a` stay the
browser's, and a held key does not repeat):

| key | behaviour |
| --- | --- |
| `a` | Nothing playing: plays the flow at the cursor.<br>Playing: restarts that flow from its start, while its token travels. In the 0.9 s hold after the token has gone in, the flow looks done and counts as done: `a` plays the next flow (after the last one: replays it).<br>A second `a` within 250 ms of the last one is a key bounce or double tap and is ignored. |
| `p` | One stop back.<br>Playing: stops, back to the start of that flow (nothing lit).<br>Idle at the start of flow k > 1: to the start of flow k−1.<br>Idle after the last flow: to the start of the last one.<br>At the start of flow 1: nothing.<br>It also clears the bounce guard, so the `a` right after it always counts. |

The stops are the start of each flow, plus "after the last". Arriving on a slide
(by →, ←, `#N` or a reload) puts the cursor on flow 1 with nothing playing and
nothing lit; leaving stops everything. When a flow finishes, the cursor moves on to
the next flow; after the last one it stays on the last, so `a` replays it. To show a
flow again: `p`, then `a`.

The class line before the ` ```diagram ``` ` fence decides what happens without keys:

| class | behaviour |
| --- | --- |
| `flow-keys`, or `flow-step` (the same; the talk's) | Only `a` and `p` play. |
| `flow-auto` (default) | The first flow plays by itself, 2 s after the cut, as if `a` had been pressed; the cursor then moves on to flow 2, and the rest is `flow-keys`. An `a` or `p` before or during it takes over. |
| `flow-loop` | Plays every flow, 0.6 s apart, rests 2 s, and repeats while the slide is up. The first `a` or `p` stops the loop: from then on the slide is `flow-keys`. Not for the talk: it keeps moving while the speaker talks, and it is costly on a software-rendered browser. |
| `flow-off` | Only the static picture: no progress line, and the keys do nothing. |
| `pop` (combines with the others) | On a forward arrival, the state's new parts pop for 220 ms (scale 1.08 → 1 and a brightness flash; opacity never changes). |

### The progress line

Under a map with flows, a hairline runs along the very bottom of the projector
slide, as wide as the figure and below the `N / 33` counter. It is for the speaker,
not the audience:
- One segment per flow, each as long as that flow takes (its 0.9 s hold included).
  When the state has two or more flows, a small dot marks each boundary; a dot is
  hollow until the line reaches it, then solid, with a thin ring of the background
  that keeps it apart from the fill.
- A thicker fill grows from the left while a flow plays. The same clock drives it
  and the token, so it shows exactly where the animation is. Idle, it rests at the
  cursor's stop: empty on arrival, at a dot between flows, full after the last one.
- It is quiet on purpose: a 1 px track at 1.3:1 on the background, a 3 px fill at
  2.4:1 (the counter's own colour). Whoever knows where to look can read it.
- `diagram.js` builds it as plain DOM in the figure (outside the SVG, no ids), and
  `diagram.css` holds its look. It is fixed-positioned, so it never moves the slide.
  Print hides it; the deck and the PDF never have it, since they run no script.

**Timing** is set in `diagram.py` (per hop) and `diagram.js` (the pauses):
- a hop shorter than 100 px takes 450 ms;
- a longer hop takes 400 + 0.8·L ms, kept between 600 and 1800 ms;
- a hop that carries a message takes at least 1200 ms;
- the token waits 0.26 s at the first door and 0.17 s at each box after that;
- the path stays lit for 0.9 s after arrival.

**Reduced motion, print, and the deck:** nothing moves.
- The picture is static, plus a print layer: each hop is numbered in its flow's
  colour (1 2 3 …, or A1 A2 … B1 … when a state has several flows), and messages
  without a twin show where the animation leaves them. A door-to-door hop too short
  to hold its number beside it (under 63 px, like src/ → watcher) is not numbered.
  A number keeps 56 units (centre to pill) from every pill of a different message,
  static or parked, so on a wire that carries several messages (`/dev/ws` →
  `inspector.js`: open and highlight) it never sits beside the wrong one.
- Under reduced motion, `a` reveals the cursor flow's numbered hops instead, and
  moves the progress line one whole segment on; `p` hides them and steps back one
  stop. `flow-auto` shows flow 1's numbers on arrival (its autoplay, the line one
  segment on). `flow-loop` shows every flow's numbers at once (the line full); its
  first `a` starts over at flow 1, its first `p` hides them and steps back one stop.

## Build checks

`build_slides.py` runs these checks, and so does `build_presenter.py`, which
imports it. So `refresh.sh` runs them in either mode.

**Errors (the build stops):**
- A DSL line it can't read: an unknown statement or option, a bad range, a `row`
  that doesn't follow a node, an id defined twice, a state defined twice. The
  message names the line.
- `chip` or `branch=`: the map is keyed to talk sections now.
- An edge end, pill edge, `hide:` or `+CLS:` id that doesn't exist. An edge `via`
  that turns the wrong way.
- A flow hop that is not an edge; a flow that plays in a state where one of its
  edges or its `lands=` box is not on screen; `lands=` that is not a box or a row.
- On a slide:
  - a ` ```diagram ``` ` or ` ```minimap ``` ` fence with a diagram name that has
    no block;
  - a state K that doesn't exist;
  - a malformed fence (` ```diagram NAME K``` `, ` ```minimap NAME K ID,…``` `);
  - a fence body that isn't empty;
  - a minimap that lights nothing, or an id that is not a region, node, row, cell
    or edge, or that is not on screen in that state;
  - more than one minimap on a slide.

  Errors on a slide name the slide.

**Warnings (the build goes on):**
- A node or row label wider than its box; cells overflowing their node.
- An edge that is on screen in a state where one of its ends is not.
- A flow that plays in no state; a hop that ends at a different box from the one
  the next hop leaves (the token would jump).
- A message that finds no clear stretch (it then rides on the wire); a hop number
  that finds no clear spot.
- A minimap on a slide that doesn't start with a heading; a minimap with no room
  beside its heading (see "Size" above). A narrowed minimap prints a `note:`.

## Standalone SVGs

```bash
python3 presenter/diagram.py BLOCK.md OUTDIR   # one NAME-KK.svg per state, look inlined
```

`BLOCK.md` is any file that contains the `<!-- diagram … -->` block, the run-sheet
included.
