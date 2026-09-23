# Why the demo has its own reader (and loader)

Research log, 2026-09-23. Conclusion: **the demo keeps its own reader.** The
dependency-ordered *what* comes from tools.namespace; the *how* (read with
tools.reader, rewrite, eval, instrument, index) has to be ours. Everything
below was checked against sources or run; evidence files are in
[`own-loader-evidence/`](own-loader-evidence/).

## The reasoning, short (what the talk says)

1. **The reader.** Clojure's reader records positions on lists only, never on
   vectors, and its loader hard-wires that reader (`Compiler.load` →
   `LispReader.read`, Compiler.java:8217 in 1.12.4). No var, option or hook
   swaps it. Hiccup is vectors, so we read with tools.reader ourselves.
2. **The step in between.** Call-site tagging rewrites forms *between* read and
   eval (it needs every defn name in the file first); instrumentation and the
   cursor index run after. No Clojure loader has a place for that.
3. **Why the rule is a discipline.** `clojure.core/load` is `^:redef` on
   purpose, so `require` can be routed through our loader — but editor eval
   (nREPL `load-file`/`eval`) never calls `load`. Hence "the loader is the
   single source of truth", and slide 17.

On the slides: one line each on slides 11, 16 and 17.

## Reloading: nothing to reuse for the *how*

No reloader lets you choose the reader or the per-file loader. They split by
which load path they end in:

| Reloader | Loads via | With a `load` hook |
|---|---|---|
| tools.namespace `refresh` (and component.repl, reloaded.repl, donut, clip, test-refresh) | remove-ns, then `(require n :reload)` (reload.clj:35) | tags kept (tested) |
| ring-devel `wrap-reload` + ns-tracker | `require :reload` on the next request, no unload | tags kept (tested) |
| kaocha `--watch` | beholder + tools.namespace fork, unloads | tags kept (tested) |
| Biff dev, Midje autotest | beholder / t.n scan, `require :reload`, **no unload** — the demo's design | kept (code-read) |
| cider-nrepl `refresh`, `cider-ns-reload`, Calva "Refresh Changed Namespaces", fireplace `:Require` | `require` | kept (tested) |
| **clj-reload 1.0.0** → integrant-repl ≥ 0.5.0 → Duct, Kit `reset`; cider's clj-reload op | `Compiler/load` on text (util.clj:121-124) | **lost** (tested) |
| **nREPL `load-file`/`eval`** (Calva Load File + evalOnSave, CIDER load-buffer + eval-defun, Cursive, Conjure) | `clojure.core/read` + eval of the buffer text | **lost** (tested) |
| refactor-nrepl (clj-refactor find-usages/rename) | tools.analyzer re-evaluates each form | tags become absolute `file:` URLs, instrumentation dropped |

- The shared part is real and reused: tools.namespace's tracker (scan-dirs +
  track) is used by Biff ("Adapted from clojure.tools.namespace.repl"), kaocha
  (a fork), Midje, test-refresh, ns-tracker (its parser) — and the demo.
  clj-reload is the one reimplementation; its README lists why (TNS-62…65).
- **The bigger obstacle is unloading, not the reader.** With a `load` hook,
  t.n `refresh` keeps every tag, but its remove-ns orphans `demo.main`'s
  `defonce` server atom and the running http-kit handler keeps serving
  pre-edit code. Opting `demo.main` out (`::unload false`, clj-reload
  `:no-unload`) fails: "Alias views already exists in namespace demo.main".
  The demo, Biff and Midje avoid this by never unloading.
- There is no accepted watch+reload tool: the norm is REPL-driven (Sierra's
  "save the file and call reset"; Sean Corfield on ClojureVerse, 2023:
  "refresh can break in all sorts of ways … just don't use it" — he evals
  top-level forms instead, which also strips tags).
- **Watchers**: beholder is the de-facto choice (kaocha, Biff, Clerk), but it
  goes permanently deaf when the watched root is deleted and recreated —
  exactly what a `--root` rebase does — and fires 5 callbacks for one atomic
  save. The 200 ms poll stays.

## The `^:redef` hook

- Intentional: Ambrose Bonnaire-Sergeant (core.typed) asked on 2015-10-27 to
  keep `load` redefinable "as it's such a useful extension point"; CLJ-1845
  (commit 10a74b3f) then CLJ-1851 (e1017ddc, Clojure 1.8) introduced
  `^:redef`; test `direct-linking-for-load` (a1eb4062). `^:redef` is
  documented in `*compiler-options*`'s docstring; `load` as a hook is not.
- Covers `require`/`use`/`:reload`/requiring-resolve/`-m`. Not `load-file`,
  `load-string`, nREPL, clj-reload.
- Prototype: [`load-hook.clj`](own-loader-evidence/load-hook.clj) (naive —
  needs: resolve `tr-load!` at call time, restrict to `./src`, keep
  `*pending-paths*`, capture the original as `(clojure.core$load.)`).
- Not adopted: covers what the watcher already covers, misses what bites
  (editor eval), global, and hides slide 11's explicit dispatch.

## A Clojure patch: feasible, measured, low odds

