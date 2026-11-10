#!/usr/bin/env node
'use strict';
/* 建置微信小遊戲（wechat/）所需的檔案：
 *   1. 把共用的 engine.js、themes.js、texts.js、server/form.js 複製到 wechat/js/lib/
 *   2. 產生手機版直式棋盤（tools/make_board_svg.py --mobile），並轉成 JPG
 *   3. 把每個主題的 54 張牌畫成一張拼版 JPG，並匯出牌的說明文字（wechat/js/data/cardinfo.js）
 *   4. 產生瀏覽器預覽用的 tools/wechat-preview/bundle.js
 * 主套件上限 4 MB，因此每個主題的棋盤與牌圖放在各自的分包 wechat/themes/<主題>/（選定主題時才下載），
 * 主套件只放程式；分包清單寫入 game.json。
 * 圖片以本機的 Google Chrome（無頭模式）繪製。
 * 執行：node tools/build_wechat.js　（可用 CHROME=/path/to/chrome 指定瀏覽器） */
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn, execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const OUT = path.join(ROOT, 'wechat');
const THEMES = require('../themes.js').order; // 所有主題
const CELL = [240, 336], COLS = 9; // 與 wechat/js/main.js 相同
const BOARD_PX = [1900, 2630];

const CHROME = process.env.CHROME || [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
].find(p => fs.existsSync(p));

const sleep = ms => new Promise(r => setTimeout(r, ms));

function copyLibs() {
  const lib = path.join(OUT, 'js', 'lib');
  fs.mkdirSync(lib, { recursive: true });
  for (const [src, dst] of [['engine.js', 'engine.js'], ['themes.js', 'themes.js'], ['texts.js', 'texts.js'], ['server/form.js', 'form.js']]) {
    fs.copyFileSync(path.join(ROOT, src), path.join(lib, dst));
  }
  console.log('copied shared modules → wechat/js/lib/');
}

function mobileBoards(dir) {
  execFileSync('python3', ['-I', path.join(ROOT, 'tools', 'make_board_svg.py'), '--mobile', dir], { stdio: 'inherit' });
  return Object.fromEntries(THEMES.map(t => [t, fs.readFileSync(path.join(dir, `board-${t}-mobile.svg`), 'utf8')]));
}

