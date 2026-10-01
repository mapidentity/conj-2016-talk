# presenter/ — how the flip-through talk deck is generated

Source for `../livecode-presenter.html` and `../livecode-presenter.pdf` — the
55-page landscape presenter script for *Where Did This `<div>` Come From?*
(projector-left / speaker-notes-right, one talk beat per page).

Everything here is **generated**: the builder contains no talk text. The
run-sheet is the single source for what is said and done, the cheatsheet for
the code (the run-sheet also holds the slides), `../figures/talk/` for the screenshots.
Edit those; never the deck.

## Files

- **`build_presenter.py`** — the renderer. Parses `../livecode-talk.md` into
  pages (see "Page markers" below), pulls code blocks from
  `../livecode-cheatsheet.md`, slides from the run-sheet's slide blocks (via
  `build_slides`), embeds the
  screenshots from `../figures/talk/` as base64, and writes one self-contained
  HTML. The only things that live here are layout and CSS.
- **`build_slides.py`** — renders the run-sheet's `<!-- slide N · name -->` blocks
  into `../slides.html`, the standalone projector deck of bookend slides;
  `slides-template.html` is its shell (CSS + arrow-key navigation).
  `build_presenter.py` imports it, so the deck always reads the same blocks and
  keeps them out of the speaker column. See "Slides" below.
- **`diagram.py`** / **`diagram.css`** / **`diagram.js`** — "the map": the one
  architecture diagram, written once in the run-sheet as a `<!-- diagram NAME · note -->`
  block and shown state by state on slides. `diagram.py` parses the DSL and draws
  each state (and each minimap) as SVG, `diagram.css` is its look, and `diagram.js`
  plays its message flows and swaps in `slides.html` (on the `a` / `p` keys) and
  draws the speaker's progress line under them. Both builders inline the CSS, and
  `build_slides.py` also inlines the JS, even when the run-sheet has no diagram.
  See "Diagrams" below, and **`DIAGRAM.md`** for the DSL reference.
- **`highlight.py`** — the build-time syntax highlighter (Clojure, JS, bash, HTML
  snippets), shared by the deck's code and REPL cards and the slides' fenced blocks.
- **`topdf.cjs`** — renders the HTML to `../livecode-presenter.pdf` (A4 landscape).
- **`capture.cjs`** — captures the browser figures into `../figures/talk/`: the
  screenshots on the demo-moment slides, which show what the finished app on stage
  cannot (the intermediate states: no `data-*` yet, a breadcrumb without names or
  glyphs, the manual reload loop) and back up the live moments. Drives a swiftshader
  Chromium, per shot at its own viewport and DPR (zoom strips at DPR 3–6), with
  `FONTCONFIG_FILE=fonts.conf` so 🌶 comes from Noto Color Emoji as on the stage
  browser, not from the pixel font Unifont. Reverse-direction highlights are produced
  by opening a second `/dev/ws` socket from the page and sending a `cursor` message,
  which the demo server broadcasts back as a `highlight`. Shots that change the
  running server — a `load-file` sent over the socket REPL — run last in their step.
  The DevTools shots are the real Chrome DevTools: the Elements rows from the DevTools
  frontend served on `--remote-debugging-port` (`$CAPTURE_DEVTOOLS_PORT`, 9333), and
  Chrome's own inspect highlight from a headed Chromium under `xvfb-run` on a display
  of its own (never `:0`), each grab checked for the tooltip and the fill and retried
  when the overlay has not painted. From §7 on the talk's pill is straight (the live
  §6 fix is never reverted), so the later shots apply that fix to the page too.
- **`refresh.sh [--deck-only]`** — the whole pipeline below as one command.
- **`run-tag.sh <step>`** — detach-checkouts `../../demo` at a step branch, boots it
  on `$CAPTURE_PORT` (8090; the app honours `PORT`) with a socket REPL on
  `$CAPTURE_REPL_PORT` (5557), runs `capture.cjs` for that step (the DevTools shots
  also take `$CAPTURE_DEVTOOLS_PORT`, 9333), kills the server.
  Shots differ per step because the talk builds up (the bare app, DevTools and the
  manual loop at `step-0`, `data-src` in DevTools at `step-3`, the element breadcrumb
  at `step-4`, components at `step-5`, reverse, call sites, glyphs and the plain-load
  sharp edge at `step-7`).
- **`preview.cjs [pageNums]`** / **`measure.cjs`** — dev helpers: screenshot pages
  for eyeballing / report per-page heights so nothing overflows one sheet.

## Regenerate

