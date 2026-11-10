'use strict';
/* 三國風雲　畫面端
 * 依「某位玩家眼中的局面」（engine.viewFor）繪製棋盤與側欄，並處理對話框、懸停說明。
 * 兩種玩法：
 *   單機（以 file:// 開啟）：引擎在本頁執行，localUI 為轉接器，可人機對戰或多人共用一台裝置。
 *   連線（由 server/server.js 提供網頁）：引擎在伺服器執行，本頁只收畫面與題目、送回作答。 */
(() => {
const E = window.SanguoEngine;
const TX = window.SanguoTexts; // 共用說明文字（texts.js）
const { S, TILES, GROUPS, CITY_TOLL, FIELD_TOLL, BUILD_COST, LEVEL_NAME, DEF_TROOPS, HIRE_COST, RANSOM, SALE_TAX,
  GEN_BASE, SPECIAL_BASE, POKER, SUIT, CARDS, KIND_HELP, PLAYER_COLORS, DIE, fmt, esc, isProp } = E;
const $ = s => document.querySelector(s);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const COMMANDERS = POKER.slice(0, 4); // 四張 A
const cmdName = j => CARDS[j].name;     // 主帥姓名隨主題改變
const tn = E.tn;

/* ---- 主題：地名、人物、棋盤圖與標題一併切換 ---- */
let themeNow = null;
function useTheme(key) {
  if (!E.THEMES[key]) key = 'sanguo';
  if (key === themeNow) return;
  themeNow = key;
  const th = E.applyTheme(key);
  window.setCardTheme?.(key);
  const img = $('#board img'); img.src = th.board; img.alt = th.label + '棋盤';
  document.title = `英雄擲天下｜${th.label}`;
  document.querySelectorAll('.themeTitle').forEach(el => { el.textContent = th.label; });
  document.querySelectorAll('.themeSub').forEach(el => { el.textContent = th.sub; });
}
const themeOptions = () => E.THEMES && Object.values(E.THEMES).map(th => `<option value="${th.key}">${th.label}</option>`).join('');

/* ---- 棋盤版面：每一格在棋盤掃描圖（2122×3000）上的位置 [x, y, 寬, 高]，順序同 TILES ---- */
const SCAN = { x: 45, y: 255, w: 1900, h: 2630 }; // 棋盤 SVG 對應掃描圖的裁切範圍
const BOXES = [[1297,290,610,525],[1690,890,210,142],[1312,840,310,175],[1307,1080,210,140],[1592,1050,310,170],[1690,1285,212,142],
  [1312,1240,310,177],[1307,1480,210,140],[1592,1445,310,177],[1692,1688,208,140],[1690,1895,210,140],[1277,1630,385,420],
  [1309,2088,210,137],[1590,2055,307,170],[1690,2293,207,140],[1307,2243,310,175],[1305,2482,210,140],[1587,2452,308,173],
  [1685,2692,209,140],[1307,2640,307,175],[1097,2623,143,205],[893,2620,142,205],[880,2130,405,490],[680,2253,142,204],
  [700,2520,175,305],[488,2623,139,210],[490,2253,173,310],[275,2253,145,202],[288,2520,177,308],[73,2623,145,205],
  [78,2253,180,310],[75,2047,213,143],[372,1895,393,300],[75,1892,213,140],[75,1687,213,140],[348,1700,320,170],
  [455,1492,213,145],[75,1497,323,170],[75,1290,205,142],[348,1300,320,175],[455,1098,213,142],[75,1095,323,175],
  [75,890,213,140],[75,687,213,140],[320,690,320,350],[457,477,211,143],[75,490,315,175],[75,285,217,142],
  [355,285,313,170],[735,285,141,202],[688,553,175,309],[928,660,138,207],[895,285,171,305],[1137,282,137,206],[1137,557,137,190]];
const DECK_BOX = { emergency: [760, 990, 450, 304], general: [734, 1384, 506, 336], strategy: [764, 1814, 452, 300] };
// 橫式棋盤：掃描座標扣除裁切偏移後逆時針轉 90 度（與 tools/make_board_svg.py 相同）
const place = (el, [x, y, w, h]) => {
  const cx = x - SCAN.x, cy = y - SCAN.y;
  const nx = cy, ny = SCAN.w - cx - w; // 轉後畫布寬 SCAN.h、高 SCAN.w
  Object.assign(el.style, { left: nx / SCAN.h * 100 + '%', top: ny / SCAN.w * 100 + '%', width: h / SCAN.h * 100 + '%', height: w / SCAN.w * 100 + '%' });
};
console.assert(BOXES.length === TILES.length, '棋盤應有 55 格');

let VIEW = null; // 目前顯示的局面
const P = id => VIEW.players[id];
const pname = p => `<b style="color:${p.color}">${esc(p.name)}</b>`;
const cimg = (id, cls = '') => `<span class="cw" data-cid="${id}" data-cls="${cls}"></span>`;
// 把引擎輸出的牌位標記換成牌面圖
function hydrate(root) {
  root.querySelectorAll('.cw[data-cid]').forEach(el => { if (!el.firstChild) el.innerHTML = cardSvg(CARDS[+el.dataset.cid], el.dataset.cls || ''); });
}

/* ------------------------------------------------------------------ *
 *  對話框（依序排隊，一次只顯示一個）
 *  onPress(k, bodyEl) 回傳 Promise<是否關閉>
 * ------------------------------------------------------------------ */
let modalChain = Promise.resolve();
let modalCurrent = null;
function showModal(title, body, buttons, onPress, key) {
  const job = modalChain.then(() => new Promise(done => {
    const m = $('#modal');
    m.querySelector('h3').innerHTML = title;
    const b = m.querySelector('.body'); b.innerHTML = body; hydrate(b);
    const bt = m.querySelector('.btns'); bt.innerHTML = '';
    const close = () => { m.hidden = true; modalCurrent = null; done(); };
    modalCurrent = { key, close, body: b };
    buttons.forEach((o, k) => {
      const e = document.createElement('button');
      e.innerHTML = o.label; if (o.cls) e.className = o.cls; e.disabled = !!o.disabled;
      e.onclick = async () => { if (await onPress(k, b)) close(); };
      bt.appendChild(e);
    });
    m.hidden = false;
  }));
  modalChain = job;
  return job;
}
// 單機用：直接以按鈕值回傳（值為函式時讀取對話框內容）
function localModal(title, body, buttons) {
  return new Promise(res => showModal(title, body, buttons, async (k, b) => {
    const o = buttons[k];
    const v = typeof o.value === 'function' ? o.value(b) : o.value;
    if (v === undefined) return false; // 輸入不正確，保持開啟
    res(v); return true;
  }));
}
const okLocal = (title, body) => localModal(title, body, [{ label: '確定', value: true, cls: 'pri' }]);

/* ------------------------------------------------------------------ *
 *  棋盤與側欄
 * ------------------------------------------------------------------ */
function buildBoard() {
  const B = $('#board');
  B.querySelectorAll('.ov, .deck, #center').forEach(e => e.remove());
  for (const [k, box] of Object.entries(DECK_BOX)) {
    if (k === 'general') continue;
    const d = document.createElement('div'); d.className = 'deck'; d.id = 'deck-' + k; place(d, box); B.appendChild(d);
  }
  TILES.forEach((T, i) => {
    const d = document.createElement('div'); d.className = 'ov'; d.id = 'tile' + i;
    place(d, BOXES[i]);
    d.innerHTML = '<div class="toks"></div>';
    d.onclick = () => tileInfo(i);
    B.appendChild(d);
  });
  const c = document.createElement('div'); c.id = 'center'; place(c, DECK_BOX.general);
  c.innerHTML = '<div id="turnInfo"></div><div id="dice"></div><div id="actions"></div><div id="pileN"></div>';
  B.appendChild(c);
}
const castleSvg = lv => `<svg viewBox="0 0 40 ${lv === 2 ? 44 : 30}">${lv === 2
  ? `<path d="M8,16 q12,-12 24,0z" fill="#c62828" stroke="#2a1a10" stroke-width="1.6"/><rect x="11" y="15" width="18" height="7" fill="#f6b93b" stroke="#2a1a10" stroke-width="1.4"/>
     <path d="M3,25 q17,-10 34,0z" fill="#1565c0" stroke="#2a1a10" stroke-width="1.6"/><rect x="6" y="24" width="28" height="8" fill="#f8f1d8" stroke="#2a1a10" stroke-width="1.4"/>
     <path d="M0,34 q20,-8 40,0z" fill="#2e7d32" stroke="#2a1a10" stroke-width="1.6"/><rect x="3" y="33" width="34" height="10" fill="#f8f1d8" stroke="#2a1a10" stroke-width="1.4"/><rect x="17" y="36" width="6" height="7" fill="#c62828"/>`
  : `<path d="M2,13 q18,-12 36,0z" fill="#c62828" stroke="#2a1a10" stroke-width="1.6"/><rect x="5" y="12" width="30" height="16" fill="#f8f1d8" stroke="#2a1a10" stroke-width="1.4"/><rect x="16" y="18" width="8" height="10" fill="#c62828"/>`}</svg>`;
// 位置旗：大面旗幟寫主帥姓氏，白字黑邊以便辨識
const flagSvg = p => `<div class="tok" title="${esc(p.name)}"><svg viewBox="0 0 44 52"><line x1="4" y1="3" x2="4" y2="50" stroke="#3b2a1a" stroke-width="3.2" stroke-linecap="round"/>
  <circle cx="4" cy="3.5" r="3" fill="#d9a514" stroke="#3b2a1a" stroke-width="1"/><path d="M5.5,6 h33 q4,10 0,12 q4,2 0,12 h-33z" fill="${p.color}" stroke="#2a1a10" stroke-width="1.6"/>
  <path d="M5.5,6 h33 q4,10 0,12 q4,2 0,12 h-33z" fill="url(#cgSh)"/>
  <text x="21.5" y="26.5" font-size="21" font-weight="900" text-anchor="middle" fill="#fff" stroke="#1a0f08" stroke-width="2.4" paint-order="stroke" font-family="'STKaiti','KaiTi','Kaiti TC',serif">${p.family}</text></svg></div>`;
function flashDeck(k) {
  const d = $('#deck-' + k); if (!d) return;
  d.classList.remove('flash'); void d.offsetWidth; d.classList.add('flash');
}
function showDice(r) { const d = $('#dice'); if (d) d.textContent = r.map(x => DIE[x]).join(' '); }
function appendLog(html) {
  const d = document.createElement('div'); d.innerHTML = html;
  const L = $('#log'); L.appendChild(d); L.scrollTop = L.scrollHeight;
  $('#msg').innerHTML = html;
}

/* ---- 動態消息：電腦的每個行動逐條顯示在棋盤中央 ----
 * 停留時間由引擎決定（慢 5 秒、中 3 秒、快 2 秒）；meta = { dur, wait }：wait 毫秒後出現、停留 dur 毫秒。
 * 戰報也在消息出現時才加入，順序與畫面一致。單機版點一下可跳過；連線版由伺服器控制節奏，不能跳過。 */
const FEED = { items: [], timer: null, skippable: true, linger: 2500 };
function addLog(html, meta) {
  const now = Date.now(), it = { html, t0: now + (meta ? meta.wait : 0), dur: meta ? meta.dur : 0, logged: false };
  FEED.items.push(it);
  while (FEED.items.length > 12 && FEED.items[0].logged && now > FEED.items[0].t0 + FEED.items[0].dur) FEED.items.shift();
  feedTick();
}
function feedTick() {
  const now = Date.now();
  for (const it of FEED.items) if (!it.logged && it.t0 <= now) { it.logged = true; appendLog(it.html); }
  const shown = FEED.items.filter(it => it.logged), last = FEED.items[FEED.items.length - 1];
  const el = $('#feed');
  const visible = el && shown.length && last && now <= last.t0 + last.dur + FEED.linger && shown.some(it => it.dur);
  // 消息框顯示時，側欄上方的最新消息不重複顯示
  $('#msg').style.visibility = visible ? 'hidden' : '';
  if (!visible) { if (el) el.hidden = true; if (!FEED.items.some(it => !it.logged)) { clearInterval(FEED.timer); FEED.timer = null; } else ensureFeedTimer(); return; }
  const reading = FEED.items.find(it => it.logged && now < it.t0 + it.dur);
  const cur = VIEW && VIEW.cur != null ? P(VIEW.cur) : null;
  el.style.borderColor = cur ? cur.color : '#d9a514';
  const recent = shown.slice(-3), newest = recent.pop();
  el.innerHTML = recent.map(it => `<div class="feed-old">${it.html}</div>`).join('') + `<div class="feed-new">${newest.html}</div>`
    + (reading ? `<div class="feed-foot"><span class="feed-bar"><i style="width:${Math.min(100, (now - reading.t0) / Math.max(1, reading.dur) * 100)}%;background:${cur ? cur.color : '#d9a514'}"></i></span>${FEED.skippable ? '<span class="feed-skip">點一下跳過</span>' : ''}</div>` : '');
  el.hidden = false;
  ensureFeedTimer();
}
function ensureFeedTimer() { if (!FEED.timer) FEED.timer = setInterval(feedTick, 100); }
function feedSkip() {
  if (!FEED.skippable) return;
  E.skipReading();
  const now = Date.now();
  FEED.items.forEach(it => { if (it.t0 > now) it.t0 = now; it.dur = Math.max(0, Math.min(it.dur, now - it.t0)); });
  feedTick();
}
function feedReset(skippable) { FEED.items = []; FEED.skippable = skippable; feedTick(); }

function renderView(v) {
  VIEW = v;
  useTheme(v.theme);
  if (!$('#tile0')) buildBoard();
  TILES.forEach((T, i) => {
    const d = $('#tile' + i), t = v.tiles[i];
    d.querySelector('.stampwrap')?.remove();
    // 已購買的領地蓋上地主主帥姓氏的印章
    if (isProp(i) && t.owner != null) {
      const o = P(t.owner);
      d.style.setProperty('--oc', o.color);
      d.insertAdjacentHTML('beforeend', `<div class="stampwrap"><div class="stamp">${o.family}</div></div>`);
    }
    // 已建城池以城樓符號表示（小城一層、大城三層）
    d.querySelector('.lvl')?.remove();
    if (isProp(i) && t.level) d.insertAdjacentHTML('beforeend', `<div class="lvl" title="${LEVEL_NAME[t.level]}">${castleSvg(t.level)}</div>`);
    d.querySelector('.toks').innerHTML = v.players.filter(p => p.alive && p.pos === i).map(flagSvg).join('');
    d.classList.toggle('here', v.cur != null && P(v.cur).pos === i);
  });
  $('#pileN').textContent = `在野武將 ${v.pile} 張`;
  const cp = v.cur != null ? P(v.cur) : null;
  $('#turnInfo').innerHTML = cp ? `輪到 <span style="color:${cp.color};background:#fff;border-radius:.5cqw;padding:0 .6cqw;text-shadow:none">${esc(cp.name)}</span>${v.me === cp.id ? '（你）' : ''}` : '';
  $('#players').innerHTML = v.players.map(p => {
    const st = !p.alive ? '<span class="tag">已出局</span>'
      : (p.rest ? `<span class="tag">休息 ${p.rest} 次</span>` : '') + (p.reserveN ? `<span class="tag">保留卡 ${p.reserveN}</span>` : '');
    let hand;
    if (p.hand) {
      hand = `<div class="hand">${p.hand.map(id => `<span onclick="zoomCard(${id})">${cimg(id)}</span>`).join('')}</div>`
        + (p.reserve?.length ? `<div class="gens">保留卡：${p.reserve.join('、')}</div>` : '');
    } else {
      // 他人手牌不公開：只顯示張數，以及你從公開俘虜中記得的牌
      hand = `<div class="gens">${p.hasCmd ? '' : '（主帥失守）'}手牌 ${p.cardN} 張${p.known.length ? `・你記得：<span class="mini">${p.known.map(id => cimg(id, 'mini')).join(' ')}</span>` : ''}</div>`;
    }
    return `<div class="pl ${p.id === v.cur ? 'cur' : ''} ${p.alive ? '' : 'dead'}" style="border-color:${p.color}">
      <div class="hd"><span><span class="stamp" style="--oc:${p.color};display:inline-flex;width:22px;height:22px;font-size:15px;border-width:2px;outline:none;vertical-align:middle;margin-right:4px">${p.family}</span>${esc(p.name)}${p.ai ? '<span class="tag">電腦</span>' : ''}${v.me === p.id ? '<span class="tag">你</span>' : ''}${st}</span><span>${fmt(p.cash)}</span></div>
      <div>⚔ 兵力 ${p.troops}・🏯 領地 ${p.owned} 處${p.groups.length ? `・同色全收：${p.groups.map(g => GROUPS[g]).join('、')}` : ''}</div>
      ${hand}</div>`;
  }).join('');
  hydrate($('#players'));
}

const levelName = i => TILES[i].t === 'field' ? '古戰場' : LEVEL_NAME[VIEW.tiles[i].level];
// 領地懸停資訊：價格、稅金、地主
function tileTipHtml(i) {
  const T = TILES[i], t = VIEW.tiles[i];
  if (!isProp(i)) return `<b>${T.n}</b><div>${TX.spaceHelp(E, T)}</div>`;
  const o = t.owner != null ? P(t.owner) : null;
  const tolls = T.t === 'field' ? FIELD_TOLL.map((v, k) => `${'一二三四五'[k]}座 ${v}`).join('、') : CITY_TOLL[T.p].map((v, k) => `${LEVEL_NAME[k]} ${v}`).join('、');
  return `<b>${T.n}</b>　<small>${GROUPS[T.g]}</small><div>領地價格 ${fmt(T.p)}${T.t === 'city' ? `・建城費用 ${fmt(BUILD_COST)}` : ''}</div>`
    + `<div>稅金：${tolls}${T.t === 'field' ? '（依地主擁有座數）' : ''}</div>`
    + (o ? `<div>地主 ${pname(o)}・${levelName(i)}・目前過路稅 <b>${fmt(t.toll)}</b>${o.rest ? '（休息中）' : ''}</div>` : '<div>空白領地，可購買</div>');
}
function tileInfo(i) {
  if (!VIEW || !$('#modal').hidden) return;
  const T = TILES[i];
  const body = TX.tileInfoHtml(E, i, VIEW, pname, levelName);
  okLocal(T.n, body);
}
window.zoomCard = id => {
  if ($('#modal').hidden) okLocal(CARDS[id].name, `<div style="text-align:center">${cimg(id, 'big')}</div><div style="margin-top:8px">${cardInfoHtml(CARDS[id], KIND_HELP[CARDS[id].kind] || '')}</div>`);
};
// 滑鼠懸停：牌顯示姓名、數值與說明；格子顯示價格與稅金
document.addEventListener('mouseover', e => {
  const tip = $('#tip');
  const el = e.target.closest?.('[data-cid]');
  const tile = !el && VIEW && e.target.closest?.('.ov');
  if (tile) { tip.innerHTML = tileTipHtml(+tile.id.slice(4)); tip.hidden = false; return; }
  if (!el) { tip.hidden = true; return; }
  const c = CARDS[+el.dataset.cid];
  const owner = VIEW && VIEW.players.find(p => p.commander === c.id);
  tip.innerHTML = cardInfoHtml(c, KIND_HELP[c.kind] || '') + (owner ? `<div class="cmdbadge">★ ${esc(owner.name)}的主帥</div>` : '');
  tip.hidden = false;
});
document.addEventListener('mousemove', e => {
  const tip = $('#tip'); if (tip.hidden) return;
  tip.style.left = Math.min(e.clientX + 16, innerWidth - tip.offsetWidth - 8) + 'px';
  tip.style.top = Math.min(e.clientY + 16, innerHeight - tip.offsetHeight - 8) + 'px';
});

// 回合按鈕：擲骰、使用錦囊、變賣資產（單機多人時另有查看手牌）
function turnButtons(opts, onPick) {
  const a = $('#actions'); a.innerHTML = '';
  const btn = (label, act, cls) => { const b = document.createElement('button'); b.textContent = label; if (cls) b.className = cls; b.onclick = () => { a.innerHTML = ''; onPick(act); }; a.appendChild(b); };
  btn('🎲 擲骰子', 'roll', 'pri');
  if (opts.reserve) btn('使用錦囊', 'reserve');
  btn('變賣資產', 'sell');
  if (opts.hand) btn('查看手牌', 'hand');
}

function showRules() {
  okLocal('遊戲說明書', TX.rulesHtml(E));
}
const showGame = () => showScreen('game');

/* ------------------------------------------------------------------ *
 *  單機版：引擎在本頁執行
 * ------------------------------------------------------------------ */
function startOffline(seats, opts) {
  const G = () => E.state();
  // 畫面視角：只有一位人類時為其本人；全電腦為旁觀；多位人類共用裝置時不顯示手牌
  const viewerId = () => { const hs = G().players.filter(p => !p.ai); return hs.length === 1 ? hs[0].id : hs.length ? null : 'all'; };
  let lastViewer = null;
  const ui = {
    sleep, log: addLog, dice: showDice, flash: flashDeck,
    render: () => renderView(E.viewFor(viewerId())),
    ask: (p, title, body, buttons) => localModal(title, body, buttons),
    handoff: async p => {
      if (G().players.filter(q => !q.ai && q.alive).length > 1 && lastViewer !== p.id) {
        await okLocal('請交換玩家', `<p style="font-size:18px">請把裝置交給 ${pname(p)}，其他人請迴避！</p>`);
      }
      lastViewer = p.id;
    },
    turn: (p, o) => new Promise(res => turnButtons({ ...o, hand: viewerId() !== p.id }, res)),
    gameOver: (w, html) => { ui.render(); localModal(w ? '🏆 勝利' : '遊戲結束', html, [{ label: '再戰一局', cls: 'pri', value: true }]).then(() => location.reload()); },
  };
  showGame();
  feedReset(true);
  E.newGame(seats, { ...opts, ...(E.PACE[opts.aiDelay] || E.PACE[450]) }, ui);
  ui.render();
  E.gameLoop();
}
function setupRows() {
  const n = +$('#nPlayers').value, rows = $('#playerRows'), prev = [...rows.children].map(r => ({ ai: r.querySelector('.ty').value, cmd: r.querySelector('.cm').value }));
  rows.innerHTML = '';
  for (let k = 0; k < n; k++) {
    const v = prev[k] || { ai: k ? 'ai' : 'human', cmd: String(k) };
    const r = document.createElement('div'); r.className = 'row';
    r.innerHTML = `<span class="swatch" style="background:${PLAYER_COLORS[k]}"></span>
      第 ${k + 1} 位 <select class="ty"><option value="human">人類</option><option value="ai">電腦</option></select>
      選擇主帥 <select class="cm">${COMMANDERS.map((c, j) => `<option value="${j}">${cmdName(j)}（${SUIT[c[0][0]]}A）</option>`).join('')}</select>`;
    r.querySelector('.ty').value = v.ai; r.querySelector('.cm').value = v.cmd;
    rows.appendChild(r);
  }
}
function offlineStartClicked() {
  const seats = [...$('#playerRows').children].map(r => ({ ai: r.querySelector('.ty').value === 'ai', cmd: +r.querySelector('.cm').value }));
  if (new Set(seats.map(r => r.cmd)).size !== seats.length) { $('#setupErr').textContent = '每位參加者須選擇不同的主帥。'; return; }
  startOffline(seats, { aiDelay: +$('#optSpeed').value, theme: $('#optTheme').value });
}

/* ------------------------------------------------------------------ *
 *  連線版：伺服器執行引擎；本頁收畫面與題目並送回作答
 * ------------------------------------------------------------------ */
// 座位代碼存在分頁（sessionStorage）：同一瀏覽器開多個分頁即可扮演不同玩家，重新整理仍保留座位
const ON = { token: sessionStorage.getItem('sanguo-token') || '', es: null, table: null, tables: null, lobby: null, you: null, shown: new Set() };
// 所有請求都帶上座位代碼與目前看的桌號（離座、回答問題由伺服器依座位代碼判斷）
const api = (path, body) => fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token: ON.token, table: ON.table, ...body }) })
  .then(r => r.json());
