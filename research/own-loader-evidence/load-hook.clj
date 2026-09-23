(ns load-hook
  "Experiment: route every view-namespace load that goes through the
  `clojure.core/load` var (i.e. any `require`, `:reload`, `:reload-all`,
  `use`) into dev.inspector/tr-load!. `clojure.core/load` is ^:redef, so
  clojure.core's own callers (load-one → load) are not direct-linked."
  (:require [clojure.java.io :as io]
            [clojure.string :as str]
            [dev.inspector :as inspector]
            [hiccup2.core :as h]))

(defonce original-load clojure.core/load)

(defn- view-resource? [^String abs-path] (str/ends-with? abs-path "views"))

(defn- project-path [^java.net.URL url]
  (when (= "file" (.getProtocol url))
    (str (.relativize (.toPath (io/file (System/getProperty "user.dir")))
                      (.toPath (io/file (.toURI url)))))))

(defn tagging-load [& paths]
  (doseq [^String path paths]
    (let [abs (if (.startsWith path "/")
                path
                (str (#'clojure.core/root-directory (ns-name *ns*)) \/ path))
          url (io/resource (str (subs abs 1) ".clj"))
          p   (when (and url (view-resource? abs)) (project-path url))]
      (if p
        (inspector/tr-load! p)
        (original-load path)))))

(defn install! [] (alter-var-root #'clojure.core/load (constantly tagging-load)) :installed)
(defn uninstall! [] (alter-var-root #'clojure.core/load (constantly original-load)) :uninstalled)

(defn tag-count
  "data-src attributes on the rendered page right now, per source file:
  {\"demo/views.clj\" n, \"demo/ui/views.clj\" m}. A file missing from the
  map lost its tags (it was loaded by the default reader)."
  []
  (let [page ((requiring-resolve 'demo.views/page) @(requiring-resolve 'demo.main/recipes) nil)
        html (str (h/html (inspector/tag-tree page)))]
    (into (sorted-map) (frequencies (map second (re-seq #"data-src=\"([^:\"]+):" html))))))
