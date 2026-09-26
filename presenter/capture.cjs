// Capture browser figures for the presenter deck and the projector slides.
// Usage: node capture.cjs <step> [shot…]  (run-tag.sh boots the demo at <step> first;
//                                         naming shots runs only those, in plan order)
//        node capture.cjs --headed <step> <shot>   (internal: see DEVTOOLS, below)
//
// The talk demonstrates only the finished app live, so every intermediate
// state the run-sheet narrates (no data-* yet, a crumb without names, the
// manual load-file loop, the REPL-strip sharp edge …) reaches the audience as
// a slide captured here, from the matching step branch. (Slide numbers in
// the comments below are the run-sheet's slide numbers.)
//
// Drives a swiftshader Chromium (the MCP browser can't rasterize in this box).
// Reverse-direction highlights are driven by opening a second /dev/ws socket
// from the page context and sending a `cursor` message; the server broadcasts
// the matching `highlight` back to the page's inspector socket.
//
// Fonts: every browser runs with FONTCONFIG_FILE=fonts.conf, which rejects
// Unifont. Without it, this container's Chromium draws 🌶 (U+1F336, text
// presentation) from Unifont, a pixel font — blown up in the zooms it is
// jagged pixel art, while the stage browser (demo/browser/Dockerfile) draws
// it in colour from Noto Color Emoji.
//
// Headless browsers never see an X display: DISPLAY is dropped from their
// environment. The one headed shot runs under its own Xvfb (see DEVTOOLS);
// the host's forwarded display (:0) is never used.
const { chromium } = require('@playwright/test');
const path = require('path');
const fs = require('fs');
const os = require('os');
const net = require('net');
const { spawnSync, execFileSync } = require('child_process');

const OUT = path.resolve(__dirname, '..', 'figures', 'talk');
const FONTS = path.join(__dirname, 'fonts.conf');
// run-tag.sh sets PORT to $CAPTURE_PORT. Never default to 8080: that is the
// speaker's own app, and some shots below reload views over the REPL.
const PORT = +(process.env.PORT || process.env.CAPTURE_PORT || 8090);
const URL = `http://127.0.0.1:${PORT}/`;
const REPL_PORT = +(process.env.CAPTURE_REPL_PORT || 5557);        // run-tag.sh's socket REPL
const DEVTOOLS_PORT = +(process.env.CAPTURE_DEVTOOLS_PORT || 9333); // DevTools frontend (see DEVTOOLS)
const V720 = { width: 1280, height: 720 };    // the slide figures: a 16:9 laptop viewport

if (PORT === 8080) { console.error('capture.cjs: refusing port 8080 (the speaker\'s app)'); process.exit(2); }