// 讀取對話框中所有輸入欄位，送給伺服器判讀
const formInputs = b => [...b.querySelectorAll('input')].map(i => ({ id: i.id || undefined, name: i.name || undefined, type: i.type, value: i.value, checked: i.checked, k: i.dataset.k }));
const setNet = text => document.querySelectorAll('.netStatus').forEach(e => { e.textContent = text; });
const seated = () => ON.you?.seat != null;

// 一次只顯示一個畫面
function showScreen(name) {
  for (const id of ['setup', 'tables', 'lobby', 'game']) $('#' + id).hidden = id !== name;
}
// 離開牌局畫面時清掉殘留的記錄、提示與對話框
function clearGameUi() {
  feedReset(false); $('#log').innerHTML = ''; $('#actions') && ($('#actions').innerHTML = ''); VIEW = null; ON.shown.clear();
  modalChain = Promise.resolve(); if (modalCurrent) modalCurrent.close();
  $('#modal').hidden = true; $('#game').hidden = true;
}
const updateStandBtn = () => { const b = $('#standBtn'); b.hidden = false; b.textContent = seated() ? '離座（交給電腦）' : '返回桌位列表'; };

// table：要看的桌號；null 只看桌位列表（已入座者伺服器一律綁在自己的桌子上）
function connect(table) {
  ON.es?.close();
  ON.table = table ?? null; ON.lobby = null;
  const es = ON.es = new EventSource('api/events?token=' + encodeURIComponent(ON.token) + '&table=' + (table == null ? 'none' : table));
  es.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.type === 'tables') { ON.tables = m.tables; if (ON.table == null) renderTables(); }
    else if (m.type === 'lobby') {
      ON.table = m.table; ON.lobby = m.lobby; ON.you = m.you;
      if (!m.lobby.started) renderLobby(); else if (!$('#game').hidden) updateStandBtn();
    }
    else if (m.type === 'reset') { clearGameUi(); if (ON.lobby) renderLobby(); }
    else if (m.type === 'view') { showGame(); updateStandBtn(); renderView(m.view); }
    else if (m.type === 'log') addLog(m.html, m.meta);
    else if (m.type === 'dice') showDice(m.r);
    else if (m.type === 'flash') flashDeck(m.k);
    else if (m.type === 'turn') turnButtons(m.opts, act => api('api/answer', { id: m.id, btn: act }));
    else if (m.type === 'ask') {
      if (ON.shown.has(m.id)) return; // 重新連線時伺服器會補送未答的題目
      ON.shown.add(m.id);
      showModal(m.title, m.body, m.buttons, async (k, b) => {
        const r = await api('api/answer', { id: m.id, btn: k, inputs: formInputs(b) });
        if (r.errors) { for (const [id, t] of Object.entries(r.errors)) { const el = b.querySelector('#' + id); if (el) el.textContent = t; } return false; }
        return !!r.ok;
      }, m.id);
    } else if (m.type === 'over') {
      const mine = seated();
      showModal(m.title, m.html, [{ label: mine ? '回到大廳開新局' : '確定', cls: 'pri' }],
        async () => { if (mine) await api('api/lobby', { op: 'reset' }); return true; });
    }
  };
  es.onerror = () => setNet('連線中斷，重新連線中……');
  es.onopen = () => setNet('');
}

