# Where Did This <div> Come From?

---

Fourteen years ago, Bret Victor argued that creators need an immediate connection to what they make. Clojure already lived it: the REPL, then Figwheel and shadow-cljs in the browser. But it stops at the rendered page: you can change the code and watch the page update, yet you can't point at something on it and ask which Clojure form made it. Render Hiccup to HTML and the `<div>` forgets it was ever Clojure code on a line. Three clicks deep? Grep and guesswork.

This talk builds the other half: a source inspector wiring your app, browser, and editor into one loop. Hover an element and the editor jumps to the Hiccup that made it. Put your cursor on a view and the element lights up, definition told apart from call site.

It's surprisingly little code. We build it live, end to end, so you can wire the same loop into your own server-rendered Hiccup app.

---

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

Script

Hi, I'm Patrick. My talk is called *Where Did This <div> Come From?*.

This question often comes up when developing web pages. A misaligned badge, a caption that needs changing. We clearly see the problem on screen, but what code do we need to fix? So I do what most do, look for something unique and do a text search in the code base. Fingers crossed, hopefully we get limited results back!

This problem space already has some partial solutions. We have a browser REPL with Figwheel, but that only shows code and state change effects. Very useful, but not for our problem. React and Svelte, among others, have an inspector where you can point at something in your browser and land in the code.

We don't have any of this for server rendered Hiccup code.

But what if we did? What if we could just point to an element, and jump to it's Clojure form in the code that made it?

What if we could easily switch between jumping to call site and implementation?

What if we could do even better, and navigate our code and see that reflected in the browser?

And what if we could easily implement this, because we render our source maps in HTML?

None of this is hypothetical, you just watched it. It's working code in a public repo.

In this talk we'll build it live:

- The browser updating on save
- The source mapping with inspector
- The connection with the editor (VSCode)
- The code navigation feedback loop

With surprisingly little code. Every attendee can take this home to implement in their own application.

I hope to see you at the Conj!


