// ---------------------------------------------------------------------------
// Clip rules, evaluated in the page (CSS px, viewport-relative — Playwright
// clips to the viewport, so every viewport below is tall enough for its clip).
const CLIPS = {
  // The title-row strip (slides 4 and 29) — the `.guide` contract with
  // slides-template.html: the strip is cut around the featured NEW badge so
  // that NEW spans exactly 25%–75% of its height and starts at 45% of its
  // width, and the slide's two hairlines, drawn from 45% to the right edge at
  // 25% and 75%, are NEW's top and bottom edges carried on past the pill. The
  // width is fixed (250), and NEW does not move when the pill's rule is
  // removed, so the crooked and straight strips flip pixel-stable. The title
  // and the pill must fit inside (checked).
  titleRow: () => {
    const r = (s) => document.querySelector(s).getBoundingClientRect();
    const h2 = r('.featured h2'), nw = r('.featured .badge:not(.hot)'), pill = r('.featured .badge.hot');
    const W = 250, x = nw.left - 0.45 * W;
    if (h2.left - x < 8 || pill.right - x > W - 8)
      throw new Error(`titleRow: title ${h2.left}..pill ${pill.right} does not fit ${W} px from ${x}`);
    return { x, y: nw.top - nw.height / 2, width: W, height: 2 * nw.height };
  },
  // Slides 6/7: the featured card's top — "recipe of the day" label, orange
  // border, photo edge and the title row — down to the description.
  featuredStrip: () => {
    const r = (s) => document.querySelector(s).getBoundingClientRect();
    const f = r('.featured'), fp = r('.featured p');
    return { x: f.left - 8, y: f.top - 8, width: 520, height: fp.top - (f.top - 8) };
  },
  // … and the same title row on a grid card (Pad Thai, the grid's second
  // card): the card alone, with the photo's bottom edge above the title.
  gridStrip: () => {
    const q = (s) => document.querySelector('.cards > article:nth-child(2) ' + s).getBoundingClientRect();
    const c = document.querySelector('.cards > article:nth-child(2)').getBoundingClientRect();
    const ph = q('.photo'), p = q('p');
    return { x: c.left - 8, y: ph.bottom - 24, width: c.width + 16, height: p.top - (ph.bottom - 24) };
  },
  // Slides 35/36/39: one fixed frame for every cursor shot — the featured
  // card through the grid — so the lit boxes flip against the same page.
  reverse: () => {
    const f = document.querySelector('.featured').getBoundingClientRect();
    const c = document.querySelector('.cards').getBoundingClientRect();
    return { x: f.left - 8, y: f.top - 8, width: f.width + 16, height: c.bottom + 8 - (f.top - 8) };
  },
  // The overlay popups (slides 28, 32, 40): the hovered card's title row
  // from its left edge — so the audience sees which pill or star — to the
  // label's right end, and down to the top of the next row (`until`: the
  // description under a pill, the tag pills under a star). Cut on the page's
  // own row edges, not through them.
  popup: ({ card, until }) => {
    const c = document.querySelector(card);
    const h2 = c.querySelector('h2').getBoundingClientRect();
    const end = c.querySelector(until).getBoundingClientRect();
    const lab = document.querySelector('.insp-label').getBoundingClientRect();
    const box = document.querySelector('.insp-box').getBoundingClientRect();
    const x = h2.left - 16, y = Math.min(lab.top, h2.top) - 12;
    return { x, y, width: Math.max(lab.right, box.right) + 16 - x, height: end.top - y };
  },
  // Slide 43: one frame for the three shots of the §10 sharp edge, on the
  // recipe of the day (its breadcrumbs fit inside the card, so no neighbour
  // shows): from the breadcrumb over the title row down to the top of the
  // tag row, and across the hovered description's box. Taken on the first
  // shot (the hovered description) and reused (clipAs), so before, after and
  // the star flip against the same pixels.
  plainEdge: ({ card, until }) => {
    const c = document.querySelector(card);
    const h2 = c.querySelector('h2').getBoundingClientRect();
    const end = c.querySelector(until).getBoundingClientRect();
    const lab = document.querySelector('.insp-label').getBoundingClientRect();
    const box = document.querySelector('.insp-box').getBoundingClientRect();
    const x = h2.left - 16, y = Math.min(lab.top, h2.top) - 12;
    return { x, y, width: Math.max(lab.right, box.right) + 16 - x, height: end.top - y };
  },
  // Slide 5 (page panel): the title row with DevTools' tooltip above the pill
  // (the tooltip's top sits ~35 px above the pill), cut where the description
  // begins — like the strips — rather than through its first line.
  devtoolsPill: () => {
    const r = (s) => document.querySelector(s).getBoundingClientRect();
    const h2 = r('.featured h2'), pill = r('.featured .badge.hot'), desc = r('.featured p');
    return { x: h2.left - 16, y: pill.top - 48, width: 420, height: desc.top - (pill.top - 48) };
  },
};

// ---------------------------------------------------------------------------
// The socket REPL (run-tag.sh boots the JVM with -Dclojure.server.repl on
// $CAPTURE_REPL_PORT). A form typed there is exactly a form typed at the
// speaker's REPL, or Calva's "Load/Evaluate buffer": a plain load-file, no
// watcher involved.
function replEval(form, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    const s = net.connect(REPL_PORT, '127.0.0.1');
    let buf = '', sent = false;
    const t = setTimeout(() => { s.destroy(); reject(new Error(`REPL timeout on ${form}: ${buf}`)); }, timeoutMs);
    s.setEncoding('utf8');
    s.on('data', (d) => {
      buf += d;
      if (!sent && /=> $/.test(buf)) { sent = true; buf = ''; s.write(form + '\n'); return; }
      if (sent && /\S+=> $/.test(buf)) {
        clearTimeout(t);
        s.end(':repl/quit\n');
        const out = buf.replace(/\S+=> $/, '').trim();
        if (/^(Execution|Syntax) error|Exception/m.test(out)) reject(new Error(`REPL: ${form}\n${out}`));
        else resolve(out);
      }
    });
    s.on('error', (e) => { clearTimeout(t); reject(new Error(`REPL on :${REPL_PORT}: ${e.message}`)); });
  });
}

// The REPL must belong to the server we screenshot — a REPL-side reload in
// another JVM would leave the shots silently unchanged.
async function replServer() {
  const port = await replEval('(System/getenv "PORT")');
  if (port !== `"${PORT}"`) throw new Error(`REPL on :${REPL_PORT} serves PORT ${port}, not ${PORT}`);
  return JSON.parse(await replEval('(System/getProperty "user.dir")'));
}

