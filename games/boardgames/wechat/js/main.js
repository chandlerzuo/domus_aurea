'use strict';
/* 微信小遊戲版：設定畫面、遊戲畫面、對話框、觸控
 * 規則引擎（lib/engine.js）與網頁版共用；本檔把引擎的 UI 介面接到畫布上。 */
const E = require('./lib/engine.js');
const TX = require('./lib/texts.js');
const { makeForm } = require('./lib/form.js');
const CARD_INFO = require('./data/cardinfo.js');
const BUILD = CARD_INFO.BUILD || '';
const { SIZE, COLOR, font, fillR, rrect, ellipsize, wrapText } = require('./gfx.js');
const R = require('./rich.js');
const { BoardView, BOXES, BW, BH } = require('./board.js');

/* ---------------- 平台 ---------------- */
const sys = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
const W = sys.windowWidth, H = sys.windowHeight, DPR = sys.pixelRatio || 2;
const canvas = wx.createCanvas();
canvas.width = Math.round(W * DPR); canvas.height = Math.round(H * DPR);
const ctx = canvas.getContext('2d');
const safeTop = Math.max((sys.safeArea && sys.safeArea.top) || 0, sys.statusBarHeight || 20);
const safeBottom = sys.safeArea && sys.safeArea.bottom ? Math.max(0, H - sys.safeArea.bottom) : 0;
// 右上角的系統膠囊按鈕：畫面避開它
let menu = wx.getMenuButtonBoundingClientRect ? wx.getMenuButtonBoundingClientRect() : null;
if (!menu || !menu.width) menu = { top: safeTop + 4, bottom: safeTop + 36, left: W - 95, right: W - 7, width: 88, height: 32 };
const GAME_NAME = '英雄擲天下', TAGLINE = '擲骰行軍，攻城略地——古今英雄任你調遣。';
if (wx.showShareMenu) wx.showShareMenu({ menus: ['shareAppMessage', 'shareTimeline'] });
if (wx.onShareAppMessage) wx.onShareAppMessage(() => ({ title: `${GAME_NAME}：擲骰行軍，攻城略地` }));
if (wx.onShareTimeline) wx.onShareTimeline(() => ({ title: `${GAME_NAME}：擲骰行軍，攻城略地` }));

const IMG = {};
let dirty = true;
const requestDraw = () => { dirty = true; };
function loadImg(src) {
  if (IMG[src]) return IMG[src];
  const im = wx.createImage(); im.onload = requestDraw; im.src = src; IMG[src] = im; return im;
}
// 每個主題的棋盤與牌圖放在各自的分包（themes/<主題>/），用到時才下載；主套件只有設定畫面用的小圖
const themePack = {}; // 主題 → { done, progress, p }
function ensureTheme(key) {
  const st = themePack[key] || (themePack[key] = { done: false, progress: 0, p: null });
  if (st.done) return Promise.resolve();
  if (st.p) return st.p;
  st.p = new Promise((res, rej) => {
    if (!wx.loadSubpackage) { st.done = true; res(); return; }
    const task = wx.loadSubpackage({ name: key,
      success: () => { st.done = true; requestDraw(); res(); },
      fail: e => { st.p = null; requestDraw(); rej(e); } });
    if (task && task.onProgressUpdate) task.onProgressUpdate(r => { st.progress = r.progress || 0; requestDraw(); });
  });
  return st.p;
}
const themeReady = key => !!(themePack[key] && themePack[key].done);
const boardImg = key => themeReady(key) ? loadImg(`themes/${key}/board.jpg`) : null;
const cardsImg = key => themeReady(key) ? loadImg(`themes/${key}/cards.jpg`) : null;
const SHEET_COLS = 9, CELL_W = 240, CELL_H = 336; // 牌圖拼版：每張 240×336，每列 9 張

/* ---------------- 狀態 ---------------- */
const COMMANDERS = [0, 1, 2, 3];
const SPEEDS = [['慢 5秒', 900], ['中 3秒', 450], ['快 2秒', 120]]; // 秒數：電腦每個動作的消息停留時間
const app = { screen: 'setup', theme: 'sanguo', view: null, logs: [], lastLog: '', turn: null, gen: 0, setupScroll: 0 };
const setup = Object.assign({ theme: 'sanguo', n: 4, seats: [false, true, true, true].map((ai, k) => ({ ai, cmd: k })), speed: 450 },
  (() => { try { return wx.getStorageSync('setup') || {}; } catch (e) { return {}; } })());
const saveSetup = () => { try { wx.setStorageSync('setup', setup); } catch (e) { /* 存不了就算了 */ } };
const board = new BoardView(requestDraw);

function useTheme(key) {
  if (!E.THEMES[key]) key = 'sanguo';
  app.theme = key;
  E.applyTheme(key);
  board.img = boardImg(key);
  cardsImg(key);
  // 下載這個主題的分包，完成後換上棋盤與牌圖
  ensureTheme(key).then(() => { if (app.theme === key) { board.img = boardImg(key); cardsImg(key); requestDraw(); } }, () => {});
  requestDraw();
}
useTheme(setup.theme);

/* ---------------- 牌 ---------------- */
function drawCard(c, id, x, y, w) {
  const h = Math.round(w * CELL_H / CELL_W), im = cardsImg(app.theme), r = Math.max(3, w * 0.07);
  c.save(); rrect(c, x, y, w, h, r); c.clip();
  if (im && im.width) c.drawImage(im, (id % SHEET_COLS) * CELL_W, Math.floor(id / SHEET_COLS) * CELL_H, CELL_W, CELL_H, x, y, w, h);
  else { c.fillStyle = '#fffdf6'; c.fillRect(x, y, w, h); c.fillStyle = COLOR.ink; c.font = font(Math.max(10, w * 0.16), 700); c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(E.CARDS[id].name, x + w / 2, y + h / 2); c.textAlign = 'left'; }
  c.restore();
  rrect(c, x, y, w, h, r); c.strokeStyle = '#a89f8a'; c.lineWidth = 1; c.stroke();
}

