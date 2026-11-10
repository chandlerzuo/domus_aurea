'use strict';
/* 一桌的遊戲：每桌在自己的 worker 執行緒中跑一份獨立的規則引擎。
 * 引擎把一局的狀態放在模組變數裡，同一個行程無法同時進行四局；每個 worker 各自載入一份引擎，彼此互不影響。
 *
 * 父行程（server.js）→ worker：
 *   { t: 'answer', id, btn, inputs, rid }   玩家回答問題
 *   { t: 'standup', pid }                   玩家離座，改由電腦接手
 * worker → 父行程：
 *   views / log / dice / flash / ask / turn / resolved / over / answered / crash
 * 啟動資料（workerData）：{ seats: [{ ai, cmd }], humanPids: [...], opts } */
const { parentPort, workerData } = require('worker_threads');
const crypto = require('crypto');
const E = require('../engine.js');
const { makeForm } = require('./form.js');

const humans = new Set(workerData.humanPids);   // 目前由真人操作的玩家
const pending = new Map();                      // id → { id, pid, buttons, body, turn, resolve }
const post = m => parentPort.postMessage(m);

/* ---- 畫面更新：每位真人一份自己的視角，另有旁觀視角 ---- */
let renderQueued = false;
function sendViews() {
  renderQueued = false;
  const byPid = {};
  for (const pid of humans) byPid[pid] = E.viewFor(pid);
  post({ t: 'views', byPid, all: E.viewFor('all') });
}

const ui = {
  sleep: ms => new Promise(r => setTimeout(r, ms)),
  log: (html, meta) => post({ t: 'log', html, meta }),
  render: () => { if (!renderQueued) { renderQueued = true; setImmediate(sendViews); } },
  dice: r => post({ t: 'dice', r }),
  flash: k => post({ t: 'flash', k }),
  handoff: async () => {},
  ask: (p, title, body, buttons) => new Promise(resolve => {
    const id = crypto.randomUUID();
    const msg = { type: 'ask', id, title, body, buttons: buttons.map(b => ({ label: b.label, cls: b.cls, disabled: !!b.disabled })) };
    const q = { id, pid: p.id, buttons, body, resolve };
    pending.set(id, q);
    // 引擎決定「給真人看」到真正送出問題之間有一小段延遲；玩家若剛好在這時離座，就直接代答，不再送出
    if (!humans.has(p.id)) autoAnswer(q); else post({ t: 'ask', id, pid: p.id, msg });
  }),
  turn: (p, opts) => new Promise(resolve => {
    const id = crypto.randomUUID();
    const q = { id, pid: p.id, turn: true, resolve };
    pending.set(id, q);
    if (!humans.has(p.id)) finish(q, 'roll'); else post({ t: 'turn', id, pid: p.id, msg: { type: 'turn', id, opts } });
  }),
  gameOver: (w, html) => {
    sendViews();
    post({ t: 'over', title: w ? '🏆 勝利' : '遊戲結束', html });
  },
};

function finish(q, value) {
  pending.delete(q.id);
  post({ t: 'resolved', id: q.id });
  q.resolve(value);
}

/* ---- 玩家回答 ---- */
const cleanInputs = list => (Array.isArray(list) ? list : []).slice(0, 200).map(i => ({
  id: typeof i.id === 'string' ? i.id : undefined, name: typeof i.name === 'string' ? i.name : undefined,
  type: typeof i.type === 'string' ? i.type : undefined, value: String(i.value ?? '').slice(0, 40), checked: !!i.checked,
  k: typeof i.k === 'string' ? i.k : undefined }));

function onAnswer(m) {
  const q = pending.get(m.id);
  if (!q) return post({ t: 'answered', rid: m.rid, ok: false, error: '這題已經結束' });
  if (q.turn) {
    if (!['roll', 'reserve', 'sell', 'hand'].includes(m.btn)) return post({ t: 'answered', rid: m.rid, ok: false, error: '未知的動作' });
    finish(q, m.btn);
    return post({ t: 'answered', rid: m.rid, ok: true });
  }
  const b = q.buttons[m.btn];
  if (!b || b.disabled) return post({ t: 'answered', rid: m.rid, ok: false, error: '按鈕錯誤' });
  let v = b.value;
  if (typeof v === 'function') {
    const form = makeForm(cleanInputs(m.inputs));
    try { v = v(form); } catch (e) { return post({ t: 'answered', rid: m.rid, ok: false, error: '表單錯誤' }); }
    if (v === undefined) return post({ t: 'answered', rid: m.rid, ok: false, errors: form.errors });
  }
  finish(q, v);
  post({ t: 'answered', rid: m.rid, ok: true });
}

/* ---- 離座：改由電腦接手 ----
 * 玩家若正好有一個問題沒答，替他按預設答案（通常是標示為主要的按鈕），之後的決定全由電腦負責。 */
function parseInputs(html) {
  const out = [];
  for (const m of String(html).matchAll(/<input\b([^>]*)>/g)) {
    const a = k => { const r = new RegExp('(?:^|\\s)' + k + '="([^"]*)"').exec(m[1]); return r ? r[1] : undefined; };
    const type = a('type') || 'text';
    out.push({ id: a('id'), name: a('name'), type, value: a('value') ?? (type === 'checkbox' ? 'on' : '0'),
      checked: /(?:^|\s)checked(?:\s|=|$)/.test(m[1]), k: a('data-k') });
  }
  return out;
}
function autoAnswer(q) {
  const base = parseInputs(q.body);
  const variants = [base];
  // 被迫變賣資產（需要錢才能付款）時，依序多勾幾項直到金額足夠；自願的變賣不替他賣東西
  if (/需要[^<]*你目前只有/.test(q.body)) {
    const boxes = base.filter(i => i.type === 'checkbox');
    for (let n = 1; n <= boxes.length; n++) {
      const on = new Set(boxes.slice(0, n));
      variants.push(base.map(i => (on.has(i) ? { ...i, checked: true } : i)));
    }
  }
  const order = q.buttons.map((b, k) => k).sort((x, y) => (q.buttons[y].cls === 'pri') - (q.buttons[x].cls === 'pri'));
  for (const k of order) {
    const b = q.buttons[k];
    if (b.disabled) continue;
    if (typeof b.value !== 'function') return finish(q, b.value);
    for (const inputs of variants) {
      try {
        const v = b.value(makeForm(cleanInputs(inputs)));
        if (v !== undefined) return finish(q, v);
      } catch (e) { /* 這個答案不行，換下一個 */ }
    }
  }
  finish(q, null);
}
function onStandUp(m) {
  const p = E.state().players[m.pid];
  if (!p || p.ai || !humans.has(m.pid)) return;
  p.ai = true;
  humans.delete(m.pid);
  ui.log(`<b style="color:${p.color}">${E.esc(p.name)}</b> 離座，由電腦接手。`);
  for (const q of [...pending.values()]) {
    if (q.pid !== m.pid) continue;
    if (q.turn) finish(q, 'roll'); else autoAnswer(q);
  }
  ui.render();
}

parentPort.on('message', m => {
  try {
    if (m.t === 'answer') onAnswer(m);
    else if (m.t === 'standup') onStandUp(m);
  } catch (err) { post({ t: 'crash', message: String(err && err.stack || err) }); }
});

E.newGame(workerData.seats, workerData.opts, ui);
sendViews();
E.gameLoop().catch(err => post({ t: 'crash', message: String(err && err.stack || err) }));