// Slides 6/7 — the §1 manual loop, at step-0. The talk types 🔥 into the
// badge (views.clj line 21: "🌶 " -> "🌶🔥 "), saves, refreshes (nothing:
// step-0 has no watcher, so the saved-only page equals the untouched one —
// that is the s01-badges-* pair), then runs (load-file "src/demo/views.clj")
// and refreshes. The capture must not touch the demo tree, so it writes the
// edited file to a temp copy and load-files that copy: the same forms, the
// same vars, the same page.
async function loadFireEdit() {
  const cwd = await replServer();
  const lines = fs.readFileSync(path.join(cwd, 'src/demo/views.clj'), 'utf8').split('\n');
  const want = '[:span.badge.hot "🌶 " t]';
  if (!lines[20].includes(want)) throw new Error(`views.clj line 21 is not ${want}: ${lines[20]}`);
  lines[20] = lines[20].replace('"🌶 "', '"🌶🔥 "');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'capture-'));
  const tmp = path.join(dir, 'views.clj');
  fs.writeFileSync(tmp, lines.join('\n'));
  let out;
  try { out = await replEval(`(load-file ${JSON.stringify(tmp)})`); }
  finally { fs.rmSync(dir, { recursive: true, force: true }); }
  console.log(`   REPL (load-file <copy with 🌶🔥>) -> ${out}`);
  if (out !== "#'demo.views/layout") throw new Error('unexpected load-file result: ' + out);
}

// Slide 43 — the §10 sharp edge, at step-7: a plain load of the real file
// (what Calva's "Load/Evaluate buffer" does). It re-defs the views with the
// default reader, so every tag from views.clj is gone, while the UI kit
// (demo/ui/views.clj, not reloaded) keeps its tags. The watcher stays silent:
// nothing changed on disk.
async function plainLoad() {
  await replServer();
  const out = await replEval('(load-file "src/demo/views.clj")');
  console.log(`   REPL (load-file "src/demo/views.clj") -> ${out}`);
  if (out !== "#'demo.views/layout") throw new Error('unexpected load-file result: ' + out);
}