/* ---------------- 對話框（由下往上的面板） ---------------- */
const sheets = [];
let docVersion = 0;
function openSheet(o) {
  const root = R.parse(o.html || '');
  const sh = { title: o.title || '', root, inputs: R.collectInputs(root), errors: {}, buttons: o.buttons || [], onPress: o.onPress, scroll: 0, ver: 0, cache: null, toBottom: !!o.toBottom, onClose: o.onClose };
  sheets.push(sh); requestDraw();
  return sh;
}
function closeSheet(sh) { const k = sheets.indexOf(sh); if (k >= 0) sheets.splice(k, 1); if (sh.onClose) sh.onClose(); requestDraw(); }
// 只有「確定」的說明面板
const infoSheet = (title, html, o = {}) => openSheet({ title, html, buttons: [{ label: '關閉', cls: 'pri' }], onPress: () => true, ...o });

// 引擎的提問：回傳 Promise，值為所按按鈕的 value
function engineAsk(title, body, buttons) {
  return new Promise(resolve => {
    const sh = openSheet({
      title: R.plainText(title), html: body,
      buttons: buttons.map(b => ({ label: R.plainText(b.label), cls: b.cls, disabled: !!b.disabled })),
      onPress: k => {
        let v = buttons[k].value;
        if (typeof v === 'function') {
          const form = makeForm(sh.inputs);
          v = v(form);
          if (v === undefined) { sh.errors = form.errors; sh.ver++; requestDraw(); return false; }
        }
        resolve(v); return true;
      },
    });
  });
}

function sheetGeom(sh) {
  const sw = Math.min(W - 12, 560), sx = (W - sw) / 2, pad = 16, bw = sw - pad * 2;
  const env = { inputs: sh.inputs, errors: sh.errors, cardW: Math.min(84, Math.floor((bw - 24) / 4)), drawCard,
    onChange: () => { sh.ver++; requestDraw(); }, onCard: id => cardSheet(id) };
  if (!sh.cache || sh.cache.ver !== sh.ver) sh.cache = { ver: sh.ver, doc: R.layout(sh.root, bw, ctx, env) };
  const doc = sh.cache.doc;
  // 按鈕：兩個以內且放得下時並排，否則每個一列
  ctx.font = font(SIZE.button, 700);
  const n = sh.buttons.length;
  const half = (bw - 10) / 2;
  const row = n <= 2 && sh.buttons.every(b => ctx.measureText(b.label).width + 24 <= (n === 1 ? bw : half));
  const bh = 50, btnH = !n ? 0 : row ? bh : n * bh + (n - 1) * 8;
  ctx.font = font(SIZE.title, 700);
  const titleLines = sh.title ? wrapText(ctx, sh.title, font(SIZE.title, 700), bw) : [];
  const titleH = titleLines.length * 28;
  const maxH = H - Math.max(menu.bottom + 8, H * 0.12);
  const fixed = pad + titleH + (titleH ? 10 : 0) + 14 + btnH + pad + safeBottom;
  const bodyH = Math.max(0, Math.min(doc.h, maxH - fixed));
  const shH = fixed + bodyH;
  const sy = H - shH;
  const maxScroll = Math.max(0, doc.h - bodyH);
  if (sh.toBottom) { sh.scroll = maxScroll; sh.toBottom = false; }
  sh.scroll = Math.max(0, Math.min(maxScroll, sh.scroll));
  return { sx, sy, sw, shH, pad, bw, doc, titleLines, bodyY: sy + pad + titleH + (titleH ? 10 : 0), bodyH, maxScroll, row, bh, btnY: H - safeBottom - pad - btnH };
}
function drawSheet(sh, top) {
  const g = sheetGeom(sh);
  // 背景變暗並擋住下層的點按
  ctx.fillStyle = COLOR.dim; ctx.fillRect(0, 0, W, H);
  addHit({ x: 0, y: 0, w: W, h: H, block: true });
  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,.35)'; ctx.shadowBlur = 16;
  fillR(ctx, g.sx, g.sy, g.sw, g.shH + 20, 18, COLOR.paper);
  ctx.restore();
  ctx.fillStyle = COLOR.ink; ctx.font = font(SIZE.title, 700); ctx.textBaseline = 'middle';
  g.titleLines.forEach((t, k) => ctx.fillText(t, g.sx + g.pad, g.sy + g.pad + 14 + k * 28));
  // 內容（可捲動）
  ctx.save(); ctx.beginPath(); ctx.rect(g.sx, g.bodyY - 4, g.sw, g.bodyH + 8); ctx.clip();
  R.drawOps(ctx, g.doc.ops, g.sx + g.pad, g.bodyY - sh.scroll);
  ctx.restore();
  if (g.maxScroll > 0) { // 捲動提示
    const th = Math.max(30, g.bodyH * g.bodyH / g.doc.h), ty = g.bodyY + (g.bodyH - th) * (sh.scroll / g.maxScroll);
    fillR(ctx, g.sx + g.sw - 7, ty, 4, th, 2, 'rgba(0,0,0,.25)');
  }
  if (top) {
    addHit({ x: g.sx, y: g.bodyY, w: g.sw, h: g.bodyH, scroll: { get: () => sh.scroll, set: v => { sh.scroll = Math.max(0, Math.min(g.maxScroll, v)); requestDraw(); } } });
    for (const h of g.doc.hits) {
      const y = g.bodyY - sh.scroll + h.y;
      const y0 = Math.max(y, g.bodyY), y1 = Math.min(y + h.h, g.bodyY + g.bodyH);
      if (y1 > y0) addHit({ x: g.sx + g.pad + h.x, y: y0, w: h.w, h: y1 - y0, tap: h.tap, hold: h.hold });
    }
  }
  // 按鈕
  sh.buttons.forEach((b, k) => {
    const n = sh.buttons.length;
    const bw = g.row ? (n === 1 ? g.bw : (g.bw - 10) / 2) : g.bw;
    const x = g.sx + g.pad + (g.row ? k * (bw + 10) : 0), y = g.btnY + (g.row ? 0 : k * (g.bh + 8));
    button(x, y, bw, g.bh, b.label, { pri: b.cls === 'pri', disabled: b.disabled || !top, key: sh, k,
      tap: async () => { if (await sh.onPress(k)) closeSheet(sh); } });
  });
}

