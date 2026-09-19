# Which Clojure Made This? (presentation draft)

> **SUPERSEDED (2026-07-08)** by `livecode-talk.md` — the talk was restructured
> around a live build (demo repo: `conj/demo`, branches `step-0`…`step-7`, plus
> `livecode-cheatsheet.md` and `slides.html`). This draft's slides+demo format
> is kept for its narration ideas (the toys/magic-machine open, the history
> beats), which can still be swapped into the live-coding open if preferred.

> Local working draft for the Clojure/conj 2026 talk. Not committed; no reference stored in the repo.
> Format: 40 minutes (≈38 + 2 Q&A). Markers: **[SLIDE]** = slide cue, **[SAY]** = speaker line / notes,
> **[DEMO]** = live action, **[BEAT]** = pause / let it land.
> The script is written to be spoken from, not read verbatim; tighten to your own voice.

---

## 1. Opening: how things work (0:00–5:00): 5 min

**[SLIDE 1: title]** *Which Clojure Made This?* Your name / handle. The subtitle ("A Source Inspector for Server-Rendered Hiccup") can sit small under it; the story still does the work.

**[SAY: the toys]** "When I was a kid, I opened up my toys. Not to break them, but to see how they were made, how they worked. I had to know what was inside, and taking the back off and looking was a tangible, direct thing: you touch the mechanism, you watch it move, and you understand it."

**[BEAT]**

**[SAY: the magic machine]** "Then I met the computer, and the computer was the magic machine. It breathed life into ideas. You think of something, you type it, and it *runs*: the same direct, hands-on thrill as the toys, except now the thing inside was whatever I could imagine."

**[SLIDE 2: Clojure / the REPL]** the word, or a tiny REPL transcript.

**[SAY: cake, and eat it too]** "And then I found Clojure, and it felt like having my cake and eating it too. The REPL and dynamic loading made feedback so fast that I never had to leave the flow. Change a function, see it, keep going, stay in the iteration. And what I ended up with was software at least as solid as anything I'd have written in Java. I didn't have to trade the magic for the seriousness. I got both."

**[SLIDE 3: Figwheel / Flappy Bird]** a still, or the words "Figwheel · Flappy Bird → shadow-cljs".

**[SAY: Flappy Bird]** "Where it really clicked for the browser was Bruce Hauman's Figwheel: a live REPL right inside the running page. You hot-load new code, and read and change state, in the live app, no reload. In the demo a Flappy Bird clone keeps playing while he tweaks the game, the bird still flying, never losing your place. That immediacy, in the browser. (Tooling later settled on shadow-cljs, but that demo is what people remember.) Worth being precise: Figwheel let you reach *into* the running page and change it. It didn't let you point *at* the bird and ask which Clojure drew it."

**[SLIDE 4: the loop]** a loop diagram: *you → change → running system → feedback → you*; emphasize how *tight* it is.

**[SAY: name the idea + thesis]** "All of it (the toys, the magic machine, the REPL, the bird that won't stop flying) is the same thing: an immediate, tangible connection to what you're making. Change it, see it, *now*. When that distance is zero you stop programming by prediction (guess, run, check) and start programming by observation, in a conversation with a running system."

**[SAY: plant the thesis]** "Hold onto that loop. This whole talk comes down to one place where it's still broken for most of us, and how to close it."

**[TRANSITION]** "And the first thing to say about this feeling is that it's a lot older than Clojure."

---

## 2. A short history (5:00–10:00): 5 min

> Goal: place that personal feeling inside a 50-year tradition, the trunk under our Figwheel branch. ~45–60s per beat, names on slides, not paragraphs.

**[SAY: lead-in]** "We just saw my branch of this: the REPL, Figwheel. Here's the trunk it grew from."

**[SLIDE 5: Smalltalk / the image]** A Smalltalk screenshot or **Smalltalk, 1970s**.
**[SAY]** "Start at Xerox PARC. Smalltalk wasn't an app you ran; it was a live *image* you inhabited and edited while it ran: always on, always inspectable, always changeable. The Lisp machines had the same soul. The running system *was* the program."

**[SLIDE 6: direct manipulation]** **Shneiderman, 1983: 'direct manipulation.'**
**[SAY]** "In 1983 Ben Shneiderman named the interface version: direct manipulation. Act on the thing itself, continuous feedback, always undoable. Not a command describing the thing, but the thing. The same hands-on feeling as the back off the toy."

