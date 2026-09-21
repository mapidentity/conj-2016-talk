# Where Did This `<div>` Come From? — live-coding run-sheet

> Master script for the Clojure/conj 2026 talk, restructured around a LIVE BUILD
> (supersedes the slides+demo draft in `where-did-this-div-come-from.md`).
> Format: 40 minutes = 38 talk + 2 Q&A. Audience: Clojure-literate, knows Hiccup.
> We start from a basic hiccup webserver and build the whole inspector on stage,
> **without ClojureStorm** — this is the ch. 15 inspector only, no tracer.
>
> Companion demo repo: `conj/demo` (its own git repo, branches `step-0` … `step-7`).
> Every checkpoint boots and has been verified end-to-end, including the WS
> contract with a fake editor. The exact forms to TYPE are in
> `livecode-cheatsheet.md` (keep it on a second screen or printed).
> Slides (15, bookends only — no plan slide, no step list until the end;
> the problem chain is the map) are defined **in this file**, each as a
> `<!-- slide N · name -->` … `<!-- /slide -->` block after the page marker
> that first shows it; `slides.html` is generated from them (projector tab).

---

## The one design decision

**The screen is the editor, not the slides.** Slides open the talk, carry the
insight and the sharp-edge rule, and close it. Everything else happens in VS
Code + browser, side by side. Live coding follows a strict discipline:

- **TYPE** only the code that carries the idea (the REPL insight,
  `element?`, `tr-load!`, `tag-tree`, the `dev-body` hook, `instrument-var!`,
  `resolve-cursor`, the message dispatch). Don't type docstrings — they're in
  the repo; a later checkout reconciles and the diff is docstring-only noise.
  Typed total after the §7 paste rebalance and §1's step-1 checkout: ~53 lines.
- **PASTE** infrastructure that has no idea in it (the html-tags set, the
  overlay JS, the Joyride script) — paste it, say what it is in one sentence,
  move on. Paste sources live in the cheatsheet.
- **CHECKOUT** the one step whose code is too intricate to do live
  (`wrap-callsites`, branch `step-7`) — show it on screen, narrate the guard.

**Recovery is a checkout.** The demo's own live-reload is the safety net: the
JVM stays up all talk, the watcher `tr-load!`s whatever changes on disk — so
`git switch -f step-N` instantly puts code AND browser in a known-good
state (verified: checkout → watcher reload → tags correct). If any section
derails: switch to its END branch, say "here's where we were going", demo the
payoff, continue. Nobody will mind; do not debug on stage for more than 30s.

| talk section | ends at git branch |
| --- | --- |
| §1 the problem + hot reload | `step-1` |
| §2 the question, asked twice | — |
| §3 why not? can we? (REPL only) | — |
| §4 keep the structure | `step-2` |
| §5 carry it to the DOM | `step-3` |
| §6 overlay + click→editor | `step-4` |
| §7 components | `step-5` |
| §8 reverse direction | `step-6` |
| §9 call sites | `step-7` |

---

## Stage setup (before doors)

1. VS Code open on `conj/demo` — or the workspace root, whose `.joyride`
   symlinks into it — **Calva jacked in** (`:dev` + `:nrepl` aliases, REPL
   cwd `demo/`), Joyride
   installed. (The editor-agent script only exists from `step-6` — it arrives
   with §8's checkout, and you run "Joyride: Run Workspace Script" then;
   nothing to connect at setup time.) Server started **from the REPL**:
   `(start!)` — the REPL lands in `user` (`dev/user.clj`) — same process as
   the REPL, that's what makes §10's sharp edge demoable.
2. Repo at `step-0`, working tree clean. Terminal tab ready with `git branch`
   listed. Browser on `https://myapp.lan` (the ingress; `localhost:8080`
   still works as a fallback), docked right; editor left.
   DevTools pre-docked (bottom), closed.
3. Font ≥ 20pt everywhere (editor, REPL, terminal, browser zoom 125%+),
   **DevTools zoomed ~150% too** (Ctrl-+ inside the pane — it does not follow
   browser zoom; §1's naked span and §5's `data-src` money shot are DevTools
   text). For the overlay demos (§6–§9) bump **browser zoom to 150%** — the
   breadcrumb is 13px CSS and scales with page zoom. Notifications off,
   network off (nothing needs it — deps are in `~/.m2`).
   **VS Code auto-save OFF** — with it on, the watcher live-loads every
   half-typed form and sprays `reload FAILED` all talk. Toggle the inspector
   with the badge click, not Alt+Shift+I, unless you've verified the
   shortcut on the stage browser/OS (it collides with browser chrome on
   some platforms).
4. Cheatsheet on second screen/printout. Slides in a browser tab (`slides.html`).
5. Fallback: the 60–90s recorded clip of the finished thing on a hotkey
   (record it during rehearsal at `step-7`). And a **live plan B for the
   Joyride agent** — the one failure a checkout can't fix: drive the reverse
   direction from the REPL,
   `(#'demo.dev.editor/handle-cursor! {:file "demo/ui/views.clj" :line 23 :col 5})`
   (verified working) — it even reinforces the point that the editor side
   is just a socket message.
6. localStorage: turn the inspector badge OFF before starting (it persists!),
   so the first toggle on stage actually turns it on.

---

## §1 · The problem, and the chain that closes it (0:00–10:00) — slides 1–6