/* ---------------- 點按區 ---------------- */
let hits = [];
const addHit = h => hits.push(h);
let touch = null; // { x0, y0, x, y, target, scroller, board, moved, key, k }
function button(x, y, w, h, label, o = {}) {
  const pressed = touch && !touch.moved && touch.target && touch.target.key === o.key && touch.target.k === o.k && o.key != null;
  const pri = o.pri && !o.disabled;
  fillR(ctx, x, y, w, h, 12, o.disabled ? COLOR.disabled : pri ? (pressed ? '#8e2c22' : COLOR.pri) : (pressed ? '#dccca4' : (o.bg || COLOR.btn)), o.border || (pri ? null : COLOR.line), 1.5);
  ctx.fillStyle = pri ? COLOR.priInk : o.disabled ? '#8a8272' : (o.ink || COLOR.btnInk);
  ctx.font = font(o.size || SIZE.button, 700); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(ellipsize(ctx, label, ctx.font, w - 12), x + w / 2, y + h / 2 + 1); ctx.textAlign = 'left';
  if (!o.disabled && o.tap) addHit({ x, y, w, h, tap: o.tap, key: o.key, k: o.k });
}

/* ---------------- 共用面板 ---------------- */
const pnameHtml = p => `<b style="color:${p.color}">${E.esc(p.name)}</b>`;
const levelName = i => E.TILES[i].t === 'field' ? '古戰場' : E.LEVEL_NAME[app.view.tiles[i].level];
function cardSheet(id) {
  const c = E.CARDS[id];
  const owner = app.view && app.view.players.find(p => p.commander === id);
  infoSheet(c.name, `<div class="cards" style="justify-content:center"><span class="cw" data-cid="${id}"></span></div>`
    + ((CARD_INFO[app.theme] || {})[id] || '') + (owner ? `<p><b style="color:#a8740a">★ ${E.esc(owner.name)}的主帥</b></p>` : ''));
}
function tileSheet(i) {
  const T = E.TILES[i];
  const html = E.isProp(i) ? TX.tileInfoHtml(E, i, app.view, pnameHtml, levelName) : `<p>${TX.spaceHelp(E, T)}</p>`;
  infoSheet(T.n, html);
}
function playerSheet(p) {
  let html = `<p>軍費 <b>${E.fmt(p.cash)}</b>・兵力 <b>${p.troops}</b> 名・領地 <b>${p.owned}</b> 處</p>`;
  if (p.groups.length) html += `<p>同色全收：${p.groups.map(g => E.GROUPS[g]).join('、')}</p>`;
  if (p.rest) html += `<p>休息中，尚需休息 ${p.rest} 次</p>`;
  if (p.hand) {
    html += `<p><b>手牌（點牌看說明）</b></p><div class="cards">${p.hand.map(id => `<div class="copt"><span class="cw" data-cid="${id}"></span>${id === p.commander ? '<span class="cmdbadge">★主帥</span>' : ''}</div>`).join('')}</div>`;
    if (p.reserve && p.reserve.length) html += `<p><b>保留卡</b>：${p.reserve.join('、')}</p>`;
  } else {
    html += `<p>主帥</p><div class="cards"><div class="copt"><span class="cw" data-cid="${p.commander}"></span>${p.hasCmd ? '' : '<span class="cmdbadge">不在手中</span>'}</div></div>`;
    html += `<p>手牌 ${p.cardN} 張${p.reserveN ? `・保留卡 ${p.reserveN} 張` : ''}</p>`;
    if (p.known.length) html += `<p>你記得的牌：</p><div class="cards">${p.known.map(id => `<div class="copt"><span class="cw" data-cid="${id}"></span></div>`).join('')}</div>`;
  }
  infoSheet(p.name, html);
}
const logSheet = () => infoSheet('戰報', app.logs.slice(-200).map(h => `<p>${h}</p>`).join('') || '<p>（尚無紀錄）</p>', { toBottom: true });
const rulesSheet = () => infoSheet('遊戲說明書', TX.rulesHtml(E));
function menuSheet() {
  const sh = openSheet({
    title: `${GAME_NAME}｜${E.THEMES[app.theme].label}`, html: '',
    buttons: [{ label: '遊戲說明' }, { label: '戰報紀錄' }, { label: '結束本局，回到設定' }, { label: '繼續遊戲', cls: 'pri' }],
    onPress: k => {
      if (k === 0) setTimeout(rulesSheet);
      if (k === 1) setTimeout(logSheet);
      if (k === 2) setTimeout(() => {
        openSheet({ title: '結束本局？', html: '<p>目前的進度不會保存。</p>', buttons: [{ label: '取消' }, { label: '結束', cls: 'pri' }],
          onPress: j => { if (j === 1) setTimeout(backToSetup); return true; } });
      });
      return true;
    },
  });
  return sh;
}

