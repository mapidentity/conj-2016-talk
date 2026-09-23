/* diagram.js — plays the `flow`s of ```diagram``` figures (see diagram.py). Inlined
   into slides.html by build_slides.py; the template calls axFlows.enter(slide) from
   show() and asks axFlows.step(slide) before advancing. The deck/PDF never runs it:
   there the figure is static and diagram.css shows the numbered hops instead.

   Why a script and not CSS motion: one clock drives token, pill, glow and edge, so
   "play the next flow on →", "finish it on a second →", loop-with-rest, restart on
   re-entry and prefers-reduced-motion are plain branches, not animation plumbing.
   It only ever sets a transform attribute and toggles classes, which every SVG
   engine has done the same way for 15 years — no offset-path, no keyframe names,
   no ids (every slide lives in one document). The geometry is precomputed by the
   generator: data-pts is the edge's own route in travel order, data-ms the hop's
   time, data-smin/-smax/-off the stretch beside the wire where its message rides.

   Per slide, a class on the figure (a {.class} line before the fence) picks:
     flow-auto (default)  play every flow once, 2 s after the cut
     flow-loop            play them, rest 2 s, play again, while the slide is up
     flow-step            → / Space / PageDown / click plays the next flow; → while
                          the token is still travelling finishes the flow; once the
                          token has arrived, → goes on (next flow, or next slide)
     flow-off             never animate (the static picture, numbers hidden)      */
