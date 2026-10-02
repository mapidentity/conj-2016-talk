# DIAGRAM.md: the map DSL

The talk has one architecture diagram, "the map". It is written once in the
run-sheet, and each slide shows one **state** of it. Every state is drawn from
the same geometry, which is the finished diagram. An element is absent until its
first state, so nothing ever moves: a hard cut between two map slides changes only
what was added. States follow the talk's **sections**, not git branches. There is
no branch chip.

The run-sheet holds a second diagram, `nav`, in the same appendix, after the map's
block. It is the reverse direction's wanted outcome, shown once, on §8's first slide
(```` ```diagram nav 1``` ````), before the map shows how it works: one state, the
lines of `recipe-card` in an EDITOR lane, a mock of the page in a BROWSER lane, and
one `cursor` wire between them. Its lanes share the map's outer edges, so the cut to
the next map slide keeps the frame. Each of its flows is one cursor position: the
code row lights (a station), the message crosses, and what the form under the cursor
renders on main lands (`lands=`); the slide is `flow-keep`, so each result stays lit
until the next key. It uses the same DSL, the same look and the same keys as the map;
everything below holds for both.

Who holds what:

| file | holds |
| --- | --- |
| `../livecode-talk.md` | the content: the `<!-- diagram … -->` block (geometry, labels, states, flows) and the slides that show it |
| `diagram.py` | structure and metrics: parsing, routing, font sizes, and the build checks |
| `diagram.css` | the look of `svg.ax` (the map) and `svg.axm` (the minimap): colours, weights and dashes |
| `diagram.js` | playing the flows and swaps in `slides.html` on the `a` / `p` keys, and the progress line under them (the deck never runs it) |
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
- **A state with a swap** is drawn as its end state (see "Swaps").
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
  body sit exactly where they would without it, and a minimap never shifts a slide,
  except on a slide with no heading (`.ax-alone`, see "Size").
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
  - on a slide that doesn't start with a heading (a full-bleed screenshot), the
    inset is `.ax-alone`: it takes its own row in the flow, at the same top-right
    box and as wide as beside a one-line h2 (7.65em), and the body starts below
    it, centred in what is left as below a heading. An image group gives up that
    height. The build prints a `note:`.
  - The two limits live in `slides-template.html`, and the build reads them from
    there.
  - The heading is measured in DejaVu Sans Bold, with emoji at 1.25em. That is the
    font Chromium uses for `system-ui` in this container, and it is wider than the
    stage laptop's `system-ui` is likely to be, so a heading that fits here fits on
    stage.
- **In the deck:** the slide card shows the inset top right, below the "slide N"
  label, at 2.1 mm per em of its projector width (about 19 mm), with thinner
  strokes. The deck's CSS in `build_presenter.py` sets this, and puts an
  `.ax-alone` inset in the card's flow at the same box, above the body.
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
flow ID [fwd|rev|warn] @S[-E] [lands=ID[,ID…]] : ITEM, ITEM, … [| ITEM, …]
  ITEM = EDGE[<] ["MSG"]  |  EDGE[<] at ID[+ID…]  |  NODE.PART[+ID…]