**Contributor rule:** clojure.org does not accept LLM-generated code (names
Claude explicitly). The diffs here are design evidence only; a real patch
must be written by a human who signed the CA. Process: ask.clojure.org first,
problem statement, then JIRA.

- **Design A** — `*read-positions*` var (`-Dclojure.read.positions`), checked
  in LispReader's vector/map/set/`#:ns{}` readers, mirroring ListReader, plus
  a separable `:file` hunk. [`clj-read-positions-var.diff`](own-loader-evidence/clj-read-positions-var.diff),
  ~35 lines of Java. Off: Clojure's full suite identical to baseline (1.12.4
  and master). On: every stock path (require, load-file, nREPL load-file,
  eval-defun) keeps all 365 element tags; 9 expected test failures (exact
  literal-meta assertions).
- **But on changes program behaviour**: constant literals stop being hoisted
  (`(contains? #{…} x)` 14–110× slower, rewrite-clj 2.3×); Java interop picks
  another overload silently (`(JSONArray. [1 2 3])` throws; `String/join`
  goes reflective, 28 → 1515 ns); method-size limit hits sooner (3865 → 874
  rows).
- **Design B** (better) — a compiler option
  (`-Dclojure.compiler.literal-positions`, no new var) passed by
  `Compiler.load` as a read option; the compiler adds `:file`; constant
  literals whose meta is only positions stay constants
  ([lispreader](own-loader-evidence/clj-literal-positions-option-lispreader.diff),
  [compiler](own-loader-evidence/clj-literal-positions-option-compiler.diff),
  [constant fix](own-loader-evidence/clj-constant-literal-meta.diff)).
  Restores 0 B/call and the right overloads. nREPL would need a one-line
  change to pass the option.
- **Prior art / precedent**: ask #13314 "Location data on all IObj" (2023,
  names Hiccup; Alex Miller's whole reply: "What problem are you trying to
  solve?"); CLJ-1513 (open since 2014, deflected to tools.reader); CLJ-960
  (`:column` for source maps, applied by Rich); CLJ-1079/CLJ-2420 (1.10);
  CLJ-2907 (2025, "patch welcome"); CLJ-2624 (filed by Alex: set-literal
  error 4 lines off).
- **Against**: ask #9446 — "The reader is closed to extension" (so never ask
  for a pluggable reader); CLJ-2945 (fixed 1.12.5, 2026) — core keeps reader
  metadata *off* runtime values ("unnecessary garbage"); ClojureScript elides
  reader meta from collection literals (`elide-reader-meta`, CLJS-685,
  CLJS-1001).
- **How to argue**: problem first — error locations inside literals
  (CLJ-2624), the macro asymmetry (a `.cljc` macro sees vector positions on
  CLJS, not the JVM), then tooling ("same source, different values depending
  on how it was loaded"). Off by default, dev-only, identical when off,
  constants stay constants. Draft: [`ask-clojure-draft.txt`](own-loader-evidence/ask-clojure-draft.txt)
  (verify its re-frame2 claim before posting). Odds low; 1.14 at the
  earliest.
- Even with a patch the demo keeps its loader: call sites, component names
  and the cursor index still need it, and absolute `:file` paths from
  `load-file`/editors break `dev.editor`'s relative-path check.

## Loader parity (open, not applied)

`tr-load!` is `load-file` with another reader; the only gap is the bindings
`Compiler.load` sets up. Verified on scratch copies:

| Gap | `tr-load!` today | Fix |
|---|---|---|
| `set!` in a view (e.g. `*warn-on-reflection*`) | fails on the watcher thread | bind `*warn-on-reflection*`, `*unchecked-math*`, `*data-readers*` |
| project tagged literals (`data_readers.clj`) | "No reader function for tag" (`#inst`/`#uuid` work) | bind `tr/*data-readers*`, `tr/*default-data-reader-fn*` to core's |
| stack-trace file name in view code | whatever file was loading | bind `*source-path*` |

Not needed by the demo's views; a `step-2` change if ever wanted.

## Editor eval (open)

- **Detect** (~a dozen lines, untested): from step 5 every view fn carries
  `::orig`; an editor re-def drops it. The render boundary can warn. Don't
  auto-re-tag from disk — it would undo an unsaved eval.
- **Route**: an nREPL middleware sending view `load-file`/`eval` through a
  string-based `tr-load!` — [`nrepl-tr-middleware.clj`](own-loader-evidence/nrepl-tr-middleware.clj)
  (155-line prototype; worked with nREPL 1.5.1/cider-nrepl 0.58 and
  1.7.0/0.62.2, unsaved buffers included). Must sit below cider-nrepl's
  `wrap-debug` if it uses nREPL's `::read-fn` key; breaks `#dbg` in view
  buffers (tools.reader has its own data-reader table).

## Done as a result (2026-09-23)

- `add-file-meta` removed: the reader is created with the file name
  (`(rt/indexing-push-back-reader (slurp path) 1 file)`) and stamps `:file`
  itself. Rewritten on `step-2`…`step-7` + `main` (only
  `dev/dev/inspector.clj`); every step renders byte-identical pages;
  backups at tags `backup/2026-09-23/*`. The REPL demo now prints `:file`
  first.
- Slides 11, 16, 17 each got one line of the reasoning above.