// ---------------------------------------------------------------------------
// Shot plans per step. Each shot:
//   name                       -> ../figures/talk/<name>.png
//   viewport, dpr              -> per shot (default V720, 2)
//   inspect: 'on' | 'off'      -> localStorage.inspector before load
//   before: async fn           -> runs before the page loads (REPL forms)
//   style: [[from, to]]        -> edit the page's inline stylesheet after load
//   hover: {sel, at}           -> mouse onto the element's centre, or its
//                                 top-left 'corner' (+1,+1)
//   expect: 'crumb' | null     -> the overlay label's text must equal this
//                                 (whitespace ignored), or be hidden (null)
//   cursor: {file,line,col}    -> inject an editor WS cursor (reverse dir)
//   clip: selectors[]          -> clip to the union bbox of these (+16)
//         'name'               -> a CLIPS rule
//         {rule, …}            -> a CLIPS rule with arguments
//   clipAs: 'shot'             -> reuse that earlier shot's clip rect
//   more: [{name, clip}]       -> further clips from the same page load
//                                 (devtools: [{name, x}], other columns)
//   kind: 'devtools' | 'devtools-page' -> see DEVTOOLS
//
// The pill after §6. The talk fixes the crooked pill live in §6 (remove the
// `top: .45rem` rule from `.badge.hot` in style.css, save) and never reverts
// it: only the finished app runs on stage, so from then on the audience sees
// a straight pill. That edit is on no branch, so every shot of a later moment
// (step-5 and step-7: slides 32, 35, 36, 39, 40, 43) applies it to the
// page's inline stylesheet (style.css is inlined per request), exactly as
// slide 29's s06-straight-zoom does.
const STRAIGHT = [['position: relative; top: .45rem;', 'position: relative;']];
const PLANS = {
  'step-0': [
    // slide 2: the app as the audience first sees it
    { name: 's01-app', viewport: V720, dpr: 2 },
    // slide 4: the crooked pill (DPR 6: the strip is 250 CSS px wide)
    { name: 's01-crooked-zoom', viewport: V720, dpr: 6, clip: 'titleRow' },
    // slide 29: the same strip after the talk's live §6 fix — remove the
    // `top: .45rem` rule from .badge.hot. The fix is typed live on stage and
    // exists on no branch, so the capture applies exactly that edit to the
    // page's inline stylesheet (style.css is inlined per request).
    { name: 's06-straight-zoom', viewport: V720, dpr: 6, clip: 'titleRow', style: STRAIGHT },
    // slide 6: after the 🔥 edit is saved and the page refreshed — unchanged
    // (no watcher at step-0), i.e. the untouched page
    { name: 's01-badges-featured', viewport: V720, dpr: 4, clip: 'featuredStrip',
      more: [{ name: 's01-badges-grid', clip: 'gridStrip' }] },
    // slides 5 and 24: DevTools on the pill, at minute one (no data-*
    // attributes). Slide 24 sets it over step-3's rows (s05-devtools-data),
    // so both share one column range; slide 5 has it alone, cut to the rows'
    // text (s01-devtools-rows), which puts the DevTools type larger.
    { name: 's01-devtools-plain', kind: 'devtools', select: '.featured .badge.hot',
      frontend: { width: 1280, height: 360 }, dpr: 3, rows: ['<h2', '</h2>'], x: [76, 726],
      more: [{ name: 's01-devtools-rows', x: [76, 456] }] },
    { name: 's01-devtools-page', kind: 'devtools-page', select: '.featured .badge.hot', dpr: 3,
      clip: 'devtoolsPill' },
    // slide 7: after (load-file …) and a refresh — both badges 🌶🔥.
    // REPL-mutating: last in its step.
    { name: 's01-fire-featured', viewport: V720, dpr: 4, before: loadFireEdit, clip: 'featuredStrip',
      more: [{ name: 's01-fire-grid', clip: 'gridStrip' }] },
  ],
  'step-3': [
    // slide 24: the same pill, now carrying its source (and data-name="span")
    { name: 's05-devtools-data', kind: 'devtools', select: '.featured .badge.hot',
      frontend: { width: 1280, height: 360 }, dpr: 3, rows: ['<h2', '</h2>'], x: [76, 726] },
    // slide 25: the eight card roots all say the same line
    { name: 's05-devtools-cards', kind: 'devtools', select: '.cards > article',
      frontend: { width: 1280, height: 420 }, dpr: 3, rows: ['<section class="cards"', '</section>'], x: [40, 724] },
  ],
  'step-4': [
    // slide 28: the element-only breadcrumb on the crooked pill (before §6's fix)
    { name: 's06-popup-plain', viewport: V720, dpr: 3, inspect: 'on',
      hover: { sel: '.featured .badge.hot' }, clip: { rule: 'popup', card: '.featured', until: 'p' },
      expect: 'main ▸ section ▸ article ▸ div ▸ h2 ▸ span demo/views.clj:21:8' },
  ],
  'step-5': [
    // slide 32: the pill and a star, the whole tower named. The star is
    // hovered at its corner, off the path, so the leaf is the svg (`star`).
    { name: 's07-popup-pill', viewport: V720, dpr: 3, inspect: 'on', style: STRAIGHT,
      hover: { sel: '.featured .badge.hot' }, clip: { rule: 'popup', card: '.featured', until: 'p' },
      expect: 'page ▸ featured ▸ recipe-card ▸ div ▸ h2 ▸ span demo/views.clj:21:8' },
    { name: 's07-popup-names', viewport: V720, dpr: 3, inspect: 'on', style: STRAIGHT,
      hover: { sel: '.featured .rating .star', at: 'corner' }, clip: { rule: 'popup', card: '.featured', until: 'ul.tags' },
      expect: 'page ▸ featured ▸ recipe-card ▸ div ▸ div ▸ rating ▸ star demo/ui/views.clj:19:1' },
  ],
  'step-7': [
    // slides 35/36 (backups): the editor cursor lights the page
    ...[['s08-cursor-desc', 'demo/views.clj', 22, 10],       // [:p description] -> nine
        ['s08-cursor-new', 'demo/views.clj', 19, 12],        // [:span.badge "NEW"] -> three
        ['s08-cursor-stars', 'demo/ui/views.clj', 23, 6],    // star's body -> 45
        // slide 39 (backup): the two call sites of recipe-card
        ['s09-callsite-grid', 'demo/views.clj', 81, 10],     // the grid's (recipe-card r) -> eight
        ['s09-callsite-featured', 'demo/views.clj', 38, 6],  // featured's (recipe-card r) -> one
    ].map(([name, file, line, col]) => ({ name, viewport: { width: 1280, height: 1700 }, dpr: 2,
      inspect: 'on', style: STRAIGHT, cursor: { file, line, col }, clip: 'reverse' })),
    // slide 40 (backup): every component folded into name + () λ
    { name: 's09-popup-glyphs', viewport: V720, dpr: 3, inspect: 'on', style: STRAIGHT,
      hover: { sel: '.featured .rating .star', at: 'corner' }, clip: { rule: 'popup', card: '.featured', until: 'ul.tags' },
      expect: 'page ▸ featured () λ ▸ recipe-card () λ ▸ div ▸ div ▸ rating () λ ▸ star () λ demo/ui/views.clj:19:1' },
    // slide 43 (backup): the §10 sharp edge, on the recipe of the day, in one
    // frame. REPL-mutating: last in its step.
    // Before: the card's description is inspectable …
    { name: 's10-plain-before', viewport: V720, dpr: 3, inspect: 'on', style: STRAIGHT,
      hover: { sel: '.featured p' }, clip: { rule: 'plainEdge', card: '.featured', until: 'ul.tags' },
      expect: 'page ▸ featured () λ ▸ recipe-card () λ ▸ div ▸ p demo/views.clj:22:5' },
    // … after a plain (load-file "src/demo/views.clj") and a reload, the same
    // hover finds nothing …
    { name: 's10-plain-dead', viewport: V720, dpr: 3, inspect: 'on', style: STRAIGHT,
      before: plainLoad, hover: { sel: '.featured p' }, clipAs: 's10-plain-before', expect: null },
    // … while a star, from the untouched UI kit, still answers.
    { name: 's10-plain-star', viewport: V720, dpr: 3, inspect: 'on', style: STRAIGHT,
      hover: { sel: '.featured .rating .star', at: 'corner' }, clipAs: 's10-plain-before',
      expect: 'rating ▸ star () λ demo/ui/views.clj:19:1' },
  ],
};