> The first three minutes are the abstract coming true in front of them —
> same arc, same key phrases ("the div forgets it was ever Clojure code on a
> line", "grep and guesswork"). The whole talk then runs on one engine,
> re-run in every section: *why don't we have this? can we have it? how?*
> The talk's real message — build what you can imagine; the status quo is a
> choice — is NEVER spoken. The form carries it: a "framework feature" built
> from a bare webserver in half an hour. Don't editorialize; demonstrate.

<!-- page "The connection that stops at the page" @0:00 [slide 1]
  slide 1
-->

<!-- slide 1 · title -->
# Where Did This `<div>` Come From?

Patrick de Kruif · Clojure/Conj 2026 {.sub}
<!-- /slide -->

**[SLIDE 1: title]** "Hello. My name is Patrick. I’m a freelance software developer and consultant from the Netherlands, and a lot of my work is building web applications in Clojure."

> Show demo application

"For years, my default stack for applications like this was Reagent and re-frame. It provided the kind of user experience we wanted from a single-page application."

"And it was delightful to work with."

"Figwheel or shadow-cljs show your changes almost instantly. React DevTools lets you point at something on the screen and start figuring out where it came from."

"The feedback loop is incredibly tight. You stay connected to the running application. You stay in the flow."

"But over the last few years, more and more web development has been moving back toward the server."

"htmx. Datastar. React Server Components. SvelteKit."

"And I started wondering whether I should do the same."

"For the kind of database-backed applications I usually build, there are good reasons to. The browser is much more capable than it used to be. You can get a rich user experience with much less JavaScript. And if the server renders the UI, quite a lot of machinery simply disappears."

"So... I tried it."

> Return attention to demo

"This application is rendered entirely on the server. And I should add: there really isn’t much to it. It’s basically http-kit and Hiccup."

> Show deps.edn file in editor

"Not a ClojureScript application. Just Clojure. It doesn't need to be this bare of course, I left out a database and optimizations like Datastar to avoid distraction here."

"The server has the data, handles the operations, renders the UI, and sends HTML to the browser."

"And to the user, nothing visibly changed."

> Return to browser

"So that’s great! I’ve ended up with a much simpler architecture."

"Which is I have to admit is roughly where we all started twenty years ago, only now the browser can hold up its end."

"There’s just one problem."

"I also left behind a development environment that I really liked. That tight connection between the code and the running application isn’t there anymore. Shopping around for existing tools turned up empty, and I *really* started feeling that when working without that again."

<!-- page "A very simple app — and nothing to inspect it with" @1:00 [demo]
  shot s01-page "The recipe app: a featured recipe, filters, eight cards, ratings, icons. Server-rendered Hiccup, zero JavaScript. The spicy pills hang crooked." tall
-->

**[browser — the felt instance]** "To show what I mean, let's have a look at this example. See this spicy pill on the recipe of the day? It hangs a little lower than the NEW badge right next to it. Crooked. We should fix that. So first: where does it come from? Right-click, inspect."

> Browser right click, select spicy badge element on recipe of the day.

"DevTools says it's a span with class `badge hot`. So let's see if we can find that in the code."

> Do a global search in the editor for "badge hot".

"Right. No hit. But that class name could be composed some other way. Let's search for the text I can see instead; `spicy`."

> Do a global search in the editor for "spicy".

"Ok, so two hits are in the static recipe data. Only reason that comes up is because the data is hardcoded, not from a database. This other match looks promising, this could be the one. But without further scrutiny, this might relate to this other pill that shows `spicy`?"

> Point at the `spicy` tag-pill displayed under the stars rating

"It also does not tell me whether this affects the featured section, or the list below?"

> Point at `spicy` badge in featured section and regular section.

"I'm going to assume it does both. Let's make sure it's the right one. I'll just change the title real quick and see the change."

> Add `Ctrl+Shift+U → type 1f525 🔥` inside `[:span.badge.hot "🌶 " t]`, save, return to browser.

"I don't see any change. Oh right, I need to refresh the page. Still nothing. Of course, I need to reload this source file first."

> In REPL execute `(load-file "src/demo/views.clj")` and refresh browser.

"There! it looks like it affects both featured and regular badges. But this edit, reload, refresh loop will get really annoying really fast and this is about the most basic of tooling that we're missing here."

<!-- page "Save, and the page follows" @1:50
  slide 2
-->

<!-- slide 2 · the dev channel -->
# 🔥 hot reload

```svg
<svg viewBox="0 0 937 258" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="the dev channel: save, watcher, load-file, reload message, location.reload()">
  <defs>
    <marker id="a" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#6b6490"/></marker>
    <marker id="b" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#8b7ff5"/></marker>
  </defs>
  <rect x="0" y="144" width="937.3" height="96" rx="14" fill="#8b7ff5" fill-opacity="0.07" stroke="#8b7ff5" stroke-opacity="0.25"/><text x="18" y="166" font-family='system-ui, sans-serif' font-size="13px" letter-spacing="1.6" fill="#8b7ff5" fill-opacity=".9">DEV ONLY</text>
  <line x1="630.8" y1="34" x2="630.8" y2="232" stroke="#6b6490" stroke-width="2" stroke-dasharray="5 7" stroke-opacity=".75"/><text x="616.8" y="26" text-anchor="end" font-family='system-ui, sans-serif' font-size="14px" letter-spacing="1.6" fill="#9d94b8">SERVER</text><text x="644.8" y="26" font-family='system-ui, sans-serif' font-size="14px" letter-spacing="1.6" fill="#9d94b8">BROWSER</text>
  <line x1="124.1" y1="86" x2="143.1" y2="86" stroke="#6b6490" stroke-width="2" marker-end="url(#a)"/><line x1="260.1" y1="86" x2="279.1" y2="86" stroke="#6b6490" stroke-width="2" marker-end="url(#a)"/><line x1="94.9" y1="200" x2="113.9" y2="200" stroke="#8b7ff5" stroke-width="2" marker-end="url(#a)"/><line x1="245.6" y1="200" x2="264.6" y2="200" stroke="#8b7ff5" stroke-width="2" marker-end="url(#a)"/><line x1="385.8" y1="86" x2="677.8" y2="86" stroke="#6b6490" stroke-width="2" marker-end="url(#a)"/><line x1="578.8" y1="200" x2="677.8" y2="200" stroke="#8b7ff5" stroke-width="2" stroke-dasharray="7 6" marker-end="url(#b)"/><text x="633.8" y="183" text-anchor="middle" font-family='ui-monospace, "JetBrains Mono", Menlo, monospace' font-size="17px" fill="#8b7ff5">&quot;reload&quot;</text>
  <rect x="8.0" y="63.0" width="116.1" height="46" rx="10" fill="#211d30" stroke="#332d47"/><text x="66.0" y="93.0" text-anchor="middle" font-family='system-ui, sans-serif' font-size="20px" fill="#ece9f1">request</text><rect x="154.1" y="63.0" width="106.0" height="46" rx="10" fill="#211d30" stroke="#332d47"/><text x="207.1" y="93.0" text-anchor="middle" font-family='system-ui, sans-serif' font-size="20px" fill="#ece9f1">render</text><rect x="290.1" y="63.0" width="95.7" height="46" rx="10" fill="#211d30" stroke="#332d47"/><text x="338.0" y="93.0" text-anchor="middle" font-family='system-ui, sans-serif' font-size="20px" fill="#ece9f1">HTML</text><rect x="688.8" y="63.0" width="90.0" height="46" rx="10" fill="#211d30" stroke="#332d47"/><text x="733.8" y="93.0" text-anchor="middle" font-family='system-ui, sans-serif' font-size="20px" fill="#ece9f1">page</text>
  <rect x="8.0" y="177.0" width="86.9" height="46" rx="10" fill="#211d30" stroke="#463c86"/><text x="51.5" y="207.0" text-anchor="middle" font-family='system-ui, sans-serif' font-size="20px" fill="#ece9f1">save</text><rect x="124.9" y="177.0" width="120.7" height="46" rx="10" fill="#211d30" stroke="#463c86"/><text x="185.2" y="207.0" text-anchor="middle" font-family='system-ui, sans-serif' font-size="20px" fill="#ece9f1">watcher</text><rect x="275.6" y="177.0" width="303.2" height="46" rx="10" fill="#211d30" stroke="#463c86"/><text x="427.2" y="206.7" text-anchor="middle" font-family='ui-monospace, "JetBrains Mono", Menlo, monospace' font-size="19px" fill="#e0e7ff">(load-file "views.clj")</text><rect x="688.8" y="177.0" width="234.5" height="46" rx="10" fill="#211d30" stroke="#463c86"/><text x="806.0" y="206.7" text-anchor="middle" font-family='ui-monospace, "JetBrains Mono", Menlo, monospace' font-size="19px" fill="#e0e7ff">location.reload()</text>
</svg>
```
<!-- /slide -->

**[SLIDE 2: hot reload]** "I've set my editor to save when switching context. And when it does that, something should inform the server to reload the file. If that succeeds, something should let the browser know to do a page refresh. Of course I could let Calva or Emacs do the reloading but lets not rely on any particular editor unless we really have to. And of course, all the development tooling that we add should not ship to production. Using macros would be one way to do that, but deps tools gives us something out of the box."

<!-- page "One alias, and dev/ exists" @1:55
  slide 3
-->

<!-- slide 3 · deps.edn, one alias -->
# 🔧 development only

```diff
  :deps {org.clojure/clojure {:mvn/version "1.12.4"}
         http-kit/http-kit   {:mvn/version "2.8.0"}
         hiccup/hiccup       {:mvn/version "2.0.0"}}

  :aliases
  {:nrepl {…}
+  :dev   {:extra-paths ["dev"]
+          :extra-deps  {…}}
  }
```
<!-- /slide -->

**[SLIDE 3: deps.edn]** "We'll start the REPL with an extra `:dev` alias. This split ensures that any library dependency or source file under that alias is excluded from the production build."

<!-- page "Watch the files" @2:00
  slide 4
-->

<!-- slide 4 · the watcher -->
# 📂👀 something watches

```clojure
(loop [seen (modified-times)]
  (Thread/sleep 200)
  (let [current (modified-times)
        changed (for [[path t] current
                      :when (and (not= t (get seen path))
                                 (watched? path))]
                  path)]
    (when (seq changed)
      (when (every? true? (mapv load-changed! (sort changed)))
        (socket/notify-reload!)))
    (recur current)))
```

`notify-reload!` for every file changed in the last 200 milliseconds. {.note}

<!-- /slide -->

**[SLIDE 4: the watcher]** "Watching for source file changes can be relatively easy, just poll every 200 milliseconds for any file change. Reload any and all that have been changed in the mean time."

<!-- page "One socket" @2:05
  slide 5
-->

<!-- slide 5 · the socket -->
# 💌🌐 something tells the browser

```clojure
(defonce clients (atom #{}))

(defn broadcast! [msg]
  (let [s (json/write-str msg)]
    (doseq [ch @clients]
      (http/send! ch s))))

(defn notify-reload! []
  (broadcast! {:type "reload"}))

(defn ws-handler [req]
  (http/as-channel req
    {:on-open  (fn [ch] (swap! clients conj ch))
     :on-close (fn [ch _] (swap! clients disj ch))}))
```

uses `org.clojure/data.json` to send a websocket message with `http-kit` {.note}
<!-- /slide -->

**[SLIDE 5: the socket]** "http-kit can trivially setup a websocket. We can use that to restore our connection to browser, similar to what Vite, figwheel, shadow-cljs and others do. Server sent events would be an option here too, but in this case I went with websockets."

<!-- page "And the browser acts" @2:10
  slide 6
-->

<!-- slide 6 · the browser side -->
# ⚡ something acts on it

```clojure
(defn- dev-body [body]
  (list body
        [:script {:src "/dev/reload.js"}]))
```

```js
ws.onmessage = function (e) {
  var m = JSON.parse(e.data);
  if (m.type === 'reload') location.reload();
};
```
<!-- /slide -->

**[SLIDE 6: the browser side]** "We need the browser to actually respond to data we send to it. That means we need to add dev only JavaScript to the application itself. We can do that by conditionally including that."

"This is a very well trodden path so I won't bore you with more details, but lets have a look whether this idea actually works *here*. We need to restart the REPL though, to include the new deps alias."

> Run checkout step-1. Restart the REPL. Revert the local badge change. Show it works.

"As we can see this solves the first hurdle. Lets quickly get back to our original question. Where did this badge come from?"

---

## §2 · The question, asked twice (10:00–11:30) — slides 7–8

> The wire is in and the page still knows nothing about itself. Ask the
> question here, answer *why not* here; everything after this is *how*.

<!-- page "The question — said twice" @10:00
  slide 7
-->

<!-- slide 7 · the question -->
# ☝ What do we need to point at a pixel\
and ask ==which Clojure made it==? 🮰

```html
<span class="badge hot">🌶 spicy</span>
```
<!-- /slide -->

**[SLIDE 7: the question — say it twice]** "So, this talk's question: why
can't I point at a pixel and ask which Clojure made it — and why can't my
editor ask the *page*? Three smaller questions hide inside: why don't we
have this? *Can* we have it? How? We'll keep asking those three, all talk."

<!-- page "Why not: render deletes the structure" @10:45
  slide 8
-->

<!-- slide 8 · why not: render deletes the structure -->
# 🗺 source mapping

## What we have
```clojure
(hiccup2/html [:span.badge.hot "🌶 " t])
```

```html
<span class="badge hot">🌶 spicy</span>
```

## What we need
```clojure
(hiccup2/html {:data-src "demo/views.clj:21:8"} [:span.badge.hot "🌶 " t])
```
```html
<span class="badge hot" data-src="demo/views.clj:21:8">🌶 spicy</span>
```
<!-- /slide -->

**[SLIDE 8: why — render deletes the structure]** "Like the page refresh, we need to add something to the page to interact with the elements shown. To be able to do that, we need some kind of source mapping. This can be done in many ways of course, but adding it as data attributes seems straightforward enough."

---

## §3 · Why not? Can we? (11:30–14:30) — slides 9–10, then REPL

> The intellectual heart, run exactly on the triad: form (1) is the WHY NOT
> shown live; forms (2)+(3) are the CAN WE. Slow down. Type all three; let
> each result sit on screen for a breath.

<!-- page "How? — what the reader could tell us" @11:30
  slide 9
-->

<!-- slide 9 · how? -->
# How?

- ✅ We already know which source file is loaded;
- ❗ Line & column data; only ==**R**==ead from ==**R**==EPL touches source files
- 🤔 Can it add metadata to hiccup forms?

```clojure
(read-string "[:span.badge.hot \"🌶 \" t]")
→ [:span.badge.hot \"🌶 \" t]
(meta …) → nil
```
<!-- /slide -->

"The reader converts our source code file into actual data structures. To match this with line numbers, we need to do that in the reader. But our standard reader does not provide that. Should we build our own reader then?"

<!-- page "The reader that keeps the position" @11:45 compact
  slide 10
-->

<!-- slide 10 · the insight -->
# clojure.tools reader

```clojure
(with-open [r (clojure.tools.reader.reader-types/indexing-push-back-reader
               "[:span.badge.hot
                \"🌶 \"
                t]")]
  (-> (clojure.tools.reader/read r)
      (nth 2)
      (#(vector (name %) (meta %)))))
→ ["t" {:column 17, :end-column 18, :end-line 3, :line 3}]
```

Load views through tools.reader → every element knows its source.\
The position **is** part of the value. {.rule}
<!-- /slide -->

"Fortunately not! Clojure has a reader that does exactly this. The metadata that is added is preserved throughout evaluation. Therefore, if we load our sources with hiccup code with this reader, we should be able to add the source mapping to the html generation."

---

## §4 · Keep the structure: `tr-load!` (14:30–18:00) → `step-2`

<!-- page "tr-load! — load, but keep the lines" @14:30
  code §4b "Not every vector is Hiccup: only vectors whose head is a bare HTML-tag keyword; the split strips `.class`/`#id` sugar."
  code §4d
-->

**[editor: `dev/demo/inspector.clj`, new file]**
- **PASTE** the ns form + `html-tags` set (§4a). "A set of tag names —
  boring, but it's the safety gate."
- **TYPE** `element?` (§4b). "Not every vector is Hiccup — `let` bindings,
  pull patterns, tuples. We only ever touch vectors whose head is a bare
  HTML tag keyword; the split strips `.class`/`#id` sugar. This gate is what
  makes everything else safe to apply blindly."
- **PASTE** `add-file-meta` (§4c), one sentence over it: "tools.reader gives
  line and column but not *which file* — one postwalk adds one key, and on
  Clojure 1.12 postwalk preserves metadata on everything it rebuilds; that
  guarantee is load-bearing."
- **TYPE** `tr-load!` (§4d) — narrate the one subtlety: "the `ns` form is
  evaluated *before* the body is read, because `::aliased` keywords resolve
  at *read* time. Get that order wrong and files with auto-resolved keywords
  mysteriously fail."
- **PASTE** the watcher wiring in `watcher.clj` (§4e): `view-file?`,
  `load-views!`, `load-clj!` + the call in `start!` — but deliver its two
  beats out loud: "by naming convention, `views.clj` — so both view
  namespaces, the page and the ui kit, load through it, and we don't pay
  tools.reader on files with no Hiccup. Note what `load-clj!` really is:
  *`tr-load!` is now the only path that loads views* — remember that
  sentence; it comes back to bite in twenty minutes. And its second branch:
  the views were compiled *by* the loader, so when anything else changes —
  the loader itself included — re-tag them. That one line is going to quietly
  carry every remaining section of this talk."

<!-- page "A runtime value that knows its source" @17:00 [demo]
  repl ~"(demo.dev.watcher/load-views!)"
-->

**[demo — REPL]** `(demo.dev.watcher/load-views!)`, then
`(meta (demo.views/recipe-card (first demo.main/recipes)))` →
`{:line 14, :column 3, …, :file "demo/views.clj"}`. "A runtime value that
knows its source. The hard part of this talk is already done — and yet
nothing visible has changed. The *value* knows; the browser has no idea,
because Clojure metadata doesn't survive into an HTML string. How does the
knowledge cross the wire?"

---

## §5 · Carry it to the DOM: `tag-tree` (18:00–21:30) → `step-3`

<!-- page "tag-tree — metadata becomes attributes" @18:00
  code §5a "At the render boundary — after the views ran, before hiccup stringifies — one walk turns metadata into `data-src` / `data-name`. Elements without metadata pass through untouched."
  code §5b
-->

- **TYPE** `tag-tree` in `inspector.clj` (§5a). "The browser can't read
  Clojure metadata, so at the render boundary — after the views ran, before
  hiccup stringifies — one walk turns metadata into `data-src` and
  `data-name` attributes. Elements without the metadata pass through
  untouched." (Pre-decided fallback: if §5 starts later than 15:30, PASTE
  the cond skeleton and type only the `assoc` of the two attributes — the
  idea lives in those three lines.)
