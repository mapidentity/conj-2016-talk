# Live-coding cheatsheet — exact code per section

> Second-screen companion to `livecode-talk.md`. **Nothing here is typed on
> stage.** Every section lands with `git switch -f step-N`, and the few lines
> that carry each idea are on the slides. These blocks are the full versions
> of what each checkout brings in: reference while you talk, and a paste
> source if a checkout ever misbehaves.
>
> Code is byte-identical to the demo repo's step branches, modulo docstrings
> (some blocks shorten them).
>
> Recovery at any point: `git switch -f <end-branch-of-section>` — the watcher
> reloads everything, the browser refreshes itself, keep talking.

## §2 · The page is deaf (live reload) → `step-1` — CHECKOUT, then walk

> `git switch -f step-1` happens in §1 (after slides 4–6). Nothing here is
> typed on stage; these blocks are what landed, for reference and recovery.

**§2a CHECKOUT — `dev/dev/socket.clj`** (landed by `step-1`; slide 5 showed it):

```clojure
(ns dev.socket
  (:require
    [clojure.data.json :as json]
    [org.httpkit.server :as http]))

(defonce clients (atom #{}))

(defn broadcast! [msg]
  (let [s (json/write-str msg)]
    (doseq [ch @clients]
      (http/send! ch s))))

(defn notify-reload! []
  (broadcast! {:type "reload"}))

(defn ws-handler [req]
  (http/as-channel req
    {:on-open (fn [ch] (swap! clients conj ch))
     :on-close (fn [ch _] (swap! clients disj ch))}))
```

**§2b CHECKOUT — `dev/dev/watcher.clj`** (landed by `step-1`; its loop is slide 4):

```clojure
(ns dev.watcher
  "Polls src/, dev/, resources/ and static/ for changes, reloads the Clojure
  that changed, and tells browsers to reload once per batch.

  What to load, and in what order, comes from clojure.tools.namespace: it
  reads the ns forms, so a changed namespace reloads together with
  everything that depends on it."
  (:require
    [clojure.java.io :as io]
    [clojure.string :as str]
    [clojure.tools.namespace.dir :as ns-dir]
    [clojure.tools.namespace.file :as ns-file]
    [clojure.tools.namespace.track :as ns-track]
    [dev.socket :as socket]))

;; --- change detection: poll modified times under the watched dirs ---
;; (a real app uses java.nio's WatchService; polling behaves the same on
;; every OS. Assets are watched too: a .css/.js edit reloads the browser
;; without loading anything into the JVM)

(def ^:private source-dirs ["src" "dev"])

(defn- watched? [path]
  (let [n (.getName (io/file path))]
    (and (not (str/starts-with? n "."))
         (or (str/ends-with? n ".clj")
             (str/ends-with? n ".css")
             (str/ends-with? n ".js")))))

(defn- modified-times []
  (into {}
    (comp (mapcat #(file-seq (io/file %)))
          (filter #(.isFile ^java.io.File %))
          (map (juxt #(.getPath ^java.io.File %)
                     #(.lastModified ^java.io.File %))))
    ["src" "dev" "resources" "static"]))

;; --- loading: the tracker decides what to load, and in what order ---

(defonce tracker (atom (ns-track/tracker)))

(defn- project-path [^java.io.File f]     ; the tracker reports absolute files
  (str (.relativize (.toPath (io/file (System/getProperty "user.dir")))
                    (.toPath f))))

(defn- load-one! [path]
  (try
    (load-file path)
    (println "reloaded" path)
    true
    (catch Throwable e
      (println "reload FAILED" path "—" (.getMessage e))
      false)))

(defn- reload-clojure! []
  (if-let [t (try (ns-dir/scan-dirs @tracker source-dirs)
                  (catch Throwable e
                    (println "scan FAILED —" (.getMessage e))
                    nil))]
    (let [paths (into {} (map (fn [[f n]] [n (project-path f)]))
                      (::ns-file/filemap t))
          [loaded ok?] (reduce (fn [[loaded _] ns-sym]
                                 (if-let [path (paths ns-sym)]
                                   (if (load-one! path)
                                     [(conj loaded ns-sym) true]
                                     (reduced [loaded false]))
                                   [(conj loaded ns-sym) true]))
                               [[] true]
                               (::ns-track/load t))]
      ;; drain only what loaded: a file that failed stays pending and is
      ;; retried on the next scan instead of being forgotten
      (reset! tracker (update t ::ns-track/load #(drop (count loaded) %)))
      ok?)
    false))

(defn- prime-tracker! []                  ; at boot everything is already loaded
  (reset! tracker (-> (ns-dir/scan-dirs (ns-track/tracker) source-dirs)
                      (assoc ::ns-track/load () ::ns-track/unload ()))))

(defonce watcher (atom nil))

(defn start-watcher! []
  (when-not @watcher
    (prime-tracker!)
    (reset! watcher
      (doto (Thread.
              (fn []
                (loop [seen (modified-times)]
                  (Thread/sleep 200)
                  (let [current (modified-times)
                        changed (for [[path t] current
                                      :when (and (not= t (get seen path))
                                                 (watched? path))]
                                  path)]
                    (when (seq changed)
                      ;; Clojure goes through the tracker (dependency order);
                      ;; assets need no load at all
                      (when (if (some #(str/ends-with? % ".clj") changed)
                              (reload-clojure!)
                              true)
                        (socket/notify-reload!)))
                    (recur current)))))
        (.setDaemon true)
        (.start)))
    (println "watching src/ + dev/ + resources/ + static/")))
```