swap ID @K : out ID,ID… ; in ID,ID…
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
  - Rows stack. A row's words are drawn as written, spaces included, so a code row
    keeps its indentation (`nav`'s lines of `recipe-card`).
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
- **`swap`**: parts that replace others, on a key press. See "Swaps" below.

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

**Classes the look defines:** `warn` (amber, dashed: a bypass; on a box, an amber
dashed outline and amber words, like the second loader in state 11), `ghost` (an
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
- `ax-swap-out` / `ax-swap-in`: the parts a swap of this state retires or brings in.
  `diagram.js` drives them; without it they show the swap's end state (see "Swaps").
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
flow ID [fwd|rev|warn] @S[-E] [lands=ID[,ID…]] : ITEM, ITEM, … [| ITEM, …]
  ITEM = EDGE[<] ["MSG"]          # a hop
       | EDGE[<] at ID[+ID…]      # a hop with a waypoint beat on it (no message)
       | NODE.PART[+ID…]          # a beat inside the box: a station, plus what lights with it
```

- **Hops** are existing edge ids, taken in order. Each hop follows the edge's
  routed path.
- **`EDGE<`** runs a hop against the edge's drawn direction, B → A. Use it for
  `--` socket wires, and for the way back from a lookup (`e-resolve, e-resolve<`).
- **`NODE.PART`**, a row or a cell in the list, is a **station**: the token is inside
  that box, and the part lights up for a beat (450 ms), in the flow's colours, with the
  near-white rim of a wire being travelled; after its beat it keeps the flow's hue,
  like a travelled wire, until the flow ends. Stations follow each other without a
  pause, and the hop after them waits at its door as usual. State 5 passes through
  tr-load!'s cells: `e-views, trload.c-read, trload.c-eval, e-deftr ":line"`. A station
  takes no `<`, no message and no `at`, and print does not number it. A station can
  also be the first item: state 7's click starts on the row it reads,
  `page.p-src, e-click, …`.
- **`+ID…` after a station** makes it a **beat**: the listed ids light for the same
  450 ms, wherever they are. They may be rows, cells, boxes, marks, notes or edges:
  - a row or a cell takes the station's look;
  - a box takes the `lands=` look (its rim near-white during the beat);
  - an edge takes the look of the wire being travelled;
  - a note's words get a plate in the flow's colours;
  - a **mark pulses** in its own hue: its glyph scales up to 1.25× and back over the
    beat, about its centre, an edge's middle or a corner, whichever lets it grow
    most. The generator sizes the pulse to the room around the mark: it keeps 4
    units, strokes included, from every other mark, word, box, lane border and wire
    (the wire the mark sits on aside), or, from what is closer than that already at
    rest, no closer than it is. Where that leaves less than 1.1×, the mark keeps still.
  - a mark **with words** lights them too, like a note's: their plate in the flow's
    colours, white words (state 7's resolve-src has no room to pulse, between the
    hub, origin-ok? and its own words: its words carry the beat). A mark **without
    words** keeps a **ring** after its beat until the flow ends, in the glyph's shape
    and its own hue: violet around a shield, amber around the ✕ and the ?. The ring
    sits 8 units out, or as far as keeps the same 4 units from everything else, down
    to 5 (closer, it would merge with the glyph: then there is no ring). State 4's ✕
    pulses about its centre and keeps its ring 5 units out, clear of *just a string*
    below.

  After the beat, what lit keeps the trail look, as a passed station does, until the
  flow ends. State 7's dispatch resolves the click: `hub.h-disp+m-resolve`; state 10's
  rewritten calls stamp their call site in the views: `views.v-main+views.v-ui`.
- **`EDGE at ID[+ID…]`** puts a **waypoint** on a hop: the token stops where the hop
  passes the first id (the route's nearest point to it), the ids light for a beat of
  600 ms (longer than a station's: the token stands still on the wire), and the token
  finishes the hop. The first id is a mark, a box, a row, a cell or a note, and lies
  within 24 units of the route; the others may be anything a beat lights. The hop
  keeps a plain hop's pace: its time is shared out by distance before and after the
  stop. One `at` per hop, and a hop with `at` takes no message. Print does not number
  a waypoint. State 4: `e-html at m-render` (the ✕ fires as the token passes);
  states 6 and 12 stop in the seam: `e-html at seam+e-binds+devbody.d-tag` (dev-body
  tags the tree) and `e-html at seam+seam-l` (the seam reads `identity`).
- **`|`** starts a new **leg**: a deliberate restart elsewhere, from somewhere the
  token has not been (state 2's three hand starts: the buffer, Calva, you). The
  token goes in at the end of a leg, comes out 0.6 s later at the next leg's first
  door, and waits there as at any door. Every leg's trail stays lit, print numbers
  keep counting (1, 2, 3 …), and the flow is one segment of the progress line. There
  is no jump warning across `|`.
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
- **`lands=ID[,ID…]`** names the boxes or rows where the flow's effect shows: the
  highlighted span, the opened buffer, the reloaded page, state 6's two new
  attributes (`lands=page.p-src,page.p-name`). They light up in the flow's colour
  when the token arrives.
- **Several flows in one state** play in the order they are written, one per press
  of `a`. Split a story where the speaker wants to pause. A state's swaps take their
  turn among its flows, in the same order (see "Swaps"): together they are the
  state's **animations**, and "flow" in the key and line rules below means either.

### How a slide plays them

Navigation never plays a flow: → / Space / PageDown / a click always go to the next
slide, and ← / PageUp to the previous one, whatever is playing. The flows have their
own two keys, on any slide with flows (either case; Ctrl/Cmd/Alt+`a` stay the
browser's, and a held key does not repeat):

| key | behaviour |
| --- | --- |
| `a` | Nothing playing: plays the flow at the cursor.<br>Playing: restarts that flow from its start, while its token travels. In the 0.9 s hold after the token has gone in, the flow looks done and counts as done: `a` plays the next flow (after the last one: replays it).<br>A swap never rewinds: `a` while it plays finishes it at once (see "Swaps").<br>A second `a` within 250 ms of the last one is a key bounce or double tap and is ignored. |
| `p` | One stop back.<br>Playing: stops, back to the start of that flow (nothing lit).<br>Idle at the start of flow k > 1: to the start of flow k−1.<br>Idle after the last flow: to the start of the last one.<br>At the start of flow 1: nothing.<br>It also clears the bounce guard, so the `a` right after it always counts.<br>On a `flow-keep` slide it also clears the result that rests (nothing lit). |

The stops are the start of each flow, plus "after the last". Arriving on a slide
(by →, ←, `#N` or a reload) puts the cursor on flow 1 with nothing playing and
nothing lit — except arriving back on a slide with a swap from a later one (see
"Swaps"); leaving stops everything. When a flow finishes, the cursor moves on to
the next flow; after the last one it stays on the last, so `a` replays it. To show a
flow again: `p`, then `a`.

The class line before the ` ```diagram ``` ` fence decides what happens without keys:

| class | behaviour |
| --- | --- |
| `flow-keys`, or `flow-step` (the same; the talk's) | Only `a` and `p` play. |
| `flow-auto` (default) | The first flow plays by itself, 2 s after the cut, as if `a` had been pressed; the cursor then moves on to flow 2, and the rest is `flow-keys`. An `a` or `p` before or during it takes over. |
| `flow-loop` | Plays every flow, 0.6 s apart, rests 2 s, and repeats while the slide is up. The first `a` or `p` stops the loop: from then on the slide is `flow-keys`. Not for the talk: it keeps moving while the speaker talks, and it is costly on a software-rendered browser. |
| `flow-off` | Only the static picture: no progress line, and the keys do nothing. |
| `flow-keep` (combines with `flow-keys` or `flow-auto`) | A finished flow does not clear after its 0.9 s hold: its end picture rests — its stations and `lands=` lit, its wires in the trail look, the token gone and a twin pill back in place — until the next `a` (the next flow starts from a clear picture), `p` (back to that flow's start, nothing lit) or leaving the slide. For a slide whose point is the result (`nav`: three small pills among nine cards need longer than 0.9 s). Under reduced motion `a` shows that end picture with the flow's numbered hops. No effect with `flow-loop`. |
| `pop` (combines with the others) | On a forward arrival, the state's new parts pop for 220 ms (scale 1.08 → 1 and a brightness flash; opacity never changes). |

### The progress line

Under a map with flows, a hairline runs along the very bottom of the projector
slide, as wide as the figure and below the `N / 48` counter. It is for the speaker,
not the audience:
- One segment per flow or swap, each as long as it takes (a flow's 0.9 s hold included).
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
- a station's beat lasts 450 ms, a waypoint's 600 ms (`STATION_MS`, `WAYPOINT_MS`); a
  station that is a flow's first item lights from the press, through the first door's
  wait: 710 ms (0.26 s + 450 ms), the token hidden meanwhile;
- between two legs the token is gone for 0.6 s (`LEG` in `diagram.js`);
- the path stays lit for 0.9 s after arrival (on a `flow-keep` slide the end picture
  then rests until the next key).

**Reduced motion, print, and the deck:** nothing moves.
- The picture is static, plus a print layer: each hop is numbered in its flow's
  colour (1 2 3 …, or A1 A2 … B1 … when a state has several flows), and messages
  without a twin show where the animation leaves them. A door-to-door hop too short
  to hold its number beside it (under 63 px, like src/ → watcher) is not numbered.
  A number keeps 56 units (centre to pill) from every pill of a different message,
  static or parked, so on a wire that carries several messages (`/dev/ws` →
  `inspector.js`: open and highlight) it never sits beside the wrong one. It also
  keeps 10 units more from a mark's glyph than from words (`NUM_MARK_GAP`), so state
  4's hop number 2 sits clear of the ✕ instead of reading as "2✕".
- Under reduced motion, `a` reveals the cursor flow's numbered hops instead (on a
  `flow-keep` slide together with its end picture), and moves the progress line one
  whole segment on; `p` hides them and steps back one
  stop. A swap is applied at once instead. `flow-auto` shows flow 1's numbers on
  arrival (its autoplay, the line one segment on). `flow-loop` shows every flow's
  numbers at once (the line full); its first `a` starts over at flow 1, its first `p`
  hides them and steps back one stop.

## Swaps

A swap replaces parts of the map in front of the audience: the old parts go, the new
ones come, on a key press. State 5 uses it for tr-load! taking over from load-file.

```text
swap ID @K : out ID,ID… ; in ID,ID…
```

- **`@K`**: the one state it plays in. A swap is a moment, like a flow, and it takes
  no range.
- **`out`**: the parts it retires. Each one is on screen in the state before K and not
  in K, by its own range: the range tells the truth about the map, and the swap only
  adds the moment in between. State 5 ends load-file at 4 (`@2-4,11,12`) and names it
  here.
- **`in`**: the parts it brings in. Each one is on screen in K and not in the state
  before it.
- Nodes, rows, edges, pills, notes and marks can be swapped, not cells or regions. A
  node goes with its rows, an edge with its pills. Either list may be left out: a
  swap with only `out` retires parts, one with only `in` draws new ones on a key press.

**On the projector:**
- **Arrival** (by →, `#N` or a reload) shows the picture *before* the swap: the out
  parts are still there, as built parts, the in parts are not yet. Everything else is
  state K, highlighter included. So the cut from state K−1 adds K's news, and the swap
  comes after it.
- **Arriving back** from a later slide (←, or a `#N` jump back) shows the end state
  instead: the talk has moved past the swap. The cursor is after the state's last
  swap, nothing plays by itself (not even under `flow-auto`), and `p` puts the before
  picture back for a replay. `flow-loop` ignores this: its rounds always start from
  the before picture.
- **Playing it** (`a`) takes 1.8 s, eased, and nothing moves:
  - an amber strike draws through an out box's label (0–0.32 s) and stands whole
    until the box starts to fade, so it reads from the back of the hall;
  - the out wires, if solid, retract into the end that stays, so the wire from the
    watcher to load-file shrinks back into the watcher (0.54–1.22 s); their
    arrowheads go first, all together, whichever end stays;
  - the out boxes fade (0.68–1.3 s);
  - the in wires draw from their source (0.9–1.67 s), their arrowheads and words
    last; in state 5 they are the state's news, so they draw in the highlighter's ink.

  A dashed wire, or one that loses both its ends, fades instead of retracting.
  Out and in overlap: it reads as one part replacing the other.
- **After it**, the resting picture is the end state: state K as its ranges say.
- **The keys and the line** treat it like a flow: it is one stop and one segment of
  the progress line, and `p` while it plays, or from the stop after it, puts the
  before picture back. But a swap never rewinds: `a` while it plays finishes it at
  once (the end state, the cursor after it), so an `a` pressed a little early for the
  next flow never shows the old parts snapping back; the next `a` plays on. It has no
  hold: the moment it ends, it is done. Leaving the slide mid-swap stops it; coming
  back by → or a reload starts from the before picture, by ← from the end state.
- **Under reduced motion**, `a` applies it at once (the end state, no frame in
  between) and `p` puts the before picture back.
- **`flow-auto`** plays it by itself if it comes first; **`flow-loop`** rests on the
  end state and starts each round from the before picture; **`flow-off`** shows the
  end state.

**Print, the deck and a minimap** show the end state, the state as its ranges say.
The deck and print add one quiet cue: an out box's label stays where the box was,
struck through in amber, with no box and no wires. On the projector the cue never
shows. A flow that plays after the swap is numbered on the end state; one that plays
before it and uses its out parts would be numbered beside wires print does not draw,
and the build warns.

**Build checks** (errors): an unknown id, or one that can't be swapped; an out part
that is not on screen in the state before K, or still is in K; an in part that is not
on screen in K, or already is in the state before; a part in two swaps of one state;
any wire that would hang from a box that is not there, before or after any of the
state's animations; and an out part whose words in state K differ from the state
before (the before picture draws it with K's words, so they would change on the cut
just before it retires: extend its label range to K). A flow must find its edges and
stations on screen where it plays in the order: before the swap, the out parts are
there and the in parts are not. A wire of a retired box that ends with the state
before, but is not in `out`, gets a warning: it would vanish on the cut instead of
retiring with the box. So does an out part whose classes differ between the two
states (its look changes on the cut; that may be on purpose).

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
- A flow hop that is not an edge, a row or a cell; a station with `<`, a message or
  `at`; a flow that plays in a state where one of its edges, stations, beat ids,
  waypoints or `lands=` boxes is not on screen at its place among the state's
  animations (a swap before it has played, one after it has not); a `lands=` id that
  is not a box or a row, or one named twice.
- A beat id that is not a row, cell, box, mark, note or edge; `+` on a hop (a hop
  takes `at`); a waypoint whose first id is not a mark or a box (row, cell, note), or
  lies more than 24 units from the hop's route in a state where the flow plays; a hop
  with both `at` and a message; an id named twice in one item
  (`hub.h-disp+hub.h-disp`); an empty leg (`| |`, a trailing `|` or `,`).
- A swap that breaks one of its rules (see "Swaps").
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
  the next hop leaves (the token would jump), within a leg (`|` is a restart on
  purpose).
- A mark that lights in a beat but has no room to pulse, no room for a ring and no
  words to light: nothing would show it fire.
- A flow that plays before a swap and uses what it retires (print numbers it on the
  end state).
- A wire of a box a swap retires that ends with the state before and is not in the
  swap's `out`: it would vanish on the cut instead of retiring with the box.
- An out part whose classes differ between the state before the swap and its state
  (its look changes on the cut).
- A message that finds no clear stretch (it then rides on the wire); a hop number
  that finds no clear spot.
- A minimap with no room beside its heading (see "Size" above). A narrowed
  minimap, and one on a slide with no heading (its own row), print a `note:`.

## Standalone SVGs

```bash
python3 presenter/diagram.py BLOCK.md OUTDIR   # one NAME-KK.svg per state, look inlined
```

`BLOCK.md` is any file that contains the `<!-- diagram … -->` block, the run-sheet
included.