- **TYPE** the one-line change in `dev-body` (§5b): `body` →
  `(inspector/tag-tree body)`. "Not a line in the app. The walk hangs off
  the seam we bound in §1 — the render boundary, where hiccup meets the
  stringifier; this app has exactly one; if yours renders fragments, tag
  each boundary, or better, make it one helper. And in prod nothing binds
  that seam, and nothing could: the walk isn't on the classpath. Structurally
  absent, not turned off."

<!-- page "That div now remembers" @20:00 [demo]
  dom '<span class="badge hot" data-src="demo/views.clj:21:8">' "DevTools, on the same crooked pill from minute one — the whole thesis rendered into one line of HTML."
-->

**[demo — the callback]** Browser reloads on save. Open DevTools, inspect
**the same crooked pill from minute one** →
`<span class="badge hot" data-src="demo/views.clj:21:8">`. **[BEAT — let it
sit]** "That div now remembers. This attribute is the entire thesis of the
talk rendered into one line of HTML: the structure we used to delete, kept,
as a thread back to the source." Quick scroll of the Elements panel: "and
it's on *every* element — 365 of them on this page, and it even knows its
namespaces apart: the stars say `demo/ui/views.clj`. Note the eight card
roots all say the same line; one template line, eight renders, exactly as
promised. So the page finally knows where it came from — and clicking it
still does nothing. It knows, and it can't *tell* anyone. Who would it even
tell?"