/* ---- 無頭 Chrome（只在本機 127.0.0.1 開除錯埠） ---- */
async function withChrome(fn) {
  if (!CHROME) throw new Error('找不到 Google Chrome；請以 CHROME=/path/to/chrome 指定');
  const prof = fs.mkdtempSync(path.join(os.tmpdir(), 'bg-chrome-'));
  const proc = spawn(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files',
    '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0', `--user-data-dir=${prof}`, 'about:blank'], { stdio: 'ignore' });
  try {
    let port;
    for (let k = 0; k < 100 && !port; k++) {
      try { port = fs.readFileSync(path.join(prof, 'DevToolsActivePort'), 'utf8').split('\n')[0]; } catch { await sleep(100); }
    }
    if (!port) throw new Error('Chrome 沒有啟動');
    let tgt;
    for (let k = 0; k < 50 && !tgt; k++) {
      try { tgt = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(t => t.type === 'page'); } catch { /* 再試 */ }
      if (!tgt) await sleep(100);
    }
    const ws = new WebSocket(tgt.webSocketDebuggerUrl);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    let id = 0; const wait = new Map();
    ws.onmessage = e => { const m = JSON.parse(e.data); if (wait.has(m.id)) { wait.get(m.id)(m); wait.delete(m.id); } };
    const cmd = (method, params = {}) => new Promise(r => { const i = ++id; wait.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
    const evaluate = async (expr) => {
      const m = await cmd('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
      if (m.result && m.result.exceptionDetails) throw new Error(JSON.stringify(m.result.exceptionDetails).slice(0, 800));
      return m.result.result.value;
    };
    const r = await fn({ cmd, evaluate });
    ws.close();
    return r;
  } finally {
    proc.kill();
    await sleep(200);
    fs.rmSync(prof, { recursive: true, force: true });
  }
}

// 在頁面中把 SVG 畫到畫布並輸出 JPG（data URL）
const PAGE_HELPERS = `
window.__svgToImg = svg => new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = rej;
  im.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg); });
`;

async function render(boards) {
  return withChrome(async ({ cmd, evaluate }) => {
    await cmd('Page.enable');
    await cmd('Page.navigate', { url: 'file://' + path.join(ROOT, 'index.html') });
    for (let k = 0; k < 100; k++) { if (await evaluate('!!(window.cardSvg && window.SanguoEngine && document.readyState === "complete")')) break; await sleep(100); }
    await evaluate(PAGE_HELPERS);
    const out = { boards: {}, cards: {}, info: {} };
    for (const t of THEMES) {
      // 棋盤
      out.boards[t] = await evaluate(`(async () => {
        const im = await __svgToImg(${JSON.stringify(boards[t])});
        const c = document.createElement('canvas'); c.width = ${BOARD_PX[0]}; c.height = ${BOARD_PX[1]};
        const g = c.getContext('2d'); g.fillStyle = '#fbf3a6'; g.fillRect(0, 0, c.width, c.height); g.drawImage(im, 0, 0, c.width, c.height);
        return { full: c.toDataURL('image/jpeg', 0.84) };
      })()`);
      // 牌：拼成一張圖；並匯出說明文字
      const r = await evaluate(`(async () => {
        const E = window.SanguoEngine;
        E.applyTheme(${JSON.stringify(t)}); window.setCardTheme(${JSON.stringify(t)});
        window.cardSvg(E.CARDS[0]); // 讓 cards.js 放入共用的漸層定義
        const defs = document.getElementById('cgSh').closest('svg').innerHTML;
        const [w, h] = ${JSON.stringify(CELL)}, cols = ${COLS}, rows = Math.ceil(E.CARDS.length / cols);
        const c = document.createElement('canvas'); c.width = w * cols; c.height = h * rows;
        const g = c.getContext('2d'); g.fillStyle = '#fffdf6'; g.fillRect(0, 0, c.width, c.height);
        const info = {};
        for (const card of E.CARDS) {
          const svg = window.cardSvg(card).replace(/^<svg([^>]*)>/, (m, a) => '<svg' + a + ' width="' + w + '" height="' + h + '">' + defs);
          const im = await __svgToImg(svg);
          g.drawImage(im, (card.id % cols) * w, Math.floor(card.id / cols) * h, w, h);
          info[card.id] = window.cardInfoHtml(card, E.KIND_HELP[card.kind] || '');
        }
        return { img: c.toDataURL('image/jpeg', 0.86), info };
      })()`);
      out.cards[t] = r.img; out.info[t] = r.info;
      console.log('rendered', t);
    }
    return out;
  });
}

const writeDataUrl = (file, url) => { fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64')); return fs.statSync(file).size; };

function bundlePreview() {
  // 把小遊戲的 CommonJS 模組包成一個檔案，供瀏覽器預覽（tools/wechat-preview/index.html）
  const files = [];
  (function walk(d) {
    for (const f of fs.readdirSync(d)) {
      const p = path.join(d, f);
      if (fs.statSync(p).isDirectory()) walk(p); else if (f.endsWith('.js')) files.push(p);
    }
  })(OUT);
  const mods = files.map(p => {
    const rel = path.relative(OUT, p).split(path.sep).join('/');
    return `${JSON.stringify(rel)}: function (module, exports, require) {\n${fs.readFileSync(p, 'utf8')}\n}`;
  });
  const src = `// 由 tools/build_wechat.js 產生，請勿手動修改
(function () {
const MODS = {
${mods.join(',\n')}
};
const cache = {};
function load(id) {
  if (cache[id]) return cache[id].exports;
  if (!MODS[id]) throw new Error('找不到模組 ' + id);
  const module = { exports: {} }; cache[id] = module;
  const dir = id.includes('/') ? id.slice(0, id.lastIndexOf('/')) : '';
  MODS[id].call(module.exports, module, module.exports, rel => {
    const parts = (dir ? dir.split('/') : []);
    for (const s of rel.split('/')) { if (s === '..') parts.pop(); else if (s !== '.') parts.push(s); }
    let p = parts.join('/'); if (!p.endsWith('.js')) p += '.js';
    return load(p);
  });
  return module.exports;
}
window.__startGame = () => load('game.js');
})();
`;
  fs.writeFileSync(path.join(ROOT, 'tools', 'wechat-preview', 'bundle.js'), src);
  console.log('wrote tools/wechat-preview/bundle.js');
}

async function main() {
  copyLibs();
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bg-boards-'));
  const boards = mobileBoards(tmp);
  fs.rmSync(tmp, { recursive: true, force: true });
  const r = await render(boards);
  for (const d of ['images', 'themes']) fs.rmSync(path.join(OUT, d), { recursive: true, force: true });
  for (const t of THEMES) {
    const dir = path.join(OUT, 'themes', t);
    fs.mkdirSync(dir, { recursive: true });
    const a = writeDataUrl(path.join(dir, 'board.jpg'), r.boards[t].full);
    const b = writeDataUrl(path.join(dir, 'cards.jpg'), r.cards[t]);
    fs.writeFileSync(path.join(dir, 'game.js'), '// 分包進入點（本分包只放這個主題的圖片）\n');
    console.log(`themes/${t}/: board ${(a / 1024).toFixed(0)} KB, cards ${(b / 1024).toFixed(0)} KB`);
  }
  // 分包清單
  const gj = path.join(OUT, 'game.json'), conf = JSON.parse(fs.readFileSync(gj, 'utf8'));
  conf.subpackages = THEMES.map(t => ({ name: t, root: `themes/${t}/` }));
  fs.writeFileSync(gj, JSON.stringify(conf, null, 2) + '\n');
  // 版本標記（建置時間）一併寫入 cardinfo.js 的 BUILD，顯示在設定畫面最下方，方便確認手機上跑的是哪一版
  const d = new Date(), pad = n => String(n).padStart(2, '0');
  const stamp = `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}`;
  fs.mkdirSync(path.join(OUT, 'js', 'data'), { recursive: true });
  fs.rmSync(path.join(OUT, 'js', 'data', 'version.js'), { force: true });
  fs.writeFileSync(path.join(OUT, 'js', 'data', 'cardinfo.js'),
    `'use strict';\n// 由 tools/build_wechat.js 產生：每個主題、每張牌的說明（HTML），以及建置版本 BUILD\nmodule.exports = ${JSON.stringify({ ...r.info, BUILD: stamp })};\n`);
  console.log('build', stamp);
  bundlePreview();
  // 主套件不得超過 4 MB，全部（含分包）不得超過 30 MB
  const size = d => fs.readdirSync(d).reduce((a, f) => { const p = path.join(d, f), st = fs.statSync(p); return a + (st.isDirectory() ? size(p) : st.size); }, 0);
  const MB = n => (n / 1024 / 1024).toFixed(2) + ' MB';
  const total = size(OUT), subs = size(path.join(OUT, 'themes')), main_ = total - subs;
  console.log(`main package ${MB(main_)} (limit 4 MB); subpackages ${MB(subs)}; total ${MB(total)} (limit 30 MB)`);
  if (main_ > 4 * 1024 * 1024 || total > 30 * 1024 * 1024) { console.error('套件超過大小上限'); process.exitCode = 1; }
}
main().catch(e => { console.error(e); process.exit(1); });