// ---------------------------------------------------------------------------
function unionBBox(page, selectors) {
  return page.evaluate((sels) => {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, n = 0;
    for (const s of sels) {
      for (const el of document.querySelectorAll(s)) {
        const st = getComputedStyle(el);
        if (st.display === 'none' || st.visibility === 'hidden') continue;
        const r = el.getBoundingClientRect();
        if (!r.width && !r.height) continue;
        x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top);
        x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom); n++;
      }
    }
    if (!n) return null;
    const pad = 16;
    x0 = Math.max(0, x0 - pad); y0 = Math.max(0, y0 - pad);
    x1 = Math.min(innerWidth, x1 + pad); y1 = Math.min(innerHeight, y1 + pad);
    return { x: x0, y: y0, width: x1 - x0, height: y1 - y0 };
  }, selectors);
}

async function resolveClip(page, clip, name) {
  if (!clip) return null;
  const c = typeof clip === 'string' ? await page.evaluate(CLIPS[clip])
    : clip.rule ? await page.evaluate(CLIPS[clip.rule], clip) : await unionBBox(page, clip);
  if (!c) throw new Error(`clip ${JSON.stringify(clip)} matched nothing`);
  const vp = page.viewportSize();
  if (c.x < 0 || c.y < 0 || c.x + c.width > vp.width + 0.01 || c.y + c.height > vp.height + 0.01)
    throw new Error(`${name}: clip ${JSON.stringify(c)} leaves the ${vp.width}x${vp.height} viewport`);
  return c;
}

const norm = (s) => (s || '').replace(/\s+/g, '');

async function hoverAt(page, h) {
  const loc = page.locator(h.sel).first();
  await loc.scrollIntoViewIfNeeded();
  const b = await loc.boundingBox();
  const [x, y] = h.at === 'corner' ? [b.x + 1, b.y + 1] : [b.x + b.width / 2, b.y + b.height / 2];
  // two moves: the overlay listens to document mousemove (capture phase)
  await page.mouse.move(x - 3, y - 3);
  await page.mouse.move(x, y);
  await page.waitForTimeout(400);
}

async function sendCursor(page, cur) {
  const res = await page.evaluate((cur) => new Promise((resolve) => {
    const ws = new WebSocket('ws://' + location.host + '/dev/ws');
    let done = false;
    const finish = (v) => { if (!done) { done = true; resolve(v); } };
    ws.onopen = () => { ws.send(JSON.stringify(Object.assign({ type: 'cursor' }, cur))); };
    ws.onerror = () => finish('ws-error');
    setTimeout(() => finish('sent'), 700);
  }), cur);
  // let the highlight boxes render (and their .5s pulse settle)
  await page.waitForTimeout(900);
  const n = await page.evaluate(() => ({
    hl: document.querySelectorAll('.insp-hl').length,
    frames: document.querySelectorAll('.insp-frame').length }));
  console.log(`   cursor ${JSON.stringify(cur)} -> ${res}, ${n.hl} lit, ${n.frames} frames`);
}

const kept = {}; // clip rects by shot name, for clipAs

async function drive(page, shot) {
  await page.goto(URL, { waitUntil: 'networkidle' });
  await page.waitForTimeout(500); // let the page's inspector WS connect

  if (shot.style) {
    const ok = await page.evaluate((edits) => {
      const s = [...document.querySelectorAll('head style')].find((x) => edits.every(([a]) => x.textContent.includes(a)));
      if (!s) return false;
      for (const [a, b] of edits) s.textContent = s.textContent.replace(a, b);
      return true;
    }, shot.style);
    if (!ok) throw new Error(`style edit found no stylesheet with ${JSON.stringify(shot.style)}`);
    await page.waitForTimeout(200);
  }

  if (shot.hover) {
    await hoverAt(page, shot.hover);
    const label = await page.evaluate(() => {
      const l = document.querySelector('.insp-label');
      return l && getComputedStyle(l).display !== 'none' ? l.textContent : null;
    });
    console.log(`   hover ${shot.hover.sel}${shot.hover.at ? ' @' + shot.hover.at : ''} -> ${label === null ? '(no label)' : label}`);
    if ('expect' in shot) {
      const ok = shot.expect === null ? label === null : norm(label) === norm(shot.expect);
      if (!ok) throw new Error(`label ${JSON.stringify(label)} != expected ${JSON.stringify(shot.expect)}`);
    }
  }

  if (shot.cursor) await sendCursor(page, shot.cursor);

  const outs = [{ name: shot.name, clip: shot.clip, clipAs: shot.clipAs }, ...(shot.more || [])];
  for (const o of outs) {
    const clip = o.clipAs ? kept[o.clipAs] : await resolveClip(page, o.clip, o.name);
    if (o.clipAs && !clip) throw new Error(`${o.name}: no kept clip from ${o.clipAs}`);
    kept[o.name] = clip;
    const file = `${OUT}/${o.name}.png`;
    await page.screenshot(clip ? { path: file, clip } : { path: file });
    console.log(`   wrote ${file}${clip ? ' clip ' + JSON.stringify(roundRect(clip)) : ''}`);
  }
}