---

## §6 · The overlay, and a click that opens your editor (21:30–25:00) → `step-4`

<!-- page "The overlay, the trust boundary, the dispatch" @21:30
  code ~"(defn handle-msg!" "Typed messages over one socket; the dispatch grows by adding cases — the hub never learns what they mean."
  code ~":on-receive (fn"
-->

- **PASTE** `static/dev/inspector.js` + its script tag (§6a) — no route: the
  dev route already serves `static/` — then
  walk THREE functions only (60–90s, don't read JS aloud): "`chain` walks up
  the `data-src` ancestors — that's the breadcrumb; `sendOpen` peels
  `file:line:col` and sends `{type: open}` down the same dev socket; the
  click handler swallows the app's click while inspecting. 200 lines of
  overlay, zero lines of framework."
- **PASTE** `resolve-src` + `handle-open!` into the new `editor.clj`, and
  `origin-ok?` into `socket.clj` (§6b), narrating the ideas over the paste: "the border asks two questions.
  Which files may be named? — a browser can send *any* string, so
  canonicalize, require `.clj`, confine to `src/` with a real path check,
  not a string prefix. And who may speak? — WebSockets aren't
  same-origin-restricted, so any page you have open could knock; browsers
  always announce their origin, native clients send none, so: no Origin, or
  the Host we were reached on, everyone else gets a 403. And then the naive bridge:
  `code -g file:line:col`. It works; it has one flaw we'll fix when the
  editor joins the conversation."
- **TYPE** `handle-msg!` + the `:on-receive` line (§6c) — the dispatch is
  the shape worth typing: "typed messages over one socket; the dispatch
  grows by adding cases, and the hub never learns what they mean."

<!-- page "From a pixel to a paren" @23:30 [demo]
  shot s06-hover-badge "Hover → a box on the element and the breadcrumb of its tagged ancestors. Click → your editor jumps to `views.clj` 21:8."
-->

**[demo]** Toggle the badge (Alt+Shift+I). Hover around: boxes + breadcrumbs
(`main ▸ section ▸ article ▸ div ▸ h2 ▸ span`) — spend 20 seconds just
wandering: a star, a pill, an icon; every pixel answers. Hover the crooked
pill — click → **your editor jumps to `views.clj` line 21, column 8.**
"From a pixel to a paren. And now the fix isn't a guess — and notice it
isn't the guess I would have made: the obvious move is to straighten
`.badge`, and that would shove the NEW badge too. The element just told me
it came from `[:span.badge.hot …]`, so `.hot` is the hook."
Remove the `top: .45rem` rule from `.badge.hot` in `style.css`, save → the
pill straightens, NEW stays where it was.
"See it, point at it, fix it, see it again. The question from minute
one is answered. But look at what the breadcrumb *says*: `article`, `div`,
`span`. True, and useless — nobody thinks in divs. I think in `recipe-card`.
What *made* this thing?"

---

## §7 · Components: name what produced it (25:00–27:00) → `step-5`

<!-- page "instrument-var! — the loader does it all" @25:00
  code §7b "The wrapper stamps the *var's* file and line onto the returned root; the `::orig` marker makes it idempotent, so reloads re-wrap cleanly."
  code §7c
-->

"Element positions can't answer 'what made this' — that needs the enclosing
`defn`. The loader can supply it invisibly."

- **PASTE** `tag-hiccup` (§7a) — "the one-element version of `tag-tree`;
  no-op on anything that isn't a Hiccup element, and it never overwrites an
  existing tag, so the innermost component wins."
- **PASTE** `instrument-var!` + `instrument-ns!` (§7b), then narrate the two
  ideas over the pasted code, pointing: "the wrapper stamps the *var's* file
  and line — always present after a defn — onto the returned root; the
  `::orig` marker makes it idempotent, so reloads re-wrap cleanly. And we
  map it over the whole namespace — wrapping a non-view fn is harmless, so
  we don't have to pick functions." (Pasting here, not typing, is what buys
  the knockout its slack — see the hard gate.)