The one-liner (from anywhere): `bash talk/presenter/refresh.sh` — captures the
figures, puts the demo repo back on its branch, builds HTML + PDF, and checks
page heights; `--deck-only` skips the capture after text-only edits. It captures
on port 8090 (`CAPTURE_PORT` overrides), so a REPL on 8080 can keep running;
it refuses to run with a dirty demo tree or a busy capture, socket-REPL or DevTools port (8090, 5557,
9333), and fails if any two figures
came out identical (a shot of the wrong server). Step by step, the same is:

Node's Playwright is global, so set `NODE_PATH` for the `.cjs` scripts
(`npm root -g` prints the right directory).

```bash
cd conj/talk/presenter
export NODE_PATH="$(npm root -g)"

# 1. (only if the demo app / a shot changed) re-capture the figures:
for t in step-0 step-3 step-4 step-5 step-7; do bash run-tag.sh "$t"; done
# leaves ../../demo on a detached HEAD — restore it afterwards:
git -C ../../demo switch -q -f main

# 2. build the HTML, then the PDF:
python3 build_presenter.py      # -> ../livecode-presenter.html
node topdf.cjs                  # -> ../livecode-presenter.pdf

# optional: sanity-check no page overflows a sheet
node measure.cjs
```

## Gotchas

- **Swiftshader is required** for rasterizing in this sandbox (`--use-angle=swiftshader`);
  the plain headless GPU path returns blank screenshots. Same lesson as the book's
  figure-capture procedure.
- Booting the demo backgrounds a JVM; `run-tag.sh` uses `setsid` to keep the JVM's
  `SIGURG` out of the shell (otherwise you get spurious non-zero exits) and guards
  `pkill` with `|| true`.
- `../../demo` is its own git repo with step branches `step-0`…`step-7`; `run-tag.sh`
  leaves it on a detached HEAD. **Put it back on `main` when done.**
- Authoritative content sources the builder transcribes: `../livecode-talk.md`
  (run-sheet: spoken lines and the bookend slides), `../livecode-cheatsheet.md`
  (per-section code).

## Page markers (how the run-sheet becomes pages)

Each `## §N · …` section of `livecode-talk.md` is cut into deck pages by HTML
comments, which rendered markdown never shows:

```
<!-- page "A WebSocket and a file watcher" @3:30 [step-1]
  code §2a "http-kit turns any request into a channel …"
-->
```

The first line: the page title, an optional `@time`, an optional `[marker]`
(the pill top-right; defaults to `slide N` when the page shows a slide, else the
section's step), and optionally `compact` (slightly smaller type for a page
that overflows by a few lines but must stay whole). Everything after the marker
up to the next one is the **speaker column**: paragraphs in quotes render as
spoken lines, `**[stage marker]**` and `**TYPE**`/`**PASTE**` lead-ins become
pills, `> quoted` blocks become beats. A section's preamble (before its first
marker) lands on its first page.

The lines inside the comment are the **projector column**, top to bottom:

| item | shows |
| --- | --- |
| `code §2a ["caption"]` | the cheatsheet block under label §2a (`§2d#2` = its second block); TYPE/PASTE/CHECKOUT pill and file name come from the label |
| `code ~"(defn tr-load!" ["caption"]` | the first cheatsheet block containing that text — for unlabeled blocks |
| `repl ~"(read-string" ~"(def render"` | one or more cheatsheet blocks as a REPL card; `;; =>` lines become results |
| `slide 5` | the run-sheet's slide 5 block, reproduced (its screenshots embedded) |
| `shot NAME ["caption"] [tall] [hero]` | `../figures/talk/NAME.png` |
| `shots NAME "cap" \| NAME "cap"` | two screenshots side by side |
| `dom '<span class="badge">' ["caption"]` | a DevTools-style element line |
| `bash "git switch -f step-7" ["caption"]` | a CHECKOUT command |
| `note "text"` | a small caption line |

Captions take inline markdown. Reference pages (cover, stage setup, backstage,
Q&A) come from the run-sheet's non-§ sections. After editing, `bash
refresh.sh --deck-only`; if `measure.cjs` reports an overflow, add a page
marker to split the page or mark it `compact`.

## Slides (how the run-sheet's slide blocks become `slides.html`)

The bookend slides live in `livecode-talk.md`, each as a
`<!-- slide N · name -->` … `<!-- /slide -->` block placed right after the page
marker that first shows it (a later page can show it again with the same
`slide N` item). `slides-template.html` holds their look; `build_slides.py`
(run by `refresh.sh`, either mode) joins them into `slides.html` — never edit
that file. The blocks are content for the projector, not speech: the deck
builder removes them before it parses the speaker column. Numbers run 1… in
order of definition; the name is only for humans:

```
<!-- page "The re-def that strips every tag" @34:00
  slide 6
