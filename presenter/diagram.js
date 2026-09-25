/* diagram.js — plays the `flow`s and `swap`s of ```diagram``` figures (see diagram.py) and
   draws the speaker's progress line under them. Inlined into slides.html by build_slides.py; the
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

   A state's animations are its flows and its swaps, in the order written: one per a, one
   segment of the line each ("flow" below means either, where it is about keys and stops).
   A swap replaces parts: before it has played (on arrival, or p back to it) its out parts
   are on screen and its in parts are not; playing it strikes an out box's label, fades the
   out parts (a solid wire retracts into the end that stays) and draws the in wires from
   their source (a dashed one fades in); after it, what rests is the end state. The markup
   itself is that end state (print, the deck, flow-off): the script only adds the "before",
   as a class, and the inline styles of the frames in between. A flow's station (a row or
   cell as a hop) lights that part for a beat while the token is inside its box; a waypoint
   (data-at) stops the token on its hop for a beat. What lights in a beat (data-with) keeps
   the trail look after it; a mark pulses (1 → data-k → 1, where it has room), then keeps
   its ring, or its lit words (diagram.css). A leg (data-leg on its first hop) is a restart
   elsewhere: the token goes in at the end of the leg before and comes out LEG ms later at
   the new leg's first door.

   Navigation never plays a flow: → / Space / PageDown / click always go to the next
   slide. On a slide with flows the template passes two keys on (either case, no Ctrl /
   Cmd / Alt, no auto-repeat):
     a   nothing playing: play the flow at the cursor. Playing: restart that flow from its
         start — while its token travels. In the 0.9 s hold after it has gone in, the flow
         looks done and counts as done: a plays the next flow (the last one: replays it).
         A swap never rewinds: a while it plays finishes it at once (its end state, the
         cursor after it), and the next a plays on.
         A second a within 250 ms of the last one is a key bounce or double tap: ignored.
     p   one stop back. Playing: stop, back to the start of that flow (nothing lit). Idle
         at the start of flow k > 1: to the start of flow k-1. Idle after the last flow:
         to the start of the last flow. At the start of flow 1: nothing. So "show that
         again" is p, then a (p also clears the bounce guard, so that a always counts).
   The stops are the start of each flow plus "after the last". Arriving on a slide (any
   direction, a #N jump, a reload) puts the cursor at flow 1 with nothing playing and
   nothing lit — except arriving back from a later slide on one with a swap (not
   flow-loop): the talk has moved past it, so the cursor is after the last swap, its end
   state rests on screen and nothing plays by itself. Leaving stops everything. A flow
   that finishes moves the cursor to the next one; after the last one it stays on the
   last, so a replays it.

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
   A swap is applied at once on a (its end state), and p puts the "before" back.
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
      LEG = 600,     // between two legs of a flow (`|`): the token has gone in; it comes out elsewhere
      GAP = 600,     // flow-loop: between two flows of one slide
      REST = 2000,   // flow-loop: the static picture between rounds
      BOUNCE = 250;  // a second a this soon after the last is a key bounce or double tap
  // a swap's phases, as fractions of its time (data-ms): the struck label, the out parts going,
  // the in wires drawing (their heads and words last). They overlap: one replaces the other.
  // The strike is drawn early and stands whole for a while before the box goes: it has to read
  // from the back of the hall.
  var SW = { strike: [0, .18], outBox: [.38, .72], outWire: [.3, .68], inWire: [.5, .93], inHead: [.88, .97], inWords: [.75, .97] };
  var KINDS = ['fwd', 'rev', 'warn'];
  var mq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  var S = null, raf = 0, timer = 0, frozen = null;

  function now() { return frozen !== null ? frozen : performance.now(); }
  function reduced() { return !!(mq && mq.matches); }
  function ease(p) { return 0.5 - 0.5 * Math.cos(Math.PI * p); }
  function sel(svg, cls, id) { return svg.querySelector('.' + cls + '[data-flow="' + id + '"]'); }
  function nums(h, a) { return (h.getAttribute(a) || '').split(',').map(Number); }

  function ids(h, a) { return (h.getAttribute(a) || '').split(' ').filter(Boolean); }
  function byIds(svg, list) {                           // every element of the listed parts (an edge: its line and its words)
    return list.length ? [].slice.call(svg.querySelectorAll(list.map(function (i) { return '[data-ax="' + i + '"]'; }).join(','))) : [];
  }
  // what lights in a beat (a station's part, and data-with): edges take the wire looks; a mark pulses to
  // data-k about data-o (the generator sizes the pulse and picks the point: it keeps off the neighbours;
  // no data-k: no room, the mark keeps still), then keeps its ring (a mark with words: they light instead)
  function beat(svg, list) {
    var b = { els: [], edges: [], marks: [] };
    byIds(svg, list).forEach(function (el) {
      if (el.classList.contains('ax-edge')) { b.edges.push(el); return; }
      b.els.push(el);
      if (el.classList.contains('ax-mark') && el.hasAttribute('data-k'))
        b.marks.push({ el: el, o: nums(el, 'data-o'), k: +el.getAttribute('data-k'), glyphs: [].slice.call(el.querySelectorAll('.ax-glyph, .ax-tick, .ax-q')) });
    });
    return b;
  }

  function parseFlow(g) {
    var svg = g.ownerSVGElement, id = g.getAttribute('data-flow');
    var kind = (/ax-f-(\w+)/.exec(g.getAttribute('class')) || [0, 'fwd'])[1];
    var under = sel(svg, 'ax-flow-under', id), glows = under ? under.querySelectorAll('.ax-hglow') : [];
    var t = PRE, prev = null, last = null, gi = 0;
    var hops = [].map.call(g.querySelectorAll('.ax-hop'), function (h, j) {
      var part = h.getAttribute('data-part'), leg = j > 0 && h.hasAttribute('data-leg');
      if (leg) { last.legEnd = true; t += LEG; }        // a new leg: the token went in; it comes out here, LEG later
      if (part) {                                       // a station: a beat inside the box, that part lit
        var st = { part: part, ms: +h.getAttribute('data-ms'), door: j ? 0 : PRE,
                   beat: beat(svg, [part].concat(ids(h, 'data-with'))), edges: [], pill: null, mp: null, glow: null };
        st.t0 = t; st.t1 = t + st.ms; t = st.t1;
        st.b0 = st.t0 - st.door; st.b1 = st.t1;         // its beat: from its door (the first item: the flow's start)
        return (last = st);
      }
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
        glow: glows[gi++] || null,                      // a station has no glow of its own
        // the next hop leaves from another side of the box: hide the token while it is "inside"
        // (a new leg's first door is not a jump: the token comes out there and waits, like at any door)
        jump: prev && !leg ? Math.hypot(pts[0][0] - prev.pts[prev.pts.length - 1][0], pts[0][1] - prev.pts[prev.pts.length - 1][1]) > 30 : false,
        at: null, wms: 0
      };
      hop.door = j ? DWELL : PRE;
      if (j) t += DWELL;
      hop.t0 = t;
      if (h.hasAttribute('data-at')) {                  // a waypoint: the token stops at arc length `at` while its beat lights
        hop.at = Math.max(0, Math.min(hop.len, +h.getAttribute('data-at'))); hop.wms = +h.getAttribute('data-wms');
        hop.m1 = hop.len ? hop.ms * hop.at / hop.len : 0;   // the hop's own time, shared out by distance: its pace is a plain hop's
        hop.b0 = t + hop.m1; hop.b1 = hop.b0 + hop.wms;
        hop.beat = beat(svg, ids(h, 'data-with'));
      }
      hop.t1 = t + hop.ms + hop.wms; t = hop.t1; prev = hop;
      return (last = hop);
    });
    return { g: g, svg: svg, id: id, kind: kind, hops: hops, token: g.querySelector('.ax-token'),
             lands: byIds(svg, ids(g, 'data-lands')),  // where the effect shows
             nums: sel(svg, 'ax-flow-nums', id), end: t, dur: t + HOLD };
  }

  // a path's length, from its d (the generator writes M x,y L x,y …): no layout needed
  function pathLen(p) {
    var v = (p.getAttribute('d') || '').replace(/[ML]/g, ' ').trim().split(/\s+/).map(function (xy) { return xy.split(',').map(Number); });
    for (var L = 0, k = 1; k < v.length; k++) L += Math.hypot(v[k][0] - v[k - 1][0], v[k][1] - v[k - 1][1]);
    return L;
  }

  function parseSwap(g) {
    var svg = g.ownerSVGElement, ms = +g.getAttribute('data-ms'), parts = [];
    [['data-out', 'out'], ['data-in', 'in']].forEach(function (r) {
      (g.getAttribute(r[0]) || '').split(' ').filter(Boolean).forEach(function (spec) {
        var id = spec.split(':')[0], keep = spec.split(':')[1] || 'a';
        [].forEach.call(svg.querySelectorAll('.ax-swap-' + r[1] + '[data-ax="' + id + '"]'), function (el) {
          var c = el.classList, p = { el: el, role: r[1], kind: 'part', paths: [], heads: [], strike: null };
          if (c.contains('ax-elab')) p.kind = 'words';
          else if (c.contains('ax-edge')) {
            p.paths = [].slice.call(el.querySelectorAll('.ax-halo, .ax-glow, .ax-line'));
            p.heads = [].slice.call(el.querySelectorAll('.ax-head'));
            var line = el.querySelector('.ax-line'), dashed = line && getComputedStyle(line).strokeDasharray;
            // a solid wire retracts (out) or draws (in); a dashed one, or one losing both ends, fades
            p.kind = line && (!dashed || dashed === 'none') && keep !== '-' ? 'wire' : 'part';
            p.keep = keep; p.D = line ? pathLen(line) + 2 : 0;
          } else if (c.contains('ax-node')) {
            p.kind = 'box'; p.strike = el.querySelector('.ax-swap-strike');
            if (p.strike) p.SD = pathLen(p.strike) + 2;
          }
          parts.push(p);
        });
      });
    });
    return { swap: true, g: g, svg: svg, id: g.getAttribute('data-swap'), kind: 'swap', parts: parts, ms: ms,
             hops: [], end: ms, dur: ms, state: null };
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
  // how far along its hop the token is at u (≥ h.t0): eased over the hop, or, with a waypoint, eased to
  // it, still for its beat, eased on (each stretch in its share of the hop's time)
  function travel(h, u) {
    if (h.at === null) return ease(Math.min(1, (u - h.t0) / h.ms)) * h.len;
    if (u < h.b0) return h.m1 > 0 ? ease((u - h.t0) / h.m1) * h.at : h.at;
    if (u < h.b1) return h.at;
    var m2 = h.ms - h.m1;
    return h.at + (m2 > 0 ? ease(Math.min(1, (u - h.b1) / m2)) : 1) * (h.len - h.at);
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
    return u >= 0 && u < S.anims[S.run.j].dur ? { j: S.run.j, u: u } : null;
  }
  // runs that have ended by t move the cursor on. flow-auto's autoplay is its first flow
  // only; flow-loop chains the next one from the end of the last (not from when a tick
  // noticed it), so a round never drifts
  function advance(t) {
    while (S && S.run && t >= S.run.at + S.anims[S.run.j].dur) {
      var j = S.run.j, end = S.run.at + S.anims[j].dur, last = j + 1 === S.anims.length;
      S.stop = j + 1; S.run = null;
      if (!S.auto || S.mode !== 'loop') { S.auto = false; break; }
      S.run = { j: last ? 0 : j + 1, at: end + (last ? REST : GAP) };
    }
  }
  // how far along the line (ms of flow time) the clock is: inside a run, or at the cursor's stop
  function along(t) {
    var r = S.run;
    if (r && t >= r.at) return S.line.B[r.j] + Math.min(t - r.at, S.anims[r.j].dur);
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
      if (h.part) hidden = true;                        // a station: the token is inside the box
      else if (u < h.t0) {                              // waiting at the door (hidden: where it is does not matter)
        s = 0; hidden = h.jump && u < h.t0 - DWELL / 2;
        where = point(h, 0);
      } else {
        s = travel(h, u); where = point(h, s);
      }
      if (h.legEnd && u >= h.t1) hidden = true;         // the end of a leg: the token has gone in, it restarts elsewhere
      if (u >= f.end) {                                 // delivered: the token has gone into the box …
        hidden = true;
        if (f.lands.length) acc.land.push([f.lands, f.kind]);   // … and what it did lights up there
      }
    }
    hops.forEach(function (h, j) {
      var now_ = active && j === cur && u < h.t1, done = active && (j < cur || (j === cur && u >= h.t1));
      if (h.beat) {                                     // a station's or a waypoint's beat: lit in it, then the trail look
        var bnow = active && u >= h.b0 && u < h.b1, bdone = active && u >= h.b1;
        if (bnow || bdone) {
          h.beat.els.forEach(function (el) { acc.beat.push([el, f.kind, bnow]); });
          (bnow ? acc.lit : acc.trail).push([h.beat.edges, f.kind]);
          h.beat.marks.forEach(function (m) {         // a mark pulses over the beat: 1 → k → 1
            acc.pulse.push([m, bnow ? 1 + (m.k - 1) * Math.sin(Math.PI * (u - h.b0) / (h.b1 - h.b0)) : 1]);
          });
        }
      }
      if (h.part) return;
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

  // ---- a swap. At rest it is "before" (class ax-swap-pre on its parts: the out parts show, the in
  // parts don't) or after (the markup as it is: the end state). Running, its parts carry
  // ax-swap-run (all of them show) and the frame's inline styles: opacity, and a one-dash
  // pattern (D D) whose offset retracts or draws a solid wire. Styles only change when needed.
  function phase(u, ms, w) { return ease(Math.max(0, Math.min(1, (u / ms - w[0]) / (w[1] - w[0])))); }
  function css(el, prop, v) { if (el.style[prop] !== v) el.style[prop] = v; }
  // f > 0: the dash ends f·D short of the path's end; f < 0: it starts |f|·D in (D: the length + 2)
  function dash(p, D, f) { css(p, 'strokeDasharray', D.toFixed(1) + ' ' + D.toFixed(1)); css(p, 'strokeDashoffset', (f * D).toFixed(1)); }
  function bare(p) {
    css(p.el, 'opacity', '');
    p.paths.concat(p.strike ? [p.strike] : []).forEach(function (q) { css(q, 'strokeDasharray', ''); css(q, 'strokeDashoffset', ''); });
    p.heads.forEach(function (h) { css(h, 'opacity', ''); });
  }
  function swapRest(sw, pre) {
    var st = pre ? 'pre' : 'post';
    if (sw.state === st) return;
    sw.parts.forEach(function (p) { bare(p); cls(p.el, 'ax-swap-run', false); cls(p.el, 'ax-swap-pre', pre); });
    sw.state = st;
  }
  function swapAt(sw, u) {
    if (sw.state !== 'run') sw.parts.forEach(function (p) { cls(p.el, 'ax-swap-pre', false); cls(p.el, 'ax-swap-run', true); });
    sw.state = 'run';
    var ms = sw.ms, cap = function (x) { return Math.max(0, Math.min(1, x)).toFixed(3); };
    sw.parts.forEach(function (p) {
      if (p.role === 'out') {
        if (p.kind === 'wire') {                        // retract into the end that stays: from the tip (a), or from the source (b)
          var q = phase(u, ms, SW.outWire);
          p.paths.forEach(function (path) { dash(path, p.D, p.keep === 'b' ? -q : q); });
          // every retiring arrowhead goes early, together, whichever end stays: none is left pointing at nothing
          p.heads.forEach(function (h) { css(h, 'opacity', cap(1 - q * 4)); });
        } else {
          css(p.el, 'opacity', cap(1 - phase(u, ms, p.kind === 'box' ? SW.outBox : SW.outWire)));
          if (p.strike) dash(p.strike, p.SD, 1 - phase(u, ms, SW.strike));   // the struck label, left to right
        }
      } else if (p.kind === 'wire') {                   // draw from its source
        p.paths.forEach(function (path) { dash(path, p.D, 1 - phase(u, ms, SW.inWire)); });
        p.heads.forEach(function (h) { css(h, 'opacity', cap(phase(u, ms, SW.inHead))); });
      } else css(p.el, 'opacity', cap(phase(u, ms, p.kind === 'words' ? SW.inWords : SW.inWire)));
    });
  }
  function unswap(sw) {                                 // back to the markup: the end state, no classes, no styles
    sw.parts.forEach(function (p) { bare(p); cls(p.el, 'ax-swap-pre', false); cls(p.el, 'ax-swap-run', false); });
    sw.state = null;
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
    var fr = frame(t), acc = { lit: [], trail: [], off: [], land: [], beat: [], pulse: [] };
    S.anims.forEach(function (f, j) {
      var u = fr && fr.j === j ? fr.u : null;
      if (!f.swap) paint(f, u, acc);
      else if (u !== null) swapAt(f, u);
      else swapRest(f, !(fr ? j < fr.j : j < S.stop));  // played: an earlier one than the one playing, or before the cursor
    });
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
      var k = null; acc.land.forEach(function (l) { if (l[0].indexOf(el) >= 0) k = l[1]; });
      cls(el, 'ax-landed', !!k); KINDS.forEach(function (kk) { cls(el, 'ax-lf-' + kk, k === kk); });
    });
    S.beats.forEach(function (el) {                     // beats: the one the flow is at, and the ones it passed
      var k = null, now_ = false; acc.beat.forEach(function (l) { if (l[0] === el) { k = l[1]; now_ = now_ || l[2]; } });
      cls(el, 'ax-lit', !!k && now_); cls(el, 'ax-trail', !!k && !now_); KINDS.forEach(function (kk) { cls(el, 'ax-lf-' + kk, k === kk); });
    });
    S.marks.forEach(function (m) {                      // a pulsing mark: its glyph scaled about data-o (1: no transform)
      var sc = 1; acc.pulse.forEach(function (l) { if (l[0] === m) sc = Math.max(sc, l[1]); });
      var v = sc === 1 ? null : 'translate(' + m.o[0] + ' ' + m.o[1] + ') scale(' + sc.toFixed(4) + ') translate(' + -m.o[0] + ' ' + -m.o[1] + ')';
      m.glyphs.forEach(function (gl) {
        if (v === null) { if (gl.hasAttribute('transform')) gl.removeAttribute('transform'); }
        else if (gl.getAttribute('transform') !== v) gl.setAttribute('transform', v);
      });
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
    S.anims.forEach(function (f, j) { cls(f.nums, 'ax-shown', j === k); });
  }

  function stop() {
    if (raf) cancelAnimationFrame(raf); clearTimeout(timer); raf = 0; timer = 0;
    frozen = null;
    if (S) {
      S.run = null; S.auto = false; S.stop = 0; render(0);
      S.svgs.forEach(function (svg) { cls(svg, 'ax-static', false); });
      S.anims.forEach(function (f) { cls(f.nums, 'ax-shown', false); if (f.swap) unswap(f); });
    }
  }

  // the line's DOM, in the figure (outside the SVG), built once per slide: a fill and one
  // dot per boundary between two animations. Placement and look: diagram.css.
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
    var flows = [];                                     // the animations, in the order written: flows and swaps
    svgs.forEach(function (svg) { [].forEach.call(svg.querySelectorAll('.ax-flow, .ax-swap'), function (g) {
      flows.push(g.classList.contains('ax-swap') ? parseSwap(g) : parseFlow(g)); }); });
    if (!flows.length) return null;
    var fig = svgs[0].parentNode, fc = fig.classList;
    var mode = fc.contains('flow-keys') || fc.contains('flow-step') ? 'keys' : fc.contains('flow-loop') ? 'loop' : fc.contains('flow-off') ? 'off' : 'auto';
    var edges = [], pills = [], lands = [], beats = [], marks = [];
    var add = function (list, x) { if (x && list.indexOf(x) < 0) list.push(x); };
    flows.forEach(function (f) { if (f.lands) f.lands.forEach(function (el) { add(lands, el); }); });
    flows.forEach(function (f) { f.hops.forEach(function (h) {
      h.edges.forEach(function (e) { add(edges, e); });
      add(pills, h.pill);
      if (h.beat) {
        h.beat.edges.forEach(function (e) { add(edges, e); });
        h.beat.els.forEach(function (el) { add(beats, el); });
        h.beat.marks.forEach(function (m) {             // one record per mark, whichever beats light it
          var same = marks.filter(function (x) { return x.el === m.el; })[0];
          if (same) h.beat.marks[h.beat.marks.indexOf(m)] = same; else marks.push(m);
        });
      }
    }); });
    return { slide: slide, svgs: svgs, anims: flows, edges: edges, pills: pills, lands: lands, beats: beats, marks: marks, mode: mode,
             line: mode === 'off' ? null : line(fig, flows),
             stop: 0, run: null, auto: false, lastA: -Infinity, shown: -1, playing: false };
  }

  function mine(slide) { return !!S && S.slide === slide && S.mode !== 'off'; }

  var api = {
    /* a slide was shown (also on re-entry and on a #N jump): reset, then maybe schedule.
       back: it was reached from a later slide (←, or a jump back) */
    enter: function (slide, back) {
      stop();
      S = load(slide);
      if (!S || S.mode === 'off') return;
      var sw = -1;
      S.anims.forEach(function (f, j) { if (f.swap) sw = j; });
      if (back && sw >= 0 && S.mode !== 'loop') {       // back from later in the talk: its swaps have been seen
        S.stop = sw + 1; render(now()); return;         // the cursor after the last one, nothing plays by itself
      }
      if (reduced()) {                                  // no motion: the print look instead
        if (S.mode === 'auto') { S.shown = 0; reveal(0); S.stop = 1; }                          // "autoplays" flow 1
        else if (S.mode === 'loop') { S.shown = 'all'; reveal('all'); S.stop = S.anims.length; } // all of them, at rest
        render(now()); return;
      }
      if (S.mode !== 'keys') { S.auto = true; S.run = { j: 0, at: now() + START }; }   // flow-auto / flow-loop
      tick();
    },
    /* the a key: play the flow at the cursor, restart the one travelling, or finish a swap. true = handled */
    play: function (slide) {
      if (!mine(slide)) return false;
      var t = now();
      if (t - S.lastA < BOUNCE) return true;            // a bounce: keep what is happening
      S.lastA = t;
      if (frozen === null) advance(t);
      S.auto = false;                                   // a key takes over from autoplay
      var n = S.anims.length;
      if (reduced()) {                                  // reveal the cursor flow's numbers, one whole segment on
        if (S.shown === 'all') S.stop = 0;              // from flow-loop's overview: start over at flow 1
        var k = Math.min(S.stop, n - 1);
        S.shown = k; reveal(k); S.stop = k + 1; render(t); return true;
      }
      var fr = frame(t);
      // a swap never rewinds: a while it plays finishes it at once (its end state), and the next a plays on
      if (fr && S.anims[fr.j].swap) { S.stop = fr.j + 1; S.run = null; tick(); return true; }
      if (fr && fr.u >= S.anims[fr.j].end) { S.stop = fr.j + 1; fr = null; }   // the hold: its token has gone in, it is done
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
      var t = now(), n = S.anims.length;
      return { mode: S.mode, playing: S.playing, stop: S.stop, cursor: Math.min(S.stop, n - 1), auto: S.auto,
        running: S.run ? S.run.j : null, since: S.run ? t - S.run.at : null, shown: S.shown,
        line: S.line ? { B: S.line.B, total: S.line.total, at: S.mode === 'off' ? 0 : along(t) / S.line.total } : null,
        swaps: S.anims.filter(function (f) { return f.swap; }).map(function (f) { return { id: f.id, state: f.state }; }),
        flows: S.anims.map(function (f) { return { id: f.id, kind: f.kind, hops: f.hops.length, dur: f.dur, end: f.end,
          hopTimes: f.hops.map(function (h) { return [h.t0, h.t1]; }),
          beats: f.hops.map(function (h) { return h.beat ? [h.b0, h.b1] : null; }),       // a station's or a waypoint's beat
          legs: f.hops.map(function (h) { return !!h.legEnd; }) }; }) };   // every animation (a swap: kind 'swap', no hops)
    }
  };
  window.axFlows = api;
})();