/* ---------------- 設定畫面 ---------------- */
function fixSeats() {
  setup.n = Math.max(2, Math.min(4, setup.n));
  while (setup.seats.length < 4) setup.seats.push({ ai: true, cmd: setup.seats.length });
  // 主帥不可重複：重複者改用第一個未被選用的主帥
  const used = new Set();
  for (let k = 0; k < setup.n; k++) {
    const s = setup.seats[k];
    if (used.has(s.cmd)) s.cmd = COMMANDERS.find(c => !used.has(c));
    used.add(s.cmd);
  }
}
function segmented(x, y, w, h, opts, cur, onPick, key) {
  const n = opts.length, sw = w / n;
  fillR(ctx, x, y, w, h, 10, '#fff', COLOR.line, 1.5);
  opts.forEach((o, k) => {
    const on = o[1] === cur;
    if (on) fillR(ctx, x + k * sw + 3, y + 3, sw - 6, h - 6, 8, COLOR.pri);
    ctx.fillStyle = on ? '#fff' : COLOR.ink; ctx.font = font(SIZE.body, 700); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(o[0], x + k * sw + sw / 2, y + h / 2 + 1); ctx.textAlign = 'left';
    addHit({ x: x + k * sw, y, w: sw, h, tap: () => onPick(o[1]), key, k });
  });
}
function drawSetup() {
  fixSeats();
  ctx.fillStyle = COLOR.bg; ctx.fillRect(0, 0, W, H);
  const x0 = 16, cw = W - 32;
  let y = menu.bottom + 10 - app.setupScroll;
  const startY = y;
  fillR(ctx, 8, y - 6, W - 16, 10000, 16, COLOR.paper); // 紙張背景（下方超出畫面）
  ctx.fillStyle = '#8b1a1a'; ctx.font = font(30, 700); ctx.textBaseline = 'middle';
  ctx.fillText(GAME_NAME, x0 + 4, y + 22);
  y += 46;
  ctx.fillStyle = COLOR.sub; ctx.font = font(SIZE.small);
  wrapText(ctx, TAGLINE, font(SIZE.small), cw - 8).forEach(l => { ctx.fillText(l, x0 + 4, y + 8); y += 21; });
  y += 12;
  // 主題
  ctx.fillStyle = COLOR.ink; ctx.font = font(SIZE.body, 700); ctx.fillText('選擇主題', x0, y + 12); y += 28;
  // 每列三個主題
  const keys = Object.keys(E.THEMES), cols = 3, gap = 10, tw = (cw - gap * (cols - 1)) / cols, tH = 150;
  keys.forEach((k, j) => {
    const T = E.THEMES[k], tx = x0 + (j % cols) * (tw + gap), ty = y + Math.floor(j / cols) * (tH + gap), on = k === setup.theme;
    const y_ = y; y = ty; // 以下沿用 y 為這一格的上緣
    // 不畫底框；選中的書加紅色外框
    const bh = tH - 30, bw = Math.min(tw - 16, bh * 0.72), bx = tx + (tw - bw) / 2;
    if (on) fillR(ctx, bx - 5, y + 3, bw + 10, bh + 10, 8, null, COLOR.pri, 3);
    drawBook(ctx, bx, y + 8, bw, bh, T.label, BOOK_COLOR[k] || '#3b4a5a');
    if (on) { ctx.fillStyle = COLOR.pri; ctx.font = font(SIZE.tiny, 700); ctx.textAlign = 'center'; ctx.fillText('✓ 已選擇', tx + tw / 2, y + tH - 11); ctx.textAlign = 'left'; }
    addHit({ x: tx, y, w: tw, h: tH, tap: () => { setup.theme = k; useTheme(k); saveSetup(); } });
    y = y_;
  });
  y += Math.ceil(keys.length / cols) * (tH + gap) + 6;
  // 人數
  ctx.fillStyle = COLOR.ink; ctx.font = font(SIZE.body, 700); ctx.fillText('參加人數', x0, y + 22);
  segmented(x0 + 90, y, cw - 90, 44, [['2 人', 2], ['3 人', 3], ['4 人', 4]], setup.n, v => { setup.n = v; saveSetup(); requestDraw(); }, 'n');
  y += 56;
  // 座位
  for (let k = 0; k < setup.n; k++) {
    const s = setup.seats[k];
    ctx.beginPath(); ctx.arc(x0 + 9, y + 22, 9, 0, Math.PI * 2); ctx.fillStyle = E.PLAYER_COLORS[k]; ctx.fill();
    ctx.fillStyle = COLOR.ink; ctx.font = font(SIZE.body, 700); ctx.fillText(`第${k + 1}位`, x0 + 24, y + 22);
    segmented(x0 + 82, y, 124, 44, [['人類', false], ['電腦', true]], s.ai, v => { s.ai = v; saveSetup(); requestDraw(); }, 'ai' + k);
    const c = E.CARDS[s.cmd];
    button(x0 + 214, y, cw - 214, 44, `主帥 ${c.name} ▾`, { size: SIZE.body, key: 'cmd', k,
      tap: () => commanderSheet(k) });
    y += 54;
  }
  y += 4;
  ctx.fillStyle = COLOR.ink; ctx.font = font(SIZE.body, 700); ctx.fillText('電腦速度', x0, y + 22);
  ctx.fillStyle = COLOR.sub; ctx.font = font(SIZE.tiny); ctx.fillText('（每步停留）', x0, y + 52);
  segmented(x0 + 90, y, cw - 90, 44, SPEEDS, setup.speed, v => { setup.speed = v; saveSetup(); requestDraw(); }, 'speed');
  y += 68;
  ctx.fillStyle = COLOR.sub; ctx.font = font(SIZE.small);
  wrapText(ctx, `佔有領地 ${E.S.winTerr} 處、收齊同色領地，或其他君主全部失敗即獲勝。`, font(SIZE.small), cw).forEach(l => { ctx.fillText(l, x0, y + 10); y += 21; });
  y += 10;
  button(x0, y, (cw - 12) * 0.38, 52, '遊戲說明', { key: 'rules', tap: rulesSheet });
  const pk = themePack[setup.theme], loading = !themeReady(setup.theme) && pk && pk.p;
  button(x0 + (cw - 12) * 0.38 + 12, y, (cw - 12) * 0.62, 52, loading ? `下載主題中 ${Math.round(pk.progress)}%` : '開始遊戲',
    { pri: true, size: loading ? SIZE.body : 19, key: 'start', tap: startClicked });
  y += 68;
  // 健康遊戲忠告（小遊戲平台要求顯示）
  ctx.fillStyle = COLOR.sub; ctx.font = font(SIZE.tiny); ctx.textAlign = 'center';
  ['健康遊戲忠告', '抵制不良遊戲，拒絕盜版遊戲。注意自我保護，謹防受騙上當。', '適度遊戲益腦，沉迷遊戲傷身。合理安排時間，享受健康生活。'].forEach(l => {
    wrapText(ctx, l, font(SIZE.tiny), cw).forEach(t => { ctx.fillText(t, W / 2, y + 8); y += 19; });
  });
  ctx.fillStyle = 'rgba(107,79,42,.6)'; ctx.font = font(12); ctx.fillText(`版本 ${BUILD}`, W / 2, y + 10); y += 22;
  ctx.textAlign = 'left';
  y += 12 + safeBottom;
  const contentH = y - startY, viewH = H - (menu.bottom + 10);
  const maxScroll = Math.max(0, contentH - viewH);
  // 捲動
  hits.unshift({ x: 0, y: 0, w: W, h: H, scroll: { get: () => app.setupScroll, set: v => { app.setupScroll = Math.max(0, Math.min(maxScroll, v)); requestDraw(); } } });
  // 膠囊按鈕那一列遮住捲上去的內容
  ctx.fillStyle = COLOR.bg; ctx.fillRect(0, 0, W, menu.bottom + 4);
}
// 古書（線裝書）封面：右側線裝，左上貼題簽，題簽上直書主題名稱
const BOOK_COLOR = { sanguo: '#23395b', shuihu: '#2f4a2b', fengshen: '#5b2333', xiyou: '#7a5418', chuhan: '#2b2626' };
function drawBook(c, x, y, w, h, title, color) {
  c.save();
  c.shadowColor = 'rgba(0,0,0,.35)'; c.shadowBlur = 6; c.shadowOffsetY = 3;
  fillR(c, x, y, w, h, 3, color);
  c.restore();
  // 書頁邊（下緣與左緣露出的紙頁）
  c.fillStyle = '#efe4c8'; c.fillRect(x + 2, y + h - 3, w - 4, 3);
  // 封面紋理：細框
  c.strokeStyle = 'rgba(255,255,255,.14)'; c.lineWidth = 1; c.strokeRect(x + 4, y + 4, w - 8, h - 8);
  // 右側線裝：四個訂孔與縫線
  const bx = x + w - Math.max(7, w * 0.11);
  c.strokeStyle = 'rgba(0,0,0,.35)'; c.beginPath(); c.moveTo(bx - 3, y + 2); c.lineTo(bx - 3, y + h - 2); c.stroke();
  c.strokeStyle = '#e8dcc0'; c.lineWidth = 1.6;
  for (let k = 0; k < 4; k++) {
    const hy = y + h * (0.12 + k * 0.253);
    c.beginPath(); c.moveTo(bx, hy); c.lineTo(x + w, hy); c.stroke();
    c.beginPath(); c.arc(bx, hy, 1.6, 0, Math.PI * 2); c.fillStyle = '#e8dcc0'; c.fill();
  }
  c.beginPath(); c.moveTo(bx, y + h * 0.12); c.lineTo(bx, y + h * 0.88); c.stroke();
  // 題簽：直書書名
  const n = title.length, sw = Math.max(16, w * 0.3), sh = h * 0.78, sx = x + w * 0.16, sy = y + h * 0.09;
  fillR(c, sx, sy, sw, sh, 2, '#f6efd9', '#b9a77d', 1);
  c.strokeStyle = '#c0392b'; c.lineWidth = 1; c.strokeRect(sx + 2.5, sy + 2.5, sw - 5, sh - 5);
  const fs = Math.min(sw * 0.72, (sh - 10) / n * 0.92);
  c.fillStyle = '#1b1b1b'; c.font = font(fs, 700); c.textAlign = 'center'; c.textBaseline = 'middle';
  const step = (sh - 10) / n;
  for (let k = 0; k < n; k++) c.fillText(title[k], sx + sw / 2, sy + 5 + step * (k + 0.5));
  c.textAlign = 'left';
}