- **TYPE** the one added line in `tr-load!` (§7c): `(instrument-ns! …)`.

<!-- page "The breadcrumb names the whole tower" @26:00 [demo]
  shot s07-hover-star "After instrumenting: the breadcrumb now names the whole tower of components."
-->

**[demo]** Save `inspector.clj` — watch the terminal: the engine reloads AND
the views re-tag themselves (§4's one line, earning its keep). Hover a star:
the breadcrumb now names the whole tower —
`page ▸ featured ▸ recipe-card ▸ div ▸ rating ▸ star`. Click a card's *root*
→ your editor opens the `defn recipe-card` line. "Views stayed plain
`defn`s — no annotations, no registry. The loader did it all. So the page
can now point at your code, precisely, in your vocabulary. One direction.
Can the conversation go the other way — can the *code* point at the *page*?"

---

## §8 · The reverse direction: your cursor drives the browser (27:00–32:00) → `step-6`

> THE KNOCKOUT. Protect it (see the hard gate in the cuts section), and when
> the stars light, stop talking for three full seconds.

<!-- page "An index, an agent, a highlighter" @27:00
  code §8b "Cursor → strings that are **byte-identical** to what we stamped into the DOM. The browser match is one attribute selector; no fuzzy matching anywhere."
  code §8c "Clients get a role (an editor announces itself); `handle-cursor!` broadcasts a highlight; `handle-open!` now *pushes* to the connected editor. The Joyride script is ClojureScript in VS Code's extension host."
-->

"This is the half almost nobody has, in any ecosystem. We need three small
things: an index, an agent in the editor, and a highlighter."

- **PASTE** the index block (§8a: `view-index`, spans, `collect-elements`,
  `index-ns!`, containment helpers) — "the same read pass we already do;
  while we're there, remember every defn's span and every element literal's
  span. Those *end* positions from minute eight — this is what they buy."
- **TYPE** `resolve-cursor` + the `index-ns!` line in `tr-load!` (§8b).
  "Cursor to strings — and note they are *byte-identical* to what we stamped
  into the DOM. The browser match will be one attribute selector. No fuzzy
  matching anywhere."
- **CHECKOUT** the glue in one move (§8c):
  `git restore -s step-6 -- dev/demo/ static/dev/inspector.js
  .joyride/scripts/workspace_activate.cljs` — then narrate the
  `socket.clj` + `editor.clj` diff for 45s: "clients now carry a role — an editor announces itself;
  `handle-cursor!` is seven lines: confine the path, `resolve-cursor`,
  broadcast a highlight; and `handle-open!` now *pushes* opens to the
  connected editor — exact window, exact range — with `code -g` demoted to
  fallback." Then the Joyride script, 30s: "ClojureScript running *inside*
  VS Code's extension host — the whole editor API, no extension to build or
  package. It reports the cursor, debounced, and receives the opens." Run
  "Joyride: Run Workspace Script". One sentence for the JS: "the highlight
  handler finds nodes by attribute — frame per component instance, strong
  box on the element."

<!-- page "Your cursor drives the browser" @29:00 [demo]
  shots s08-desc-9 "cursor in `recipe-card`'s `[:p description]` → nine green boxes, one per card" | s08-badges-3 "cursor onto `[:span.badge]` → the three NEW badges"
-->

**[demo — narrate every move, then stop narrating]** Inspect mode on. Editor
cursor into `recipe-card`'s body on `[:p description]` (line 22) → **nine
green boxes**, one per card — the featured one included — framed by nine
component outlines. "Your cursor is driving the browser." Cursor onto
`[:span.badge "NEW"]` (line 19) → the three NEW badges — **and the three
spicy pills right beside them stay dark.** "Not a class selector: the page
knows which line made which pill."

<!-- page "The knockout — all forty-five stars" @30:00 [the knockout]
  shot s08-stars-45 "Cursor in `star`'s body, in the UI-kit namespace → all 45 stars on the page ignite." tall hero
-->

Then the knockout: switch files to
`ui/views.clj`, cursor into `star`'s body — **all forty-five stars on the
page ignite. SAY NOTHING. Three seconds.** Then: "my cursor is in the UI-kit
namespace; those elements were rendered by the page namespace. Your editor
and your page are one connected surface now. And notice: *all* instances
light, every time — the DOM is telling the truth about one template, many
renders. Which raises the last question of the day: what if I mean *that
one*?" **[point at the featured card]**

---

## §9 · Call sites: telling instances apart (32:00–34:30) → `step-7` (CHECKOUT)

<!-- page "Same function, two call sites, told apart" @32:00
  bash "git switch -f step-7" "The watcher loads the new engine, re-tags the views, and reloads the page — `data-callsite` is in the DOM with no manual step."
  shots s09-grid-8 "grid `(recipe-card r)` → 8 grid cards; featured stays dark" | s09-featured-1 "`featured`'s `(recipe-card r)` → only the featured card"
-->

"Three `(stat …)` calls, three identical roots — nothing in the DOM records
*which call* made *which one*. The fix: while loading, rewrite each call to
a view fn so the rendered instance carries its invocation site. This is the
one piece I won't type — rewriting source is delicate and the code is
defensive; let me show it instead." **`git switch -f step-7`** — and point
at the terminal while it lands: "the watcher just loaded the new engine,
re-tagged the views, and reloaded the page. One command, whole state."

**[editor: show `wrap-callsites` on screen, 60s]** "Each call to a file-own
fn becomes `(tag-callsite \"file:l:c\" (the-call …))`. Three guards make it
safe: only *unqualified* heads naming fns this file defines; never inside
threading macros or `quote`, where rewriting changes meaning; and every
rebuilt form re-attaches its reader metadata — get that wrong and you
silently break the element tags you built twenty minutes ago."

**[demo — the payoff pair]** `recipe-card` is called from TWO places: the
grid's `for`, and `featured`.
1. Cursor on the grid's `(recipe-card r)` (line 81) → **the eight grid
   cards light — and the featured card, same component, stays dark.**
2. Cursor on `featured`'s `(recipe-card r)` (line 38) → **only the featured
   card.** "Same function, two call sites, told apart on screen. And there
   is minute one, answered: one line made all three spicy pills — and the
   page can now say which call made which, so I can give the big card its
   word and leave the grid alone."
<!-- page "One crumb, two files" @33:30 [demo]
  shot s09-hover-glyphs "The breadcrumb folds every component: `()` the call site, `λ` the definition. One crumb spans two files."
-->

3. Cursor on `(ui/stat "cooks" 7)` (line 73) → exactly one stat — "and note
   that's a *cross-namespace* call: the rewriter wraps unqualified calls the
   file defines, and alias-qualified calls that resolve into any views
   namespace." The grid case doubles as the honest floor: one looped call
   site → eight renders; lighting the family is the *correct* answer.
4. Hover a star in the featured card: the breadcrumb folds every component —
   `page ▸ featured () λ ▸ recipe-card () λ ▸ … ▸ rating () λ ▸ star () λ`.
   Don't *describe* where the glyphs point (the destinations live in
   tooltips nobody in the room can read) — **prove it with two clicks**:
   click `rating`'s `λ` → the editor opens `demo/ui/views.clj`; click its
   `()` → the editor opens the call in `demo/views.clj`. "One crumb, two
   files. Same distinction, forward direction, four components deep."

