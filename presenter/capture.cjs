// Capture browser figures for the live-coding presenter script.
// Usage: node capture.cjs <tag>
// Drives a swiftshader Chromium (the MCP browser can't rasterize in this box).
// Reverse-direction highlights are driven by opening a second /dev/ws socket
// from the page context and sending a `cursor` message; the server broadcasts
// the matching `highlight` back to the page's inspector socket.
const { chromium } = require('@playwright/test');
const path = require('path');

const OUT = path.resolve(__dirname, '..', 'figures', 'talk');
const URL = `http://127.0.0.1:${process.env.PORT || 8080}/`;  // run-tag.sh sets PORT
const VIEW = { width: 1440, height: 1900 };

// Shot plans per tag. Each shot:
//   { name, inspect, hover, cursor, clip }
//   inspect: 'on' | 'off'        -> localStorage.inspector before load
//   hover:   selector            -> hover it (element/component breadcrumb)
//   cursor:  {file,line,col}      -> inject an editor WS cursor (reverse dir)
//   clip:    selectors[]         -> clip to the union bbox of these (+pad)
const PLANS = {
  'step-0': [
    { name: 's01-page', inspect: 'off' },
    { name: 's01-featured-crop', inspect: 'off', clip: ['.featured'] },
  ],
  'step-4': [
    // element-only breadcrumb: main > section > article > div > h2 > span
    { name: 's06-hover-badge', inspect: 'on', hover: '.featured .badge.hot',
      clip: ['.insp-box', '.insp-label'] },
  ],
  'step-5': [
    // component breadcrumb: page > featured > recipe-card > ... > rating > star
    { name: 's07-hover-star', inspect: 'on', hover: '.featured .rating .star',
      clip: ['.insp-box', '.insp-label'] },
  ],
  'step-7': [
    // reverse direction (element cursors -> identical at step-6 and step-7)
    { name: 's08-desc-9',   inspect: 'on', cursor: { file: 'demo/views.clj', line: 22, col: 10 } },
    { name: 's08-badges-3', inspect: 'on', cursor: { file: 'demo/views.clj', line: 19, col: 12 } },
    { name: 's08-stars-45', inspect: 'on', cursor: { file: 'demo/ui/views.clj', line: 23, col: 6 } },
    // call-site cursors (need step-7)
    { name: 's09-grid-8',     inspect: 'on', cursor: { file: 'demo/views.clj', line: 81, col: 10 } },
    { name: 's09-featured-1', inspect: 'on', cursor: { file: 'demo/views.clj', line: 38, col: 6 } },
    { name: 's09-rating-9',   inspect: 'on', cursor: { file: 'demo/views.clj', line: 24, col: 8 } },
    // folded () / lambda glyph breadcrumb on the featured card's star
    { name: 's09-hover-glyphs', inspect: 'on', hover: '.featured .rating .star',
      clip: ['.insp-box', '.insp-label'] },
  ],
};

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

async function drive(page, shot) {
  await page.goto(URL, { waitUntil: 'networkidle' });
  await page.waitForTimeout(500); // let the page's inspector WS connect

  if (shot.hover) {
    await page.hover(shot.hover);
    // nudge so the overlay's document mousemove (capture) fires
    const box = await page.locator(shot.hover).first().boundingBox();
    if (box) await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.waitForSelector('.insp-label', { state: 'visible', timeout: 3000 }).catch(() => {});
    await page.waitForTimeout(250);
  }

  if (shot.cursor) {
    const res = await page.evaluate((cur) => new Promise((resolve) => {
      const ws = new WebSocket('ws://' + location.host + '/dev/ws');
      let done = false;
      const finish = (v) => { if (!done) { done = true; resolve(v); } };
      ws.onopen = () => { ws.send(JSON.stringify(Object.assign({ type: 'cursor' }, cur))); };
      ws.onerror = () => finish('ws-error');
      setTimeout(() => finish('sent'), 700);
    }), shot.cursor);
    // let the highlight boxes render
    await page.waitForTimeout(600);
    const n = await page.evaluate(() =>
      document.querySelectorAll('.insp-hl, .insp-frame').length);
    console.log(`   cursor ${JSON.stringify(shot.cursor)} -> ${res}, ${n} boxes`);
  }

  let clip = null;
  if (shot.clip) {
    clip = await unionBBox(page, shot.clip);
    if (!clip) console.log(`   WARN: clip selectors matched nothing: ${shot.clip}`);
  }
  const path = `${OUT}/${shot.name}.png`;
  await page.screenshot(clip ? { path, clip } : { path });
  console.log(`   wrote ${path}${clip ? ' (clipped)' : ''}`);
}

(async () => {
  const tag = process.argv[2];
  const plan = PLANS[tag];
  if (!plan) { console.error('no plan for', tag); process.exit(2); }
  const browser = await chromium.launch({
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--no-sandbox', '--hide-scrollbars'],
  });
  console.log(`== ${tag}: ${plan.length} shots ==`);
  for (const shot of plan) {
    const ctx = await browser.newContext({ viewport: VIEW, deviceScaleFactor: 2 });
    await ctx.addInitScript((v) => {
      try { localStorage.setItem('inspector', v); } catch (e) {}
    }, shot.inspect === 'on' ? '1' : '0');
    const page = await ctx.newPage();
    console.log(` - ${shot.name} (inspect ${shot.inspect || 'off'})`);
    try { await drive(page, shot); }
    catch (e) { console.log(`   ERROR ${shot.name}: ${e.message}`); }
    await ctx.close();
  }
  await browser.close();
  console.log('done', tag);
})();
