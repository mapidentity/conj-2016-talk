(ns nrepl-tr
  "Experiment: make the editor path (nREPL load-file / eval of a form from a
  view buffer) read view files with tools.reader, from the SENT buffer text.

  One nREPL middleware, `wrap-tr`, placed above wrap-load-file and above
  whatever handles \"eval\". It never evaluates anything itself: for a
  message that concerns a view file it stashes the buffer text and replaces
  the code with a one-liner `(nrepl-tr/load-stashed! \"<key>\")` (resp.
  eval-stashed!). The rewritten message then runs through the normal pipeline
  (wrap-load-file -> cider's wrap-debug -> interruptible-eval), on the session
  thread, with the session's bindings and output capture. Whatever read-fn /
  eval-fn another middleware installs (cider's wrap-debug installs both on every
  eval with nREPL >= 1.5) only ever sees the one-liner, so the order relative
  to those middleware does not matter. The stash (rather than inlining the text
  as a string literal) sidesteps the 64K constant-pool limit that nREPL's old
  load-file-code approach hit."
  (:require [clojure.java.io :as io]
            [clojure.string :as str]
            [clojure.tools.reader :as tr]
            [clojure.tools.reader.reader-types :as rt]
            [dev.inspector :as inspector]
            [nrepl.middleware :refer [set-descriptor!]]))

;; --- string-based mirror of dev.inspector/tr-load! -------------------------

(def ^:private view-defn-names @#'inspector/view-defn-names)
(def ^:private wrap-callsites @#'inspector/wrap-callsites)

(defn tr-load-string!
  "dev.inspector/tr-load!, except the source text is passed in (the editor
  buffer, possibly unsaved) instead of slurped from disk. `file` is the
  source-root-relative path, e.g. \"demo/ui/views.clj\". Returns the value of
  the last top-level form, like load-file."
  [source file]
  (let [rdr   (rt/indexing-push-back-reader source)
        eof   (Object.)
        read1 #(tr/read {:eof eof} rdr)]
    (binding [*ns* *ns*, *file* file]
      (eval (read1))                    ; ns form first: ::aliases resolve at read time
      (let [body  (loop [acc []]
                    (let [form (read1)]
                      (if (identical? form eof) acc (recur (conj acc form)))))
            names (view-defn-names body)
            value (reduce (fn [_ form]
                            (eval (inspector/add-file-meta
                                    file (wrap-callsites names file form true))))
                          nil body)]
        (inspector/instrument-ns! (ns-name *ns*))
        (inspector/index-ns! file (ns-name *ns*) body)
        value))))

(defn- merge-index!
  "Fold the index entry of a partial eval (only the evaluated defns) into the
  file's existing entry: replaced defns (same name) drop their old spans."
  [file ns-sym forms]
  (let [old (get @inspector/view-index file)]
    (inspector/index-ns! file ns-sym forms)
    (when old
      (let [new       (get @inspector/view-index file)
            new-names (set (map :name (:defns new)))
            stale     (filter #(new-names (:name %)) (:defns old))
            inside?   (fn [{[l c] :span}]
                        (some (fn [{[dl dc el ec] :span}]
                                (and (or (< dl l) (and (= dl l) (<= dc c)))
                                     (or (< l el) (and (= l el) (< c ec)))))
                              stale))]
        (swap! inspector/view-index assoc file
               {:defns    (into (vec (remove #(new-names (:name %)) (:defns old))) (:defns new))
                :elements (into (vec (remove inside? (:elements old))) (:elements new))
                :calls    (into (vec (remove inside? (:calls old))) (:calls new))})))))

(defn tr-eval-string!
  "Evaluate code sent from a view buffer (eval-defun, eval-region) with
  tools.reader, positioned at line/column of the file, so element literals get
  their real file coordinates. Re-instruments every fn var it defines."
  [code file line column]
  (let [pad   (str (str/join (repeat (dec (or line 1)) \newline))
                   (str/join (repeat (dec (or column 1)) \space)))
        rdr   (rt/indexing-push-back-reader (str pad code))
        eof   (Object.)
        forms (binding [*file* file]
                (loop [acc []]
                  (let [form (tr/read {:eof eof} rdr)]
                    (if (identical? form eof) acc (recur (conj acc form))))))
        names (into (view-defn-names forms)
                    (keep (fn [[s v]] (when (and (var? v) (fn? @v)
                                                 (= file (:file (meta v))))
                                        (name s))))
                    (ns-interns *ns*))]
    (binding [*file* file]
      (let [value (reduce (fn [_ form]
                            (let [v (eval (inspector/add-file-meta
                                            file (wrap-callsites names file form true)))]
                              (when (and (var? v) (fn? @v))
                                (inspector/instrument-var! v))
                              v))
                          nil forms)]
        (merge-index! file (ns-name *ns*) forms)
        value))))

;; --- the middleware -----------------------------------------------------------

(defonce ^:private stash (atom {}))

(defn- stash! [x]
  (let [k (str (java.util.UUID/randomUUID))]
    (swap! stash assoc k x)
    k))

(defn- take! [k]
  (let [[old _] (swap-vals! stash dissoc k)]
    (or (get old k) (throw (ex-info "nrepl-tr: nothing stashed under key" {:key k})))))

(defn load-stashed! [k]
  (let [{:keys [source file]} (take! k)]
    (tr-load-string! source file)))

(defn eval-stashed! [k]
  (let [{:keys [code file line column]} (take! k)]
    (tr-eval-string! code file line column)))

(defn view-file
  "The source-root-relative path (\"demo/ui/views.clj\") when path names a
  view file under ./src of the JVM's cwd, else nil. Accepts the absolute path
  CIDER/Calva send, or a classpath-relative one."
  [path]
  (when (and (string? path) (str/ends-with? path "views.clj"))
    (let [src (.toAbsolutePath (.toPath (io/file (System/getProperty "user.dir") "src")))
          p   (.toPath (io/file path))
          abs (if (.isAbsolute p) p (.resolve src p))]
      (when (and (.startsWith (.normalize abs) src) (.exists (.toFile abs)))
        (str/replace (str (.relativize src (.normalize abs))) java.io.File/separatorChar \/)))))

(defn wrap-tr
  "Route view-file loads/evals sent by an editor through tools.reader."
  [h]
  (fn [{:keys [op] :as msg}]
    (h (case op
         "load-file"
         (if-let [f (view-file (:file-path msg))]
           (assoc msg :file (format "(nrepl-tr/load-stashed! %s)"
                                    (pr-str (stash! {:source (:file msg) :file f}))))
           msg)
         "eval"
         (if-let [f (and (string? (:code msg)) (view-file (:file msg)))]
           (assoc msg :code (format "(nrepl-tr/eval-stashed! %s)"
                                    (pr-str (stash! {:code (:code msg) :file f
                                                     :line (:line msg) :column (:column msg)}))))
           msg)
         msg))))

(set-descriptor! #'wrap-tr
                 {:requires #{}
                  :expects  #{"load-file" "eval"}
                  :handles  {}})