function commanderSheet(k) {
  const used = setup.seats.slice(0, setup.n).map((s, j) => j !== k ? s.cmd : -1);
  const html = COMMANDERS.map(c => `<label class="opt"><input type="radio" name="c" value="${c}" ${c === setup.seats[k].cmd ? 'checked' : ''}> <b>${E.CARDS[c].name}</b>（${E.SUIT[E.CARDS[c].code[0]]}A）${used.includes(c) ? `　<small>第${used.indexOf(c) + 1}位已選</small>` : ''}</label>`).join('');
  const sh = openSheet({ title: `第${k + 1}位的主帥`, html, buttons: [{ label: '取消' }, { label: '確定', cls: 'pri' }],
    onPress: j => {
      if (j !== 1) return true;
      const pick = +sh.inputs.find(i => i.checked).value, other = used.indexOf(pick);
      if (other >= 0) setup.seats[other].cmd = setup.seats[k].cmd; // 與已選者互換
      setup.seats[k].cmd = pick; saveSetup(); return true;
    } });
}
function startClicked() {
  fixSeats(); saveSetup();
  if (!themeReady(setup.theme)) {
    ensureTheme(setup.theme).then(() => { if (app.screen === 'setup') startClicked(); },
      () => infoSheet('下載失敗', '<p>主題圖片下載失敗，請確認網路連線後再試一次。</p>'));
    requestDraw();
    return;
  }
  startGame(setup.seats.slice(0, setup.n).map(s => ({ ai: s.ai, cmd: s.cmd })),
    { aiDelay: setup.speed, theme: setup.theme, hints: { card: '長按牌可看說明', tile: '點格子可查看領地資訊，兩指可放大棋盤' } });
}
function backToSetup() {
  app.gen++; // 讓仍在執行的引擎停住
  sheets.length = 0; app.screen = 'setup'; app.view = null; app.turn = null; board.dice = null; feedReset();
  if (wx.setKeepScreenOn) wx.setKeepScreenOn({ keepScreenOn: false });
  requestDraw();
}

