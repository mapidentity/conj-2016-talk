# Clojure/conj 2026: Talk proposal (Sessionize draft)

> Local working draft. Not committed; no reference to this file is stored anywhere in the repo.
> Fill the `[bracketed]` bits before submitting. Deadline: June 14, 2026 (Sessionize).

---

## Session title

**Where Did This <div> Come From?**

*(The problem as a question; the subtitle answers it. Echoes the abstract's key sentence. Alternates:)*
- *From Pixel to Paren: A Source Inspector for Server-Rendered Hiccup*
- *The Other Half of the REPL: A Source Inspector for Server-Rendered Hiccup*
- *Back to the Parens: A Source Inspector for Server-Rendered Hiccup*
- *Building on Principle: A Source Inspector for Server-Rendered Hiccup* (rejected: the Bret Victor reference doesn't land without context, and "principle" doesn't connect to "source inspector")

---

## Track

**Tools**

---

## Level

**Intermediate.** Assumes you've written Hiccup and use a REPL. The core idea ("Hiccup is data, so we can attach source information to it") is accessible to anyone; the mechanics (tools.reader metadata, var instrumentation, an editor bridge) give the advanced crowd something to chew on.

---

## Session format

40 minutes, with a live demo.

---

## Description (public abstract)

*(947 characters. Sessionize limit is 100–1000.)*

Fourteen years ago, Bret Victor argued that creators need an immediate connection to what they make. Clojure already lived it: the REPL, then Figwheel and shadow-cljs in the browser. But it stops at the rendered page: you can change the code and watch the page update, yet you can't point at something on it and ask which Clojure form made it. Render Hiccup to HTML and the `<div>` forgets it was ever Clojure code on a line. Three clicks deep? Grep and guesswork.

This talk builds the other half: a source inspector wiring your app, browser, and editor into one loop. Hover an element and the editor jumps to the Hiccup that made it. Put your cursor on a view and the element lights up, definition told apart from call site.

It's surprisingly little code. We build it live, end to end, so you can wire the same loop into your own server-rendered Hiccup app.

---

## Reviewer info

> Sessionize prompt: "provide additional info not present in the abstract." So this is the *why-accept* case plus what the abstract can't say, not a re-pitch of the talk.

**Where it fits, and what's new.** It carries interactive, REPL-driven development into the one place the Clojure web stack hasn't tooled: the server-rendered UI. The "element → open in editor" half exists in the JS world (React dev-inspectors, Next's overlay); what's new is Clojure-shaped. (1) The *reverse* direction, editor cursor to browser, telling a component's definition from a specific call site, is uncommon even in JS. (2) For *server-rendered* output there's no live component tree to read, so the source map has to be *manufactured*. (3) It stays tiny: once Hiccup is data, recovering that map is a metadata pass, not a framework.

**An idea, not a gadget.** I frame it within the immediate-feedback lineage, from Smalltalk and direct manipulation through Bret Victor to Figwheel and moldable development, so it reads as a venerable principle reaching a place it hasn't rather than a one-off trick, and lands even for people who'll never build it.

**Shape & timing (40 min).**
1. The idea: an immediate connection to the running system, and why, once you have it, you can't go back. (3)
2. A short history: REPL, the Smalltalk/Lisp-machine image, direct manipulation, Bret Victor, Figwheel; what they share. (6)
3. Why we don't have it for the rendered UI: the REPL gives it for code and DevTools inspects output, but server-rendered Hiccup throws its structure away at render: no path from page to source, or editor to page. (5)
4. Live demo: closing the loop, both directions, definition vs. call site. (6)
5. How it's built: manufacture the source map we discarded (`tools.reader` metadata), carry it to the DOM (a render-boundary walk plus var instrumentation), relay the click, drive the editor. (10)
6. Trade-offs & sharp edges (dev/prod separation by classpath; the re-def-that-strips-tags; keeping the loader authoritative), and what this generalizes to. (8)
7. Q&A. (2)

**What broke, and what you take home.** The talk includes a real failure mode: any re-`def` that bypasses the loader (a plain `load-file`, an editor eval-on-save) silently strips the source tags, so the loader has to stay the single source of truth. Attendees leave with the actual mechanism, a clean dev/prod-separation-by-classpath model, and a sharper sense of what "code is data" buys in tooling.

**Demo feasibility.** Live, against a seeded local instance, with a recorded 60–90s clip as fallback; projector + laptop, no network needed. The inspector is working code in a public companion project (a server-rendered Clojure/Datomic SaaS), with a chapter documenting it end to end: https://github.com/mapidentity/parens-to-production (book: https://mapidentity.github.io/parens-to-production/).

**Scope, and what it isn't.** A technique-and-tools talk, not a production experience report: the companion app isn't a large-scale production system, so I'll present it as "here's the technique and exactly how it works," not "here's what broke at scale."

**Speaker.** I built every layer (the loader, the instrumentation, the dev-socket relay, the editor bridge), and I'm comfortable with live REPL-plus-browser demos. [First-time Conj speaker]

---

## Speaker tagline

*[pick one / edit]*
- Server-rendered Clojure, REPL-driven tools, no framework required.
- Building a Clojure/Datomic SaaS from the database out.

---

## Speaker bio

*[Draft: verify the name, role, location, and links; replace brackets.]*

[P. de Kruif] builds [product/company], a multi-tenant SaaS in Clojure and Datomic, server-rendered from the database out, and writes the open companion book *Building a Clojure/Datomic SaaS from Scratch*. [He/they] is happiest where the REPL meets the browser, and has a weakness for small, sharp tools over large frameworks. [Optional: based in [city]; previously [role/company]; [site / GitHub / Mastodon].]

---

## Pitch video (2 minutes)

### Approach

**The one decision that matters: show the demo.** A pitch video is the only submission format where the inspector can be *seen* instead of described. A reviewer who watches an editor jump to source from a browser click will remember this proposal out of sixty. So the video is a hybrid: face to open (proves you can present), screen capture in the middle (proves the demo is real), face to close. Do not re-read the abstract; the reviewers have it. The video's job is to add what text cannot: the demo, and you.

**Tell the problem as a story, then make a promise.** No one understands a solution to a problem they haven't felt, so the first half is a narrative told over screen recordings, in story order:

1. *The problem, felt*: something's visibly off in our app; what code do we fix? Under that line, a silent visual: right-click → Inspect → the trail ends at a naked `<div>` (this plants the build's callback without costing narration). Then the real-world ritual: search for something unique in the code base, fingers crossed the results are few.
2. *Others recognized it and attacked it*: Figwheel, a browser REPL showing code and state-change effects, very useful, not this problem. Then the ones that did attack navigation: React and Svelte's inspectors, point at the browser, land in the code. Recognition and solutions; one direction, and they need a component tree kept alive in the browser.
3. *The current state in Clojure*: for server-rendered Hiccup there is nothing.
4. *The what-if cascade*: four escalating questions, each one asked **while its answer plays on screen**: point at an element and jump to its Clojure form (the demo's click → editor); switch between call site and implementation (the λ/() crumbs); navigate code and see it in the browser (cursor → highlight); and "what if we could easily implement this, because we render our source maps in HTML?", landing on the same naked div from beat 1, now carrying `data-myapp-src`. The narration asks; the screen answers; the viewer experiences the reveal instead of being told about it. The fourth what-if is the callback and the thesis in one shot.
5. *The existence claim, to camera*: "None of this is hypothetical, you just watched it. It's working code in a public repo." This is the one sentence that separates "ambitious idea" from "working tool" on a reviewer's scorecard, and delivering it on camera doubles as the mid-video presence beat.
6. *The contents list*: "In this talk we'll build it live:" with the four bullets as on-screen text (the bullet may read "(VS Code)"; the voice just says "the editor"), each getting a 3-4 second code flash (the watcher/reload, the tagging pass, the editor bridge, the loop closed). This folds the spill-the-beans proof into the list: "with surprisingly little code" lands over actual code on screen, not over a claim.

This is the talk's real claim in miniature: **SSR Hiccup is behind, and we don't just catch up, we exceed.**

**And spill the beans: show how it's made, in turbo time.** Mystery sells tickets to attendees; substance sells slots to reviewers. Their quiet worry about a demo-driven talk is "is this a five-minute gadget stretched to forty?" A thirty-second how-it's-made montage answers it, proves you can explain the machinery crisply, and has a money shot the demo alone doesn't: open devtools on an element and show it carrying `data-myapp-src="...views.clj:240:8"`. The manufactured source map, visible on screen. That is the talk's entire thesis ("the structure we delete at render is structure we can keep") as a single image.

**Production plan.** The montage means edited segments, not a single take: record the screen clips first, then narrate the whole script as one continuous voiceover laid under the reel (one voice take over an edited picture track sounds far better than four stitched narrations). Webcam on for the open and close only.

**Clips to prepare (the new work in this plan):**
- *DevTools dead end*: our app, the pre-picked element, right-click → Inspect. Silent visual under the problem narration. (5s)
- *The text search*: editor-wide search on a class name from that div, returning a wall of results. (5s)
- *Flappy Bird*: record your own run of Bruce Hauman's demo (`bhauman/flappy-bird-demo-new` is the figwheel-main version and most likely to run on modern tooling) rather than reusing conference footage: cleaner rights, crisper capture. Make one visible live edit while the bird flies. (12s)
- *Svelte inspector*: scaffold a default SvelteKit starter, enable the vite-plugin-svelte inspector, record hover → click → editor opens. (10s) React devtools are covered verbally; at most a 2s cutaway still.
- *Our demo + turbo build*: as below.

**Setup checklist (same discipline as the talk demo):**
- Seeded local instance running; editor left, browser right; fonts large enough for a phone screen (reviewers watch on anything).
- 1080p, decent mic, quiet room, notifications off, network off (nothing in the demo needs it).
- Problem beat: pick the element in advance (ideally something visibly off, e.g. a misaligned badge), DevTools docked and ready, so right-click → Inspect lands on the naked div instantly.
- Rehearse the two demo moves to muscle memory: (toggle inspector, hover, click) and (cursor on view, watch highlight).
- For the turbo-build segment: return to the *same element* in devtools, now showing `data-myapp-src` (the callback), and have the four code spots ready as editor tabs so each "move" is one tab-switch, not scrolling.
- A small lower-third caption naming each tool during the montage (DevTools / Figwheel / Svelte inspector) so viewers track what they're seeing without narration overhead.
- Rehearse the full voiceover aloud to **1:55**; if over, trim the React mention first, then Svelte's second sentence; never cut the dead end, Flappy Bird, the demo, or the build.
- Look at the lens for the face segments. Energy slightly above natural; video flattens it.

**Accuracy guardrails (the fact-check items that bite on camera):**
- Hover *highlights*; **click** jumps the editor. Alt+Shift+I *toggles* the inspector.
- Don't say "a hundred lines"; "surprisingly little code" is the calibrated claim.
- It's Joyride driving VS Code; say "my editor" and leave it at that.
- Figwheel/Flappy Bird is *liveness* (hot code loading, state in atoms surviving reload), not inspection: credit it for "change it and see it," not for navigation.
- Scope the gap claim precisely: ClojureScript is not unserved, but its tools cover *different* things: re-frame-10x inspects the data flow (events, app-db, subscriptions), and element-level inspection comes from React DevTools, because Reagent components are React components. Neither navigates element → Clojure source, and nothing at all covers *server-rendered* Hiccup. Say the reverse direction is "rare," not "nobody has it."

### Script (~265 words, ≈1:50 at a conversational pace; comfortably inside 2:00)

**[0:00–0:05, FACE]**
"Hi, I'm Patrick. My talk is called *Where Did This <div> Come From?*"

**[0:05–0:30, SCREEN: our app; under "what code do we need to fix?" a silent right-click → Inspect ending on the naked div (plants the callback); then an editor text search with a wall of results]**
"This question often comes up when developing web pages. A misaligned badge, a caption that needs changing. We clearly see the problem on screen, but what code do we need to fix? So I do what most do, look for something unique and do a text search in the code base. Fingers crossed, hopefully we get limited results back!"

**[0:30–0:50, SCREEN: Flappy Bird clip, then Svelte inspector clip, then back on our naked div]**
"This problem space already has some partial solutions. We have a browser REPL with Figwheel, but that only shows code and state change effects. Very useful, but not for our problem. React and Svelte, among others, have an inspector where you can point at something in your browser and land in the code.
We don't have any of this for server-rendered Hiccup code."

**[0:50–1:18, SCREEN: the what-if cascade; each question plays over its answer]**
"But what if we did? What if we could just point to an element, and jump to its Clojure form in the code that made it?
What if we could easily switch between jumping to call site and implementation?
What if we could do even better, and navigate our code and see that reflected in the browser?
And what if we could easily implement this, because we render our source maps in HTML?"

**[1:18–1:26, FACE: the existence claim, delivered to camera; doubles as the mid-video presence beat]**
"None of this is hypothetical, you just watched it. It's working code in a public repo."

**[1:26–1:48, SCREEN: contents list as on-screen text, a 3-4s code flash per bullet]**
"In this talk we'll build it live:
The browser updating on save.
The source mapping with inspector.
The connection with the editor.
The code navigation feedback loop.
With surprisingly little code. Every attendee can take this home to implement in their own application."

**[1:48–1:55, FACE]**
"I hope to see you at the Conj!"

### Teleprompter copy

> Spoken lines only. Paste into any prompter app; the bracketed cues are not read aloud.

[FACE]

Hi, I'm Patrick. My talk is called *Where Did This <div> Come From?*

[SCREEN: our app, the silent inspect dead end, the text search]

This question often comes up when developing web pages. A misaligned badge, a caption that needs changing.

We clearly see the problem on screen, but what code do we need to fix?

So I do what most do, look for something unique and do a text search in the code base.

Fingers crossed, hopefully we get limited results back!

[SCREEN: Flappy Bird, then Svelte inspector]

This problem space already has some partial solutions.

We have a browser REPL with Figwheel, but that only shows code and state change effects. Very useful, but not for our problem.

React and Svelte, among others, have an inspector where you can point at something in your browser and land in the code.

[SCREEN: back on our naked div]

We don't have any of this for server-rendered Hiccup code.

[SCREEN: the what-if cascade, each answer playing as it's asked]

But what if we did? What if we could just point to an element, and jump to its Clojure form in the code that made it?

What if we could easily switch between jumping to call site and implementation?

What if we could do even better, and navigate our code and see that reflected in the browser?

And what if we could easily implement this, because we render our source maps in HTML?

[FACE: the existence claim]

None of this is hypothetical, you just watched it. It's working code in a public repo.

[SCREEN: contents list with code flashes]

In this talk we'll build it live:

The browser updating on save.

The source mapping with inspector.

The connection with the editor.

The code navigation feedback loop.

With surprisingly little code. Every attendee can take this home to implement in their own application.

[FACE]

I hope to see you at the Conj!

---

## Submission checklist

- [ ] Confirm name, bio, tagline, links, headshot (Sessionize profile)
- [ ] Pick final title
- [ ] Confirm session length matches the Conj slot options on Sessionize
- [ ] Record a 60–90s demo clip as the reviewer-facing proof / fallback
- [ ] Record the 2-minute pitch video (script above); rehearse to 1:50
- [ ] Submit before June 14, 2026, 11:59 PM ET
