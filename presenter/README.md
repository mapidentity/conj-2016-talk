# presenter/ — how the flip-through talk deck is generated

Source for `../livecode-presenter.html` and `../livecode-presenter.pdf` — the
28/29-page landscape presenter script for *Where Did This `<div>` Come From?*
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
- **`highlight.py`** — the build-time syntax highlighter (Clojure, JS, bash, HTML
  snippets), shared by the deck's code and REPL cards and the slides' fenced blocks.
- **`topdf.cjs`** — renders the HTML to `../livecode-presenter.pdf` (A4 landscape).
- **`capture.cjs`** — captures the browser figures into `../figures/talk/`.
  Drives a swiftshader Chromium; reverse-direction highlights are produced by
  opening a second `/dev/ws` socket from the page and sending a `cursor` message,
  which the demo server broadcasts back as a `highlight`.
- **`refresh.sh [--deck-only]`** — the whole pipeline below as one command.
- **`run-tag.sh <step>`** — detach-checkouts `../../demo` at a step branch, boots it
  on `$CAPTURE_PORT` (8090; the app honours `PORT`), runs `capture.cjs` for that step, kills the server. Shots differ per step because
  the talk builds up (element breadcrumb at `step-4`, components at `step-5`,
  reverse + call-sites at `step-7`).
- **`preview.cjs [pageNums]`** / **`measure.cjs`** — dev helpers: screenshot pages
  for eyeballing / report per-page heights so nothing overflows one sheet.

## Regenerate

The one-liner (from anywhere): `bash talk/presenter/refresh.sh` — captures the
figures, puts the demo repo back on its branch, builds HTML + PDF, and checks
page heights; `--deck-only` skips the capture after text-only edits. It captures
on port 8090 (`CAPTURE_PORT` overrides), so a REPL on 8080 can keep running;
it refuses to run with a dirty demo tree or a busy capture port, and fails if any two figures
came out identical (a shot of the wrong server). Step by step, the same is:

Node's Playwright is global, so set `NODE_PATH` for the `.cjs` scripts
(`npm root -g` prints the right directory).

```bash
cd conj/talk/presenter
export NODE_PATH="$(npm root -g)"

# 1. (only if the demo app / a shot changed) re-capture the figures:
for t in step-0 step-4 step-5 step-7; do bash run-tag.sh "$t"; done
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
  (run-sheet: spoken lines and the 10 bookend slides), `../livecode-cheatsheet.md`
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
| `slide 5` | the run-sheet's slide 5 block, reproduced |
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

The ten bookend slides live in `livecode-talk.md`, each as a
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
| `{.big}` on a line of its own | classes for the block that follows; `{.steps}` renders a list as the two-column step grid |
| `… {.sub}` at the end of a paragraph, list item or table cell | classes for that paragraph / item / cell |
| `**bold**`, `` `code` `` | inline |
| `==text==`, `++text++`, `~~text~~` | accent (purple), green, strike spans |

The classes are the ones `slides-template.html` styles: `sub` (muted),
`big`, `rule` (left bar), `accent`, `green`, `strike`, `steps`. Add a class
there when a slide needs a new look; add markdown syntax here only when the
content cannot be said with the above. `slides.html` still opens standalone in
a browser tab (arrow keys / click to advance) for the projector. The current
slide is kept in the URL hash (`slides.html#3`), so a reload — e.g. after
`refresh.sh` rebuilt the file — stays on that slide, and `#N` jumps straight
to slide N.