**§2c CHECKOUT — `static/dev/reload.js`** (landed by `step-1`; slide 6):

```js
// Dev-only: refresh the page when the server says the source reloaded.
(function () {
  function connect() {
    var ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/dev/ws');
    ws.onmessage = function (e) {
      var m = JSON.parse(e.data);
      if (m.type === 'reload') location.reload();
    };
    ws.onclose = function () { setTimeout(connect, 1000); };
  }
  connect();
})();
```

**§2d CHECKOUT — the wiring** (landed by `step-1`; `dev-body` is slide 6):

`dev/dev/core.clj` (new file) — the composition root: the dev routes, the
render boundary, and `start!`:

```clojure
(ns dev.core
  (:require
    [dev.socket :as socket]
    [dev.static :as static]
    [dev.watcher :as watcher]
    [demo.main :as main]
    [demo.views :as views]))

;; --- the dev middleware: the app, wrapped ---

(defn- dev-body
  "What the app's render boundary does in dev: the page, plus the dev
  scripts."
  [body]
  (list body
        [:script {:src "/dev/reload.js"}]))

(defn- dev-route
  "The dev endpoints, then anything under static/ — the dev scripts among
  them. nil for whatever is left, which is the app's."
  [req]
  (case (:uri req)
    "/dev/ws" (socket/ws-handler req)
    (static/file (:uri req))))

(defn wrap-dev
  "Middleware around the app: answers the dev endpoints, and renders every
  other request with the render boundary bound to dev-body."
  [handler]
  (fn [req]
    (or (dev-route req)
        (binding [views/*render-boundary* dev-body]
          (handler req)))))

(defn start!
  "Starts the app wrapped in the dev middleware, then the watcher."
  []
  (main/start! (wrap-dev #'main/app))
  (watcher/start-watcher!))
```

`src/demo/main.clj` — the app's `start!` takes the handler to serve:

```clojure
(defn start!
  ([] (start! #'app))
  ([handler]
   (if @server
     (println (str "already running on http://localhost:" port))
     (do (reset! server (http/run-server handler {:ip "0.0.0.0" :port port}))
         (println (str "listening on http://localhost:" port))))))
```

`src/demo/views.clj` — the app's one seam, above `layout`; in `layout`,
`[:body body]` → `[:body (*render-boundary* body)]`:

```clojure
(def ^:dynamic *render-boundary* identity)
```

`dev/user.clj` — `start!` now goes through the middleware:
`'demo.main/start!` → `'dev.core/start!`.

REPL after wiring (one bootstrap: reload the app, reload the helpers, restart
the server wrapped — from here the watcher owns saves; §4's REPL call is a
demo, not a load path):

```clojure
(require 'demo.main :reload-all)
(load-file "dev/user.clj")
(restart!)
```

…then hard-refresh the browser once so it picks up `reload.js`.

**Demo:** change `.badge` color in `resources/style.css`, save → instant.

## §3 · The insight → slides 9–10 (the three facts behind them)

