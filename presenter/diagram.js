/* diagram.js — plays the `flow`s of ```diagram``` figures (see diagram.py) and draws the
   speaker's progress line under them. Inlined into slides.html by build_slides.py; the
   template calls axFlows.enter(slide) from show() and hands it the a and p keys
   (axFlows.play / axFlows.back). The deck/PDF never runs it: there the figure is static
   and diagram.css shows the numbered hops instead.

   Why a script and not CSS motion: one clock drives token, pill, glow, edge and the
   progress line, so "a plays the next flow", "a again restarts it", "p steps back",
   loop-with-rest, reset on arrival and prefers-reduced-motion are plain branches, not
   animation plumbing. It only ever sets a transform and toggles classes, which every
   engine has done the same way for 15 years — no offset-path, no keyframe names, no ids
   (every slide lives in one document). The geometry is precomputed by the generator:
   data-pts is the edge's own route in travel order, data-ms the hop's time,
   data-smin/-smax/-off the stretch beside the wire where its message rides.

   Navigation never plays a flow: → / Space / PageDown / click always go to the next
   slide. On a slide with flows the template passes two keys on (either case, no Ctrl /
   Cmd / Alt, no auto-repeat):
     a   nothing playing: play the flow at the cursor. Playing: restart that flow from its
         start — while its token travels. In the 0.9 s hold after it has gone in, the flow
         looks done and counts as done: a plays the next flow (the last one: replays it).
         A second a within 250 ms of the last one is a key bounce or double tap: ignored.
     p   one stop back. Playing: stop, back to the start of that flow (nothing lit). Idle
         at the start of flow k > 1: to the start of flow k-1. Idle after the last flow:
         to the start of the last flow. At the start of flow 1: nothing. So "show that
         again" is p, then a (p also clears the bounce guard, so that a always counts).
   The stops are the start of each flow plus "after the last". Arriving on a slide (any
   direction, a #N jump, a reload) puts the cursor at flow 1 with nothing playing and
   nothing lit; leaving stops everything. A flow that finishes moves the cursor to the
   next one; after the last one it stays on the last, so a replays it.

   Per slide, a class on the figure (a {.class} line before the fence) picks:
     flow-keys            only a and p play (flow-step is the same: the talk's old name)
     flow-auto (default)  the first flow plays by itself, 2 s after the cut, as if a had
                          been pressed; the rest is flow-keys (the cursor then on flow 2).
                          An a or p before or during it takes over.
     flow-loop            plays them all, GAP apart, rests 2 s, plays again while the slide
                          is up; the first a or p stops the loop and from then on it is
                          flow-keys
     flow-off             never animates: no line, the keys do nothing

   Reduced motion: nothing moves. a shows the cursor flow's numbered hops (the print
   layer) and moves the line one whole segment on; p hides them and steps back one stop.
   flow-auto shows flow 1's numbers on arrival (its "autoplay"; the line one segment on).
   flow-loop shows every flow's numbers at once on arrival (the line full); its first a
   starts over at flow 1, its first p hides them and steps back one stop.

   The progress line (look: diagram.css, .ax-prog): a hairline along the very bottom of the
   slide, as wide as the figure, one segment per flow, each as long as its flow's own time
   (the hold included), with a small dot at each boundary between two flows. Its fill runs
   from the left to where the clock is — drawn in the same render() as the token, from the
   same t — and rests on the cursor's stop while nothing plays. It is plain DOM in the
   figure, outside the SVG, built on the first visit.                                    */