-->

<!-- slide 6 · the sharp edge -->
## The re-def that strips every tag

The tags exist **only because the loader applied them**.\
A plain `load-file` — or your editor’s eval-on-save —\
re-defs the views untagged. Silently.

The loader is the ==single source of truth==\
for how views load. {.rule .big}
<!-- /slide -->

**[SLIDE 6: the sharp edge]** "What happens when …"
```

| markdown | renders as |
| --- | --- |
| `# Title` / `## Title` | the slide heading, `<h1>` / `<h2>` |
| a paragraph | `<p>` — lines up to a blank line; a line ending in `\` breaks (`<br>`), otherwise lines flow |
| `- item` (indented lines continue the item) | `<ul>` / `<li>` |
| `\| a \| b \|` rows, with a `\|---\|---\|` row after the first | a table; the first row becomes the header |
| ```` ```clojure ```` … ```` ``` ```` fenced block | `<pre><code>`, verbatim; syntax-highlighted when the fence names a language: `clojure`/`clj`, `html`/`dom`, `js`, `bash`/`sh` (no inline markup inside) |
| ```` ```svg ```` … ```` ``` ```` fenced block | an inline figure: the SVG is passed through **verbatim** (not escaped) inside `<div class="figure">`. Use the slide palette (`#ece9f1` text, `#8b7ff5` accent, `#9d94b8` muted, `#211d30` chips) and a `viewBox` with no fixed width, so it scales in both `slides.html` and the deck |
| ```` ```diagram NAME K ```` fence (empty body) | state K of the run-sheet's `diagram NAME` block, full size, filling the room below the heading. See "Diagrams" |
| ```` ```minimap NAME K ID,ID… ```` fence (empty body) | state K as a small you-are-here inset beside the heading, with those parts lit. One per slide; on a slide with no heading it takes its own row at the top. See "Diagrams" |
| ```` ```clojure from=17 cursor=21:8 ```` | options after the language: `from=N` numbers the lines from N in a gutter; `cursor=L:C` bands line L and puts a caret before column C (1-based, as the reader counts: keep the file's indentation). Not for `diff` |
| ```` ```diff inline ```` | a `-` line followed by a `+` line that only adds characters (or only removes them) becomes one row, the change marked in place: added green, removed struck through. Columns stay put. Any other pair keeps its two lines, and the build prints a note |
| `{.repl}` before a ```` ```clojure ```` fence | a REPL exchange: a line starting `user=> ` is input (prompt dim, form highlighted), every other line is output (muted) |
| `![alt](figures/talk/NAME.png "caption")` alone on a line | a screenshot, `<figure class="shot">`. The path is relative to `talk/` and must exist (the build fails otherwise); the caption is optional, inline markdown, one line (write `'…'` when it holds a `"`); no `]` in the alt. `{.guide}` at the end of the line: dashed hairlines at 25% and 75% of the image's height, from 45% of its width to the right edge (the capture cuts the strip so the measured element spans exactly that: `capture.cjs`, the title-row strip rule) |
| consecutive image lines | one group: side by side (`{.pair}`, the default) or one above the other (`{.stack}`) — the class on the line before. The group has **one scale** (from the PNGs' pixel sizes), so its images must share a capture DPR; it takes the room below the other blocks, and a blank line starts a new group |
| `{.big}` on a line of its own | classes for the block that follows; `{.steps}` renders a list as the two-column step grid |
| `… {.sub}` at the end of a paragraph, list item or table cell | classes for that paragraph / item / cell |
| `**bold**`, `` `code` `` | inline |
| `==text==`, `++text++`, `~~text~~` | accent (purple), green, strike spans |

The classes are the ones `slides-template.html` styles: `sub` (muted),
`big`, `hero` (on a `#` heading: the slide's one word, huge and centred on
the page, e.g. DEMO — no heading row), `rule` (left bar, for the talk's assertions), `note` (boxed aside —
a caption remarking on the block above it), `accent`, `green`, `strike`,
`steps`, `repl`; for images `pair`, `stack` and `guide`. For a ```` ```diagram ```` fence there are also the flow modes
`flow-keys` (alias `flow-step`), `flow-auto`, `flow-loop` and `flow-off`, plus `pop`. For a
```` ```minimap ```` fence there are `rev` and `warn`. Add a class
there when a slide needs a new look; add markdown syntax here only when the
content cannot be said with the above. `slides.html` still opens standalone in
a browser tab (arrow keys / click to advance; on a map with flows, `a` plays
the next flow and `p` steps back — see "Flow modes" below) for the projector.
It references its screenshots relatively (`figures/talk/NAME.png`), so the
`figures/talk/` folder travels with it; the deck embeds them instead. The current
slide is kept in the URL hash (`slides.html#3`), so a reload — e.g. after
`refresh.sh` rebuilt the file — stays on that slide, and `#N` jumps straight
to slide N.

### Screenshots on slides

The demo-moment slides show the app through real captures (`capture.cjs`), each
beside the narration that already describes it. How they are laid out:

- **Fill without shifting.** A group asks for the height it needs at the full slide
  width and gives height back when the slide has less room; every other block on an
  image slide keeps its size. Each image takes the smaller of the two widths that fit
  across and down, so it is never letterboxed or stretched, and the `<img>`'s
  `width`/`height` attributes give it its box before it loads. Checked at 1920×1080,
  1280×720 and 1024×768.
- **One scale per group.** A pair (before/after) or a stack (minute one/now) shows
  equal app pixels at equal size, which is what makes the comparison honest. That is
  why a group's shots share one capture DPR.
- **Legibility.** Text the audience must read inside a screenshot (DevTools rows, the
  breadcrumb) needs about 28 px on a 1080p slide: capture zooms at DPR 3 or more and
  crop tight (`capture.cjs` has the clip rules). Page-wide shots are backups for live
  moments and read as a pattern, not as detail.
- **The deck** shows the same groups on the slide card, scaled to the card's width and
  at most 112 mm tall per group, embedded as base64 like every other figure.

## Diagrams (the map)

The talk has one architecture diagram, "the map". It grows state by state: a full
MAP slide opens a section with its new parts lit, and a code slide can carry a
small minimap of the current state with the part under discussion lit. The whole
diagram is **content**, so it lives in the run-sheet, written once as a block in a
small DSL. The builders only draw it. The reference, with every statement and
option, is **`DIAGRAM.md`**. In short:

````text
<!-- diagram arch · what we build: one more piece per section -->
```text
canvas 1760x870
step 1 "a webserver, a REPL, an editor"   # a state; the caption is its heading and aria-label
step 3 "hot reload"
step 5 "tr-load! keeps the lines"
region jvm lane "JVM" 380,16 1020x846
…                                    # the other regions, nodes and edges
node watcher "watcher" 420,318 180x64 @3          # @3: on screen from state 3 on
edge e-poll src:r=350 -> watcher:l @3
flow save-load @3 : e-save, e-poll, e-dep, e-def
# state 5 arrives with load-file still wired; the first a retires it and draws tr-load!'s wires
# (loader, e-read, … are defined in the elided lines, with ranges that end at 4 or start at 5)
swap loader-swap @5 : out loader, e-read, e-dep, e-repl, e-def ; in e-views, e-deftr
```
<!-- /diagram -->
````

- **The block** goes in the run-sheet, outside every slide block (the talk keeps it
  in the appendix section "The map (diagram source)", at the end). It starts with
  `<!-- diagram NAME · note -->`, holds one ```` ```text ```` fence and ends with
  `<!-- /diagram -->`. The deck's speaker column never sees it. Every state is
  drawn from the same geometry, and an element is simply absent before its first
  state, so a cut between two map slides changes only what was added. States follow
  the talk's sections; there is no branch chip, and `chip` / `branch=` are build
  errors.
- **A full map on a slide:** an empty ```` ```diagram NAME K ```` fence inside a
  slide block, with a flow-mode class line before it. Give the slide a one-line
  `##` heading (`## 🗺 caption` on the talk's map slides), so the map sits at the
  same place and scale on every map slide:

  ````text
  <!-- slide 9 · the dev channel -->
  ## 🔥 hot reload

  {.flow-step}
  ```diagram arch 3
  ```
  <!-- /slide -->
  ````

- **A minimap:** an empty ```` ```minimap NAME K ID,ID… ```` fence anywhere in the
  slide block. It lights the listed regions, nodes, rows, cells or edges in the
  accent colour, or green with `{.rev}`, or amber with `{.warn}`. The build places
  it top right, beside the heading and out of the flow, so the body doesn't move.
  It sizes the inset to the heading row, about 327 px wide at 1080p beside an h1.
  Beside a long heading it narrows the inset (`note:`), and warns when even
  `--ax-mini-min` doesn't fit. On a slide with no heading (a full-bleed
  screenshot) the inset (`.ax-alone`, `note:`) takes its own row at the top, at the
  same top-right box and as wide as beside a one-line h2, and the body starts
  below it, centred in what is left as it would be below a heading.

  ````text
  ```minimap arch 3 watcher,e-poll
  ```
  ````

  Both fences also work on one line: ```` ```minimap arch 3 watcher``` ````.
- **Playing the flows.** Navigation never plays one: → / Space / PageDown / click
  always go to the next slide, ← / PageUp back, whatever is playing. On a map with
  flows, two keys do (either case; Ctrl/Cmd/Alt+`a` stay the browser's):
  - `a` plays the flow at the cursor, or restarts the one playing from its start.
    Once the token has gone in (the path still lit for 0.9 s), the flow counts as
    done: `a` then plays the next one. A second `a` within 250 ms is a bounce and is
    ignored.
  - `p` steps back one stop: a playing flow stops at its start (nothing lit); idle,
    the cursor goes back to the start of the flow before (after the last flow: to
    the start of the last one).

  Every arrival puts the cursor on flow 1 with nothing lit (arriving back on a slide
  with a swap from a later one: after the swap, see below). A finished flow moves it
  on; after the last one it stays there, so `a` replays it. To show a flow again:
  `p`, then `a`.

  A **swap** (state 5: tr-load! takes over from load-file) is played by the same keys,
  in its turn among the state's flows: the slide arrives with the old parts still
  there, `a` strikes and retires them while the new wires draw in (1.8 s), and `p`
  puts the old picture back. An `a` while it plays finishes it at once (a swap never
  rewinds). Arriving back from a later slide shows its end state. Print, the deck and
  minimaps show the end state too; print and the deck keep the retired box's label,
  struck through, where it was. A flow can also pass through a
  box's rows or cells (`trload.c-read`): each lights for a beat, and `+ID` lights more
  with it (`hub.h-disp+m-resolve`: resolve-src's words light; a mark pulses where it
  has room). `EDGE at ID` stops the token on a hop for a beat (`e-html at m-render`),
  `|` starts a new leg elsewhere (state 2's three hand starts), and `lands=` takes a
  list. Details: `DIAGRAM.md`, "Flows" and "Swaps".

  On stage: the keys reach the slides only while the page has focus — after the
  address bar, press F6 (a click would also advance). Reduced motion must be off
  on the presenting machine, or the flows only show as numbers. The line sits in
  the bottom ~12 px at 1080p: check that the projector does not overscan.
- **The progress line.** Under a map with flows, a hairline along the very bottom of
  the slide (below the `N / 49` counter) shows the speaker where the flows are: one
  segment per flow, as long as the flow; a small dot between two flows; a thicker
  fill that grows with the animation's own clock and rests at the cursor when idle.
  It is quiet on purpose (the audience should hardly notice it). Print, the deck and
  the PDF never show it. Details: `DIAGRAM.md`, "The progress line".
- **Flow modes** (the class line before a ```` ```diagram ```` fence):
  - `{.flow-keys}`, or `{.flow-step}` (the same; the talk uses it): only `a` / `p`
    play.
  - `{.flow-auto}` (the default): the first flow plays by itself, 2 s after the cut,
    as if `a` had been pressed; the rest is `flow-keys`. An `a` or `p` before or
    during it takes over.
  - `{.flow-loop}`: plays and repeats; the first `a` or `p` stops the loop. Not for
    the talk.
  - `{.flow-off}`: the static picture only; no line, and the keys do nothing.
  - `{.pop}` combines with any of them: the new parts pop on a forward arrival.

  The deck and the PDF show the static picture with numbered hops instead. Under
  reduced motion, `a` reveals one flow's numbered hops at a time (and moves the line
  one segment); `p` hides them again. There `{.flow-auto}` shows flow 1's numbers on
  arrival, and `{.flow-loop}` all of them.
- **Build checks.** Errors stop the build:
  - unknown ids;
  - a flow or `lands=` that is not on screen in its state (at its turn among the
    state's flows and swaps);
  - a swap whose parts break its rules (on screen before it, not after, or the other
    way round for the parts it brings in), or that would leave a wire hanging;
  - a fence naming a diagram or state that doesn't exist;
  - a non-empty fence body;
  - two minimaps on one slide;
  - a minimap id that is not on screen in that state;
  - `chip` or `branch=`.

  Warnings let the build go on: labels wider than their box, a flow whose token
  would jump, a message or hop number with no clear spot, a minimap with no room
  beside its heading. The full list is in `DIAGRAM.md`, "Build checks".
- **Where the look lives:**
  - `diagram.css` holds the colours of the map and the minimap;
  - `slides-template.html` places the map and minimap on the projector, and holds
    the minimap's width limits `--ax-mini-max` / `--ax-mini-min`, which
    `build_slides.py` reads;
  - `build_presenter.py` places them on the deck's slide cards.