**[transition]** "At this point everything works, both directions. Which is
exactly when you should stop trusting me and ask: how does it *break*?"

---

## §10 · The sharp edge (34:30–36:30) — slides 11–12

<!-- page "The re-def that strips every tag" @34:30
  slide 11
-->

<!-- slide 11 · the sharp edge -->
## The re-def that strips every tag

The tags exist **only because the loader applied them**.\
A plain `load-file` — or your editor’s eval-on-save —\
re-defs the views untagged. Silently.

The loader is the ==single source of truth==\
for how views load. {.rule .big}

The moment there are two ways to load a thing, one of them is wrong. {.sub}
<!-- /slide -->

**[SLIDE 11: the re-def that strips every tag]** "Before you build this at
home, the one thing that WILL bite you. Everything works because the loader
applied the tags. Watch what happens when I go around it." **[live]** Calva:
*Load/Evaluate buffer* on `views.clj` (a plain load, no tools.reader).
"Perfectly good code, evaluated the way you eval Clojure every day. The page
still *looks* fine — it was rendered before. Refresh it." **[F5]** → hover a
card body: **dead. No boxes, no breadcrumbs.** Then hover a star: **still
alive.** "Only the file I bypassed died — the ui kit was never re-evaled.
That's exactly how it presents at home, and the partialness is what makes it
so baffling: 'I evaluated a view and *some* of my elements lost their
borders.'" Recover: **make a whitespace edit** in `views.clj`, then save —
the buffer is *clean* after a Calva load, and saving an unmodified buffer
writes nothing, so the watcher would never fire (rehearse this; a silent
recovery fumble inside the section about silent failures would be brutal).
Watcher tr-loads → page reloads itself → everything returns.