const roundRect = (c) => Object.fromEntries(Object.entries(c).map(([k, v]) => [k, +v.toFixed(1)]));

// ---------------------------------------------------------------------------
// DEVTOOLS — the real Chrome DevTools UI, never a mock-up. Two recipes:
//
// kind 'devtools' (the Elements panel, slides 5, 24, 25): a headless Chromium
// started with --remote-debugging-port serves the DevTools frontend itself
// (http://127.0.0.1:$CAPTURE_DEVTOOLS_PORT/devtools/inspector.html?ws=…). One
// context loads the app page (1280x720); a second context opens the frontend
// on that page's target, at the shot's size and DPR. Then, as a person would:
// toggle the frontend's screencast off (the Elements panel gets the width),
// Esc for the console drawer, `inspect(document.querySelector(SEL))`, Enter,
// Esc. The node is selected in Elements, the tree expanded to it and
// scrolled into view. The figure is a clip of the frontend page: x as given
// (CSS px; `more` cuts further figures from the same rows at other x), y from the row starting with rows[0] − 4 to the first row after
// it starting with rows[1], cut on the rows' own edges (any padding would
// show slivers of the neighbouring rows). The frontend's own default (light)
// theme.
//
// kind 'devtools-page' (Chrome's inspect highlight on the page, slide 5): the
// highlight and its tooltip ("span.badge.hot 64.89 × 19.52") are drawn by the
// browser's overlay, which no page screenshot contains (headless or headed;
// Overlay.highlightNode alone drew nothing either). So this shot runs a
// HEADED Chromium on a private Xvfb display — capture.cjs re-runs itself as
// `xvfb-run -n 99 -a node capture.cjs --headed <step> <shot>`, which picks
// :99 or the next free display, never the host's :0 — puts the page in
// DevTools' "select an element" mode (Overlay.setInspectMode searchForNode,
// the highlight colours DevTools uses), moves the real mouse onto the element
// and grabs the X screen (PIL ImageGrab) — checked for the tooltip and the
// fill, and retried, since the overlay does not always paint on the first
// hover (see GRAB_CHECK). The window has no decorations (no
// window manager), so the viewport starts at x 0, y (outerHeight −
// innerHeight)·DPR. No mouse pointer is drawn (the grab has none).

function browserEnv({ keepDisplay = false } = {}) {
  const env = { ...process.env, FONTCONFIG_FILE: FONTS };
  if (!keepDisplay) delete env.DISPLAY;
  return env;
}