**[SLIDE 7: Bret Victor]** **'Inventing on Principle,' 2012.** A still of the slider/tree demo.
**[SAY]** "And the talk many of us can quote from memory: Bret Victor, *Inventing on Principle*, 2012. 'Creators need an immediate connection to what they're making.' He drags a number and the picture changes *as he drags*. Same idea, sharpened into a principle you feel guilty for not having."

**[SLIDE 8: moldable / Glamorous Toolkit]** **Moldable development: Tudor Gîrba / Glamorous Toolkit.**
**[SAY]** "One more, because it's where this talk points: moldable development, the Glamorous Toolkit world. The claim: build small, custom tools (especially inspectors) for your *own* system, because a generic view of your data is almost never the view you actually need. Hold that thought."

**[BEAT]**

**[SAY: synthesis]** "So the feeling I had as a kid has a fifty-year pedigree, and our corner of it, the REPL, is one of its purest forms anywhere. We believe in this so much we named a development style after it."

**[TRANSITION]** "Which makes the next part of my story a little embarrassing, because I had all of this, and then I walked away from half of it."

---

## 3. The turn, and the half we gave up (10:00–15:00): 5 min

**[SAY: the React/re-frame era]** "We took that same Clojure energy to real front ends, and we *succeeded*. We leveraged React, we got re-frame, and for a good while it all seemed great. Reagent made views feel like Clojure data; re-frame gave us one tidy place for state; and, a bit later, real inspection arrived: React's own DevTools extension showed the component tree, and re-frame-10x showed app-db and the whole event-and-subscription flow. We had a version of that loop on the rendered side too, and barely noticed we had it."

