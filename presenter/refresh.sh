#!/usr/bin/env bash
# refresh.sh [--deck-only] : re-capture the figures and rebuild the presenter deck.
#
#   bash talk/presenter/refresh.sh              # screenshots + HTML + PDF + overflow check
#   bash talk/presenter/refresh.sh --deck-only  # skip the screenshots (text-only edits)
#
# Capturing boots the demo at step-0/3/4/5/7 (detached checkouts) on port
# $CAPTURE_PORT (default 8090 — never the REPL's 8080), with a socket REPL on
# $CAPTURE_REPL_PORT (5557) and the DevTools frontend on $CAPTURE_DEVTOOLS_PORT
# (9333), so it needs those ports free and the demo working tree clean; the
# demo repo is put back on the branch it was on. Every step aborts the script
# on failure.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO="$(cd "$HERE/../.." && pwd)/demo"
STEPS=(step-0 step-3 step-4 step-5 step-7)   # the steps whose shots differ (see capture.cjs)
cd "$HERE"
export NODE_PATH="${NODE_PATH:-$(npm root -g)}"
PORT="${CAPTURE_PORT:-8090}"

capture=1
[ "${1:-}" = "--deck-only" ] && capture=0

if [ "$capture" = 1 ]; then
  if [ -n "$(git -C "$DEMO" status --porcelain)" ]; then
    echo "demo working tree is not clean — commit or stash first (capture does 'git switch -f'):" >&2
    git -C "$DEMO" status --short >&2
    exit 1
  fi
  for p in "$PORT" "${CAPTURE_REPL_PORT:-5557}" "${CAPTURE_DEVTOOLS_PORT:-9333}"; do
    if ss -ltn 2>/dev/null | grep -q ":$p "; then
      echo "capture port $p is in use — stop that process first (or set CAPTURE_PORT /" \
           "CAPTURE_REPL_PORT / CAPTURE_DEVTOOLS_PORT):" >&2
      ss -ltnp 2>/dev/null | grep ":$p " >&2
      exit 1
    fi
  done
  # remember where the demo repo was, and put it back whatever happens
  branch="$(git -C "$DEMO" symbolic-ref --short -q HEAD || echo main)"
  trap 'git -C "$DEMO" switch -q -f "$branch"; echo "### demo repo back on $branch"' EXIT

  for t in "${STEPS[@]}"; do
    echo "===== capture $t"
    # own session: the JVM's signals must not reach this shell
    setsid -w bash "$HERE/run-tag.sh" "$t" < /dev/null
  done
  n_png=$(ls "$HERE/../figures/talk/"*.png | wc -l)
  n_distinct=$(md5sum "$HERE/../figures/talk/"*.png | cut -c1-8 | sort -u | wc -l)
  if [ "$n_png" != "$n_distinct" ]; then
    echo "some figures are identical ($n_distinct distinct of $n_png) — a shot captured the wrong page" >&2
    exit 1
  fi
  echo "### $n_png figures, all distinct"
fi

echo "===== build"
python3 "$HERE/build_slides.py"        # run-sheet slide blocks -> slides.html
python3 "$HERE/build_presenter.py"
node "$HERE/topdf.cjs"
echo "===== page heights"
if node "$HERE/measure.cjs" | grep -v ' ok '; then
  echo "some pages overflow a sheet — see above" >&2
  exit 1
fi
echo "### rebuilt: talk/slides.html, talk/livecode-presenter.html + .pdf"