async function captureDevtools(shot) {
  const browser = await chromium.launch({
    env: browserEnv(),
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--no-sandbox', '--hide-scrollbars',
      `--remote-debugging-port=${DEVTOOLS_PORT}`, '--remote-allow-origins=*'],
  });
  try {
    const ctx = await browser.newContext({ viewport: V720, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    await page.goto(URL, { waitUntil: 'networkidle' });
    const list = await (await fetch(`http://127.0.0.1:${DEVTOOLS_PORT}/json/list`)).json();
    const tgt = list.find((t) => t.type === 'page' && t.url.startsWith(URL));
    if (!tgt) throw new Error('no DevTools target for ' + URL);
    const fctx = await browser.newContext({ viewport: shot.frontend, deviceScaleFactor: shot.dpr });
    const fe = await fctx.newPage();
    await fe.goto(`http://127.0.0.1:${DEVTOOLS_PORT}/devtools/inspector.html?ws=127.0.0.1:${DEVTOOLS_PORT}/devtools/page/${tgt.id}`);
    await fe.locator('ol.elements-tree-outline li').first().waitFor({ timeout: 15000 });
    await fe.waitForTimeout(1500);
    const tog = fe.locator('[aria-label="Toggle screencast"]');
    if (await tog.count()) { await tog.first().click(); await fe.waitForTimeout(800); }
    await fe.mouse.move(shot.frontend.width - 5, shot.frontend.height - 5); // no hover on the tree
    await fe.keyboard.press('Escape'); await fe.waitForTimeout(800);
    await fe.keyboard.type(`inspect(document.querySelector('${shot.select}'))`);
    await fe.keyboard.press('Enter'); await fe.waitForTimeout(1500);
    await fe.keyboard.press('Escape'); await fe.waitForTimeout(1200);
    const rows = await fe.locator('ol.elements-tree-outline li').evaluateAll((els) => els.map((e) => {
      const r = e.getBoundingClientRect();
      return { text: (e.innerText || '').split('\n')[0].replace(/​/g, ''), sel: e.classList.contains('selected'),
               top: r.top, bottom: r.bottom, h: r.height };
    }));
    const vis = rows.filter((r) => r.h > 0);
    const i0 = vis.findIndex((r) => r.text.startsWith(shot.rows[0]));
    const i1 = vis.findIndex((r, i) => i > i0 && r.text.startsWith(shot.rows[1]));
    const selected = vis.find((r) => r.sel);
    if (i0 < 0 || i1 < 0 || !selected) throw new Error(`rows ${shot.rows} not found (selected: ${selected && selected.text})`);
    // every row of the clip must be on screen: below the panel tabs (~27 px),
    // above the element breadcrumb bar at the bottom (~23 px)
    const y0 = vis[i0].top, y1 = vis[i1].bottom;
    if (vis[i0].top < 30 || vis[i1].bottom > shot.frontend.height - 26)
      throw new Error(`rows ${y0}..${y1} not all visible in the ${shot.frontend.height}px-high frontend`);
    console.log(`   devtools selected: ${selected.text}`);
    for (const r of vis.slice(i0, i1 + 1)) console.log(`     | ${r.text}`);
    for (const o of [{ name: shot.name, x: shot.x }, ...(shot.more || [])]) {
      const clip = { x: o.x[0], y: y0, width: o.x[1] - o.x[0], height: y1 - y0 };
      const file = `${OUT}/${o.name}.png`;
      await fe.screenshot({ path: file, clip });
      console.log(`   wrote ${file} clip ${JSON.stringify(roundRect(clip))}`);
    }
  } finally {
    await browser.close();
  }
}

// Runs in the parent: re-run this script headed under a private Xvfb.
function captureDevtoolsPage(step, shot) {
  const env = browserEnv();
  // headed Chromium puts its singleton socket under $TMPDIR, and a unix
  // socket path must fit 108 bytes: a long TMPDIR kills the browser at start
  if (os.tmpdir().length > 60) env.TMPDIR = '/tmp';
  const r = spawnSync('xvfb-run', ['-n', '99', '-a', '-s', '-screen 0 3840x2700x24',
    process.execPath, __filename, '--headed', step, shot.name],
  { env, stdio: 'inherit', timeout: 120000 });
  if (r.status !== 0) throw new Error(`headed capture exited ${r.status}${r.error ? ' ' + r.error.message : ''}`);
}

// Grab the X screen, crop, save; report what the inspect highlight left in
// the crop: purple pixels (the tooltip's tag name), dark-blue pixels (its
// class list) and, inside the element's box, the share of pixels bluer than
// red (the content fill). argv: file, crop box (4), element box in the crop (4).
const GRAB_CHECK = `
import sys, os, json
from PIL import ImageGrab
a = [int(v) for v in sys.argv[2:10]]
im = ImageGrab.grab(xdisplay=os.environ["DISPLAY"]).crop(a[:4]).convert("RGB")
im.save(sys.argv[1])
px, (w, h) = im.load(), im.size
tag = cls = 0
for y in range(h):
    for x in range(w):
        r, g, b = px[x, y]
        if 90 < r < 180 and g < 70 and 90 < b < 180: tag += 1
        elif r < 80 and g < 80 and b > 130: cls += 1
x0, y0, x1, y1 = a[4:]
box = [px[x, y] for y in range(max(0, y0), min(h, y1)) for x in range(max(0, x0), min(w, x1))]
fill = sum(1 for r, g, b in box if b > r) / max(1, len(box))
print(json.dumps({"tag": tag, "cls": cls, "fill": round(fill, 2)}))
`;

// Runs in the child, under xvfb-run.
async function headed(step, name) {
  const shot = (PLANS[step] || []).find((s) => s.name === name);
  const disp = process.env.DISPLAY || '';
  const num = +(disp.match(/^:(\d+)/) || [])[1];
  if (!shot || shot.kind !== 'devtools-page') throw new Error(`no devtools-page shot ${name} in ${step}`);
  if (!(num >= 99)) throw new Error(`refusing DISPLAY ${JSON.stringify(disp)}: run under xvfb-run -n 99 -a`);
  const dpr = shot.dpr;
  const browser = await chromium.launch({
    headless: false,
    env: browserEnv({ keepDisplay: true }),
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--no-sandbox', '--hide-scrollbars',
      `--force-device-scale-factor=${dpr}`, '--window-position=0,0', '--window-size=1280,900'],
  });
  try {
    const ctx = await browser.newContext({ viewport: null });
    const page = await ctx.newPage();
    await page.goto(URL, { waitUntil: 'networkidle' });
    await page.bringToFront();
    const cdp = await ctx.newCDPSession(page);
    await cdp.send('DOM.enable');
    await cdp.send('Overlay.enable');
    await cdp.send('Overlay.setInspectMode', { mode: 'searchForNode', highlightConfig: {
      showInfo: true, showStyles: false, showAccessibilityInfo: false,
      contentColor: { r: 111, g: 168, b: 220, a: 0.66 }, paddingColor: { r: 147, g: 196, b: 125, a: 0.55 },
      borderColor: { r: 255, g: 229, b: 153, a: 0.66 }, marginColor: { r: 246, g: 178, b: 107, a: 0.66 } } });
    const b = await page.locator(shot.select).first().boundingBox();
    const g = await page.evaluate(() => ({ iw: innerWidth, ih: innerHeight, ow: outerWidth, oh: outerHeight,
      sx: screenX, sy: screenY, dpr: devicePixelRatio }));
    if (g.dpr !== dpr || g.iw !== 1280) throw new Error('unexpected window geometry ' + JSON.stringify(g));
    const c = await page.evaluate(CLIPS[shot.clip]);
    const ox = g.sx * dpr + (g.ow - g.iw) * dpr, oy = g.sy * dpr + (g.oh - g.ih) * dpr;
    const box = [c.x * dpr + ox, c.y * dpr + oy, (c.x + c.width) * dpr + ox, (c.y + c.height) * dpr + oy].map(Math.round);
    // the element, in the crop's pixels (for the check below)
    const el = [(b.x - c.x) * dpr, (b.y - c.y) * dpr, (b.x + b.width - c.x) * dpr, (b.y + b.height - c.y) * dpr].map(Math.round);
    const file = `${OUT}/${shot.name}.png`;
    // The overlay does not always paint on the first hover (a grab 300 ms in
    // is often bare, and a whole run can come out bare), and a page grab
    // cannot tell. So every grab is checked for what Chrome draws: the
    // tooltip's tag name ("span", purple) and class list (".badge.hot", dark
    // blue), and the element's content box filled blue (over the red pill,
    // blue outweighs red). Otherwise: mouse off, back on, grab again — five
    // tries, then fail rather than ship a bare title row.
    for (let tryNo = 1; ; tryNo++) {
      await page.mouse.move(b.x + 10, b.y + 8);
      await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
      await page.waitForTimeout(1500);
      const seen = JSON.parse(execFileSync('python3', ['-c', GRAB_CHECK, file, ...box.map(String), ...el.map(String)]).toString());
      console.log(`   headed ${disp} try ${tryNo}: ${JSON.stringify(seen)}`);
      if (seen.tag >= 150 && seen.cls >= 300 && seen.fill >= 0.5) break;
      if (tryNo === 5) throw new Error(`no inspect highlight after ${tryNo} tries: ${JSON.stringify(seen)}`);
      await page.mouse.move(5, 5);
      await page.waitForTimeout(500);
    }
    console.log(`   headed ${disp} ${JSON.stringify(g)}; wrote ${file} crop ${JSON.stringify(box)}`);
  } finally {
    await browser.close();
  }
}