```clojure
(meta (read-string "[:div [:span 42]]"))
;; => nil
```

```clojure
(require '[clojure.tools.reader :as tr]
         '[clojure.tools.reader.reader-types :as rt])

(let [form (tr/read (rt/indexing-push-back-reader "[:div [:span 42]]"))]
  {:outer (meta form) :inner (meta (nth form 1))})
;; => {:outer {:line 1, :column 1, :end-line 1, :end-column 18},
;;     :inner {:line 1, :column 7, :end-line 1, :end-column 17}}
```

```clojure
(def render (eval '(fn [xs] (mapv (fn [x] ^{:line 9} [:li x]) xs))))
(map meta (render [1 2 3]))
;; => ({:line 9} {:line 9} {:line 9})
```

## §4 · Keep the structure → `step-2`

**§4a CHECKOUT — `dev/dev/inspector.clj` (new file), ns + gate set:**

```clojure
(ns dev.inspector
  (:require
    [clojure.string :as str]
    [clojure.tools.reader :as tr]
    [clojure.tools.reader.reader-types :as rt]))

(def ^:private html-tags
  #{"a" "abbr" "address" "article" "aside" "audio" "b" "blockquote" "body"
    "br" "button" "canvas" "caption" "cite" "code" "col" "colgroup" "dd"
    "details" "dfn" "dialog" "div" "dl" "dt" "em" "fieldset" "figcaption"
    "figure" "footer" "form" "h1" "h2" "h3" "h4" "h5" "h6" "head" "header"
    "hr" "html" "i" "iframe" "img" "input" "ins" "kbd" "label" "legend" "li"
    "link" "main" "mark" "menu" "meta" "nav" "ol" "optgroup" "option" "output"
    "p" "picture" "pre" "progress" "q" "s" "samp" "script" "section" "select"
    "small" "source" "span" "strong" "style" "sub" "summary" "sup" "table"
    "tbody" "td" "template" "textarea" "tfoot" "th" "thead" "time" "title"
    "tr" "u" "ul" "video"
    ;; SVG
    "svg" "g" "path" "circle" "rect" "line" "polyline" "polygon" "text"
    "ellipse" "defs" "stop" "use" "symbol"})
```

**§4b CHECKOUT** (the gate — its first user is `tag-tree`, §5):