<!-- page "Your REPL is the second loader" @35:15 [slide 11]
  slide 11
-->

"And it's not just buffer loads: alt-Enter on a single view `defn` — the
gesture we all make a hundred times a day — strips that one function's tags
the same way. Your REPL is the *second loader* the rule forbids. The fix is
a design rule, not a patch: **the loader is the single source of truth for
how views load.** The watcher owns reloads; editor eval stays off for
views — or, the structural version, you make your editor's load path go
*through* the loader with an nREPL middleware. The moment there are two
ways to load a thing, one of them is wrong. That's true of every
instrumentation system you'll ever build."

<!-- page "Nothing ships" @35:45
  slide 12
  repl ~"demo.views/*render-boundary*"
-->

<!-- slide 12 · nothing ships -->
## Nothing ships

```clojure
(def ^:dynamic *render-boundary* identity)        ; the app's one seam
(binding [views/*render-boundary* dev-body] …)    ; dev/, per request
```

- no loader in prod → no metadata, no wrapping, empty index
- overlay + agent + middleware live in `dev/`
- a dev-only **classpath**: nothing binds the seam — structurally absent,\
  not ~~disabled~~
- the reason we never had this — we throw structure away —\
  is what keeps it safe in prod: there, we still do {.sub}
<!-- /slide -->

**[SLIDE 12: nothing ships]** REPL: `demo.views/*render-boundary*` →
`#function[clojure.core/identity]` — "the app's one seam, and outside a dev
request that is all it ever is — even in this JVM. `wrap-dev` binds it per
request, and `wrap-dev` lives in `dev/`, which prod's classpath doesn't
have. So in prod: identity — hiccup precompiles as if we'd never been here,
the loader never runs, the index is empty, the scripts aren't served. The
split is structural — all of this lives on a dev-only classpath. There is
no flag to forget. And notice the symmetry: the reason we never had this
tool — we throw the structure away — is exactly what keeps it safe in
production. There, we still throw it away."

---

## §11 · What it generalizes to + close (36:30–38:00) — slides 13–15

<!-- page "What you take home" @36:30
  slide 13
-->

<!-- slide 13 · what generalizes -->
## What you take home

{.big}
- **“Code is data” is tooling leverage** — Hiccup is data,\
  so ~450 lines of Clojure bought what JSX needs a build plugin for —\
  and the other direction too
- **keep a thread across the boundary** — logs → code,\
  errors → UI, data → provenance
- **build the inspector your system needs** —\
  ~800 lines all in, glue included. A weekend.
<!-- /slide -->

**[SLIDE 13: three take-homes]**
- "'Code is data' is usually sold with macros. This is the better demo:
  because Hiccup is data, ~450 lines of Clojure bought a bidirectional
  inspector — the same source-stamping trick JSX needs a build-time plugin
  for, and half of it the framework inspectors don't have at all."
- "Every system throws structure away at some boundary. Keep even a thread
  across it and loops close everywhere — logs that jump to code, errors that
  highlight UI." *(if behind: compress this bullet to one clause)*
- "The highest-leverage tool is the small one you build for *your* system."

<!-- page "Take the same walk" @37:00
  slide 14
-->

<!-- slide 14 · repo -->
## Take the same walk

{.steps}
- **step-0** a basic hiccup webserver
- **step-4** overlay + click→editor
- **step-1** live reload
- **step-5** components
- **step-2** tr-load! keeps the lines
- **step-6** cursor→browser
- **step-3** data-src on every element
- **step-7** call sites

demo repo: branched, step by step — github.com/mapidentity/…\
the production-shaped version, every trade-off argued:\
**Parens to Production** — mapidentity.github.io/parens-to-production {.sub}
<!-- /slide -->

**[SLIDE 14: repo + book]** "The demo repo is branched step by step — clone it,
`git switch step-0`, and take the same walk. The production-shaped
version — classpath separation, morphing reloads, reconnect handling, every
trade-off argued — is a chapter in the open companion book."

<!-- page "Hiccup is just data. So inspect it." @37:30
  slide 15
-->

<!-- slide 15 · close -->
# ++Hiccup is just data.++\
So inspect it.

“Creators need an immediate connection to what they make.” — Bret Victor {.sub}

Thank you. · questions? {.sub}
<!-- /slide -->

**[SLIDE 15: close]** "We started with Bret Victor's principle — an
immediate connection to what you make — and the one place our stack broke
it: a crooked pill nobody could trace. Now the connection runs both ways,
and the gap between the tools you have and the tools you can imagine turned
out to be about a weekend wide. **Hiccup is just data. So inspect it.**
Thank you." → Q&A (2:00).

---

## The hard gate (decide now, not on stage)