/* ---------------- 動態消息：電腦的每個行動逐條顯示 ----------------
 * 停留時間由引擎決定（opts.readMs：慢 5 秒、中 3 秒、快 2 秒）；引擎會等消息讀完才繼續。
 * UI.log(html, { dur, wait })：這條消息 wait 毫秒後出現、停留 dur 毫秒。點一下消息框可跳過。 */
const LINGER = 2500; // 讀完後消息框再留一會兒
const feed = { items: [] };
function feedPush(html, meta) {
  const now = Date.now();
  feed.items.push({ html, text: R.plainText(html), t0: now + (meta ? meta.wait : 0), dur: meta ? meta.dur : 0, cache: null });
  while (feed.items.length > 12 && now > feed.items[0].t0 + feed.items[0].dur) feed.items.shift();
  requestDraw();
}
function feedSkip() {
  E.skipReading();
  const now = Date.now();
  feed.items.forEach(it => { if (it.t0 > now) it.t0 = now; it.dur = Math.max(0, Math.min(it.dur, now - it.t0)); });
  requestDraw();
}
function feedReset() { feed.items = []; }
function feedVisible() {
  const last = feed.items[feed.items.length - 1];
  return !!last && Date.now() <= last.t0 + last.dur + LINGER;
}
function drawFeed() {
  if (sheets.length || !feedVisible() || !app.view) return;
  const now = Date.now(), shown = feed.items.filter(it => it.t0 <= now).slice(-3);
  if (!shown.length) return;
  const r = board.rect, pw = Math.min(r.w - 16, 520), px = r.x + (r.w - pw) / 2, pad = 12, bw = pw - pad * 2;
  const newest = shown[shown.length - 1], older = shown.slice(0, -1);
  const key = bw;
  if (!newest.cache || newest.cache.key !== key) {
    const env = { inputs: [], errors: {}, cardW: 40, drawCard, onChange() {}, onCard() {} };
    newest.cache = { key, doc: R.layout(R.parse(`<div style="font-size:17px">${newest.html}</div>`), bw, ctx, env) };
  }
  const doc = newest.cache.doc;
  const reading = feed.items.find(it => it.t0 <= now && now < it.t0 + it.dur);
  const ph = pad + older.length * 22 + (older.length ? 4 : 0) + doc.h + (reading ? 22 : 0) + pad - 4;
  // 放在目前玩家所在位置的另一半，避免擋住正在移動的旗幟
  const v = app.view, cur = v.cur != null ? v.players[v.cur] : null;
  let atTop = false;
  if (cur) { const [, by, , bh] = BOXES[cur.pos]; atTop = board.oy + (by + bh / 2) * board.s > r.y + r.h / 2; }
  const py = atTop ? r.y + 8 : r.y + r.h - ph - 8;
  ctx.save(); ctx.shadowColor = 'rgba(0,0,0,.35)'; ctx.shadowBlur = 10;
  fillR(ctx, px, py, pw, ph, 12, 'rgba(251,243,220,.97)', cur ? cur.color : COLOR.gold, 2.5);
  ctx.restore();
  let y = py + pad;
  ctx.font = font(SIZE.small); ctx.textBaseline = 'middle'; ctx.fillStyle = 'rgba(42,26,16,.6)';
  older.forEach(it => { ctx.fillText(ellipsize(ctx, it.text, ctx.font, bw), px + pad, y + 10); y += 22; });
  if (older.length) { ctx.fillStyle = COLOR.line; ctx.fillRect(px + pad, y, bw, 1); y += 4; }
  R.drawOps(ctx, doc.ops, px + pad, y);
  y += doc.h;
  if (reading) { // 閱讀進度與跳過提示
    const k = Math.max(0, Math.min(1, (now - reading.t0) / Math.max(1, reading.dur)));
    fillR(ctx, px + pad, y + 8, bw - 96, 5, 2.5, 'rgba(0,0,0,.1)');
    fillR(ctx, px + pad, y + 8, (bw - 96) * k, 5, 2.5, cur ? cur.color : COLOR.gold);
    ctx.fillStyle = COLOR.sub; ctx.font = font(SIZE.tiny); ctx.textAlign = 'right'; ctx.fillText('點一下跳過', px + pw - pad, y + 11); ctx.textAlign = 'left';
  }
  addHit({ x: px, y: py, w: pw, h: ph, tap: feedSkip, key: 'feed' });
}