(function () {
  'use strict';
  var START = 2000,  // flow-auto/-loop: after the hard cut, before autoplay: the audience finds the new parts first
      PRE = 260,     // the token waits at the first door
      DWELL = 170,   // … and at every node between hops
      HOLD = 900,    // after the last hop, the whole path stays lit (the token has gone in)
      GAP = 600,     // flow-loop: between two flows of one slide
      REST = 2000,   // flow-loop: the static picture between rounds
      BOUNCE = 250;  // a second a this soon after the last is a key bounce or double tap
  var KINDS = ['fwd', 'rev', 'warn'];
  var mq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  var S = null, raf = 0, timer = 0, frozen = null;

  function now() { return frozen !== null ? frozen : performance.now(); }
  function reduced() { return !!(mq && mq.matches); }
  function ease(p) { return 0.5 - 0.5 * Math.cos(Math.PI * p); }
  function sel(svg, cls, id) { return svg.querySelector('.' + cls + '[data-flow="' + id + '"]'); }
  function nums(h, a) { return (h.getAttribute(a) || '').split(',').map(Number); }

  function parseFlow(g) {
    var svg = g.ownerSVGElement, id = g.getAttribute('data-flow');
    var kind = (/ax-f-(\w+)/.exec(g.getAttribute('class')) || [0, 'fwd'])[1];
    var under = sel(svg, 'ax-flow-under', id), glows = under ? under.querySelectorAll('.ax-hglow') : [];
    var t = PRE, prev = null;
    var hops = [].map.call(g.querySelectorAll('.ax-hop'), function (h, j) {
      var pts = h.getAttribute('data-pts').split(' ').map(function (p) { return p.split(',').map(Number); });
      var cum = [0];
      for (var k = 1; k < pts.length; k++) cum.push(cum[k - 1] + Math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]));
      var pid = h.getAttribute('data-pill'), mp = h.querySelector('.ax-mpill');
      var hop = {
        pts: pts, cum: cum, len: cum[cum.length - 1], ms: +h.getAttribute('data-ms'),
        // the edge's line group and its label group (a layer above the tokens) light together
        edges: [].slice.call(svg.querySelectorAll('.ax-edge[data-ax="' + h.getAttribute('data-edge') + '"]')),
        pill: pid ? svg.querySelector('.ax-pill[data-ax="' + pid + '"]') : null,   // the static twin
        mp: mp, smin: +h.getAttribute('data-smin') || 0, smax: +h.getAttribute('data-smax') || 0,
        off: mp ? nums(h, 'data-off') : [0, 0],
        glow: glows[j] || null,
        // the next hop leaves from another side of the box: hide the token while it is "inside"
        jump: prev ? Math.hypot(pts[0][0] - prev.pts[prev.pts.length - 1][0], pts[0][1] - prev.pts[prev.pts.length - 1][1]) > 30 : false
      };
      hop.door = j ? DWELL : PRE;
      if (j) t += DWELL;
      hop.t0 = t; hop.t1 = t + hop.ms; t = hop.t1; prev = hop;
      return hop;
    });
    var lands = g.getAttribute('data-lands');
    return { g: g, svg: svg, id: id, kind: kind, hops: hops, token: g.querySelector('.ax-token'),
             lands: lands ? svg.querySelector('[data-ax="' + lands + '"]') : null,   // where the effect shows
             nums: sel(svg, 'ax-flow-nums', id), end: t, dur: t + HOLD };
  }

  function point(h, s) {
    s = Math.max(0, Math.min(h.len, s));
    for (var k = 1; k < h.pts.length; k++) {
      if (s <= h.cum[k] || k === h.pts.length - 1) {
        var a = h.pts[k - 1], b = h.pts[k], L = h.cum[k] - h.cum[k - 1], f = L ? (s - h.cum[k - 1]) / L : 0;
        return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f];
      }
    }
    return h.pts[h.pts.length - 1];
  }
  // the message beside the wire: in step with the token on its clear stretch, waiting before it, parked after it
  function pillAt(h, s) {
    var q = point(h, Math.max(h.smin, Math.min(h.smax, s)));
    return [q[0] + h.off[0], q[1] + h.off[1]];
  }

  // ---- the one run: S.run = {j, at} is flow j playing from time `at` (a future `at`:
  // autoplay waiting for its start). What is on screen at time t: {j, u} (u = ms into
  // flow j), or null.
  function frame(t) {
    if (!S || !S.run) return null;
    var u = t - S.run.at;
    return u >= 0 && u < S.flows[S.run.j].dur ? { j: S.run.j, u: u } : null;
  }
  // runs that have ended by t move the cursor on. flow-auto's autoplay is its first flow
  // only; flow-loop chains the next one from the end of the last (not from when a tick
  // noticed it), so a round never drifts
  function advance(t) {
    while (S && S.run && t >= S.run.at + S.flows[S.run.j].dur) {
      var j = S.run.j, end = S.run.at + S.flows[j].dur, last = j + 1 === S.flows.length;
      S.stop = j + 1; S.run = null;
      if (!S.auto || S.mode !== 'loop') { S.auto = false; break; }
      S.run = { j: last ? 0 : j + 1, at: end + (last ? REST : GAP) };
    }
  }
  // how far along the line (ms of flow time) the clock is: inside a run, or at the cursor's stop
  function along(t) {
    var r = S.run;
    if (r && t >= r.at) return S.line.B[r.j] + Math.min(t - r.at, S.flows[r.j].dur);
    return S.line.B[S.stop];
  }

  function cls(el, name, on) { if (el && el.classList.contains(name) !== on) el.classList.toggle(name, on); }
  function show(el, on) { cls(el, 'ax-on', on); }
  function place(el, p) {
    var v = 'translate(' + p[0].toFixed(1) + ' ' + p[1].toFixed(1) + ')';
    if (el.getAttribute('transform') !== v) el.setAttribute('transform', v);
  }

  // paint one flow at u ms (u === null: at rest). Its token, pills and glows are its own;
  // edges and static pills can be shared, so it only reports what it wants of them (acc).
  function paint(f, u, acc) {
    var active = u !== null, hops = f.hops, cur = -1, s = 0, where = null, hidden = false;
    if (active) {
      for (var j = 0; j < hops.length; j++) if (u >= hops[j].t0 - hops[j].door) cur = j;
      var h = hops[cur];
      if (u < h.t0) {                                   // waiting at the door
        s = 0; hidden = h.jump && u < h.t0 - DWELL / 2;
        where = hidden ? point(hops[cur - 1], hops[cur - 1].len) : point(h, 0);
      } else {
        s = ease(Math.min(1, (u - h.t0) / h.ms)) * h.len; where = point(h, s);
      }
      if (u >= f.end) {                                 // delivered: the token has gone into the box …
        hidden = true;
        if (f.lands) acc.land.push([[f.lands], f.kind]);  // … and what it did lights up there
      }
    }
    hops.forEach(function (h, j) {
      var now_ = active && j === cur && u < h.t1, done = active && (j < cur || (j === cur && u >= h.t1));
      cls(h.glow, 'ax-lit', now_);
      if (now_) acc.lit.push([h.edges, f.kind]); else if (done) acc.trail.push([h.edges, f.kind]);
      if (h.mp) {
        var riding = now_ && !(hidden && u < h.t0), parked = done && !h.pill;   // no twin: it stays where it arrived
        show(h.mp, riding || parked);
        if (riding) place(h.mp, pillAt(h, u < h.t0 ? 0 : s));
        else if (parked) place(h.mp, pillAt(h, h.len));
        if (now_ && h.pill) acc.off.push(h.pill);      // the twin steps aside while its message is in flight
      }
    });
    show(f.token, active && !hidden);
    if (active && !hidden) place(f.token, where);
  }

  // the progress line: the fill to x (0..1), each boundary dot filled once reached
  function paintLine(ms) {
    var L = S.line;
    if (!L) return;
    var v = 'scaleX(' + (ms / L.total).toFixed(4) + ')';
    if (L.v !== v) { L.fill.style.transform = v; L.v = v; }
    L.dots.forEach(function (d, k) { cls(d, 'ax-passed', ms >= L.B[k + 1] - 0.5); });
  }

  function render(t) {
    if (!S || S.mode === 'off') return;
    var fr = frame(t), acc = { lit: [], trail: [], off: [], land: [] };
    S.flows.forEach(function (f, j) { paint(f, fr && fr.j === j ? fr.u : null, acc); });
    S.edges.forEach(function (e) {                      // an edge can serve several hops: decide once
      var lit = null, trail = null;
      acc.lit.forEach(function (l) { if (l[0].indexOf(e) >= 0) lit = l[1]; });
      acc.trail.forEach(function (l) { if (l[0].indexOf(e) >= 0) trail = l[1]; });
      var k = lit || trail;
      cls(e, 'ax-lit', !!lit); cls(e, 'ax-trail', !lit && !!trail);
      KINDS.forEach(function (kk) { cls(e, 'ax-lf-' + kk, k === kk); });
    });
    S.pills.forEach(function (p) { cls(p, 'ax-pill-off', acc.off.indexOf(p) >= 0); });   // … and so can a static pill
    S.lands.forEach(function (el) {
      var k = null; acc.land.forEach(function (l) { if (l[0][0] === el) k = l[1]; });
      cls(el, 'ax-landed', !!k); KINDS.forEach(function (kk) { cls(el, 'ax-lf-' + kk, k === kk); });
    });
    paintLine(along(t));
    S.playing = !!fr;
  }

  // the next moment anything changes (animating: now; autoplay waiting: its start), or null
  function wake(t) {
    if (!S || !S.run || frozen !== null) return null;
    return t < S.run.at ? S.run.at : t;
  }

  function tick() {
    raf = 0; clearTimeout(timer); timer = 0;
    if (!S) return;
    var t = now();
    if (frozen === null) advance(t);
    render(t);
    var w = wake(t);
    if (w === null) return;
    if (w <= t + 16) raf = requestAnimationFrame(tick);
    else timer = setTimeout(tick, w - t - 8);
  }

  // reduced motion: which flow's numbered hops show — k, 'all' (the static overview) or -1
  function reveal(k) {
    S.svgs.forEach(function (svg) { cls(svg, 'ax-static', k === 'all'); });
    S.flows.forEach(function (f, j) { cls(f.nums, 'ax-shown', j === k); });
  }

  function stop() {
    if (raf) cancelAnimationFrame(raf); clearTimeout(timer); raf = 0; timer = 0;
    frozen = null;
    if (S) {
      S.run = null; S.auto = false; S.stop = 0; render(0);
      S.svgs.forEach(function (svg) { cls(svg, 'ax-static', false); });
      S.flows.forEach(function (f) { cls(f.nums, 'ax-shown', false); });
    }
  }

  // the line's DOM, in the figure (outside the SVG), built once per slide: a fill and one
  // dot per boundary between two flows. Placement and look: diagram.css.
  function line(fig, flows) {
    var B = [0];
    flows.forEach(function (f, j) { B.push(B[j] + f.dur); });
    var total = B[flows.length], el = null;
    for (var c = fig.firstElementChild; c; c = c.nextElementSibling) if (c.classList.contains('ax-prog')) el = c;
    if (!el) {
      el = document.createElement('div');
      el.className = 'ax-prog'; el.setAttribute('aria-hidden', 'true');
      var fill = document.createElement('div'); fill.className = 'ax-prog-fill'; el.appendChild(fill);
      for (var k = 1; k < flows.length; k++) {
        var d = document.createElement('div'); d.className = 'ax-prog-dot';
        d.style.left = (100 * B[k] / total).toFixed(3) + '%'; el.appendChild(d);
      }
      fig.appendChild(el);
    }
    return { el: el, fill: el.querySelector('.ax-prog-fill'), dots: [].slice.call(el.querySelectorAll('.ax-prog-dot')),
             B: B, total: total, v: null };
  }

  function load(slide) {
    var svgs = [].slice.call(slide.querySelectorAll('svg.ax'));
    var flows = [];
    svgs.forEach(function (svg) { [].forEach.call(svg.querySelectorAll('.ax-flow'), function (g) { flows.push(parseFlow(g)); }); });
    if (!flows.length) return null;
    var fig = svgs[0].parentNode, fc = fig.classList;
    var mode = fc.contains('flow-keys') || fc.contains('flow-step') ? 'keys' : fc.contains('flow-loop') ? 'loop' : fc.contains('flow-off') ? 'off' : 'auto';
    var edges = [], pills = [], lands = [];
    flows.forEach(function (f) { if (f.lands && lands.indexOf(f.lands) < 0) lands.push(f.lands); });
    flows.forEach(function (f) { f.hops.forEach(function (h) {
      h.edges.forEach(function (e) { if (edges.indexOf(e) < 0) edges.push(e); });
      if (h.pill && pills.indexOf(h.pill) < 0) pills.push(h.pill);
    }); });
    return { slide: slide, svgs: svgs, flows: flows, edges: edges, pills: pills, lands: lands, mode: mode,
             line: mode === 'off' ? null : line(fig, flows),
             stop: 0, run: null, auto: false, lastA: -Infinity, shown: -1, playing: false };
  }

  function mine(slide) { return !!S && S.slide === slide && S.mode !== 'off'; }

  var api = {
    /* a slide was shown (also on re-entry and on a #N jump): reset, then maybe schedule */
    enter: function (slide) {
      stop();
      S = load(slide);
      if (!S || S.mode === 'off') return;
      if (reduced()) {                                  // no motion: the print look instead
        if (S.mode === 'auto') { S.shown = 0; reveal(0); S.stop = 1; }                          // "autoplays" flow 1
        else if (S.mode === 'loop') { S.shown = 'all'; reveal('all'); S.stop = S.flows.length; } // all of them, at rest
        render(now()); return;
      }
      if (S.mode !== 'keys') { S.auto = true; S.run = { j: 0, at: now() + START }; }   // flow-auto / flow-loop
      tick();
    },
    /* the a key: play the flow at the cursor, or restart the one travelling. true = handled */
    play: function (slide) {
      if (!mine(slide)) return false;
      var t = now();
      if (t - S.lastA < BOUNCE) return true;            // a bounce: keep what is happening
      S.lastA = t;
      if (frozen === null) advance(t);
      S.auto = false;                                   // a key takes over from autoplay
      var n = S.flows.length;
      if (reduced()) {                                  // reveal the cursor flow's numbers, one whole segment on
        if (S.shown === 'all') S.stop = 0;              // from flow-loop's overview: start over at flow 1
        var k = Math.min(S.stop, n - 1);
        S.shown = k; reveal(k); S.stop = k + 1; render(t); return true;
      }
      var fr = frame(t);
      if (fr && fr.u >= S.flows[fr.j].end) { S.stop = fr.j + 1; fr = null; }   // the hold: its token has gone in, it is done
      S.run = { j: fr ? fr.j : Math.min(S.stop, n - 1), at: t };
      tick(); return true;
    },
    /* the p key: one stop back (see the top). true = handled */
    back: function (slide) {
      if (!mine(slide)) return false;
      var t = now();
      S.lastA = -Infinity;                              // p, then a at once is on purpose, not a bounce
      if (frozen === null) advance(t);
      S.auto = false;
      if (reduced()) {
        if (S.shown !== -1) { S.shown = -1; reveal(-1); }
        if (S.stop > 0) S.stop--;
        render(t); return true;
      }
      var fr = frame(t);
      if (fr) S.stop = fr.j;                            // playing: back to that flow's start
      else if (S.stop > 0) S.stop--;
      S.run = null;
      tick(); return true;
    },
    /* for tests and screenshots: freeze the clock at ms into flow j of the current slide
       (the line follows: it shows exactly what the flow shows) */
    at: function (ms, j) {
      if (!S || S.mode === 'off') return null;
      if (raf) cancelAnimationFrame(raf); clearTimeout(timer); raf = 0; timer = 0;
      frozen = 1e9; S.auto = false; S.run = { j: j || 0, at: frozen - ms };
      render(frozen);
      return api.info();
    },
    release: function () { frozen = null; if (S && S.mode !== 'off') { S.run = null; render(now()); } },
    info: function () {
      if (!S) return null;
      var t = now(), n = S.flows.length;
      return { mode: S.mode, playing: S.playing, stop: S.stop, cursor: Math.min(S.stop, n - 1), auto: S.auto,
        running: S.run ? S.run.j : null, since: S.run ? t - S.run.at : null, shown: S.shown,
        line: S.line ? { B: S.line.B, total: S.line.total, at: S.mode === 'off' ? 0 : along(t) / S.line.total } : null,
        flows: S.flows.map(function (f) { return { id: f.id, kind: f.kind, hops: f.hops.length, dur: f.dur, end: f.end,
          hopTimes: f.hops.map(function (h) { return [h.t0, h.t1]; }) }; }) };
    }
  };
  window.axFlows = api;
})();