// 離座：牌局中由電腦接手；回到桌位列表
async function leaveSeat() {
  await api('api/leave', {});
  ON.token = ''; ON.you = null; sessionStorage.removeItem('sanguo-token');
  clearGameUi(); connect(null);
}
function backToTables() { clearGameUi(); connect(null); }

/* ---- 桌位列表 ---- */
const cmdNameIn = (theme, j) => { if (j == null) return '尚未選主帥';  const th = E.THEMES[theme]; return (th && th.cards && th.cards[COMMANDERS[j][0]]) || COMMANDERS[j][1]; };
function renderTables() {
  showScreen('tables');
  $('#tableCards').innerHTML = (ON.tables || []).map(t => {
    const th = E.THEMES[t.theme] || E.THEMES.sanguo;
    const nh = t.seats.filter(s => s.state === 'human').length, na = t.seats.filter(s => s.state === 'ai').length;
    const status = t.over ? `牌局已結束・${th.label}` : t.started ? `遊戲進行中・${th.label}（真人 ${nh}・電腦 ${na}）`
      : nh + na === 0 ? '空桌，等你入座' : `等待中・${th.label}（真人 ${nh}・電腦 ${na}）`;
    const seats = t.seats.map(s => s.state === 'open' ? '<span class="tseat open">空位</span>'
      : `<span class="tseat ${s.state}">${esc(cmdNameIn(t.theme, s.cmd))}${s.state === 'ai' ? '・電腦' : s.online ? '' : '（離線）'}</span>`).join('');
    const full = t.seats.every(s => s.state !== 'open');
    return `<div class="tcard"><h3>第 ${t.id + 1} 桌</h3><div class="st">${status}</div><div class="tseats">${seats}</div>
      <button data-table="${t.id}" class="${t.started || full ? '' : 'pri'}">${t.started || full ? '觀戰' : '入座'}</button></div>`;
  }).join('');
  $('#tableCards').querySelectorAll('[data-table]').forEach(b => b.onclick = () => connect(+b.dataset.table));
}

