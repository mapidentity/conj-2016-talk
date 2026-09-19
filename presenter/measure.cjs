// Report each .pg height; flags any page that overflows one A4-landscape sheet (794px @96dpi).
const { chromium } = require('@playwright/test');
const path = require('path');
const CONJ = path.resolve(__dirname, '..');
(async () => {
  const b = await chromium.launch({ args:['--use-gl=angle','--use-angle=swiftshader','--no-sandbox'] });
  const p = await b.newContext({ viewport:{width:1123,height:794}, deviceScaleFactor:1 }).then(c=>c.newPage());
  await p.goto('file://' + path.join(CONJ, 'livecode-presenter.html'),{waitUntil:'networkidle'});
  const rows = await p.evaluate(() => {
    const px794 = 794; // 210mm @96dpi
    return [...document.querySelectorAll('.pg')].map((el,i) => {
      const h = el.getBoundingClientRect().height;
      const t = el.querySelector('.ptitle')?.textContent || el.querySelector('h1')?.textContent || '(cover)';
      return { i:i+1, h: Math.round(h), over: h > px794+2 ? 'OVER by '+Math.round(h-px794) : '', t: t.slice(0,42) };
    });
  });
  for (const r of rows) console.log(String(r.i).padStart(2), String(r.h).padStart(4), (r.over||'ok').padEnd(14), r.t);
  await b.close();
})();