```clojure
(defn element?
  "True when x is a Hiccup element vector — an unnamespaced HTML/SVG tag
  keyword head (`.class`/`#id` suffixes allowed)."
  [x]
  (and (vector? x)
       (keyword? (first x))
       (nil? (namespace (first x)))
       (contains? html-tags (first (str/split (name (first x)) #"[.#]")))))
```

**§4c CHECKOUT** (told the file name, the reader stamps `:file` itself — slide 11):

```clojure
(defn tr-load!
  "load-file, except every Hiccup element literal keeps its source position."
  [path]
  (let [file  (str/replace path #"^src/" "")
        rdr   (rt/indexing-push-back-reader (slurp path) 1 file)
        eof   (Object.)
        read1 #(tr/read {:eof eof} rdr)]
    (binding [*ns* *ns*, *file* file]
      (eval (read1))   ; the ns form FIRST — ::aliases resolve at read time
      (let [body (loop [acc []]
                   (let [form (read1)]
                     (if (identical? form eof) acc (recur (conj acc form)))))]
        (doseq [form body]
          (eval form))))))
```

**§4d CHECKOUT — `dev/dev/watcher.clj`** (deliver the "only path that loads
views" beat out loud): require `[dev.inspector :as inspector]`; insert
`view-file?` + `load-views!` above `tracker`, teach `load-one!` to route
views, and re-tag after any non-view load. The tracker still decides *what*
loads and in what order — this only decides *how*:

```clojure
(defn- view-file?
  "True for a view namespace — by filename alone: anything ending in
  views.clj. Naive by design. Replace this by logic that fits your own
  architecture."
  [path]
  (str/ends-with? path "views.clj"))

(defn load-views!
  "tr-load! every view namespace, so tags exist from boot — not only after
  the first save."
  []
  (doseq [f (file-seq (io/file "src"))
          :when (and (.isFile ^java.io.File f) (view-file? (.getPath ^java.io.File f)))]
    (inspector/tr-load! (.getPath ^java.io.File f))))

;; …in load-one!, the one line that routes views through the loader:
(if (view-file? path)
  (inspector/tr-load! path)
  (load-file path))

;; …in reload-clojure!, right after the batch: the views were COMPILED by
;; the loader and no ns form records that, so re-tag them whenever anything
;; else was loaded — the loader itself included.
(when (and ok?
           (some #(when-let [path (paths %)] (not (view-file? path))) loaded))
  (load-views!))
```

…and in `dev.clj`'s `start!`: `(watcher/load-views!)` as the *first* line —
before the server starts, so no request can ever be served from untagged views.
That re-tag in `reload-clojure!` is what keeps the rest of the talk honest:
every later section edits the *engine* and the views re-tag themselves.

**Demo — REPL:**

```clojure
(dev.watcher/load-views!)
(meta (demo.views/recipe-card (first demo.main/recipes)))
;; => {:file "demo/views.clj", :line 14, :column 3, :end-line 31, :end-column 64}
```

(the reader stamps `:file` **first**, then the position)

## §5 · Carry it to the DOM → `step-3`

**§5a CHECKOUT — `inspector.clj`:**

```clojure
(defn tag-tree
  "Walk an assembled Hiccup tree just before it becomes HTML, turning each
  element's source metadata into real attributes."
  [node]
  (cond
    (vector? node)
    (let [m (meta node)
          children (mapv tag-tree node)]
      (if (and (:line m) (:file m) (element? node))
        (let [has-attrs? (map? (second children))
              attrs (if has-attrs? (second children) {})
              body (subvec children (if has-attrs? 2 1))]
          (into [(first children)
                 (assoc attrs
                   :data-src (str (:file m) ":" (:line m) ":" (or (:column m) 1))
                   :data-name (first (str/split (name (first node)) #"[.#]")))]
                body))
        children))

    (seq? node) (doall (map tag-tree node))

    :else node))
```

**§5b CHECKOUT — `dev.clj`, in `dev-body`:** `body` → `(inspector/tag-tree body)`:

```clojure
(defn- dev-body
  [body]
  (list (inspector/tag-tree body)
        [:script {:src "/dev/reload.js"}]))
```

That is the whole hook — not a line in the app. `wrap-dev` binds the app's
render boundary to `dev-body` per request; in prod nothing binds it, and
nothing could: the walk is not on the classpath.

**Demo:** save → DevTools on the crooked spicy pill →
`<span class="badge hot" data-src="demo/views.clj:21:8">` — and scroll to a
star: `data-src="demo/ui/views.clj:23:4"`. Two namespaces, correctly told
apart, element by element.

## §6 · Overlay + click→editor → `step-4`

**§6a CHECKOUT — the overlay:**

```
git restore -s step-4 -- static/dev/inspector.js
```

No route to add — `dev-route` already serves anything under `static/`. Just
the script tag in `dev-body`:

```clojure
  (list (inspector/tag-tree body)
        [:script {:src "/dev/reload.js"}]
        [:script {:src "/dev/inspector.js"}]))
```

Walk these three in the JS (60–90s max): `chain` (ancestors with `data-src`),
`sendOpen` (peel `file:line:col`, send `{type: "open"}`), the capturing
`click` handler (swallows the app's click while inspecting).

**§6b CHECKOUT — two files.** First `dev/dev/socket.clj` gains the peer
gate (`send1!` after `notify-reload!`, `origin-ok?` before `ws-handler`);
then `dev/dev/editor.clj` is a **new file** holding the relay
(the trust boundary + the naive bridge — slide 13):

```clojure
(defn send1! [ch msg]
  (http/send! ch (json/write-str msg)))
```

```clojure
(ns dev.editor
  (:require
    [clojure.java.io :as io]
    [clojure.java.shell :as shell]
    [clojure.string :as str]
    [dev.socket :as socket]))

(defn- resolve-src
  "The trust boundary: a browser can send any string. Canonicalize and
  confine it to the project's src/ tree, .clj only — or nil."
  ^java.io.File [src]
  (let [root (.getCanonicalFile (io/file "src"))
        f (.getCanonicalFile (io/file root (str src)))]
    (when (and (.exists f)
               (str/ends-with? (.getName f) ".clj")
               (.startsWith (.toPath f) (.toPath root)))
      f)))
```

**§6c CHECKOUT — `editor.clj`** (the relay's other half; the dispatch
block below goes right after it):

```clojure
(defn- handle-open! [ch {:keys [src line col]}]
  (if-let [f (resolve-src src)]
    (try
      (shell/sh "code" "-g" (str (.getPath f) ":" line ":" col))
      (socket/send1! ch {:type "open-result" :ok true})
      (catch Exception e
        (socket/send1! ch {:type "open-result" :ok false :error (.getMessage e)})))
    (socket/send1! ch {:type "open-result" :ok false :error (str "unresolved: " src)})))
```

…and the peer gate in `socket.clj`, right before `ws-handler`:

```clojure
(defn- origin-ok?
  "The PEER trust boundary (dev.editor/resolve-src is the path one). Browsers always
  send Origin on a WebSocket handshake — sockets aren't same-origin
  restricted, so any page you have open could try — accept only our own.
  Native clients (the editor agent, curl) send no Origin at all."
  [req]
  (let [origin (get-in req [:headers "origin"])]
    (or (nil? origin)
        (= (get-in req [:headers "host"])
           (str/replace origin #"^https?://" "")))))
```

**§6d CHECKOUT — the dispatch** (the shape slide 13 shows; it goes in
`editor.clj`, after `handle-open!` — and it is public: the composition root
hands it to the socket):

```clojure
(defn handle-msg! [ch msg]
  (case (:type msg)
    "open" (handle-open! ch msg)
    nil))
```

…and `ws-handler` in `socket.clj` grows the origin gate and
takes the dispatch as an argument — the hub never learns what messages
mean):

```clojure
(defn ws-handler [req handle-msg!]
  (if-not (origin-ok? req)
    {:status 403 :headers {"Content-Type" "text/plain"} :body "forbidden origin"}
    (http/as-channel req
    {:on-open (fn [ch] (swap! clients conj ch))
     :on-receive (fn [ch raw] (handle-msg! ch (json/read-str raw :key-fn keyword)))
     :on-close (fn [ch _] (swap! clients disj ch))})))
```

…and in `dev.clj` wire the two together — `"/dev/ws"` becomes
`(socket/ws-handler req editor/handle-msg!)`, with `[dev.editor :as
editor]` required.

**Demo:** Alt+Shift+I → hover → click the spicy pill → editor at views.clj 21:8. Then
fix it: delete `position: relative; top: .45rem;` from `.badge.hot` in `style.css`,
save. (Straightening `.badge` instead would shove the NEW badge too — the element's
own line is what tells you `.hot` is the right hook.)

## §7 · Components → `step-5`

**§7a CHECKOUT — `inspector.clj`** (insert above `tag-tree`; `instrument-var!`
comes right after it):

```clojure
(defn tag-hiccup
  "Add source attributes to a Hiccup element vector, else return it
  unchanged. An already-tagged element is left alone, so the innermost
  component's location wins."
  [h src nm]
  (if (and (element? h)
           (not (and (map? (second h)) (contains? (second h) :data-src))))
    (let [has-attrs? (map? (second h))
          attrs (if has-attrs? (second h) {})
          children (subvec h (if has-attrs? 2 1))]
      (into [(first h) (assoc attrs :data-src src :data-name nm)] children))
    h))
```

**§7b CHECKOUT** (the var's-meta trick + `::orig` idempotence — slide 14):

```clojure
(defn instrument-var!
  "Wrap a view fn so the root element it returns carries the var's source
  location (data-src = the defn site) and name (data-name = ns/fn).
  Idempotent — unwraps to the original before re-wrapping on a reload."
  [v]
  (let [cur @v]
    (when (fn? cur)
      (let [orig (or (::orig (meta cur)) cur)
            m (meta v)
            src (str (:file m) ":" (:line m) ":" (or (:column m) 1))
            nm (str (ns-name (:ns m)) "/" (:name m))
            wrapped (with-meta
                      (fn [& args] (tag-hiccup (apply orig args) src nm))
                      {::orig orig})]
        (alter-var-root v (constantly wrapped))))))
```

**§7b′ CHECKOUT:**

```clojure
(defn instrument-ns!
  "Source-tag every fn the namespace defines — safe to blanket-apply,
  tag-hiccup passes non-Hiccup returns through."
  [ns-sym]
  (doseq [[_ v] (ns-interns ns-sym)
          :when (and (var? v) (fn? @v))]
    (instrument-var! v)))
```

**§7c CHECKOUT — in `tr-load!`, after the `doseq`:**

```clojure
        (instrument-ns! (ns-name *ns*))
```

**Demo:** save `inspector.clj` — the watcher reloads the engine AND re-tags
the views (that's §4d's re-tag in `reload-clojure!` earning its keep; the
terminal shows both reloads). Hover:
`page ▸ section ▸ recipe-card ▸ h2 ▸ span`; click a card root → the
`defn recipe-card` line.

## §8 · The reverse direction → `step-6`

**§8a CHECKOUT — `inspector.clj`, above `tr-load!`:**

```clojure
;; --- the reverse direction: editor cursor -> on-screen element ---
;; The same tools.reader pass that powers the forward tags also builds a
;; span index. resolve-cursor produces the SAME strings the DOM carries
;; (data-name / data-src), so the browser match is an attribute selector.

(defonce view-index (atom {}))

(defn- form-span [form]
  (let [{:keys [line column end-line end-column]} (meta form)]
    (when (and line column end-line end-column)
      [line column end-line end-column])))

(defn- src-key [file [line column]]
  (str file ":" line ":" (or column 1)))

(defn- defn-form? [form]
  (and (seq? form)
       (symbol? (first form))
       (contains? #{"defn" "defn-"} (name (first form)))
       (symbol? (second form))))

(defn- collect-elements
  "Depth-first {:key :span} for every element literal in form."
  [file form]
  (cond
    (and (vector? form) (element? form) (form-span form))
    (cons {:key (src-key file (form-span form)) :span (form-span form)}
          (mapcat #(collect-elements file %) form))
    (coll? form) (mapcat #(collect-elements file %) form)
    :else nil))

(defn index-ns!
  "Build the reverse index for file from its read top-level forms: each
  defn's span, and every element literal's span inside one."
  [file ns-sym forms]
  (let [defns (filter defn-form? forms)]
    (swap! view-index assoc file
      {:defns (vec (keep (fn [f]
                           (when-let [span (form-span f)]
                             {:name (str ns-sym "/" (second f)) :span span}))
                         defns))
       :elements (vec (mapcat #(collect-elements file %) defns))})))

(defn- contains-pos?
  "Inclusive start, exclusive end (tools.reader's :end-column is one past
  the last character)."
  [[l c el ec] line col]
  (and (or (< l line) (and (= l line) (<= c col)))
       (or (< line el) (and (= line el) (< col ec)))))

(defn- innermost [items line col]
  (->> items
       (filter #(contains-pos? (:span %) line col))
       (sort-by (fn [{[l c el ec] :span}] [(- el l) (- ec c)]))
       first))
```

**§8b CHECKOUT:**

```clojure
(defn resolve-cursor
  "Map an editor cursor to the strings the DOM carries: the enclosing defn
  (:component matches data-name) and the innermost element literal under
  the cursor (:element matches data-src). nil outside any view defn."
  [file line col]
  (when-let [{:keys [defns elements]} (get @view-index file)]
    (when-let [d (innermost defns line col)]
      {:component (:name d)
       :element (:key (innermost elements line col))})))
```

…and in `tr-load!`, after `instrument-ns!`:

```clojure
        (index-ns! file (ns-name *ns*) body)
```

**§8c CHECKOUT — the glue (relay roles, editor push, highlight JS, agent):**

```
git restore -s step-6 -- dev/ static/dev/inspector.js .joyride/scripts/workspace_activate.cljs
```

Then show the `socket.clj` + `editor.clj` diff (45s): clients get roles (`hello`/`cursor` mark
an editor); `handle-cursor!` = confine path → `resolve-cursor` → broadcast
`highlight`; `handle-open!` now *pushes* to a connected editor (exact window,
via the agent) with `code -g` demoted to fallback. Show the Joyride script
(30s): ClojureScript in the extension host; reports the cursor debounced,
receives opens, reconnects on close *and* error. Run
**"Joyride: Run Workspace Script"** to connect it (the file only exists from
this checkout on — that's why setup couldn't run it).

No manual re-index needed: saving `inspector.clj` after §8b already re-tagged
and re-indexed the views, and the checkout's `dev.clj` reload did it again.

**Demo cursor positions** (verified against `step-6`):

| put cursor on | expect |
| --- | --- |
| `views.clj` 22 `[:p description]` | 9 green boxes — every card's description, featured included |
| `views.clj` 19 `[:span.badge "NEW"]` | the three NEW badges (two grid + featured) — the spicy pills beside them stay dark |
| `views.clj` 21 `[:span.badge.hot …]` | the three spicy pills (Pad Thai ×2 + tacos); the NEW badges stay dark |
| `ui/views.clj` 23, inside `star`'s body | **all 45 stars light** — the cursor is in the UI-KIT file, driving elements another namespace rendered |
| inside `layout` (bottom of `views.clj`) | nothing lights, nothing breaks (string root) |

## §9 · Call sites → `step-7` — CHECKOUT only

```
git switch -f step-7
```

Self-healing: the checkout changes `inspector.clj` (+ the overlay JS); the
watcher loads the new engine in dependency order, the re-tag after the batch
restores the view tags, and ONE reload lands in the browser — `data-callsite`
is in the DOM with no manual step (watch the terminal print the reloads).

Show on screen, don't type: `tag-callsite`, `wrap-callsites` (the
`no-wrap-heads` guard + `(meta form)` re-attachment), `call-head` (one
sentence: unqualified calls this file defines, plus alias-qualified calls
that resolve to a fn from any views namespace — that's how `(ui/rating …)`
gets a call site), `collect-calls`, `:callsite` in `resolve-cursor`, and in
`tr-load!` the eval line now reads
`(eval (wrap-callsites names file form true))`.

**Demo cursor positions** (verified against `step-7`; in `views.clj` unless noted):

| put cursor on | expect |
| --- | --- |
| line 81 `(recipe-card r)` — the grid `for` | the 8 grid cards light; **the featured card does NOT** |
| line 38 `(recipe-card r)` — inside `featured` | **only** the featured card |
| line 73 `(ui/stat "cooks" 7)` | exactly ONE stat |
| line 24 `(ui/rating stars)` | all 9 ratings — a cross-namespace call site |
| hover a star in the featured card (forward) | `page ▸ featured () λ ▸ recipe-card () λ ▸ div ▸ div ▸ rating () λ ▸ star () λ` — and `rating`'s `()` points at `demo/views.clj` while its `λ` points at `demo/ui/views.clj`: two files on one crumb |

## §10 · Sharp edge + prod

Sharp edge (live): Calva **"Load/Evaluate buffer"** on `views.clj`, then
**refresh the browser** (the current DOM was rendered from tagged views and
still carries the attributes — the next render is the naked one; no file
changed, so the watcher won't refresh for you) → hover a card body: dead.
Hover a star: still alive — only the file you bypassed died, `ui/views.clj`
was never re-evaled. That partial deadness is exactly how it presents at
home, which is why it's so baffling. Recover: **make a whitespace edit in
`views.clj`, then save** — the buffer is CLEAN after a Calva load and saving
an unmodified buffer writes nothing, so a bare Ctrl+S would silently do
nothing. The watcher then tr-loads and reloads the page on its own.

Joyride plan B (if the agent won't connect — drive the reverse from the REPL):

```clojure
(#'dev.editor/handle-cursor! {:file "demo/ui/views.clj" :line 23 :col 5})
```

Prod beat (REPL):

```clojure
demo.views/*render-boundary*
;; => #function[clojure.core/identity]   — the app's seam; outside a dev request, even here
(clojure.java.io/resource "demo/dev.clj")
;; => #object[java.net.URL … "file:/…/dev/core.clj"]   — dev/, the :dev alias only
```

Stretch-only (boots a second JVM, ~10s — prod, for real):

```
clojure -M -e "(require 'dev.inspector)"
;; => Could not locate demo/inspector__init.class, demo/inspector.clj … on classpath.
clojure -M -e "(require 'demo.main) (println (re-find #\"data-src|/dev/\" (:body (demo.main/app {:uri \"/\"}))))"
;; => nil
```

## Useful at any moment

```
git switch -f step-N            # full recovery to a section's end state
git restore -s step-N -- FILE   # surgical recovery of one file
git diff step-3 step-4 --stat   # "what lands in this section"
```