// ---------------------------------------------------------------------------
(async () => {
  if (process.argv[2] === '--headed') {
    try { await headed(process.argv[3], process.argv[4]); }
    catch (e) { console.error(`   ERROR (headed): ${e.message}`); process.exit(1); }
    return;
  }
  const tag = process.argv[2], only = process.argv.slice(3);
  const plan = (PLANS[tag] || []).filter((s) => !only.length || only.includes(s.name));
  if (!plan.length) { console.error('no plan for', tag, only.join(' ')); process.exit(2); }
  let browser = null;
  const browserFor = async () => (browser ||= await chromium.launch({
    env: browserEnv(),
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--no-sandbox', '--hide-scrollbars'],
  }));
  console.log(`== ${tag}: ${plan.length} shots ==`);
  let failed = 0;
  for (const shot of plan) {
    console.log(` - ${shot.name}${shot.kind ? ' (' + shot.kind + ')' : ` (inspect ${shot.inspect || 'off'})`}`);
    try {
      if (shot.kind === 'devtools') { await captureDevtools(shot); continue; }
      if (shot.kind === 'devtools-page') { captureDevtoolsPage(tag, shot); continue; }
      if (shot.before) await shot.before();
      const ctx = await (await browserFor()).newContext({ viewport: shot.viewport || V720, deviceScaleFactor: shot.dpr || 2 });
      await ctx.addInitScript((v) => {
        try { localStorage.setItem('inspector', v); } catch (e) {}
      }, shot.inspect === 'on' ? '1' : '0');
      const page = await ctx.newPage();
      try { await drive(page, shot); }
      finally { await ctx.close(); }
    } catch (e) {
      failed++;
      console.log(`   ERROR ${shot.name}: ${e.message}`);
    }
  }
  if (browser) await browser.close();
  console.log(`done ${tag}${failed ? ` — ${failed} shot(s) FAILED` : ''}`);
  process.exit(failed ? 1 : 0);
})();
