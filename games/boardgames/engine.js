'use strict';
/* 三國風雲　遊戲規則引擎
 * 不碰畫面：所有顯示與提問都透過注入的 UI 轉接器（瀏覽器單機版見 client.js，連線版見 server/server.js）。
 * 瀏覽器中為全域 SanguoEngine；Node 中以 require 取得。 */
(function (root, factory) {
  const m = factory();
  if (typeof module === 'object' && module.exports) module.exports = m; else root.SanguoEngine = m;
})(typeof self !== 'undefined' ? self : this, function () {
'use strict';

const S = { startCash: 15000, startTroops: 1500, passStart: 2000, winTerr: 20, aiDelay: 450, stepMs: 110, readMs: 0 };
// 操作提示：依裝置不同（網頁用滑鼠、手機用點按），由 newGame 的 opts.hints 替換
const HINT_BASE = { card: '滑鼠移到牌上可看數值', tile: '滑鼠移到格子上可查看領地資訊' };
let HINT = HINT_BASE;
const CITY_TOLL = { 1000: [500, 1000, 2000], 1500: [800, 1500, 3000], 2000: [1000, 2000, 4000] }; // 領地／小城／大城稅金
const FIELD_TOLL = [500, 1000, 2000, 4000, 8000]; // 依地主擁有古戰場座數
const BUILD_COST = 600;                           // 建城費用（建小城、小城改建大城各一次）
const SIEGE_NEED = [500, 1000, 1500];             // 攻領地、小城、大城所需兵力（古戰場 1000）
const DEF_TROOPS = 500, HIRE_COST = 1000, RANSOM = 5000, SALE_TAX = 500, TROOP_UNIT = 500;
const GEN_BASE = 1000, SPECIAL_BASE = 500;        // 自訂：武將、特別卡賣給國庫之底價

const GROUPS = { orange: '橙色', blue: '藍色', magenta: '紫紅色', yellow: '黃色', green: '綠色', field: '古戰場' };

/* ---- 棋盤：路線由起點出發，繞一圈回到起點 ---- */
// 這裡只定義每一格的種類、地價、顏色與費用；格子名稱一律來自 themes.js（applyTheme 填入 n）
const C = (p, g) => ({ t: 'city', p, g });
const F = () => ({ t: 'field', p: 1000, g: 'field' });
const R = { t: 'recruit' }, H = { t: 'hire' }, E = { t: 'emergency' }, K = { t: 'strategy' };
const SH = fee => ({ t: 'shop', fee });
const TILES = [
  { t: 'start' },
  R, C(1500, 'orange'), E, C(1000, 'orange'), H, C(2000, 'orange'), K, C(1000, 'orange'), SH(500), F(),
  { t: 'rest', fee: 500 },
  E, C(1000, 'blue'), R, C(2000, 'blue'), K, C(1000, 'blue'), H, C(1500, 'blue'), SH(500), F(),
  { t: 'rest', fee: 800 },
  E, C(1000, 'yellow'), R, C(1500, 'yellow'), K, C(1000, 'yellow'), H, C(2000, 'yellow'), SH(400),
  { t: 'island' }, F(),
  R, C(2000, 'magenta'), E, C(1000, 'magenta'), H, C(1500, 'magenta'), K, C(1000, 'magenta'), SH(300), F(),
  { t: 'cottage' },
  E, C(1000, 'green'), R, C(2000, 'green'), H, C(1500, 'green'), K, C(1000, 'green'), SH(200), F(),
].map(t => ({ ...t }));
const N = TILES.length; // 55
// 依格子種類找位置（名稱會隨主題改變，不可用名稱查）
const IDXT = (t, nth = 0) => TILES.map((T, i) => T.t === t ? i : -1).filter(i => i >= 0)[nth];
// 格子種類的顯示名稱（如「緊急軍情」／「江湖告急」），隨主題改變
const tn = t => TILES[IDXT(t)].n;

/* ---- 武將撲克牌（54 張）：A 為主帥，2–J 武將，Q 武器，K 陣式，鬼牌為霸王卡 ---- */
const SUIT = { S: '♠', H: '♥', D: '♦', C: '♣' };
const POKER = [
  ['SA', '曹操', 1900, 2000], ['HA', '劉備', 1900, 2000], ['DA', '孫權', 1900, 2000], ['CA', '董卓', 1900, 2000],
  ['S2', '黃承彥', 1850, 1850], ['H2', '木鹿大王', 1850, 1850], ['D2', '于吉', 1850, 1850], ['C2', '張角', 1850, 1850], // 2 點：身懷異術者
  ['S3', '蔡陽', 1550, 1600], ['H3', '嚴顏', 1550, 1600], ['D3', '董襲', 1550, 1600], ['C3', '貂蟬', 1550, 1600],
  ['S4', '于禁', 1600, 1550], ['H4', '法正', 1600, 1550], ['D4', '黃蓋', 1600, 1550], ['C4', '郭汜', 1600, 1550],
  ['S5', '郭嘉', 1500, 1750], ['H5', '龐統', 1500, 1750], ['D5', '諸葛瑾', 1500, 1750], ['C5', '徐庶', 1500, 1750],
  ['S6', '典韋', 1700, 1650], ['H6', '黃忠', 1700, 1650], ['D6', '甘寧', 1700, 1650], ['C6', '胡赤兒', 1700, 1650],
  ['S7', '司馬懿', 1600, 1900], ['H7', '諸葛亮', 1600, 1900], ['D7', '魯肅', 1600, 1900], ['C7', '賈詡', 1600, 1900],
  ['S8', '徐晃', 1800, 1700], ['H8', '魏延', 1800, 1700], ['D8', '呂蒙', 1800, 1700], ['C8', '李肅', 1800, 1700],
  ['S9', '張郃', 1750, 1850], ['H9', '趙雲', 1750, 1850], ['D9', '陸遜', 1750, 1850], ['C9', '華雄', 1750, 1850],
  ['S10', '許褚', 1850, 1750], ['H10', '張飛', 1850, 1750], ['D10', '周泰', 1850, 1750], ['C10', '張遼', 1850, 1750],
  ['SJ', '夏侯惇', 2000, 1800], ['HJ', '關羽', 2000, 1800], ['DJ', '周瑜', 2000, 1800], ['CJ', '呂布', 2000, 1800],
];
const SPECIALS = [
  ['SQ', '火鏞炮', 'weapon', 2000], ['HQ', '巨魔劍', 'weapon', 2000], ['DQ', '淬毒弓', 'weapon', 2000], ['CQ', '迷魂彈', 'weapon', 2000],
  ['SK', '火牛陣', 'formation', 5000], ['HK', '烈焰陣', 'formation', 5000], ['DK', '五行八卦陣', 'formation', 5000], ['CK', '轟雷術', 'formation', 5000],
  ['X1', '霸王卡', 'overlord', 0], ['X2', '霸王卡', 'overlord', 0],
];
const KIND_LABEL = { weapon: '武器卡', formation: '陣式卡', overlord: '霸王卡' };
const BASE_KIND_LABEL = { ...KIND_LABEL };
const KIND_HELP = {
  weapon: '取代武將出戰：雙方出戰之牌（武將、主帥、武器或陣式卡）同歸於盡，歸還國庫。該次戰鬥雙方平手，攻城者不得佔有領地。',
  formation: '取代武將出戰：俘虜敵方出戰之武將（主帥），使用之一方獲勝；雙方都用陣式則互相抵消。',
  overlord: '取代武將出戰：使用之一方獲勝，可將敵方所出之牌、攻城損失之士兵及領地占為己有。雙方同時使用則平手。',
};
const CARDS = [];
POKER.forEach(([code, name, atk, def]) => CARDS.push({ code, kind: 'general', name, atk, def }));
SPECIALS.forEach(([code, name, kind, power]) => CARDS.push({ code, kind, name, power, atk: 0, def: 0 }));
CARDS.forEach((c, id) => { c.id = id; });

/* ---- 主題：同一套規則，依主題替換地名與人物姓名 ---- */
const THEME_SRC = (typeof module === 'object' && typeof require === 'function') ? require('./themes.js')
  : (typeof self !== 'undefined' ? self.SanguoThemes : null);
if (!THEME_SRC) throw new Error('請先載入 themes.js（格子名稱定義在其中）');
const THEMES = THEME_SRC.THEMES;
const BASE_CARD_NAME = CARDS.map(c => c.name);
let themeKey = 'sanguo';
function applyTheme(key) {
  const th = THEMES[key] || THEMES.sanguo;
  themeKey = th.key;
  th.tiles.forEach((n, i) => { if (TILES[i]) TILES[i].n = n; });
  CARDS.forEach((c, i) => { c.name = th.cards[c.code] || BASE_CARD_NAME[i]; });
  STRATEGY.forEach(c => { c.n = th.strategy[c.k] || BASE_STRAT_NAME[c.k]; });
  Object.keys(BASE_KIND_LABEL).forEach(k => { KIND_LABEL[k] = th.kinds[k] || BASE_KIND_LABEL[k]; });
  return th;
}

const PLAYER_COLORS = ['#d62828', '#1d70b8', '#2a9d8f', '#7b2cbf'];
const DIE = ['', '⚀', '⚁', '⚂', '⚃', '⚄', '⚅'];

/* ------------------------------------------------------------------ */
/* 介面轉接器由外部注入（瀏覽器單機版或連線伺服器） */
let UI = null;
/* ---- 閱讀停頓：電腦回合的每條消息停留 S.readMs 毫秒，讓玩家看清楚每一步 ----
 * 消息排隊顯示；引擎的下一次等待（sleep、提問、輪到人類、交換玩家、宣布勝負）都會先等前面的消息讀完。
 * 畫面端由 UI.log(html, { dur, wait }) 得知每條消息要停多久、還要等多久才輪到它；skipReading() 可跳過。 */
let readUntil = 0, readSkip = null;
function waitRead() {
  const ms = readUntil - Date.now();
  if (ms <= 0) return Promise.resolve();
  return Promise.race([UI.sleep(ms), new Promise(r => { readSkip = r; })]);
}
function skipReading() { readUntil = 0; if (readSkip) { const r = readSkip; readSkip = null; r(); } }
const sleep = ms => Promise.all([UI.sleep(ms), waitRead()]);
const rnd = n => Math.floor(Math.random() * n);
const pickRandom = a => a[rnd(a.length)];
const shuffle = a => { for (let i = a.length - 1; i > 0; i--) { const j = rnd(i + 1); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const fmt = n => `${Math.round(n).toLocaleString()} 兩`;
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const roll = k => Array.from({ length: k }, () => 1 + rnd(6));
const showDice = r => UI.dice(r);

let G = null;
const P = id => G.players[id];
const alive = () => G.players.filter(p => p.alive);
const others = p => alive().filter(q => q !== p);
const pname = p => `<b style="color:${p.color}">${esc(p.name)}</b>`;
const tname = i => `<b>${TILES[i].n}</b>`;
const humans = () => G.players.filter(p => !p.ai && p.alive);

// holdMs：這條消息停留的毫秒數（預設 S.readMs）；擲骰消息改為與旗幟移動同時進行、停留到走完為止
function log(html, holdMs) {
  const cur = G && G.cur != null ? G.players[G.cur] : null;
  if (!(S.readMs && cur && cur.ai)) { UI.log(html); return; }
  const now = Date.now(), start = Math.max(now, readUntil), dur = holdMs ?? S.readMs;
  readUntil = start + dur;
  UI.log(html, { dur, wait: start - now });
}
const render = () => UI.render();
const flashDeck = k => UI.flash(k);

/* ---- 對話框：每個提問都指定對象玩家 ---- */
// buttons: [{label, value, cls, disabled}]；value 可為函式 b => …，b 提供 querySelector 讀取表單；回傳 undefined 表示輸入不正確
const ask = (p, title, body, buttons) => waitRead().then(() => UI.ask(p, title, body, buttons));
const ok = (p, title, body) => ask(p, title, body, [{ label: '確定', value: true, cls: 'pri' }]);
// 人類玩家顯示對話框；電腦只記錄
async function tell(p, title, body) { log(body); render(); if (!p.ai) await ok(p, title, body); else await sleep(S.aiDelay); }
// 單選清單；opts: [{label, value}]，可加一個「不使用」選項
async function choose(p, title, desc, opts, cancelLabel) {
  if (!opts.length) return null;
  const body = `${desc ? `<p>${desc}</p>` : ''}${opts.map((o, k) => `<label class="opt"><input type="radio" name="c" value="${k}" ${k ? '' : 'checked'}> ${o.label}</label>`).join('')}`;
  const btns = [{ label: '確定', cls: 'pri', value: b => opts[+b.querySelector('input:checked').value].value }];
  if (cancelLabel) btns.unshift({ label: cancelLabel, value: null });
  return ask(p, title, body, btns);
}

/* ---- 牌 ---- */
const card = id => CARDS[id];
// 牌面只畫人物與點數；姓名與數值以滑鼠懸停顯示
// 牌以占位標記輸出，由畫面端換成牌面圖
const cimg = (id, cls = '') => `<span class="cw" data-cid="${id}" data-cls="${cls}"></span>`;
const suitOf = c => c.code.startsWith('X') ? '鬼牌' : SUIT[c.code[0]] + c.code.slice(1);
const cardLabel = id => {
  const c = card(id);
  return c.kind === 'general' ? `${c.name}（${suitOf(c)}）` : `${c.name}（${KIND_LABEL[c.kind]}）`;
};
const generals = p => p.cards.filter(id => card(id).kind === 'general');
const specials = p => p.cards.filter(id => card(id).kind !== 'general');
const findSpec = (p, kind) => p.cards.find(id => card(id).kind === kind) ?? null;
function bestStat(p, stat, excludeCmd) {
  let g = generals(p);
  if (excludeCmd && g.some(id => id !== p.commander)) g = g.filter(id => id !== p.commander);
  return g.length ? Math.max(...g.map(id => card(id)[stat])) : 0;
}
function returnToPile(id) { G.pile.splice(rnd(G.pile.length + 1), 0, id); }
function drawFromPile(p, n = 1) {
  const got = [];
  for (let i = 0; i < n && G.pile.length; i++) { const id = G.pile.shift(); p.cards.push(id); got.push(id); }
  return got;
}

/* ---- 記憶：玩家看不到別人的牌，只記得公開被俘虜／奪走的牌；
 *      對方一出牌，對其所有記憶即失效 ---- */
function seenBy(obs, target, id) { if (obs !== target) G.mem[obs.id][target.id].add(id); }
function publicGain(target, id) { G.players.forEach(o => seenBy(o, target, id)); }
function cardGone(target, id) { G.players.forEach(o => G.mem[o.id][target.id].delete(id)); }
function forgetAbout(target) { G.players.forEach(o => G.mem[o.id][target.id].clear()); }
const known = (obs, target) => [...G.mem[obs.id][target.id]].filter(id => target.cards.includes(id) && id !== target.commander);
// 把一張牌從 from 移到 to（to 為 null 則歸還國庫）；此為公開事件
function transferCard(from, to, id) {
  from.cards = from.cards.filter(x => x !== id); cardGone(from, id);
  if (to) { to.cards.push(id); publicGain(to, id); } else returnToPile(id);
}
// 電腦依記憶估計對手最強數值（主帥除外，因其公開但通常不出戰）
function estBest(obs, target, stat) {
  const kn = known(obs, target).filter(id => card(id).kind === 'general');
  let best = Math.max(0, ...kn.map(id => card(id)[stat]));
  const unknown = target.cards.filter(id => id !== target.commander).length - kn.length;
  if (unknown > 0) best = Math.max(best, unknown >= 3 ? 1900 : 1800);
  if (!best && target.cards.includes(target.commander)) best = card(target.commander)[stat];
  return best;
}
// 應戰單挑時的估計：記得的牌取其最強，不明的牌以一般武將水準（約 1750）估算
function estTypical(obs, target, stat) {
  const kn = known(obs, target).filter(id => card(id).kind === 'general');
  const unknown = target.cards.filter(id => id !== target.commander).length - kn.length;
  return Math.max(0, ...kn.map(id => card(id)[stat]), unknown > 0 ? 1750 : 0);
}
/* ---- 領地 ---- */
const isProp = i => TILES[i].t === 'city' || TILES[i].t === 'field';
const owned = p => G.tiles.map((t, i) => t.owner === p.id ? i : -1).filter(i => i >= 0);
const fieldsOwned = p => owned(p).filter(i => TILES[i].t === 'field').length;
const ownsGroup = (p, g) => TILES.every((T, i) => T.g !== g || G.tiles[i].owner === p.id);
const groupsComplete = p => Object.keys(GROUPS).filter(g => ownsGroup(p, g));
function tollOf(i) {
  const T = TILES[i], t = G.tiles[i];
  if (t.owner == null) return T.t === 'field' ? FIELD_TOLL[0] : CITY_TOLL[T.p][0];
  const o = P(t.owner);
  const base = T.t === 'field' ? FIELD_TOLL[Math.max(1, fieldsOwned(o)) - 1] : CITY_TOLL[T.p][t.level];
  return base; // 收齊同色全部領地即獲勝，所以不會有「同色加倍」的過路稅
}
const siegeNeed = i => TILES[i].t === 'field' ? 1000 : SIEGE_NEED[G.tiles[i].level];
const tileValue = i => TILES[i].p + BUILD_COST * G.tiles[i].level;
const LEVEL_NAME = ['領地', '小城', '大城'];
const levelName = i => TILES[i].t === 'field' ? '古戰場' : LEVEL_NAME[G.tiles[i].level];

/* ------------------------------------------------------------------ *
 *  軍費
 * ------------------------------------------------------------------ */
function assetsOf(p) {
  const items = p.cards.filter(id => id !== p.commander)
    .map(id => ({ k: 'card', id, label: cardLabel(id), v: card(id).kind === 'general' ? GEN_BASE : SPECIAL_BASE }));
  owned(p).forEach(i => items.push({ k: 'tile', id: i, label: `${TILES[i].n}（${levelName(i)}）`, v: tileValue(i) }));
  return items;
}
function maxRaise(p) {
  const s = assetsOf(p).reduce((a, x) => a + x.v, 0) + Math.floor(p.troops / TROOP_UNIT) * TROOP_UNIT;
  return Math.max(0, s - SALE_TAX);
}
// 每次賣出（不論物品種類與數量）需繳交易稅
function doSale(p, items, units) {
  let total = units * TROOP_UNIT;
  p.troops -= units * TROOP_UNIT;
  for (const it of items) {
    total += it.v;
    if (it.k === 'card') transferCard(p, null, it.id);
    else { G.tiles[it.id].owner = null; G.tiles[it.id].level = 0; }
  }
  p.cash += total - SALE_TAX;
  const nCards = items.filter(it => it.k === 'card').length;
  const what = [...(units ? [`士兵 ${units * TROOP_UNIT} 名`] : []), ...(nCards ? [`撲克牌 ${nCards} 張`] : []),
    ...items.filter(it => it.k === 'tile').map(it => it.label)].join('、');
  log(`${pname(p)} 將 ${what} 賣給國庫，得 ${fmt(total)}（繳交易稅 ${fmt(SALE_TAX)}）。`);
  render();
}
function aiSell(p, short) {
  const tUnits = Math.floor(p.troops / TROOP_UNIT);
  const items = assetsOf(p).sort((a, b) => {
    const rank = x => x.k === 'tile' ? 2 : (card(x.id).kind === 'general' ? 1 : 0);
    return rank(a) - rank(b) || (a.k === 'card' && b.k === 'card' ? card(a.id).atk + card(a.id).def - card(b.id).atk - card(b.id).def : a.v - b.v);
  });
  let units = 0, total = 0;
  const pick = [];
  while (units < tUnits && total - SALE_TAX < short) { units++; total += TROOP_UNIT; }
  for (const it of items) { if (total - SALE_TAX >= short) break; pick.push(it); total += it.v; }
  doSale(p, pick, units);
}
async function sellDialog(p, needed) {
  await handoff(p);
  const items = assetsOf(p), tUnits = Math.floor(p.troops / TROOP_UNIT);
  if (!items.length && !tUnits) { await ok(p, '無物可賣', '你已經沒有可以變賣的物品了。'); return null; }
  const body = `${needed ? `<p class="err">需要 ${fmt(needed)}，你目前只有 ${fmt(p.cash)}。</p>` : ''}
    <p>賣給國庫。每次賣出不論物品種類與數量，皆需繳 ${fmt(SALE_TAX)} 交易稅，請一次選齊。</p>
    <div>士兵：<input id="sellT" type="number" min="0" max="${tUnits * TROOP_UNIT}" step="${TROOP_UNIT}" value="0" style="width:90px"> 名／共 ${p.troops} 名（每 ${TROOP_UNIT} 名換 ${TROOP_UNIT} 兩）</div>
    ${items.map((it, k) => `<label class="opt"><input type="checkbox" data-k="${k}"> ${it.label} — ${fmt(it.v)}</label>`).join('')}
    <div class="err" id="sellErr"></div>`;
  return ask(p, `${esc(p.name)}：變賣資產`, body, [
    { label: needed ? '放棄（宣告破產）' : '取消', value: null },
    { label: '賣出所選', cls: 'pri', value: b => {
      const units = Math.floor(Math.max(0, Math.min(+b.querySelector('#sellT').value || 0, tUnits * TROOP_UNIT)) / TROOP_UNIT);
      const pick = [...b.querySelectorAll('input[type=checkbox]:checked')].map(e => items[+e.dataset.k]);
      const total = units * TROOP_UNIT + pick.reduce((a, x) => a + x.v, 0);
      if (total <= SALE_TAX) { b.querySelector('#sellErr').textContent = `所選物品須超過 ${fmt(SALE_TAX)}，才足以支付交易稅。`; return undefined; }
      doSale(p, pick, units); return true;
    } },
  ]);
}
async function raiseFunds(p, amount) {
  while (p.cash < amount && p.alive) {
    if (p.cash + maxRaise(p) < amount) return;
    if (p.ai) aiSell(p, amount - p.cash);
    else if ((await sellDialog(p, amount)) === null) return;
  }
}
// 付不出時宣告破產並出局，回傳 false
async function pay(p, amt, to) {
  if (amt <= 0 || !p.alive) return p.alive;
  if (p.cash < amt) await raiseFunds(p, amt);
  if (p.cash < amt) {
    if (to) to.cash += p.cash;
    log(`${pname(p)} 無力支付 ${fmt(amt)}，宣告破產！`);
    p.cash = 0;
    await eliminate(p);
    return false;
  }
  p.cash -= amt; if (to) to.cash += amt;
  render();
  return true;
}
async function eliminate(p) {
  if (!p.alive) return;
  p.alive = false; p.cash = 0; p.troops = 0; p.rest = 0; p.reserve = [];
  owned(p).forEach(i => { G.tiles[i].owner = null; G.tiles[i].level = 0; });
  [...p.cards].forEach(id => transferCard(p, null, id));
  log(`💀 ${pname(p)} 失敗出局，剩餘領地、武將及軍費歸還國庫。`);
  render();
  if (!p.ai) await ok(p, '失敗', `${pname(p)} 已失敗出局，流落街頭……`);
  checkWin();
}

/* ------------------------------------------------------------------ *
 *  武將俘虜與主帥贖回
 * ------------------------------------------------------------------ */
async function loseGeneral(owner, id, captor) {
  if (!owner.cards.includes(id)) return;
  transferCard(owner, captor, id);
  log(captor ? `${pname(captor)} 俘虜了 ${pname(owner)} 的 ${card(id).name}。` : `${pname(owner)} 的 ${card(id).name} 陣亡，歸還國庫。`);
  if (id === owner.commander && owner.alive) await ransom(owner, captor);
}
async function ransom(owner, captor) {
  const id = owner.commander, to = captor && captor.alive ? captor : null;
  const msg = `${pname(owner)} 的主帥 ${card(id).name} ${captor ? '被俘虜' : '陣亡'}了！需以 ${fmt(RANSOM)} 向${to ? ' ' + pname(to) + ' ' : '國庫'}贖回，否則即告失敗。`;
  if (!owner.ai) await ok(owner, '主帥失守！', msg); else log(msg);
  if (await pay(owner, RANSOM, to)) {
    if (captor) transferCard(captor, owner, id); else { G.pile = G.pile.filter(x => x !== id); owner.cards.push(id); }
    log(`${pname(owner)} 贖回了主帥 ${card(id).name}。`);
  } else if (captor) {
    log(`${card(id).name} 從此成為 ${pname(captor)} 手中的一般武將，必須為其搖旗吶喊、加油助勢！`);
  }
  render();
}

/* ------------------------------------------------------------------ *
 *  戰鬥
 * ------------------------------------------------------------------ */
// 多位人類玩家共用一台裝置時，顯示私人資訊前先請其他人迴避
// 單機多人共用一台裝置時，顯示私人資訊前先請其他人迴避（連線版不需要）
async function handoff(p) { if (!p.ai) { await waitRead(); await UI.handoff(p); } }
function rememberText(p, opp) {
  const kn = known(p, opp);
  return `${pname(opp)} 的主帥 <span class="mini">${cimg(opp.commander, 'mini')}</span>${opp.cards.includes(opp.commander) ? '' : '（不在手中）'}・手牌 ${opp.cards.length} 張`
    + (kn.length ? `・你記得：<span class="mini">${kn.map(id => cimg(id, 'mini')).join(' ')}</span>` : '・其餘手牌不明');
}
// 出戰只能用一張牌：一名武將，或一張特別卡（武器、陣式、霸王卡）取代武將
async function humanPick(p, role, kind, opp, i) {
  await handoff(p);
  const key = role === 'atk' ? 'atk' : 'def';
  const gens = generals(p).sort((a, b) => card(b)[key] - card(a)[key]);
  const specs = specials(p);
  const best = gens.find(id => id !== p.commander) ?? gens[0];
  const body = `<p>${role === 'atk' ? '⚔ 你是攻方' : '🛡 你是守方'}——在 ${tname(i)} 與 ${pname(opp)} 進行<b>${kind === 'duel' ? '武將單挑' : '攻城戰'}</b>。
      每次只出<b>一張牌</b>：派一名武將（以${role === 'atk' ? '攻擊力' : '防禦力'}對抗敵方${role === 'atk' ? '防禦力' : '攻擊力'}），或改用一張特別卡。</p>
    <p><small>${rememberText(p, opp)}</small></p>
    <b>武將</b>（${HINT.card}；主帥若失去須以 ${fmt(RANSOM)} 贖回）
    <div class="cards">${gens.map(id => `<label class="copt"><input type="radio" name="c" value="${id}" ${id === best ? 'checked' : ''}>${cimg(id)}${id === p.commander ? '<span class="cmdbadge">★主帥</span>' : ''}</label>`).join('')}</div>
    ${specs.length ? `<b>或改用特別卡</b><div class="cards">${specs.map((id, k) => `<label class="copt"><input type="radio" name="c" value="${id}" ${!gens.length && !k ? 'checked' : ''}>${cimg(id)}</label>`).join('')}</div>
    <small>${[...new Set(specs.map(id => card(id).kind))].map(k => `<b>${KIND_LABEL[k]}</b>：${KIND_HELP[k]}`).join('<br>')}</small>` : ''}`;
  return ask(p, `${esc(p.name)}：選擇出戰的牌`, body, [{ label: '確定', cls: 'pri', value: b => +b.querySelector('input[name=c]:checked').value }]);
}
function aiPick(p, role, kind, opp) {
  const key = role === 'atk' ? 'atk' : 'def', okey = role === 'atk' ? 'def' : 'atk';
  let gens = generals(p);
  if (gens.some(id => id !== p.commander)) gens = gens.filter(id => id !== p.commander);
  gens.sort((a, b) => card(b)[key] - card(a)[key]);
  const gen = gens[0];
  // 武將可能落敗時，改出特別卡
  if (gen == null || card(gen)[key] <= estBest(p, opp, okey)) {
    const s = findSpec(p, 'overlord') ?? findSpec(p, 'formation') ?? findSpec(p, 'weapon');
    if (s != null) return s;
  }
  return gen;
}
const pick = (p, role, kind, opp, i) => p.ai ? aiPick(p, role, kind, opp) : humanPick(p, role, kind, opp, i);

async function battle(kind, A, D, i) {
  const ca = card(await pick(A, 'atk', kind, D, i));
  const cd = card(await pick(D, 'def', kind, A, i));
  const isGen = c => c.kind === 'general';
  // fate：keep 留在手中、spent 特別卡用畢歸還國庫、captured 被對方奪走、dies 武將陣亡歸還國庫
  let res, why, lord = null, fa = 'spent', fd = 'spent';
  if (ca.kind === 'overlord' && cd.kind === 'overlord') { res = 'draw'; why = `雙方同時使用${ca.name}，戰鬥平手。`; }
  else if (ca.kind === 'overlord') { res = 'A'; lord = 'A'; fd = 'captured'; why = `${A.name} 使出${ca.name}，奪下敵方的${cd.name}！`; }
  else if (cd.kind === 'overlord') { res = 'D'; lord = 'D'; fa = 'captured'; why = `${D.name} 使出${cd.name}，奪下敵方的${ca.name}！`; }
  else if (ca.kind === 'weapon' || cd.kind === 'weapon') {
    res = 'draw'; fa = isGen(ca) ? 'dies' : 'spent'; fd = isGen(cd) ? 'dies' : 'spent';
    why = `${(ca.kind === 'weapon' ? ca : cd).name} 出擊，雙方出戰之牌同歸於盡！`;
  }
  else if (ca.kind === 'formation' && cd.kind === 'formation') { res = 'draw'; why = '雙方陣式互相抵消，戰鬥平手。'; }
  else if (ca.kind === 'formation') { res = 'A'; fd = 'captured'; why = `${A.name} 的${ca.name}困住並俘虜了${cd.name}！`; }
  else if (cd.kind === 'formation') { res = 'D'; fa = 'captured'; why = `${D.name} 的${cd.name}困住並俘虜了${ca.name}！`; }
  else {
    why = `${ca.name} 攻 ${ca.atk} 對 ${cd.name} 守 ${cd.def}`;
    res = ca.atk > cd.def ? 'A' : ca.atk < cd.def ? 'D' : 'draw';
    if (res === 'A') { fa = 'keep'; fd = 'captured'; why += '。'; }
    else if (res === 'D') { fa = 'captured'; fd = 'keep'; why += '。'; }
    else { fa = fd = 'dies'; why += '，勢均力敵，雙方武將同歸於盡。'; }
  }

  // 出牌之後，其他人對雙方手牌的記憶隨即失效
  forgetAbout(A); forgetAbout(D);
  // 特別卡限用一次；被奪走的特別卡歸對方
  if (!isGen(ca)) { if (fa === 'captured') transferCard(A, D, ca.id); else transferCard(A, null, ca.id); }
  if (!isGen(cd)) { if (fd === 'captured') transferCard(D, A, cd.id); else transferCard(D, null, cd.id); }

  let troopTxt = '';
  if (kind === 'siege') {
    const lossA = Math.min(A.troops, siegeNeed(i)), lossD = Math.min(D.troops, DEF_TROOPS);
    A.troops -= lossA; D.troops -= lossD;
    if (lord === 'A') A.troops += lossD;
    if (lord === 'D') D.troops += lossA;
    troopTxt = `兵力損失：${A.name} ${lossA} 名、${D.name} ${lossD} 名。` + (lord ? `${lord === 'A' ? A.name : D.name} 俘獲敵軍損失之兵力。` : '');
  }

  const winnerTxt = res === 'draw' ? '平手！' : `${res === 'A' ? A.name : D.name} 獲勝！`;
  const outcome = kind === 'siege'
    ? (res === 'A' ? `${A.name} 佔領 ${TILES[i].n}。` : `${D.name} 守住 ${TILES[i].n}。`)
    : '本次單挑，守方不得收取過路稅。';
  const side = (pl, c) => `<div>${pname(pl)}<div class="cards" style="justify-content:center">${cimg(c.id)}</div></div>`;
  const html = `<div class="vs">${side(A, ca)}<div style="align-self:center;font-size:28px">對</div>${side(D, cd)}</div>
    <p>${esc(why)}</p><p><b>${esc(winnerTxt)}</b>${esc(outcome)}</p><p>${esc(troopTxt)}</p>`;
  log(`${kind === 'duel' ? '⚔ 單挑' : '🏯 攻城戰'}（${tname(i)}）：${pname(A)} 出 ${ca.name} 對 ${pname(D)} 出 ${cd.name}。${esc(why)}${esc(winnerTxt)}`);
  const viewers = [A, D].filter(x => !x.ai);
  if (viewers.length) await Promise.all(viewers.map(x => ok(x, kind === 'duel' ? '武將單挑' : '攻城戰', html))); else await sleep(S.aiDelay * 2);

  if (kind === 'siege' && res === 'A') G.tiles[i].owner = A.id;
  render();
  // 武將：被俘虜者歸對方（主帥需贖回），陣亡者歸還國庫
  if (isGen(cd) && fd === 'captured') await loseGeneral(D, cd.id, A);
  if (isGen(ca) && fa === 'captured') await loseGeneral(A, ca.id, D);
  if (isGen(cd) && fd === 'dies') await loseGeneral(D, cd.id, null);
  if (isGen(ca) && fa === 'dies') await loseGeneral(A, ca.id, null);
  render();
}

/* ------------------------------------------------------------------ *
 *  停留領地
 * ------------------------------------------------------------------ */
async function territory(p, i) {
  const T = TILES[i], t = G.tiles[i];
  if (t.owner == null) {
    if (p.cash < T.p) { log(`${pname(p)} 軍費不足，無法購買 ${tname(i)}（${fmt(T.p)}）。`); return; }
    const buy = p.ai ? p.cash - T.p >= 3000
      : await ask(p, T.n, `<p>空白${T.t === 'field' ? '古戰場' : '領地'}・${GROUPS[T.g]}</p>
          <p>領地價格 <b>${fmt(T.p)}</b>。${T.t === 'city' ? `稅金：領地 ${fmt(CITY_TOLL[T.p][0])}／小城 ${fmt(CITY_TOLL[T.p][1])}／大城 ${fmt(CITY_TOLL[T.p][2])}；建城費用 ${fmt(BUILD_COST)}。`
            : `稅金依擁有古戰場座數：${FIELD_TOLL.map(fmt).join('／')}。古戰場不得建設城池。`}</p><p>你目前有 ${fmt(p.cash)}。</p>`,
        [{ label: '不買', value: false }, { label: `以 ${fmt(T.p)} 購買`, value: true, cls: 'pri' }]);
    if (buy) { p.cash -= T.p; t.owner = p.id; log(`${pname(p)} 以 ${fmt(T.p)} 購得 ${tname(i)}，取得領地所有證。`); }
  } else if (t.owner === p.id) {
    if (T.t === 'field' || t.level >= 2 || p.cash < BUILD_COST) return;
    const what = t.level === 0 ? '小城' : '大城';
    const build = p.ai ? p.cash - BUILD_COST >= 3000
      : await ask(p, `${T.n}：建設城池？`, `<p>花費 ${fmt(BUILD_COST)} ${t.level === 0 ? '建設' : '改建為'}<b>${what}</b>？稅金將由 ${fmt(CITY_TOLL[T.p][t.level])} 提高為 ${fmt(CITY_TOLL[T.p][t.level + 1])}，敵軍攻城需 ${SIEGE_NEED[t.level + 1]} 名兵力。</p>`,
        [{ label: '不建設', value: false }, { label: `建設（${fmt(BUILD_COST)}）`, value: true, cls: 'pri' }]);
    if (build) { p.cash -= BUILD_COST; t.level++; log(`${pname(p)} 在 ${tname(i)} ${t.level === 1 ? '建設小城' : '改建大城'}。`); }
  } else {
    await encounter(p, i, P(t.owner));
  }
}

// 出戰需要至少一張牌；手上沒有牌時不能單挑或攻城（守方無兵可守時，城池不戰而得）
const hasCard = p => p.cards.length > 0;
function aiEncounter(p, i, o, toll, need) {
  if (!hasCard(p)) return p.troops >= need && o.troops < DEF_TROOPS ? 'siege' : 'toll';
  const strong = bestStat(p, 'atk', true) > estBest(p, o, 'def') || findSpec(p, 'overlord') != null || findSpec(p, 'formation') != null;
  if (p.troops >= need && (o.troops < DEF_TROOPS || (strong && p.troops >= need + DEF_TROOPS))) return 'siege';
  if (toll > 0 && (strong || p.cash < toll)) return 'duel';
  return 'toll';
}
async function encounter(p, i, o) {
  const T = TILES[i], toll = o.rest ? 0 : tollOf(i), need = siegeNeed(i);
  let choice;
  if (p.ai) choice = aiEncounter(p, i, o, toll, need);
  else {
    choice = await ask(p, `${T.n}（${esc(o.name)} 的領地）`,
      `<p>${levelName(i)}・${GROUPS[T.g]}。${o.rest ? `${pname(o)} 休息中，不得收取過路稅。` : `過路稅：<b>${fmt(toll)}</b>。`}</p>
       <p><b>武將單挑</b>：主要目的為避稅。對方可自由選擇是否出戰，不論勝負，本次過路稅皆不得收取。敗方武將被俘虜。</p>
       <p><b>攻城戰</b>：需 ${need} 名兵力（你有 ${p.troops} 名）。不論勝負，你損失 ${need} 名、對方損失 ${DEF_TROOPS} 名。獲勝即佔領 ${T.n}。</p>
       <p><small>${rememberText(p, o)}・兵力 ${o.troops}</small></p>${hasCard(p) ? '' : '<p class="err">你手上沒有牌，不能單挑或攻城（守方兵力不足時仍可佔領）。</p>'}`,
      [{ label: toll === 0 ? '免費通過' : `繳交過路稅 ${fmt(toll)}`, value: 'toll' },
       { label: '⚔ 武將單挑', value: 'duel', disabled: toll === 0 || !hasCard(p) },
       { label: `🏯 攻城戰（${need} 兵）`, value: 'siege', disabled: p.troops < need || (!hasCard(p) && o.troops >= DEF_TROOPS), cls: 'pri' }]);
  }
  if (choice === 'toll') {
    if (toll === 0) { log(`${pname(o)} 休息中，${pname(p)} 免費通過 ${tname(i)}。`); return; }
    log(`${pname(p)} 向 ${pname(o)} 繳交 ${tname(i)} 過路稅 ${fmt(toll)}。`);
    await pay(p, toll, o);
  } else if (choice === 'duel') {
    log(`${pname(p)} 在 ${tname(i)} 向 ${pname(o)} 提出武將單挑！`);
    let accept;
    if (!hasCard(o)) { log(`${pname(o)} 手上沒有牌，無法應戰，${pname(p)} 免繳過路稅通過。`); return; }
    if (o.ai) accept = bestStat(o, 'def', true) > estTypical(o, p, 'atk') || findSpec(o, 'overlord') != null || findSpec(o, 'formation') != null;
    else {
      await handoff(o);
      accept = await ask(o, `${esc(o.name)}：有人挑戰單挑！`, `<p>${pname(p)} 在 ${tname(i)} 向你提出武將單挑。不論勝負，本次皆不得收取過路稅。</p><p>若應戰，敗方武將將被俘虜。</p><p><small>${rememberText(o, p)}</small></p>`,
        [{ label: '拒絕', value: false }, { label: '應戰', value: true, cls: 'pri' }]);
    }
    if (!accept) { log(`${pname(o)} 拒絕出戰，${pname(p)} 免繳過路稅通過。`); return; }
    await battle('duel', p, o, i);
  } else {
    log(`${pname(p)} 對 ${tname(i)} 發動攻城戰！`);
    // 空城之計：免除敵軍攻城一次並俘虜敵軍士兵 500 人
    if (hasReserve(o, 'kongcheng')) {
      let use = true;
      if (!o.ai) {
        await handoff(o);
        use = await ask(o, `${esc(o.name)}：敵軍攻城！`, `<p>${pname(p)} 進攻 ${tname(i)}。你持有保留卡<b>${sName('kongcheng')}</b>，可免除敵軍攻城一次並俘虜敵軍士兵 500 人。是否使用？</p>`,
          [{ label: '不使用', value: false }, { label: `使用${sName('kongcheng')}`, value: true, cls: 'pri' }]);
      }
      if (use) {
        useReserve(o, 'kongcheng');
        const n = Math.min(500, p.troops); p.troops -= n; o.troops += n;
        await tell(o.ai ? p : o, `${tn('strategy')}：${sName('kongcheng')}`, `${pname(o)} 使出<b>${sName('kongcheng')}</b>！${pname(p)} 的攻城被免除，${n} 名士兵被俘虜。`);
        return;
      }
    }
    if (o.troops < DEF_TROOPS) {
      G.tiles[i].owner = p.id;
      await tell(o.ai ? p : o, '攻城戰', `${pname(o)} 兵力不足，無法防禦敵軍攻城，${tname(i)} 被迫棄守，歸 ${pname(p)} 所有。`);
      return;
    }
    if (!hasCard(o)) {
      G.tiles[i].owner = p.id;
      await tell(o.ai ? p : o, '攻城戰', `${pname(o)} 手上沒有牌可出戰，${tname(i)} 被迫棄守，歸 ${pname(p)} 所有。`);
      return;
    }
    let defend = true;
    if (!o.ai) {
      await handoff(o);
      defend = await ask(o, `${esc(o.name)}：敵軍攻城！`, `<p>${pname(p)} 率 ${need} 名兵力進攻 ${tname(i)}。</p><p>若出戰防守，不論勝負損失 ${DEF_TROOPS} 名兵力；若棄守，${T.n} 及其城池之主權歸 ${pname(p)} 所有。</p>`,
        [{ label: '棄守', value: false }, { label: '出戰防守', value: true, cls: 'pri' }]);
    }
    if (!defend) { G.tiles[i].owner = p.id; log(`${pname(o)} 棄守 ${tname(i)}，主權歸 ${pname(p)} 所有。`); return; }
    await battle('siege', p, o, i);
  }
}

/* ------------------------------------------------------------------ *
 *  其他格子
 * ------------------------------------------------------------------ */
async function recruit(p) {
  const max = Math.floor(p.cash / TROOP_UNIT) * TROOP_UNIT;
  if (!max) return;
  let n;
  if (p.ai) n = p.troops < 3000 && p.cash > 4000 ? Math.min(3000 - p.troops, Math.floor((p.cash - 4000) / TROOP_UNIT) * TROOP_UNIT) : 0;
  else n = await ask(p, tn('recruit'), `<p>每名士兵一兩，徵兵數量不限（以 ${TROOP_UNIT} 名為單位）。你目前有兵力 ${p.troops} 名、軍費 ${fmt(p.cash)}。</p>
      徵兵 <input id="rq" type="number" min="0" max="${max}" step="${TROOP_UNIT}" value="${Math.min(1000, max)}" style="width:110px"> 名`,
    [{ label: '不徵兵', value: 0 }, { label: '徵兵', cls: 'pri', value: b => Math.floor(Math.max(0, Math.min(+b.querySelector('#rq').value || 0, max)) / TROOP_UNIT) * TROOP_UNIT }]);
  if (n > 0) { p.cash -= n; p.troops += n; log(`${pname(p)} 徵兵 ${n} 名，花費 ${fmt(n)}。`); }
}
// 從在野武將抽牌（私下抽取，其他人不知道抽到什麼）
async function gainCards(p, n, title, why) {
  const got = drawFromPile(p, n);
  if (!got.length) { log(`${why}，可惜在野武將已無牌可抽。`); return; }
  log(`${why}，${pname(p)} 抽得 ${got.length} 張牌。`);
  render();
  if (!p.ai) await ok(p, title, `<p>${why}，你抽得：</p><div class="cards">${got.map(id => `<div class="copt">${cimg(id)}</div>`).join('')}</div>`);
  else await sleep(S.aiDelay);
}
async function hire(p) {
  if (p.cash < HIRE_COST || !G.pile.length) return;
  const h = p.ai ? p.cash >= 5000
    : await ask(p, tn('hire'), `<p>花費 ${fmt(HIRE_COST)}，從在野武將中隨機抽取一張（也可能抽到特別卡）。</p>`,
        [{ label: '不用了', value: false }, { label: `招募（${fmt(HIRE_COST)}）`, value: true, cls: 'pri' }]);
  if (!h) return;
  p.cash -= HIRE_COST;
  await gainCards(p, 1, tn('hire'), `${pname(p)} 在${tn('hire')}花費 ${fmt(HIRE_COST)}`);
}
// 休息（可用嫁禍于人轉嫁他人）
async function goRest(p, n, fee, where) {
  if (hasReserve(p, 'jiahuo')) {
    const opts = others(p).map(q => ({ label: q.name, value: q }));
    const q = p.ai ? opts.sort((a, b) => b.value.cash - a.value.cash)[0]?.value
      : await choose(p, `${tn('strategy')}：${sName('jiahuo')}`, `你將在${where}休息 ${n} 次。要使用保留卡<b>${sName('jiahuo')}</b>，任選一人代替嗎？`, opts, '不使用');
    if (q) {
      useReserve(p, 'jiahuo');
      log(`${pname(p)} 使出<b>${sName('jiahuo')}</b>，由 ${pname(q)} 代替在${where}休息 ${n} 次！`);
      if (await pay(q, fee, null)) q.rest += n;
      render();
      return;
    }
  }
  if (fee && !(await pay(p, fee, null))) return;
  p.rest += n;
  log(`${pname(p)} 在${where}${fee ? `繳交 ${fmt(fee)}，` : ''}休息 ${n} 次（其間不得收取過路稅）。`);
  render();
}

/* ---- 緊急軍情（15 張）：抽後放回重新洗牌 ---- */
const EMERGENCY = [
  { t: '天災人禍，百姓流離失所，義軍雪中送炭。', s: '向每人說：可憐喔！可憐我吧！再收取每人 1000 兩捐款。',
    f: async p => { for (const q of others(p)) await pay(q, 1000, p); } },
  { k: 'raid', t: '★城池遭遇西涼羌兵洗劫，損失慘重。', s: '損失大小每座城池 500 兩，領地上無城池者免除。',
    f: p => pay(p, 500 * owned(p).filter(i => G.tiles[i].level > 0).length, null) },
  { k: 'parlor', t: '★中了王允的連環美人計，軍心渙散，困守郿塢。', s: '前進至郿塢休息三次。',
    f: async p => { const i = IDXT('rest', 1); await moveTo(p, i); await goRest(p, 3, TILES[i].fee, TILES[i].n); } },
  { k: 'island', t: '洛陽甄官井中五色毫光沖天，撈得失落的傳國玉璽。', s: '速至甄官井尋寶，擲骰子領取點數 ×1000 兩的賞金。',
    f: async p => { await moveTo(p, IDXT('island')); await land(p); } },
  { k: 'mentor', t: '水鏡先生司馬徽為你舉薦臥龍、鳳雛，介紹武將 2 名。', s: '前進至茅廬，如經起點領取雙倍慰勞金。',
    f: async p => { await moveTo(p, IDXT('cottage'), true); await gainCards(p, 2, tn('emergency'), '貴人介紹武將 2 名'); } },
  { k: 'magic', t: '★設壇做法，請來烏角先生左慈施展仙術，撒豆成兵為你助陣。', s: '得士兵 1000 名。',
    f: p => { p.troops += 1000; } },
  { t: '★勇聚殺敵，轟動武林，驚動萬教，招待你至銅雀台。', s: '前進至銅雀台休息一次，並向每人收取 1000 兩。',
    f: async p => { const i = IDXT('rest', 0); await moveTo(p, i); await goRest(p, 1, TILES[i].fee, TILES[i].n); for (const q of others(p)) await pay(q, 1000, p); } },
  { t: '★高薪禮聘請來建築大師「狐搜疤盜」設計大城 2 座。', s: '任意在自己之領地上建設大城或小城改建大城。',
    f: async p => {
      for (let k = 0; k < 2; k++) {
        const opts = owned(p).filter(i => TILES[i].t === 'city' && G.tiles[i].level < 2);
        if (!opts.length) { if (!k) log('……可惜沒有可以建設的領地。'); return; }
        const i = p.ai ? opts.sort((a, b) => TILES[b].p - TILES[a].p)[0]
          : await choose(p, `建築大師（第 ${k + 1} 座）`, '選擇要建成大城的領地：', opts.map(i => ({ label: `${TILES[i].n}（${levelName(i)}）`, value: i })));
        G.tiles[i].level = 2; log(`${pname(p)} 在 ${tname(i)} 建成大城。`); render();
      }
    } },
  { k: 'spy', agent: '蔣幹', t: '派說客蔣幹過江探營，盜得敵軍機密書信。', s: '任選敵方一名，查看其所有武將及軍力。',
    f: async p => {
      const opts = others(p).map(q => ({ label: q.name, value: q }));
      const q = p.ai ? opts.sort((a, b) => b.value.cards.length - a.value.cards.length)[0]?.value
        : await choose(p, `派${spyAgent()}打探`, '選擇要打探的敵方：', opts);
      if (!q) return;
      q.cards.forEach(id => seenBy(p, q, id));
      log(`${pname(p)} 派${spyAgent()}打探，看清了 ${pname(q)} 的所有武將及軍力。`);
      if (!p.ai) await ok(p, `${esc(q.name)} 的軍情`, `<p>兵力 ${q.troops} 名、軍費 ${fmt(q.cash)}</p><div class="cards">${q.cards.map(id => `<div class="copt">${cimg(id)}</div>`).join('') || '（無牌）'}</div>`);
    } },
  { t: '★敵軍大舉入侵，幸遇仙人指點，全軍脫離戰場。', s: '前進至最近「錦囊妙計」抽卡一張，並得士兵 500 名。',
    f: async p => {
      let k = 1; while (TILES[(p.pos + k) % N].t !== 'strategy') k++;
      await move(p, k); p.troops += 500; await drawStrategy(p);
    } },
  { t: '★勤政愛民，深得民心，大笑三聲鼓舞自己。', s: '送給其他敵軍每人 1000 兩，並說「感謝支持謝謝啦」。',
    f: async p => { for (const q of others(p)) if (!(await pay(p, 1000, q))) return; } },
  { k: 'move', title: '木牛流馬', t: '★得諸葛亮所造木牛流馬，運糧行軍來去自如。', s: '可隨心所欲，前進或退後十步內之任何地點。',
    f: async p => {
      const opts = [];
      for (let k = -10; k <= 10; k++) if (k) opts.push({ label: `${k > 0 ? '前進' : '退後'} ${Math.abs(k)} 步：${TILES[(p.pos + k + N) % N].n}`, value: k });
      const k = p.ai ? aiBestStep(p, opts.map(o => o.value)) : await choose(p, themeCard('move').title || EMERGENCY.find(c => c.k === 'move').title, '選擇要移動到的地點：', opts);
      if (k > 0) await move(p, k); else { p.pos = (p.pos + k + N) % N; render(); }
      await land(p);
    } },
  { t: '★勤練兵法，派兵參加體能競賽，並交報名費 1000 兩。', s: '做仰臥起坐：5 下領 1000 兩，10 下領 3000 兩，15 下領 10000 兩；放棄或未滿 5 下者不得領獎。',
    f: async p => {
      if (!(await pay(p, 1000, null))) return;
      const prize = p.ai ? pickRandom([0, 1000, 1000, 3000, 3000, 10000])
        : await choose(p, '體能競賽', '請實際做仰臥起坐，然後選擇完成的次數：',
            [{ label: '15 下以上（領 10000 兩）', value: 10000 }, { label: '10 下以上（領 3000 兩）', value: 3000 }, { label: '5 下以上（領 1000 兩）', value: 1000 }, { label: '放棄或未滿 5 下', value: 0 }]);
      p.cash += prize; log(prize ? `${pname(p)} 在體能競賽中獲得 ${fmt(prize)}！` : `${pname(p)} 在體能競賽中未能得獎。`);
    } },
  { t: '★強將手下無弱兵，敵兵慕名前來向你投靠。', s: '為證明你是強將，交互蹲跳 5 下，並向每人收取 500 名士兵。',
    f: p => { for (const q of others(p)) { const n = Math.min(500, q.troops); q.troops -= n; p.troops += n; } } },
  { t: '智能不足（IQ75）聽信敵軍謠言，軍心渙散，損失士兵 1000 人。', s: '吐舌頭，自罵三次「偶素傻瓜」。',
    f: p => { p.troops = Math.max(0, p.troops - 1000); } },
];
function aiBestStep(p, steps) {
  const score = k => {
    const i = (p.pos + k + N) % N, T = TILES[i], t = G.tiles[i];
    if (isProp(i)) {
      if (t.owner == null) return p.cash - T.p >= 3000 ? 3 + T.p / 1000 : 0;
      if (t.owner === p.id) return 1;
      return -tollOf(i) / 1000;
    }
    return { island: 4, cottage: 3, strategy: 1, hire: 1, start: 2, recruit: 0.5, emergency: 0, shop: -0.5, rest: -2 }[T.t] ?? 0;
  };
  return steps.reduce((a, b) => score(b) > score(a) ? b : a);
}

/* ---- 錦囊妙計（15 張）：保留卡可留在手中，限用一次 ---- */
const STRATEGY = [
  { k: 'yibing', n: '疑兵之計', keep: 'turn', s: '所有敵軍休息一次，並退後三步。',
    f: p => { for (const q of others(p)) { q.rest += 1; q.pos = (q.pos - 3 + N) % N; } log(`所有敵軍休息一次並退後三步。`); } },
  { k: 'yihua', n: '移花接木', s: '用己方小城，交換任一敵軍之大城一座。',
    f: async p => {
      const mine = owned(p).filter(i => G.tiles[i].level === 1);
      const theirs = G.tiles.map((t, i) => i).filter(i => G.tiles[i].owner != null && G.tiles[i].owner !== p.id && G.tiles[i].level === 2);
      if (!mine.length || !theirs.length) { log('……沒有可交換的小城或敵軍大城，此計無效。'); return; }
      let a, b;
      if (p.ai) { a = mine.sort((x, y) => TILES[x].p - TILES[y].p)[0]; b = theirs.sort((x, y) => TILES[y].p - TILES[x].p)[0]; }
      else {
        a = await choose(p, '移花接木', '選擇你要交出的小城：', mine.map(i => ({ label: TILES[i].n, value: i })));
        b = await choose(p, '移花接木', '選擇要換來的敵軍大城：', theirs.map(i => ({ label: `${TILES[i].n}（${P(G.tiles[i].owner).name}）`, value: i })));
      }
      const o = G.tiles[b].owner; G.tiles[b].owner = p.id; G.tiles[a].owner = o;
      log(`${pname(p)} 以 ${tname(a)} 小城交換 ${pname(P(o))} 的 ${tname(b)} 大城。`);
    } },
  { k: 'kurou', n: '苦肉之計', s: '每名敵軍彈你兩下耳朵，並抽他們武將一名。',
    f: p => { for (const q of others(p)) stealGeneral(p, q); } },
  { k: 'kongcheng', n: '空城之計', keep: 'siege', s: '免除敵軍攻城一次，並俘虜敵軍士兵 500 人。（被攻城時使用）' },
  { k: 'jinchan', n: '金蟬脫殼', keep: 'turn', s: '可移動至任何地點。（取代本回合擲骰）' },
  { k: 'caochuan', n: '草船借箭', s: '擲骰子，向每人收取每點士兵 500 名。',
    f: p => { const [r] = roll(1); showDice([r]); log(`${pname(p)} 擲出 ${r} 點。`); for (const q of others(p)) { const n = Math.min(r * 500, q.troops); q.troops -= n; p.troops += n; } } },
  { k: 'dongfeng', n: '孔明借東風', s: '擲骰子，單數得武將一名，雙數得兩名。',
    f: async p => { const [r] = roll(1); showDice([r]); await gainCards(p, r % 2 ? 1 : 2, '孔明借東風', `${pname(p)} 擲出 ${r} 點`); } },
  { k: 'toulong', n: '偷龍轉鳳', keep: 'turn', s: '可任選一名敵軍，與其交換領地，含城池。' },
  { k: 'huoshao', n: '火燒連營', s: '燒毀敵軍每人城池兩座，大城變小城。',
    f: p => {
      for (const q of others(p)) {
        const cs = owned(q).filter(i => G.tiles[i].level > 0).sort((a, b) => G.tiles[b].level - G.tiles[a].level || TILES[b].p - TILES[a].p).slice(0, 2);
        cs.forEach(i => { G.tiles[i].level--; });
        if (cs.length) log(`${pname(q)} 的 ${cs.map(tname).join('、')} 被燒毀一級。`);
      }
    } },
  { k: 'paozhuan', n: '拋磚引玉', s: '擲骰子，向每人收取每點 500 兩。',
    f: async p => { const [r] = roll(1); showDice([r]); log(`${pname(p)} 擲出 ${r} 點。`); for (const q of others(p)) await pay(q, r * 500, p); } },
  { k: 'luojing', n: '落井下石', keep: 'turn', s: '休息之中任何敵軍，加倍休息次數。' },
  { k: 'huilu', n: '賄賂之計', s: '任選一名敵軍付他 500 兩，抽選其武將一名。',
    f: async p => {
      const opts = others(p).filter(q => generals(q).some(id => id !== q.commander)).map(q => ({ label: q.name, value: q }));
      if (!opts.length) { log('……沒有敵軍可以賄賂。'); return; }
      const q = p.ai ? pickRandom(opts).value : await choose(p, '賄賂之計', '選擇要賄賂的敵軍：', opts);
      if (await pay(p, 500, q)) stealGeneral(p, q);
    } },
  { k: 'jijiang', n: '激將之計', s: '任選敵軍兩人猜拳，輸者伏地挺身 5 下並休息一次。',
    f: async p => {
      const os = others(p);
      let pair;
      if (os.length >= 2) {
        if (p.ai) pair = shuffle([...os]).slice(0, 2);
        else {
          const a = await choose(p, '激將之計', '選擇第一位敵軍：', os.map(q => ({ label: q.name, value: q })));
          const b = await choose(p, '激將之計', '選擇第二位敵軍：', os.filter(q => q !== a).map(q => ({ label: q.name, value: q })));
          pair = [a, b];
        }
      } else pair = [p, os[0]]; // 只剩一名敵軍時，由你與他猜拳
      const loser = pickRandom(pair);
      loser.rest += 1;
      log(`${pname(pair[0])} 與 ${pname(pair[1])} 猜拳，${pname(loser)} 輸了，伏地挺身 5 下並休息一次。`);
    } },
  { k: 'diaohu', n: '調虎離山', keep: 'turn', s: '可任意調離敵軍至其他領地，並不得經由起點。' },
  { k: 'jiahuo', n: '嫁禍于人', keep: 'rest', s: '若走進休息指示時，可任選一人代替。' },
];
// 錦囊以固定代號（k）辨識，顯示名稱可依主題替換
const stratIdx = key => STRATEGY.findIndex(c => c.k === key);
const sName = key => STRATEGY[stratIdx(key)].n;
const sDesc = key => STRATEGY[stratIdx(key)].s;
const BASE_STRAT_NAME = Object.fromEntries(STRATEGY.map(c => [c.k, c.n]));
const hasReserve = (p, key) => p.reserve.some(i => STRATEGY[i].k === key);
function useReserve(p, key) { const i = p.reserve.findIndex(x => STRATEGY[x].k === key); if (i >= 0) p.reserve.splice(i, 1); flashDeck('strategy'); render(); }
function stealGeneral(p, q) {
  const g = generals(q).filter(id => id !== q.commander);
  if (!g.length) return;
  const id = pickRandom(g);
  transferCard(q, p, id);
  log(`${pname(p)} 抽走了 ${pname(q)} 的武將 ${card(id).name}。`);
}
const slip = (head, text, sub) => `<div class="slip"><div class="hd">${head}</div><div>${text}</div>${sub ? `<small>（${sub}）</small>` : ''}</div>`;

// 主題對某張緊急軍情卡的替換內容（themes.js 的 emergency）
const themeCard = k => (k && (THEMES[themeKey].emergency || {})[k]) || {};
// 打探敵情卡的探子：三國為蔣幹，其他主題可在 themes.js 指定
const spyAgent = () => themeCard('spy').agent || EMERGENCY.find(c => c.k === 'spy').agent;
// 卡面文字中提到的格子名稱，換成目前主題的名稱
const themedText = str => themeKey === 'sanguo' ? str : str.replace(/錦囊妙計|郿塢|銅雀台|甄官井|茅廬/g, m =>
  ({ 錦囊妙計: tn('strategy'), 郿塢: TILES[IDXT('rest', 1)].n, 銅雀台: TILES[IDXT('rest', 0)].n, 甄官井: tn('island'), 茅廬: tn('cottage') })[m]);

async function drawEmergency(p) {
  flashDeck('emergency');
  // 主題可替換個別卡面文字（themes.js 的 emergency，以卡的 k 為鍵）；其餘卡只換格子名稱
  const e = pickRandom(EMERGENCY), o = themeCard(e.k);
  const c = { ...e, t: o.t || themedText(e.t), s: o.s || themedText(e.s) };
  log(`${pname(p)} 抽到${tn('emergency')}：${c.t}（${c.s}）`);
  render();
  if (!p.ai) await ok(p, tn('emergency'), slip(tn('emergency'), c.t, c.s)); else await sleep(S.aiDelay);
  await c.f(p);
  render();
}
async function drawStrategy(p) {
  flashDeck('strategy');
  const avail = STRATEGY.map((c, k) => k).filter(k => !G.players.some(q => q.reserve.includes(k)));
  if (!avail.length) { log(`${tn('strategy')}已被抽光。`); return; }
  const k = pickRandom(avail), c = STRATEGY[k];
  if (c.keep) {
    p.reserve.push(k);
    log(`${pname(p)} 抽到一張${tn('strategy')}保留卡，收入錦囊中。`);
    render();
    if (!p.ai) await ok(p, tn('strategy'), slip(c.n, c.s, '保留卡，限用一次') + '<p>已收入你的錦囊，可在適當時機使用。</p>'); else await sleep(S.aiDelay);
    return;
  }
  log(`${pname(p)} 抽到${tn('strategy')}：<b>${c.n}</b>——${c.s}`);
  render();
  if (!p.ai) await ok(p, tn('strategy'), slip(c.n, c.s)); else await sleep(S.aiDelay);
  await c.f(p);
  render();
}

/* ---- 回合中使用的錦囊保留卡 ---- */
function turnReserves(p) {
  return [...new Set(p.reserve.map(i => STRATEGY[i].k))].filter(key => {
    if (STRATEGY[stratIdx(key)].keep !== 'turn') return false;
    if (key === 'luojing') return others(p).some(q => q.rest > 0);
    if (key === 'toulong' || key === 'diaohu') return others(p).length > 0;
    return true;
  });
}
// 回傳 true 表示已移動並結算（金蟬脫殼取代擲骰）
async function playReserve(p, key, opts = {}) {
  const ai = p.ai, n = sName(key);
  if (key === 'yibing') {
    useReserve(p, key); log(`${pname(p)} 使出<b>${n}</b>！`); STRATEGY[stratIdx('yibing')].f(p); render(); return false;
  }
  if (key === 'luojing') {
    const rs = others(p).filter(q => q.rest > 0).map(q => ({ label: `${q.name}（休息 ${q.rest} 次）`, value: q }));
    const q = ai ? rs.sort((a, b) => b.value.rest - a.value.rest)[0].value : await choose(p, n, '選擇休息中的敵軍：', rs, '取消');
    if (!q) return false;
    useReserve(p, key); q.rest *= 2; log(`${pname(p)} 使出<b>${n}</b>，${pname(q)} 休息次數加倍為 ${q.rest} 次！`); render(); return false;
  }
  if (key === 'toulong') {
    const os = others(p).map(q => ({ label: `${q.name}（領地 ${owned(q).length} 處）`, value: q }));
    const q = ai ? opts.target : await choose(p, n, '選擇要與你交換全部領地（含城池）的敵軍：', os, '取消');
    if (!q) return false;
    useReserve(p, key);
    G.tiles.forEach(t => { if (t.owner === p.id) t.owner = q.id; else if (t.owner === q.id) t.owner = p.id; });
    log(`${pname(p)} 使出<b>${n}</b>，與 ${pname(q)} 交換全部領地及城池！`); render(); return false;
  }
  if (key === 'diaohu') {
    let q, dest;
    if (ai) ({ target: q, dest } = opts);
    else {
      q = await choose(p, n, '選擇要調離的敵軍：', others(p).map(o => ({ label: o.name, value: o })), '取消');
      if (!q) return false;
      dest = await choose(p, n, `把 ${esc(q.name)} 調到哪一處領地？`, TILES.map((T, i) => i).filter(i => isProp(i) && i !== q.pos)
        .map(i => ({ label: `${TILES[i].n}（${G.tiles[i].owner == null ? '空白' : P(G.tiles[i].owner).name + '・稅 ' + tollOf(i)}）`, value: i })), '取消');
      if (dest == null) return false;
    }
    useReserve(p, key);
    q.pos = dest; // 不得經由起點，故不領軍費
    log(`${pname(p)} 使出<b>${n}</b>，把 ${pname(q)} 調到 ${tname(dest)}！`);
    render();
    await land(q);
    return false;
  }
  if (key === 'jinchan') {
    const dest = ai ? opts.dest : await choose(p, n, '選擇要移動到的地點：', TILES.map((T, i) => ({ label: T.n + (isProp(i) && G.tiles[i].owner != null ? `（${P(G.tiles[i].owner).name}）` : ''), value: i })).filter(o => o.value !== p.pos), '取消');
    if (dest == null) return false;
    useReserve(p, key);
    p.pos = dest; log(`${pname(p)} 使出<b>${n}</b>，移動到 ${tname(dest)}。`); render();
    await land(p);
    return true;
  }
  return false;
}
async function humanReserveMenu(p) {
  const keys = turnReserves(p);
  const key = await choose(p, '使用保留卡', '選擇要使用的保留卡：', keys.map(k => ({ label: `<b>${sName(k)}</b>——${sDesc(k)}`, value: k })), '取消');
  return key ? playReserve(p, key) : false;
}
async function aiReserves(p) {
  for (const key of turnReserves(p)) {
    if (!p.alive || G.over) return false;
    if (key === 'luojing' || key === 'yibing') await playReserve(p, key);
    else if (key === 'toulong') {
      const val = q => owned(q).reduce((a, i) => a + tileValue(i), 0);
      const q = others(p).sort((a, b) => val(b) - val(a))[0];
      if (q && val(q) > val(p) * 1.3 + 1000) await playReserve(p, key, { target: q });
    } else if (key === 'diaohu') {
      const mine = owned(p).filter(i => tollOf(i) >= 1000).sort((a, b) => tollOf(b) - tollOf(a));
      const q = others(p).sort((a, b) => b.cash - a.cash)[0];
      if (mine.length && q && q.pos !== mine[0]) await playReserve(p, key, { target: q, dest: mine[0] });
    } else if (key === 'jinchan') {
      const buys = TILES.map((T, i) => i).filter(i => isProp(i) && G.tiles[i].owner == null && p.cash - TILES[i].p >= 3000 && i !== p.pos)
        .sort((a, b) => TILES[b].p - TILES[a].p);
      if (buys.length) return playReserve(p, key, { dest: buys[0] });
    }
  }
  return false;
}

async function land(p) {
  if (!p.alive || G.over) return;
  const i = p.pos, T = TILES[i];
  render();
  switch (T.t) {
    case 'city': case 'field': return territory(p, i);
    case 'recruit': return recruit(p);
    case 'hire': return hire(p);
    case 'shop': log(`${pname(p)} 在${T.n}消費 ${fmt(T.fee)}。`); await pay(p, T.fee, null); return;
    case 'rest': return goRest(p, 1, T.fee, T.n);
    case 'island': {
      const r = roll(1);
      showDice(r);
      p.cash += r[0] * 1000;
      return tell(p, T.n, `${pname(p)} 在${T.n}擲出 ${r[0]} 點，向國庫領取 ${fmt(r[0] * 1000)} 軍費！`);
    }
    case 'cottage': {
      const r = roll(3), s = r.reduce((a, b) => a + b, 0);
      showDice(r);
      const n = s >= 16 ? 3 : s >= 13 ? 2 : s >= 10 ? 1 : 0;
      if (!n) return tell(p, T.n, `${pname(p)} 來到${T.n}，擲出 ${s} 點——可惜無人應門。`);
      return gainCards(p, n, T.n, `${pname(p)} 來到${T.n}，擲出 ${s} 點，免費得武將 ${n} 名`);
    }
    case 'emergency': return drawEmergency(p);
    case 'strategy': return drawStrategy(p);
  }
}

/* ------------------------------------------------------------------ *
 *  行軍與回合
 * ------------------------------------------------------------------ */
// withDice：擲骰後的移動與擲骰消息同時進行，逐格前進時不等消息讀完
async function move(p, steps, doublePass = false, withDice = false) {
  for (let k = 0; k < steps; k++) {
    p.pos = (p.pos + 1) % N;
    if (p.pos === 0 && k < steps - 1) {
      const amt = S.passStart * (doublePass ? 2 : 1);
      p.cash += amt; log(`${pname(p)} 經過起點，向國庫支領 ${fmt(amt)} 軍費。`);
    }
    render(); // 電腦逐格前進的速度可由 opts.stepMs 調整
    if (withDice) await UI.sleep(p.ai ? S.stepMs : 110); else await sleep(p.ai ? S.stepMs : 110);
  }
  if (p.pos === 0 && steps > 0) { p.cash += S.passStart * 2; log(`${pname(p)} 停留起點，加倍領取 ${fmt(S.passStart * 2)} 軍費！`); render(); }
}
const moveTo = (p, target, doublePass) => move(p, (target - p.pos + N) % N, doublePass);
async function rollAndMove(p) {
  const r = roll(1), s = r[0]; // 全遊戲只用一顆骰子（1–6 點）
  await waitRead(); // 先讀完之前的消息
  showDice(r);
  // 擲骰消息與旗幟移動同時進行：至少停留選定的閱讀時間，旗幟走得更久就停留到走完
  log(`${pname(p)} 擲出 ${s} 點。`, p.ai ? Math.max(S.readMs, s * S.stepMs) : undefined);
  await move(p, s, false, true);
  await land(p);
}
async function showHand(p) {
  await handoff(p);
  const mem = others(p).map(q => `<li>${rememberText(p, q)}</li>`).join('');
  await ok(p, `${esc(p.name)} 的手牌`, `<div class="cards">${p.cards.map(id => `<div class="copt">${cimg(id)}${id === p.commander ? '<span class="cmdbadge">★主帥</span>' : ''}</div>`).join('')}</div>
    ${p.reserve.length ? `<p><b>保留卡：</b>${p.reserve.map(k => `${STRATEGY[k].n}（${STRATEGY[k].s}）`).join('；')}</p>` : ''}
    <p><b>你對其他人的記憶：</b></p><ul>${mem}</ul>`);
}
// 人類回合：等待擲骰，期間可使用錦囊、變賣資產、查看手牌。回傳 true 表示已用金蟬脫殼移動
async function humanTurn(p) {
  for (;;) {
    await waitRead();
    const act = await UI.turn(p, { reserve: turnReserves(p).length > 0 });
    if (act === 'roll') return false;
    if (act === 'reserve') { const moved = await humanReserveMenu(p); render(); if (moved || !p.alive || G.over) return true; }
    else if (act === 'sell') { await sellDialog(p, 0); render(); }
    else if (act === 'hand') await showHand(p);
  }
}
async function turn(p) {
  if (p.rest > 0) { p.rest--; log(`${pname(p)} 休息中，本回合暫停${p.rest ? `（尚需休息 ${p.rest} 次）` : ''}。`); render(); await sleep(S.aiDelay); return; }
  let moved;
  if (p.ai) { await sleep(S.aiDelay); moved = await aiReserves(p); }
  else { await handoff(p); moved = await humanTurn(p); }
  if (!moved && p.alive && !G.over) await rollAndMove(p);
}
function checkWin() {
  if (G.over) return;
  const al = alive();
  if (al.length === 0) { G.over = true; waitRead().then(() => UI.gameOver(null, '所有人都失敗了！')); return; }
  let w = null, why = '';
  if (al.length === 1) { w = al[0]; why = '其他所有對手全部失敗，流落街頭或成為俘虜，成為統一中國之霸主！'; }
  else for (const p of al) {
    if (owned(p).length >= S.winTerr) { w = p; why = `佔有領地達 ${owned(p).length} 處，國力雄厚，其他君主不得不伏首稱臣！`; break; }
    const gs = groupsComplete(p);
    if (gs.length) { w = p; why = `佔有${GROUPS[gs[0]]}全部領地，其他君主不得不伏首稱臣！`; break; }
  }
  if (w) {
    G.over = true;
    log(`🏆 ${pname(w)} 獲勝：${why}`);
    render();
    const html = `<p style="font-size:20px">${pname(w)} 獲勝：${why}</p><p>勝利者可向每人提出一個要求，他人不得拒絕。若有不服氣者，可以重新再戰，討回面子！</p>`;
    waitRead().then(() => UI.gameOver(w, html));
  }
}
async function gameLoop() {
  while (!G.over) {
    const p = G.players[G.turn];
    if (p.alive) { G.cur = p.id; render(); await turn(p); render(); checkWin(); }
    G.turn = (G.turn + 1) % G.players.length;
  }
  render();
}


/* ------------------------------------------------------------------ *
 *  建立新局
 *  seats: [{ ai: 是否電腦, cmd: 主帥牌 id（0–3）}]；opts: { aiDelay, stepMs, readMs, theme, hints }（佔有領地 20 處獲勝為固定規則）
 * ------------------------------------------------------------------ */
function newGame(seats, opts, ui) {
  UI = ui;
  applyTheme(opts.theme || 'sanguo');
  HINT = { ...HINT_BASE, ...(opts.hints || {}) };
  if (opts.aiDelay != null) S.aiDelay = opts.aiDelay;
  S.stepMs = opts.stepMs || 110;
  S.readMs = opts.readMs || 0;
  readUntil = 0; readSkip = null;
  const chosen = seats.map(r => r.cmd);
  G = {
    // 主帥全場公開；玩家即以主帥稱呼，旗幟與印章使用主帥姓氏
    players: seats.map((r, k) => ({ id: k, name: CARDS[r.cmd].name, family: CARDS[r.cmd].name[0], ai: r.ai, color: PLAYER_COLORS[k], pos: 0,
      cash: S.startCash, troops: S.startTroops, cards: [r.cmd], commander: r.cmd, rest: 0, reserve: [], alive: true })),
    tiles: TILES.map(() => ({ owner: null, level: 0 })),
    pile: shuffle(CARDS.map(c => c.id).filter(id => !chosen.includes(id))), // 未被選用之主帥當作一般武將
    turn: 0, cur: null, over: false, theme: themeKey,
  };
  G.mem = G.players.map(() => G.players.map(() => new Set()));
  for (const p of G.players) drawFromPile(p, 3); // 每名參加者選定主帥後再抽三張牌
  log(`遊戲開始！每位君主有軍費 ${fmt(S.startCash)}、兵力 ${S.startTroops} 名、主帥一名及撲克牌三張。${HINT.tile}。`);
  return G;
}

/* 某位玩家眼中的局面：只含自己的手牌，以及從公開事件記得的他人牌。
 * vid：玩家 id；'all' 為旁觀（不顯示任何手牌）；null 為多人共用裝置 */
function viewFor(vid) {
  const me = typeof vid === 'number' ? G.players[vid] : null;
  return {
    me: me ? me.id : null, theme: themeKey,
    cur: G.cur, over: G.over, pile: G.pile.length,
    players: G.players.map(p => ({
      id: p.id, name: p.name, family: p.family, color: p.color, ai: p.ai, alive: p.alive, pos: p.pos,
      cash: p.cash, troops: p.troops, rest: p.rest, reserveN: p.reserve.length, owned: owned(p).length,
      groups: groupsComplete(p), cardN: p.cards.length, commander: p.commander, hasCmd: p.cards.includes(p.commander),
      hand: me === p ? [...p.cards] : null,
      reserve: me === p ? p.reserve.map(k => STRATEGY[k].n) : null,
      known: me && me !== p ? known(me, p) : [],
    })),
    tiles: G.tiles.map((t, i) => ({ owner: t.owner, level: t.level,
      toll: isProp(i) && t.owner != null ? (G.players[t.owner].rest ? 0 : tollOf(i)) : null })),
  };
}

// 載入時先套用三國主題的名稱（格子名稱只定義在 themes.js）
applyTheme('sanguo');

return {
  S, TILES, GROUPS, CITY_TOLL, FIELD_TOLL, BUILD_COST, SIEGE_NEED, LEVEL_NAME, DEF_TROOPS, HIRE_COST, RANSOM, SALE_TAX,
  GEN_BASE, SPECIAL_BASE, POKER, SUIT, CARDS, KIND_LABEL, KIND_HELP, PLAYER_COLORS, DIE,
  fmt, esc, isProp, newGame, viewFor, gameLoop, state: () => G,
  THEMES, applyTheme, theme: () => themeKey, sName, sDesc, tn, skipReading,
  // 速度設定（aiDelay）對應的逐格速度與每條消息停留時間：慢 5 秒、中 3 秒、快 2 秒
  PACE: { 900: { stepMs: 380, readMs: 5000 }, 450: { stepMs: 260, readMs: 3000 }, 120: { stepMs: 150, readMs: 2000 } },
};
});