(function () {
  'use strict';
  var START = 2000,  // after the hard cut, before autoplay: the audience finds the new parts first
      PRE = 260,     // the token waits at the first door
      DWELL = 170,   // … and at every node between hops
      HOLD = 900,    // after the last hop, the whole path stays lit (the token has gone in)
      GAP = 600,     // between two flows of one slide
      REST = 2000,   // flow-loop: the static picture between rounds
      BOUNCE = 250;  // flow-step: a second press this soon after a start is a clicker bounce
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

  // ---- what is on screen at time t: {flow, u} (u = ms into that flow), or null
  function frame(t) {
    if (!S) return null;
    if (S.run) return t >= S.run.at && t < S.run.at + S.run.flow.dur ? { flow: S.run.flow, u: t - S.run.at } : null;
    if (S.t0 === null || t < S.t0 || !S.flows.length) return null;
    var x = t - S.t0;
    if (S.mode === 'loop') x %= S.total + REST;
    for (var j = 0; j < S.flows.length; j++) {
      var f = S.flows[j];
      if (x < f.dur) return { flow: f, u: x };
      x -= f.dur + GAP;
      if (x < 0) return null;
    }
    return null;
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

  function render(t) {
    if (!S) return;
    var fr = frame(t), acc = { lit: [], trail: [], off: [], land: [] };
    S.flows.forEach(function (f) { paint(f, fr && fr.flow === f ? fr.u : null, acc); });
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
    S.playing = !!fr;
  }

  // the next moment anything changes (for sleeping between rounds), or null
  function wake(t) {
    if (!S || frozen !== null) return null;
    if (S.run) return t < S.run.at + S.run.flow.dur ? t : null;
    if (S.t0 === null || !S.flows.length) return null;
    if (t < S.t0) return S.t0;
    if (frame(t)) return t;
    var P = S.total + REST, base = S.mode === 'loop' ? S.t0 + Math.floor((t - S.t0) / P) * P : S.t0, at = base;
    for (var j = 0; j < S.flows.length; j++) { if (at > t) return at; at += S.flows[j].dur + GAP; }
    return S.mode === 'loop' ? base + P : null;
  }

  function tick() {
    raf = 0; clearTimeout(timer); timer = 0;
    var t = now();
    render(t);
    if (S && S.run && !S.playing) S.run = null;
    var w = wake(t);
    if (w === null) return;
    if (w <= t + 16) raf = requestAnimationFrame(tick);
    else timer = setTimeout(tick, w - t - 8);
  }

  function stop() {
    if (raf) cancelAnimationFrame(raf); clearTimeout(timer); raf = 0; timer = 0;
    if (S) {
      S.run = null; S.t0 = null; frozen = null; render(0);
      S.svgs.forEach(function (svg) { cls(svg, 'ax-static', false); });
      S.flows.forEach(function (f) { cls(f.nums, 'ax-shown', false); });
    }
  }

  function load(slide) {
    var svgs = [].slice.call(slide.querySelectorAll('svg.ax'));
    var flows = [];
    svgs.forEach(function (svg) { [].forEach.call(svg.querySelectorAll('.ax-flow'), function (g) { flows.push(parseFlow(g)); }); });
    if (!flows.length) return null;
    var fig = svgs[0].parentNode.classList;
    var mode = fig.contains('flow-step') ? 'step' : fig.contains('flow-loop') ? 'loop' : fig.contains('flow-off') ? 'off' : 'auto';
    var edges = [], pills = [], lands = [];
    flows.forEach(function (f) { if (f.lands && lands.indexOf(f.lands) < 0) lands.push(f.lands); });
    flows.forEach(function (f) { f.hops.forEach(function (h) {
      h.edges.forEach(function (e) { if (edges.indexOf(e) < 0) edges.push(e); });
      if (h.pill && pills.indexOf(h.pill) < 0) pills.push(h.pill);
    }); });
    var total = flows.reduce(function (a, f) { return a + f.dur; }, 0) + GAP * (flows.length - 1);
    return { slide: slide, svgs: svgs, flows: flows, edges: edges, pills: pills, lands: lands, mode: mode, total: total,
             t0: null, run: null, next: 0, playing: false };
  }

  var api = {
    /* a slide was shown (also on re-entry and on a #N jump): reset, then schedule */
    enter: function (slide) {
      stop();
      S = load(slide);
      if (!S || S.mode === 'off') return;
      if (reduced()) {                                  // no motion: the print look instead
        if (S.mode !== 'step') S.svgs.forEach(function (svg) { cls(svg, 'ax-static', true); });
        return;
      }
      if (S.mode !== 'step') { S.t0 = now() + START; tick(); }
    },
    /* → on this slide: true = consumed (a flow started, was finished, or it was a bounce), false = advance */
    step: function (slide) {
      if (!S || S.slide !== slide || S.mode !== 'step') return false;
      if (reduced()) {                                  // reveal each flow's numbered path instead
        if (S.next >= S.flows.length) return false;
        S.flows.forEach(function (f, j) { cls(f.nums, 'ax-shown', j === S.next); });
        S.next++; return true;
      }
      var t = now();
      if (S.run) {
        var u = t - S.run.at;
        if (u < BOUNCE) return true;                    // a clicker's double press: keep playing
        if (u < S.run.flow.end) { S.run = null; tick(); return true; }   // still travelling: finish (the static picture)
        S.run = null;                                   // arrived, path still lit: that press means "go on"
      }
      if (S.next >= S.flows.length) { tick(); return false; }
      S.run = { flow: S.flows[S.next++], at: t };
      tick(); return true;
    },
    /* for tests and screenshots: freeze the clock at ms into flow j of the current slide */
    at: function (ms, j) {
      if (!S) return null;
      if (raf) cancelAnimationFrame(raf); clearTimeout(timer); raf = 0; timer = 0;
      frozen = 1e9; S.t0 = null; S.run = { flow: S.flows[j || 0], at: frozen - ms };
      render(frozen);
      return api.info();
    },
    release: function () { frozen = null; if (S) { S.run = null; render(now()); } },
    info: function () {
      return S && { mode: S.mode, playing: S.playing, next: S.next, total: S.total,
        flows: S.flows.map(function (f) { return { id: f.id, kind: f.kind, hops: f.hops.length, dur: f.dur, end: f.end,
          hopTimes: f.hops.map(function (h) { return [h.t0, h.t1]; }) }; }) };
    }
  };
  window.axFlows = api;
})();
