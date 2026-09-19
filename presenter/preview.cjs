// Screenshot pages of the built HTML for eyeballing. Usage: node preview.cjs [pageNums...]
// PNGs land in $TMPDIR/presenter-preview/prev-N.png.
const { chromium } = require('@playwright/test');
const path = require('path');
const fs = require('fs');
const os = require('os');
const CONJ = path.resolve(__dirname, '..');
const OUTDIR = path.join(os.tmpdir(), 'presenter-preview');
fs.mkdirSync(OUTDIR, { recursive: true });
(async () => {
  const which = process.argv.slice(2).map(Number); // page indexes to shoot (1-based)
  const b = await chromium.launch({
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--no-sandbox', '--hide-scrollbars'],
  });
  const p = await b.newContext({ viewport: { width: 1123, height: 794 }, deviceScaleFactor: 1.6 })
    .then(c => c.newPage());
  await p.goto('file://' + path.join(CONJ, 'livecode-presenter.html'), { waitUntil: 'networkidle' });
  const n = await p.locator('.pg').count();
  console.log('pages:', n, '· writing to', OUTDIR);
  const list = which.length ? which : [...Array(n)].map((_, i) => i + 1);
  for (const i of list) {
    const el = p.locator('.pg').nth(i - 1);
    await el.scrollIntoViewIfNeeded();
    await el.screenshot({ path: path.join(OUTDIR, `prev-${i}.png`) });
    console.log('shot page', i);
  }
  await b.close();
})();