The knockout (§8) sits in the riskiest slot — last-ish — and it is
untouchable. So: **if §7 has not STARTED by 25:00, §7 becomes checkout-only**
(`git switch -f step-5`, show `instrument-var!` for 30 seconds, demo the
breadcrumb, move on). **If §8 has not started by 27:30, §9 is spoken, not
demoed** (one sentence + the breadcrumb `()`/`λ` hover, which needs no
cursor work). §8 always gets its full five minutes and its three seconds of
silence. Never rush the stars.

## Cuts if running long (drop in order)

1. §6's live badge *fix* (keep the click→editor jump; the fix is 20s but cuttable).
2. §10's REPL beat (the seam is `identity`) — one spoken sentence instead.
3. §9 walkthrough of `wrap-callsites` internals — checkout, demo the payoff
   pair, one sentence on the guards. (Never cut the payoff pair; it's the
   talk's most distinctive 40 seconds.)
4. §7 typing — paste `instrument-var!` instead of typing (saves ~90s).

## Stretch if running short

- §8: also put the cursor inside `layout` — nothing lights (it returns a
  string, no root element) and nothing breaks: DOM-as-truth means the
  resolver can propose and the page disposes. The book version draws a
  bounding box over the layout's span members instead.
- §5: prod, for real: `clj -M -e "(require 'demo.inspector)"` from the
  cheatsheet (§10) — "Could not locate"; needs a ~10s JVM boot, hence
  stretch-only.

## Rehearsal checklist

- [ ] Full run ×3 against the clock; each section has a hard out (the
      timings above). If §4 ends past 16:00, paste `tr-load!` instead of
      typing it.
- [ ] Record the fallback clip at `step-7` (both directions + `()`/`λ`).
- [ ] Rehearse the recovery move once deliberately: sabotage a paren in §5,
      `git switch -f step-3`, keep talking. Muscle memory.
- [ ] At `step-7` during rehearsal: verify the Joyride agent connects
      ("Joyride: Run Workspace Script"; check the extension-host console) and
      that both directions work end to end. Then return to `step-0` for the
      talk — the script leaves the working tree with the checkout.
- [ ] The badge OFF in localStorage before starting; DevTools docked+closed;
      terminal font; browser zoom.
- [ ] `git switch step-0` + `git status` clean + server up + one hover
      test at `step-7` then BACK to step-0 (leaves ~/.m2 warm and the clip
      fresh in your fingers).

## Likely Q&A (adapted from the proposal draft)

- **"Only VS Code?"** The browser→source half is editor-agnostic — it's one
  socket message; `code -g` works with zero editor code. The agent is ~80
  lines of Joyride; the same contract ports to any editor that can hold a
  WebSocket and move a cursor (Emacs: websocket.el + `xref--goto`).
- **"Performance?"** Two costs, both dev-only, and be precise: the
  tools.reader read + wrapping + indexing is paid per view file per
  (re)load; the render-boundary walk (`tag-tree` + the per-call wrappers)
  IS per request in dev — one linear pass over the tree, microseconds on
  this page. Prod has neither: normal loads, and nothing binds the render
  boundary — it stays `identity`.
- **"Why not a SPA framework's devtools?"** They read a live component tree
  the framework maintains in the browser. We don't ship one — the point is
  you don't need to: manufacture the map at load time instead.
- **"What about `(for …)` iteration N?"** Can't — one call site, N renders;
  they're intentionally the same family. If instances must be told apart,
  that's data identity, not source identity: put an id in your markup.
- **"Macros that generate Hiccup?"** Honest answer: syntax-quote strips
  reader positions (verified — the expansion's meta is `nil`), so
  syntax-quoted macro output is invisible to the *element* layer; clicks
  fall back to the nearest tagged ancestor, and the *component* layer still
  tags the calling fn's root via the var. Only an unquoted literal in a
  macro body keeps its position. Components composed via `->` lose
  call-site tags (the guard refuses) but keep everything else.
- **"Why not ClojureStorm / FlowStorm?"** Different tool: Storm records
  *execution* (we use it for a construction-view tracer in the book — see
  ch. 16–17). This is a *static* thread from pixels to source; it needs no
  compiler swap and costs nothing at runtime. They compose beautifully,
  and that tracer talk is the sequel.
- **"Hiccup compiles some literals — does instrumentation break it?"** We
  never touch hiccup's compiler: tag-tree runs on the data before
  stringification in dev, and in prod nothing runs at all.
- **"Security of the dev socket?"** Three layers, each for a different
  attacker: the network boundary (nothing is published outside the compose
  network; running bare, tighten the `0.0.0.0` bind back to loopback),
  `resolve-src` (what a peer may name), and the Origin gate (who may speak —
  WebSockets aren't same-origin-restricted, so without it any page in your
  own browser could connect; that's the webpack/Vite dev-server CVE class).
  Dev-only either way; don't expose it.
- **"I serve htmx fragments, not full pages — where does `*render-boundary*` go?"**
  At the render boundary: wherever hiccup meets the stringifier. This app
  has one (the layout); if you render fragments from several endpoints,
  funnel them through one `render` helper and tag there — the rule is one
  boundary per stringify, not one per app.
- **"My views are `defmethod`s / built by a def-macro?"** Then both
  directions go quiet for them: `defn-form?` only knows `defn`/`defn-`, and
  `instrument-var!` gates on `fn?` (false for MultiFn). Plain-`defn` views
  are the demo's and the book app's convention; extending the recognizer
  and the gate is a genuinely good first PR.
- **"The reverse highlight while my buffer is dirty?"** The index holds
  on-disk spans, so unsaved edits drift until you save — the watcher
  re-indexes on save. Everyday practice (save-driven views) makes this
  invisible; it's still worth saying out loud.
- **"Eval-driven teams?"** The discipline rule ("the watcher owns view
  loads") really does mean no alt-Enter on view defns — a single-form eval
  strips that fn's tags just like the buffer-load demo. The structural fix
  is to make the editor's load path go *through* the loader — an nREPL
  middleware routing view-namespace `load-file`/eval through `tr-load!` —
  which the single-source-of-truth rule begs for; neither the demo nor the
  book builds it yet.
- **"The abstract said hover-to-jump."** Precisely: hover shows (box +
  breadcrumb), click jumps. You want the click — hover-jumping would yank
  your editor around on every mouse move.