/* ---------------- 遊戲 ---------------- */
function startGame(seats, opts) {
  const gen = ++app.gen;
  const live = () => gen === app.gen;
  const never = new Promise(() => {});
  app.screen = 'game'; app.logs = []; app.lastLog = ''; app.turn = null; sheets.length = 0; board.dice = null;
  feedReset();
  opts = { ...opts, ...(E.PACE[opts.aiDelay] || E.PACE[450]) };
  useTheme(opts.theme);
  layoutGame(); board.fit();
  if (wx.setKeepScreenOn) wx.setKeepScreenOn({ keepScreenOn: true });
  const S = () => E.state();
  // 視角：只有一位人類時為其本人；全電腦為旁觀；多位人類共用手機時不顯示手牌
  const viewerId = () => { const hs = S().players.filter(p => !p.ai); return hs.length === 1 ? hs[0].id : hs.length ? null : 'all'; };
  let lastViewer = null;
  const ui = {
    sleep: ms => live() ? new Promise(r => setTimeout(r, ms)) : never,
    log: (html, meta) => {
      if (!live()) return;
      app.logs.push(html); if (app.logs.length > 400) app.logs.shift(); app.lastLog = html;
      feedPush(html, meta);
    },
    dice: r => { board.dice = r; requestDraw(); },
    flash: k => board.flash(k),
    render: () => {
      if (!live()) return;
      const v = E.viewFor(viewerId()), prev = app.view;
      app.view = v;
      if (v.cur != null && (!prev || prev.players[v.cur].pos !== v.players[v.cur].pos || prev.cur !== v.cur)) board.focusTile(v.players[v.cur].pos);
      requestDraw();
    },
    ask: (p, title, body, buttons) => live() ? engineAsk(title, body, buttons) : never,
    handoff: async p => {
      if (!live()) return never;
      if (S().players.filter(q => !q.ai && q.alive).length > 1 && lastViewer !== p.id) {
        await engineAsk('請交換玩家', `<p style="font-size:20px">請把手機交給 ${pnameHtml(p)}，其他人請迴避！</p>`, [{ label: '我是' + p.name, cls: 'pri', value: true }]);
      }
      lastViewer = p.id;
    },
    turn: (p, o) => live() ? new Promise(res => {
      app.turn = { p, opts: { ...o, hand: viewerId() !== p.id }, resolve: a => { app.turn = null; requestDraw(); res(a); } };
      requestDraw();
    }) : never,
    gameOver: (w, html) => {
      ui.render();
      engineAsk(w ? '🏆 勝利' : '遊戲結束', html, [{ label: '再來一局', cls: 'pri', value: true }]).then(() => { if (live()) backToSetup(); });
    },
  };
  E.newGame(seats, opts, ui);
  ui.render();
  E.gameLoop().catch(err => { console.error(err); ui.log('（程式錯誤，本局中止）'); });
}

const L = {}; // 遊戲畫面版面
function layoutGame() {
  const top = menu.bottom + 6;
  const chipH = 50, panelH = chipH * 2 + 6 + 8 + 54 + 10;
  const avail = H - safeBottom - panelH - top;
  const bh = Math.max(200, Math.min(avail, W * BH / BW));
  board.setRect(0, top, W, bh);
  L.top = top; L.chipH = chipH; L.panelY = top + bh + 6; L.actY = L.panelY + chipH * 2 + 6 + 8;
}
function drawGame() {
  ctx.fillStyle = COLOR.bg; ctx.fillRect(0, 0, W, H);
  const v = app.view;
  // 上方：選單鈕與目前回合（避開右上角膠囊）
  button(8, menu.top, 44, menu.height, '≡', { size: 22, key: 'menu', bg: '#5a3d26', ink: '#fff', border: '#7a5a3a', tap: menuSheet });
  if (v && v.cur != null) {
    const p = v.players[v.cur], x = 60, maxW = menu.left - x - 8;
    const txt = `輪到 ${p.name}${v.me === p.id ? '（你）' : p.ai ? '（電腦）' : ''}`;
    ctx.font = font(SIZE.body, 700);
    const t = ellipsize(ctx, txt, ctx.font, maxW - 20), tw = ctx.measureText(t).width;
    fillR(ctx, x, menu.top, tw + 20, menu.height, menu.height / 2, '#fff', p.color, 2);
    ctx.fillStyle = p.color; ctx.textBaseline = 'middle'; ctx.fillText(t, x + 10, menu.top + menu.height / 2 + 1);
  }
  // 棋盤
  board.draw(ctx, v, v ? v.players : []);
  addHit({ ...board.rect, board: true });
  if (!v) return;
  drawFeed();
  // 玩家資訊（2×2）
  const cw = (W - 24) / 2;
  v.players.forEach((p, k) => {
    const x = 8 + (k % 2) * (cw + 8), y = L.panelY + Math.floor(k / 2) * (L.chipH + 6), h = L.chipH;
    const cur = v.cur === p.id;
    fillR(ctx, x, y, cw, h, 10, cur ? '#fff8e1' : COLOR.paper, cur ? COLOR.gold : p.color, cur ? 3 : 2);
    fillR(ctx, x + 7, y + 10, 30, 30, 6, p.color, '#fff', 1.5);
    ctx.fillStyle = '#fff'; ctx.font = font(18, 700); ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(p.family, x + 22, y + 26); ctx.textAlign = 'left';
    ctx.font = font(SIZE.body - 1, 700); const cash = E.fmt(p.cash), cwid = ctx.measureText(cash).width;
    ctx.fillStyle = COLOR.ink; ctx.fillText(ellipsize(ctx, p.name, ctx.font, cw - 52 - cwid - 8), x + 44, y + 16);
    ctx.textAlign = 'right'; ctx.fillText(cash, x + cw - 8, y + 16); ctx.textAlign = 'left';
    ctx.fillStyle = COLOR.sub; ctx.font = font(SIZE.tiny);
    const st = !p.alive ? '已出局' : `兵${p.troops}・地${p.owned}・牌${p.cardN}${p.rest ? `・休${p.rest}` : ''}`;
    ctx.fillText(ellipsize(ctx, st, ctx.font, cw - 52), x + 44, y + 36);
    if (v.me === p.id) { // 「你」標記在印章角落
      fillR(ctx, x + 1, y + 1, 20, 17, 5, COLOR.gold, '#fff', 1);
      ctx.fillStyle = COLOR.ink; ctx.font = font(12, 700); ctx.textAlign = 'center'; ctx.fillText('你', x + 11, y + 10); ctx.textAlign = 'left';
    }
    if (!p.alive) { fillR(ctx, x, y, cw, h, 10, 'rgba(60,40,20,.45)'); }
    addHit({ x, y, w: cw, h, tap: () => playerSheet(p), key: 'chip', k });
  });
  // 行動列：輪到你時顯示按鈕，否則顯示最新消息
  const ay = L.actY, ah = 50;
  if (app.turn) {
    const o = app.turn.opts, acts = [['🎲 擲骰子', 'roll', 2]];
    if (o.reserve) acts.push(['錦囊', 'reserve', 1]);
    acts.push(['變賣', 'sell', 1]);
    if (o.hand) acts.push(['手牌', 'hand', 1]);
    const tot = acts.reduce((a, b) => a + b[2], 0), gap = 8, unit = (W - 16 - gap * (acts.length - 1)) / tot;
    let x = 8;
    acts.forEach(([label, act, wgt], k) => {
      button(x, ay, unit * wgt, ah, label, { pri: act === 'roll', size: act === 'roll' ? 19 : SIZE.button, key: 'act', k, tap: () => app.turn && app.turn.resolve(act) });
      x += unit * wgt + gap;
    });
  } else if (feedVisible()) {
    // 棋盤上的消息框已在顯示這些消息，下方只留戰報入口，不重複顯示
    ctx.fillStyle = 'rgba(255,255,255,.6)'; ctx.font = font(SIZE.small, 700); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('查看戰報 ›', W / 2, ay + ah / 2); ctx.textAlign = 'left';
    addHit({ x: 8, y: ay, w: W - 16, h: ah, tap: logSheet, key: 'log' });
  } else {
    fillR(ctx, 8, ay, W - 16, ah, 10, 'rgba(255,255,255,.9)', COLOR.line, 1);
    ctx.fillStyle = COLOR.ink; ctx.font = font(SIZE.small); ctx.textBaseline = 'middle';
    const lines = wrapText(ctx, R.plainText(app.lastLog || '遊戲開始'), font(SIZE.small), W - 16 - 64).slice(0, 2);
    if (lines.length === 2 && wrapText(ctx, R.plainText(app.lastLog), font(SIZE.small), W - 80).length > 2) lines[1] = ellipsize(ctx, lines[1] + '……', ctx.font, W - 80);
    lines.forEach((l, k) => ctx.fillText(l, 16, ay + ah / 2 + (k - (lines.length - 1) / 2) * 20));
    ctx.fillStyle = COLOR.pri; ctx.font = font(SIZE.tiny, 700); ctx.textAlign = 'right'; ctx.fillText('戰報 ›', W - 16, ay + ah / 2); ctx.textAlign = 'left';
    addHit({ x: 8, y: ay, w: W - 16, h: ah, tap: logSheet, key: 'log' });
  }
}

