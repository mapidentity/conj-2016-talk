#!/usr/bin/env bash
# run-tag.sh <step-branch> : detached-checkout the demo at <step>, boot it, capture, kill.
set -u
STEP="$1"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO="$(cd "$HERE/../.." && pwd)/demo"
LOG="${TMPDIR:-/tmp}/demo-server.log"
PORT="${CAPTURE_PORT:-8090}"   # not 8080: never collide with (or capture) the REPL's server
export PORT                    # honoured by demo.main, and by capture.cjs
MARK="demo-run-tag"   # tag on the JVM command line, so pkill finds exactly our server
MARK_RE="[d]emo-run-tag"   # regex that matches the tag but not a command line quoting this pattern
export NODE_PATH="${NODE_PATH:-$(npm root -g)}"

echo "### switch $STEP (detached)"
git -C "$DEMO" switch -q -f -d "$STEP" || { echo "switch failed"; exit 1; }

# kill any stragglers from a previous run
pkill -f "$MARK_RE" 2>/dev/null || true
sleep 1

# refuse to capture somebody else's server (anything holding the port answers
# curl below just fine — and every shot would silently be of the wrong app)
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then
  echo "port $PORT is already in use — stop that server first:"
  ss -ltnp 2>/dev/null | grep ":$PORT "
  git -C "$DEMO" switch -q -f main
  exit 1
fi

echo "### boot"
# setsid isolates the JVM's SIGURG from this shell's session
( cd "$DEMO" && setsid bash -c \
    "exec clojure -M:dev -e \"(start!)@(promise)\" $MARK" \
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