/* ---- 一桌的大廳 ---- */
function renderLobby() {
  showScreen('lobby');
  const L = ON.lobby, you = ON.you || {};
  if (!L) return;
  $('#lobbyNo').textContent = ON.table + 1;
  useTheme(L.theme);
  renderThemePick(L, you);
  const hostSeat = L.seats.findIndex(s => s.host);
  const taken = L.seats.filter(s => s.state !== 'open' && s.cmd != null).map(s => s.cmd);
  const free = COMMANDERS.map((c, j) => j).filter(j => !taken.includes(j));
  const mineCmd = (L.seats.find(s => s.mine) || {}).cmd;

  // ① 只有一個按鈕：成為桌主（不列座位）
  $('#ownerBox').innerHTML = hostSeat < 0
    ? '<button data-claim class="pri" style="font-size:18px;padding:10px 24px">成為桌主</button>'
    : you.host ? '<b>你是桌主</b>' : '<span>這桌已有桌主</span>';

  // ③ 座位與角色：主題定了才列出。想入座的人在空位上直接挑角色；已入座的人可改選
  const heroBtns = (k, canPick, current) => COMMANDERS.map((c, j) => {
    const off = taken.includes(j) && j !== current;
    return `<button data-hero="${j}" data-seat="${k}" class="hero ${j === current ? 'on' : ''}" ${canPick && !off ? '' : 'disabled'}>${cmdName(j)}<small>${SUIT[c[0][0]]}A${off ? '・已被選走' : ''}</small></button>`;
  }).join('');
  if (!L.themeChosen) {
    $('#seatRows').innerHTML = '';
  } else {
    $('#seatRows').innerHTML = L.seats.map((s, k) => {
      const sw = `<span class="swatch" style="background:${PLAYER_COLORS[k]}"></span> 第 ${k + 1} 位`;
      if (s.state === 'open') {
        return `<div class="seat"><div class="row">${sw}　<i>空位</i>${you.seat != null ? `<button data-move="${k}">坐到這裡</button>` : ''}${you.host ? `<button data-ai="${k}" ${free.length ? '' : 'disabled'}>設為電腦</button>` : ''}</div>
          ${you.seat == null ? `<div class="heroes row">${heroBtns(k, true, null)}</div>` : ''}</div>`;
      }
      const who = s.state === 'ai' ? '電腦' : (s.mine ? '你' : '玩家') + (s.host ? '（桌主）' : '') + (s.online ? '' : '（離線）');
      const hero = s.cmd == null ? '<i>尚未選角色</i>' : `<b>${cmdName(s.cmd)}</b>`;
      return `<div class="seat"><div class="row">${sw}　${hero}　${who}
        ${you.host && s.state === 'ai' ? `<button data-remove="${k}">移除</button>` : ''}${s.mine ? '<button data-leave>離座</button>' : ''}</div>
        ${s.mine ? `<div class="heroes row">${heroBtns(k, true, s.cmd)}</div>` : ''}</div>`;
    }).join('');
  }
  const nSeated = L.seats.filter(s => s.state !== 'open').length;
  const unpicked = L.seats.some(s => s.state === 'human' && s.cmd == null);
  $('#lobbyHost').hidden = !you.host;
  $('#lobbyFill').hidden = !free.length || !L.themeChosen;
  $('#lobbyWait').textContent = hostSeat < 0 ? '① 還沒有桌主：按「成為桌主」，由桌主先選主題。'
    : you.host && !L.themeChosen ? '② 你是桌主：請先在上面點一本書選擇主題。'
    : !L.themeChosen ? '② 等待桌主選擇主題……'
    : you.seat == null ? '③ 選一個空位，並點選你要扮演的角色入座。'
    : mineCmd == null ? '③ 請選擇你的角色。'
    : you.host ? (unpicked ? '等其他玩家選好角色。' : nSeated < 2 ? '至少需要 2 位：等朋友入座，或按「空位全部設為電腦」。' : '人到齊了就按「開始遊戲」；空位會留給電腦。')
    : '等待桌主開始遊戲……';
  $('#lobbyStart').disabled = nSeated < 2 || unpicked || !L.themeChosen;
  $('#onSpeed').value = String(L.speed);
  $('#lobbyBack').textContent = seated() ? '離座並返回桌位列表' : '返回桌位列表';

  const join = async body => {
    const r = await api('api/join', body);
    if (r.token) { ON.token = r.token; sessionStorage.setItem('sanguo-token', r.token); connect(r.table); } else alert(r.error || '無法入座');
  };
  const claim = $('#ownerBox').querySelector('[data-claim]');
  if (claim) claim.onclick = () => join({});
  $('#seatRows').querySelectorAll('[data-hero]').forEach(b => b.onclick = async () => {
    if (you.seat == null) return join({ seat: +b.dataset.seat, cmd: +b.dataset.hero });
    const r = await api('api/lobby', { op: 'pick', cmd: +b.dataset.hero }); if (r.error) alert(r.error);
  });
  $('#seatRows').querySelectorAll('[data-move]').forEach(b => b.onclick = async () => { const r = await api('api/lobby', { op: 'move', seat: +b.dataset.move }); if (r.error) alert(r.error); });
  $('#seatRows').querySelectorAll('[data-ai]').forEach(b => b.onclick = () => api('api/lobby', { op: 'ai', seat: +b.dataset.ai, cmd: free[0] }));
  $('#seatRows').querySelectorAll('[data-remove]').forEach(b => b.onclick = () => api('api/lobby', { op: 'open', seat: +b.dataset.remove }));
  $('#seatRows').querySelectorAll('[data-leave]').forEach(b => b.onclick = leaveSeat);
}
// 主題：一排古書封面。桌主點選；其他人只看得到選了哪一本
const BOOK_COLOR = { sanguo: '#23395b', shuihu: '#2f4a2b', fengshen: '#5b2333', xiyou: '#7a5418', chuhan: '#2b2626' };
function renderThemePick(L, you) {
  const th = Object.values(E.THEMES);
  const chosen = L.themeChosen ? L.theme : null;
  $('#themePick').innerHTML = th.map(t => `<button class="book ${t.key === chosen ? 'on' : ''}" data-theme="${t.key}" style="--bk:${BOOK_COLOR[t.key] || '#3b4a5a'}" title="${t.label}" ${you.host ? '' : 'disabled'}><span class="slip"><i>${t.label}</i></span></button>`).join('');
  $('#themeNote').textContent = you.host ? (chosen ? `你是桌主：點一本書選擇主題（目前：${E.THEMES[chosen].label}；換主題後大家要重選主帥）` : '你是桌主：請點一本書選擇主題。')
    : chosen ? `本桌主題：${E.THEMES[chosen].label}（由桌主選擇）`
    : you.seat != null ? '等待桌主選擇主題……' : '先有人成為桌主，再由桌主選主題。';
  if (you.host) $('#themePick').querySelectorAll('[data-theme]').forEach(b => b.onclick = () => api('api/lobby', { op: 'theme', theme: b.dataset.theme }));
}
function startOnline() {
  FEED.skippable = false; // 連線版：節奏由伺服器控制
  $('#setup').hidden = true;
  $('#lobbyStart').onclick = async () => { const r = await api('api/lobby', { op: 'start', speed: +$('#onSpeed').value }); if (r.error) alert(r.error); };
  $('#lobbyFill').onclick = () => api('api/lobby', { op: 'fillai' });
  $('#lobbyBack').onclick = () => { if (seated()) leaveSeat(); else backToTables(); };
  $('#standBtn').onclick = () => {
    if (!seated()) return backToTables();
    if (confirm('離座後，你的座位由電腦接手。確定要離座嗎？')) leaveSeat();
  };
  connect(null);
}

/* ---- 啟動 ---- */
$('#rulesBtn0').onclick = showRules;
$('#feed').onclick = feedSkip;
$('#rulesBtn').onclick = showRules;
$('#rulesBtn1').onclick = showRules;
$('#rulesBtn2').onclick = showRules;
if (location.protocol === 'http:' || location.protocol === 'https:') startOnline();
else {
  const qs = new URLSearchParams(location.search);
  $('#optTheme').innerHTML = themeOptions();
  $('#optTheme').value = E.THEMES[qs.get('theme')] ? qs.get('theme') : 'sanguo';
  useTheme($('#optTheme').value);
  $('#optTheme').onchange = () => { useTheme($('#optTheme').value); setupRows(); };
  $('#nPlayers').onchange = setupRows;
  $('#startBtn').onclick = offlineStartClicked;
  setupRows();
  // 示範模式：index.html?demo 直接由四位電腦對戰（可加 &theme=shuihu）
  if (qs.has('demo')) startOffline([0, 1, 2, 3].map(k => ({ ai: true, cmd: k })), { aiDelay: 450, theme: $('#optTheme').value });
}
})();
