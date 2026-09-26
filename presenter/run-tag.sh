#!/usr/bin/env bash
# run-tag.sh <step-branch> : detached-checkout the demo at <step>, boot it, capture, kill.
#
# The JVM also opens a socket REPL on $CAPTURE_REPL_PORT (5557): some shots
# type forms there before a reload, as the speaker would at the REPL — the §1
# (load-file …) of an edited views.clj at step-0, and the §10 plain load that
# strips the tags at step-7 (see capture.cjs). The DevTools shots (step-0,
# step-3) need $CAPTURE_DEVTOOLS_PORT (9333) for the DevTools frontend, and
# one of them a private Xvfb display (xvfb-run -n 99 -a; never :0).
set -u
STEP="$1"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO="$(cd "$HERE/../.." && pwd)/demo"
LOG="${TMPDIR:-/tmp}/demo-server.log"
PORT="${CAPTURE_PORT:-8090}"   # not 8080: never collide with (or capture) the REPL's server
export PORT                    # honoured by demo.main, and by capture.cjs
REPL_PORT="${CAPTURE_REPL_PORT:-5557}"          # the capture JVM's socket REPL
DEVTOOLS_PORT="${CAPTURE_DEVTOOLS_PORT:-9333}"  # the DevTools frontend (capture.cjs)
export CAPTURE_REPL_PORT="$REPL_PORT" CAPTURE_DEVTOOLS_PORT="$DEVTOOLS_PORT"
MARK="demo-run-tag"   # tag on the JVM command line, so pkill finds exactly our server
MARK_RE="[d]emo-run-tag"   # regex that matches the tag but not a command line quoting this pattern
export NODE_PATH="${NODE_PATH:-$(npm root -g)}"

echo "### switch $STEP (detached)"
git -C "$DEMO" switch -q -f -d "$STEP" || { echo "switch failed"; exit 1; }

# kill any stragglers from a previous run
pkill -f "$MARK_RE" 2>/dev/null || true
sleep 1

# refuse to capture somebody else's server (anything holding the port answers
# curl below just fine — and every shot would silently be of the wrong app);
# likewise a busy REPL port (the forms would reach another JVM) or DevTools
# port (the frontend would inspect another browser)
for p in "$PORT" "$REPL_PORT" "$DEVTOOLS_PORT"; do
  if ss -ltn 2>/dev/null | grep -q ":$p "; then
    echo "port $p is already in use — stop that process first:"
    ss -ltnp 2>/dev/null | grep ":$p "
    git -C "$DEMO" switch -q -f main
    exit 1
  fi
done

echo "### boot"
# setsid isolates the JVM's SIGURG from this shell's session. The -J option
# must come before -M:dev: after it, clojure takes it for a script path.
( cd "$DEMO" && setsid bash -c \
    "exec clojure -J-Dclojure.server.repl='{:port $REPL_PORT :accept clojure.core.server/repl}' -M:dev -e \"(start!)@(promise)\" $MARK" \
    >"$LOG" 2>&1 </dev/null & )

echo "### wait for :$PORT"
ok=0
for i in $(seq 1 90); do
  if curl -sf -o /dev/null http://127.0.0.1:$PORT/ ; then ok=1; break; fi
  sleep 1
done
if [ "$ok" != 1 ]; then echo "server never came up; log:"; tail -30 "$LOG"; \
  pkill -f "$MARK_RE" 2>/dev/null || true; exit 1; fi
echo "### up after ${i}s"
sleep 1

echo "### capture"
node "$HERE/capture.cjs" "$STEP"
rc=$?

echo "### kill"
pkill -f "$MARK_RE" 2>/dev/null || true
sleep 1
echo "### done $STEP (capture rc=$rc)"
exit $rc