**[NOTE: your 'for a while': fill with the real reason you moved off it. One or two sentences; this is a tooling talk, not the SSR-vs-SPA debate. Consistent with the book's positioning: client-owned state cost us addressability, and for content-shaped apps the server is the right authority.]**

**[SAY: the move to the server]** "Then we moved to the server: rendered our HTML from Hiccup, kept the truth in the database, shed the client app. The right trade for our kind of app, but something quietly left with it, and it took me a while to notice what."

**[SLIDE 9: two boxes that don't touch]** Left: **REPL: interactivity for *code*.** Right: **DevTools: inspection of *output*.** A gap labeled **?**.
**[SAY: the gap]** "This is what left. The REPL still gives us total interactivity with our *code*. The browser still ships world-class inspection of the *output*: DevTools, back to Firebug in 2006: click any pixel, see the DOM. But the two halves no longer touch. I'm looking at a misaligned badge three clicks deep. Which *Clojure* produced it? DevTools shows a `<span>`; it has no idea that came from line 240 of `recipe/views.clj`. And my editor has no idea which pixels it's responsible for."

**[SLIDE 10: render throws the structure away]** A Hiccup vector → an HTML string, source info falling on the floor. Caption: **we delete the structure, every request.**
**[SAY: the real reason + the hook]** "And *why* did it vanish exactly when we moved to the server? In React and re-frame, the framework keeps a live component tree at runtime; that tree is the thing the devtools inspect; the structure is still *there*. Server-side we do the opposite: we take Hiccup, structured Clojure data, render it to a *string*, and throw the structure away. By the time it's HTML on the wire, nothing remembers it was `[:span ...]` on a particular line. The information didn't go missing. We deleted it, on purpose, every request."

**[BEAT]**

**[SAY: reframe to opportunity]** "So no one built this inspector for us, because the data it needs is gone by render time. But look at what kind of problem that is: not a missing feature in a tool we don't control. It's *our* data, in *our* language, through *our* render function. Hiccup is just data. If the structure is something we threw away, we can choose to keep it."

**[TRANSITION]** "Let me show you what it looks like when you do. Then we'll build it."

---

## 4. Live demo (15:00–21:00): 6 min

> Demo discipline: big font, one browser + one editor side by side, pre-seeded data, network off. Narrate every click. Have the recorded clip ready on a hotkey if anything stalls.

**[DEMO 0: setup shot]** Editor (left) on `recipe/views.clj`; browser (right) on a real page of the app. "This is the running app. This is the code. Watch the gap close."

**[DEMO 1: element → code]**
- Hold the inspect key (Alt+Shift+I), hover a few elements: highlight box + a **breadcrumb of tagged ancestors** appears.
- **[SAY]** "Hovering, I get the element *and* its chain of ancestors: not DOM ancestors, the Hiccup components that nest to produce it."
- Click one element. **The editor jumps to the exact line** that produced it.
- **[SAY]** "Click, and the editor is now on the line of Clojure that rendered that thing. From a pixel to a paren."

**[DEMO 2: definition vs. call site]**
- Hover the same kind of element rendered in two different places; show that one click takes you to the component's *definition*, another walks to the specific *call site* that produced *this* instance.
- **[SAY]** "And it knows the difference between *where the component is defined* and *the exact call that produced this one instance on screen*. That distinction matters the moment a component appears more than once."

**[DEMO 3: code → element (the half nobody has)]**
- In the editor, move the cursor onto a view function. **The matching element lights up in the browser.**
- **[SAY]** "Now the other direction, the half almost nobody has. I put my cursor on a view *in the editor*, and the element it produces lights up *in the page*. The editor is driving the browser."

**[DEMO 4: close the loop with a live edit]** (optional, high-impact if reload is wired)
- Edit the view, save; the page updates in place (morph). Re-hover to show the tag still points at the new line.
- **[SAY]** "And because this rides the same dev loop, I can change the code, watch the page update, and the inspector still knows where everything came from."

**[BEAT]** "That's the loop closed, both directions. Now the fun part: it's about a hundred lines of idea. Let's build it."

---

## 5. How it's built (21:00–31:00): 10 min

> Four moves. Each gets a slide with a *small* code excerpt (5–10 lines max) and one sentence of narration. Resist showing whole files.

**[SLIDE 11: the problem restated as a plan]** "Four moves: (1) stop throwing the structure away, (2) carry it to the DOM, (3) relay a click, (4) drive the editor."

**Move 1: keep the structure (`tools.reader`).**
**[SLIDE 12]** Tiny excerpt: loading a view namespace through `clojure.tools.reader` instead of the default loader.
**[SAY]** "The default Clojure reader doesn't attach line info to nested vector literals, so `[:span ...]` inside a `defn` has no source position. `tools.reader` *does*. So in dev, we load view namespaces through a `tools.reader` pass (call it `tr-load!`) and now every Hiccup vector carries `^{:line ... :column ...}` metadata. That's it. That's the move that recovers what render normally deletes."

**Move 2: carry it to the DOM (instrumentation).**
**[SLIDE 13]** Excerpt: `instrument-var!` wrapping a view fn so the element it returns gets tagged (e.g. a `data-src` attribute) from the metadata; `instrument-ns!` does a namespace.
**[SAY]** "Metadata on a vector doesn't survive into an HTML string by itself. So we instrument the view vars: wrap each one so that, as it produces Hiccup, the source position rides along onto the element as a data attribute. Now the rendered HTML carries a thread back to the source: file, line, the component identity, and the call site. The structure we deleted is back in the output, in a form the browser can read."

**[SLIDE 14: naming convention]** One line: "we tag *views*, by naming convention, only in dev."
**[SAY]** "We only do this to view namespaces, detected by naming convention, so we're not paying the `tools.reader` cost on code with no Hiccup, and so the tags only exist in development."

**Move 3: relay the click (the dev WebSocket).**
**[SLIDE 15]** Excerpt: the browser `inspector.js` sending `{:type "open-source" :file ... :line ...}` over the existing `/dev/ws` socket.
**[SAY]** "The page already has a dev WebSocket, the same one live reload uses. The inspector script reads the data attribute off the element you clicked and sends it down that socket: 'open this file at this line.' The browser can't open your editor, but the server can relay to something that can."

**Move 4: drive the editor (the bridge).**
**[SLIDE 16]** Excerpt: the editor-side script (Joyride/Calva) subscribing to the relay and opening the file at the line; and the reverse: cursor position → message → browser highlight.
**[SAY]** "On the editor side, a small script connects to the same relay. One direction: it receives 'open file at line' and opens it. The other direction: it watches your cursor, and when you land on a view, it tells the browser which source position you're on, and the page highlights the matching element. The server in the middle is just a hub passing typed messages between two peers: browser and editor."

**[SLIDE 17: the whole picture]** The earlier two-boxes-with-a-gap slide, now with the gap filled: **source tags → DOM → socket → editor**, arrows both ways.
**[SAY]** "That's the entire system. Recover the structure with `tools.reader`, carry it out with instrumentation, relay over the socket you already have, bridge to the editor. Four moves, and the loop is closed."

**[TRANSITION]** "It's small because Hiccup is data and the REPL is right there. But 'small' hides two sharp edges worth your time."

---

## 6. Trade-offs, the sharp edge, and what generalizes (31:00–39:00): 8 min

**[SLIDE 18: dev/prod separation]** "None of this ships."
**[SAY]** "First: this is strictly a development tool, and it has to be *impossible* to ship. We get that structurally, not by discipline. The whole thing lives on a dev-only classpath, and the page only emits the inspector script when the dev namespace resolves, which it never does in production. There's no flag to forget. The code simply isn't there."

**[SLIDE 19: the bug that teaches the design]** Title: **The re-def that strips every tag.**
**[SAY]** "Second, the sharp edge, and it's the most useful thing I can give you, because it's the one that'll bite you if you build this. The tags exist *only because the loader applied them*. So any re-definition of a view that goes *around* the loader (a plain `load-file`, or your editor evaluating a single `defn` on save) re-defs that function with the *default* reader and no instrumentation, and silently strips every tag in that file. The symptom is baffling: 'I edited a view, saved, and a bunch of elements just lost their inspection borders.' It looks like the edit broke it. It didn't."

**[SAY: the lesson]** "The fix is a design rule, not a patch: the loader has to be the *single source of truth* for how views get loaded. Load them through it at startup, reload them through it on file change, and don't let a second, untagged path sneak in behind it. That's a general lesson about instrumentation: the instant there are two ways to load a thing, one of them is wrong."

**[SLIDE 20: what generalizes]** Three bullets revealed one at a time:
- *Code is data isn't a slogan; it's tooling leverage.*
- *Don't throw structure away; or if you must, keep a thread back to it.*
- *Build the inspector your system actually needs (moldable).*

**[SAY]** "Step back and the technique generalizes past this one tool. One: 'code is data' usually gets sold with macros, but this is the better demo, because Hiccup is data, a hundred lines buys you a bidirectional inspector that the JavaScript world builds entire framework machinery to approximate. Two: every system throws some structure away at a boundary; if you keep even a thread back to the source across that boundary, you can close loops everywhere: logs that jump to code, errors that highlight UI, data that knows where it came from. Three (and this is the moldable-development point from the start): the highest-leverage tool is usually the small custom one *you* build for *your* system, because you know what you actually need to see."

**[SLIDE 21: callback to the open]** The loop diagram from slide 3, whole.
**[SAY]** "We started with one feeling: change it, see it, immediately. The REPL gave us that for our code decades into a tradition that goes back to Smalltalk. The rendered page was the half we'd left out, not because it was impossible, but because we delete the structure that would make it possible, every request. Keep the structure, and the other half of the loop is a weekend project."

**[SLIDE 22: close]** One line: **"Hiccup is just data. So inspect it."** + repo / book link + your handle.
**[SAY]** "It's all in an open companion project if you want the code. Keep the loop closed. Thank you."

**[BEAT → Q&A]** (~2 min)

---

## Appendix A: Demo run-sheet (rehearse to muscle memory)

1. Reset DB to seeded state; start dev server + watcher; open app to the recipe page.
2. Editor + browser side by side, font ≥ 20pt, cursor visible, highlight colors high-contrast.
3. Disable notifications; airplane-mode the demo machine (no network needed).
4. Sequence: hover → breadcrumb → click→editor → defn-vs-call-site → cursor→browser highlight → (optional) live edit + morph.
5. Fallback: 60–90s screen recording bound to a hotkey; switch to it on any stall, narrate over it, move on.

## Appendix B: Slide list (22)

Title · Clojure/REPL · Figwheel/Flappy Bird · The loop · Smalltalk · Direct manipulation · Bret Victor · Moldable/GT · Two boxes + gap (React/re-frame had it → the server gave it up) · Render throws structure away · (demo) · 4-move plan · tools.reader · instrument-var! · views-only convention · WS open-source msg · editor bridge · whole picture · dev/prod separation · the re-def bug · what generalizes · close.

## Appendix C: Cuts if running long (drop in this order)

1. Demo 4 (live edit + morph): nice-to-have, not load-bearing.
2. Move 4 reverse direction detail: show it in the demo, describe the bridge in one sentence.
3. Trim history to three beats: Smalltalk, Bret Victor, moldable (the opening already carries REPL/Figwheel).

## Appendix D: Likely Q&A

- *"Doesn't this only work in VS Code/Calva?"* The browser→source half is editor-agnostic (it's a socket message); the editor side is a small per-editor script. Show the contract, not the editor.
- *"Performance?"* Dev-only; `tools.reader` + instrumentation cost is paid on load, not per request that matters; production never sees it.
- *"Why not just use a SPA framework's devtools?"* That's the point of section 3: they keep a runtime tree; we don't ship one. This gets you the same affordance without the framework.
- *"Source maps?"* Same spirit (keep a thread from output back to source) but for server-rendered Hiccup and bidirectional, into the editor.