/* ---------------- 繪製迴圈 ---------------- */
function draw() {
  hits = [];
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  if (app.screen === 'setup') drawSetup(); else drawGame();
  sheets.forEach((sh, k) => drawSheet(sh, k === sheets.length - 1));
}
function frame() {
  if (board.step()) dirty = true;
  if (app.screen === 'game' && feedVisible()) dirty = true; // 消息框的進度條與輪替
  if (dirty) { dirty = false; draw(); }
  requestAnimationFrame(frame);
}

/* ---------------- 觸控 ---------------- */
const pts = e => Array.from(e.touches || []).map(t => ({ x: t.clientX, y: t.clientY, id: t.identifier }));
const inR = (h, x, y) => x >= h.x && x <= h.x + h.w && y >= h.y && y <= h.y + h.h;
function topHit(x, y, pred) {
  for (let k = hits.length - 1; k >= 0; k--) {
    const h = hits[k];
    if (!inR(h, x, y)) continue;
    if (h.block) return null; // 被對話框擋住
    if (pred(h)) return h;
  }
  return null;
}
wx.onTouchStart(e => {
  const ts = pts(e);
  if (touch && touch.board) { board.touchStart(ts); return; } // 第二指：縮放
  const { x, y } = ts[0] || { x: e.changedTouches[0].clientX, y: e.changedTouches[0].clientY };
  const target = topHit(x, y, h => h.tap || h.board);
  const scroller = topHit(x, y, h => h.scroll);
  touch = { x0: x, y0: y, x, y, target, scroller, s0: scroller ? scroller.scroll.get() : 0, moved: false, board: target && target.board };
  if (target && target.hold) { const me = touch; touch.timer = setTimeout(() => { if (touch === me && !me.moved) { me.held = true; target.hold(); } }, 450); }
  if (touch.board) board.touchStart(ts);
  requestDraw();
});
wx.onTouchMove(e => {
  if (!touch) return;
  const ts = pts(e);
  if (touch.board) { board.touchMove(ts); return; }
  const t = ts[0]; if (!t) return;
  touch.x = t.x; touch.y = t.y;
  if (Math.hypot(t.x - touch.x0, t.y - touch.y0) > 8) { if (!touch.moved) requestDraw(); touch.moved = true; }
  if (touch.moved && touch.scroller) touch.scroller.scroll.set(touch.s0 - (t.y - touch.y0));
});
wx.onTouchEnd(e => {
  if (!touch) return;
  const t = touch;
  if (t.board) {
    if ((e.touches || []).length) return; // 還有手指在螢幕上
    touch = null;
    const c = e.changedTouches[0], i = board.touchEnd(c.clientX, c.clientY);
    if (i != null && i >= 0 && app.view) tileSheet(i);
    requestDraw(); return;
  }
  touch = null; clearTimeout(t.timer);
  if (!t.moved && !t.held && t.target && t.target.tap && inR(t.target, t.x, t.y)) t.target.tap();
  requestDraw();
});
wx.onTouchCancel(() => { touch = null; board.touch = null; requestDraw(); });

layoutGame();
requestAnimationFrame(frame);

// 瀏覽器預覽的自動測試用（小遊戲中沒有 window，不會執行）
if (typeof window !== 'undefined' && window.__wxTest) {
  window.__wxTest.api = {
    app, sheets, E, start: startClicked,
    press: k => { const sh = sheets[sheets.length - 1]; return sh && Promise.resolve(sh.onPress(k)).then(c => { if (c) closeSheet(sh); return c; }); },
    top: () => { const sh = sheets[sheets.length - 1]; return sh ? { title: sh.title, buttons: sh.buttons.map(b => b.label + (b.disabled ? '(x)' : '') + (b.cls === 'pri' ? '*' : '')) } : null; },
  };
}
