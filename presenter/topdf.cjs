// HTML -> print-ready A4-landscape PDF. Run: NODE_PATH=<global node_modules> node topdf.cjs
const { chromium } = require('@playwright/test');
const path = require('path');
const CONJ = path.resolve(__dirname, '..');   // talk/
(async () => {
  const b = await chromium.launch({
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--no-sandbox'],
  });
  const p = await b.newPage();
  await p.goto('file://' + path.join(CONJ, 'livecode-presenter.html'), { waitUntil: 'networkidle' });
  await p.pdf({
    path: path.join(CONJ, 'livecode-presenter.pdf'),
    width: '297mm', height: '210mm',       // A4 landscape, matches @page
    printBackground: true,
    margin: { top: '0', bottom: '0', left: '0', right: '0' },
  });
  await b.close();
  console.log('pdf written');
})();
