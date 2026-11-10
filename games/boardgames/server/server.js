'use strict';
/* 三國風雲　連線伺服器（Node.js，無外部套件）
 *
 * 四張桌子，每張桌子有自己的座位、大廳與牌局。玩家可以入座後等朋友加入，或用電腦補滿空位開局；
 * 牌局中隨時可以離座，該座位由電腦接手；真人全部離座時牌局結束、桌子重新開放。
 *
 * 每一局在自己的 worker 執行緒中執行一份獨立的規則引擎（見 game_worker.js）：引擎把一局的狀態放在
 * 模組變數裡，同一個行程裡無法同時進行四局。每位玩家的瀏覽器只會收到「自己眼中的局面」與自己的題目，
 * 因此他人的手牌不會傳到你的瀏覽器。
 *
 * 安全：本程式沒有自己的登入，只接受 127.0.0.1／::1／localhost。
 * 座位代碼（token）只用來把瀏覽器分頁對應到座位，不是登入驗證；
 * 要讓其他電腦的朋友加入，必須放在有登入的 HTTPS 反向代理後面（見 README.md 的 deploy/）。
 *
 * 執行：node server/server.js　（可用 SANGUO_PORT 改埠號，預設 8765）
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { Worker } = require('worker_threads');
const E = require('../engine.js');   // 只用主題與速度設定；牌局在 worker 中執行

const HOST = process.env.SANGUO_HOST || '127.0.0.1';
const PORT = +process.env.SANGUO_PORT || 8765;
const LOOPBACK = ['127.0.0.1', '::1', 'localhost'];
if (!LOOPBACK.includes(HOST)) {
  console.error(`拒絕在 ${HOST} 上啟動：本版本沒有登入驗證，只允許本機位址（127.0.0.1）。`);
  console.error('要開放給其他電腦，請先依 README.md 部署到個人主機並接上正式登入。');
  process.exit(1);
}

/* ---- 靜態檔案：只提供白名單內的檔案 ---- */
const ROOT = path.join(__dirname, '..');
const FILES = {
  '/': ['index.html', 'text/html; charset=utf-8'],
  '/index.html': ['index.html', 'text/html; charset=utf-8'],
  '/engine.js': ['engine.js', 'text/javascript; charset=utf-8'],
  '/client.js': ['client.js', 'text/javascript; charset=utf-8'],
  '/cards.js': ['cards.js', 'text/javascript; charset=utf-8'],
  '/themes.js': ['themes.js', 'text/javascript; charset=utf-8'],
  '/texts.js': ['texts.js', 'text/javascript; charset=utf-8'],
};
// 每個主題的棋盤圖與卡圖檔（名單取自 themes.js，不提供名單以外的檔案）
for (const th of Object.values(E.THEMES)) {
  FILES['/' + th.board] = [th.board, 'image/svg+xml'];
  const art = `theme-${th.key}-art.js`;
  if (fs.existsSync(path.join(ROOT, art))) FILES['/' + art] = [art, 'text/javascript; charset=utf-8'];
}

/* ---- 桌子與連線 ---- */
const NTABLES = 4, NSEATS = 4;
const GRACE_MS = +process.env.SANGUO_GRACE_MS || 90000;   // 斷線超過這段時間，座位改由電腦接手（或釋出）
const newTable = id => ({ id, seats: Array.from({ length: NSEATS }, () => ({ state: 'open' })), host: null, speed: 450, theme: 'sanguo', started: false, game: null });
const tables = Array.from({ length: NTABLES }, (_, id) => newTable(id));
const clients = new Set();   // { res, token, table: 桌號或 null }
// table.game：{ seatOf: 座位→引擎玩家 id, pending: Map, logs, over, views, worker, waiters }

const find = token => {   // 這個座位代碼坐在哪一桌哪一個座位
  if (!token) return null;
  for (const t of tables) { const k = t.seats.findIndex(s => s.token === token); if (k >= 0) return { t, k }; }
  return null;
};
const online = token => [...clients].some(c => c.token === token);
function send(c, msg) { try { c.res.write(`data: ${JSON.stringify(msg)}\n\n`); } catch (e) { /* 連線已斷 */ } }
const sendTable = (t, msg) => clients.forEach(c => { if (c.table === t.id) send(c, msg); });
const sendPid = (t, pid, msg) => clients.forEach(c => {
  const me = c.table === t.id && find(c.token);
  if (me && me.t === t && t.game && t.game.seatOf[me.k] === pid) send(c, msg);
});

function lobbyFor(t, token) {
  const me = find(token), mine = me && me.t === t ? me.k : -1;
  return {
    type: 'lobby', table: t.id,
    lobby: { started: t.started, speed: t.speed, theme: t.theme,
      seats: t.seats.map((s, k) => ({ state: s.state, cmd: s.cmd, mine: k === mine, host: !!s.token && s.token === t.host, online: s.state !== 'human' || online(s.token) })) },
    you: { seat: mine >= 0 ? mine : null, host: mine >= 0 && token === t.host },
  };
}
const summary = t => ({ id: t.id, started: t.started, over: !!(t.game && t.game.over), theme: t.theme,
  seats: t.seats.map(s => ({ state: s.state, cmd: s.cmd, online: s.state !== 'human' || online(s.token) })) });
const tablesFor = token => { const me = find(token); return { type: 'tables', tables: tables.map(summary), you: me ? { table: me.t.id, seat: me.k } : null }; };
function broadcastLobby(t) {
  if (t) clients.forEach(c => { if (c.table === t.id) send(c, lobbyFor(t, c.token)); });
  clients.forEach(c => send(c, tablesFor(c.token)));
}
const broadcastAll = () => { tables.forEach(t => clients.forEach(c => { if (c.table === t.id) send(c, lobbyFor(t, c.token)); })); clients.forEach(c => send(c, tablesFor(c.token))); };

// 這位用戶在這一桌看到的局面：自己的視角（真人）或旁觀視角
function viewFor(t, token) {
  const g = t.game;
  if (!g || !g.views) return null;
  const me = find(token), pid = me && me.t === t ? g.seatOf[me.k] : undefined;
  return (pid != null && g.views.byPid[pid]) || g.views.all;
}

/* ---- 牌局（每桌一個 worker） ---- */
function startGame(t) {
  const seated = t.seats.map((s, k) => ({ s, k })).filter(x => x.s.state !== 'open');
  const g = t.game = { seatOf: {}, pending: new Map(), logs: [], over: null, views: null, worker: null, waiters: new Map() };
  seated.forEach((x, pid) => { g.seatOf[x.k] = pid; });
  t.started = true;
  const worker = g.worker = new Worker(path.join(__dirname, 'game_worker.js'), {
    workerData: {
      seats: seated.map(x => ({ ai: x.s.state === 'ai', cmd: x.s.cmd })),
      humanPids: seated.map((x, pid) => (x.s.state === 'human' ? pid : -1)).filter(pid => pid >= 0),
      opts: { aiDelay: t.speed, ...E.PACE[t.speed], theme: t.theme },
    },
    resourceLimits: { maxOldGenerationSizeMb: 128 },
  });
  worker.on('message', m => onWorker(t, g, m));
  worker.on('error', err => crashed(t, g, err));
  worker.on('exit', () => { if (g.worker === worker) g.worker = null; });
  broadcastLobby(t);
}
function onWorker(t, g, m) {
  if (t.game !== g) return;   // 這一局已經結束或換桌
  switch (m.t) {
    case 'views':
      g.views = m;
      clients.forEach(c => { if (c.table === t.id) { const v = viewFor(t, c.token); if (v) send(c, { type: 'view', view: v }); } });
      break;
    case 'log': g.logs.push(m.html); if (g.logs.length > 400) g.logs.shift(); sendTable(t, { type: 'log', html: m.html, meta: m.meta }); break;
    case 'dice': sendTable(t, { type: 'dice', r: m.r }); break;
    case 'flash': sendTable(t, { type: 'flash', k: m.k }); break;
    case 'ask': case 'turn': g.pending.set(m.id, { id: m.id, pid: m.pid, msg: m.msg }); sendPid(t, m.pid, m.msg); break;
    case 'resolved': g.pending.delete(m.id); break;
    case 'answered': { const w = g.waiters.get(m.rid); if (w) { g.waiters.delete(m.rid); w(m); } break; }
    case 'over':
      g.over = { type: 'over', title: m.title, html: m.html };
      g.pending.clear();
      sendTable(t, g.over);
      setImmediate(() => { if (g.worker) g.worker.terminate(); });
      broadcastLobby(null);
      break;
    case 'crash': crashed(t, g, new Error(m.message)); break;
  }
}
function crashed(t, g, err) {
  if (t.game !== g || g.over) return;
  console.error(`第 ${t.id + 1} 桌的牌局發生錯誤：`, err);
  g.over = { type: 'over', title: '遊戲中止', html: '<p>伺服器發生錯誤，本局中止。</p>' };
  g.pending.clear();
  sendTable(t, g.over);
  if (g.worker) g.worker.terminate();
  broadcastLobby(null);
}
function stopGame(t) { if (t.game && t.game.worker) t.game.worker.terminate(); }

// 桌子恢復成全空、等待新玩家的狀態
function emptyTable(t) {
  stopGame(t);
  Object.assign(t, newTable(t.id));
  sendTable(t, { type: 'reset' });
  broadcastLobby(t);
}
const ensureHost = t => {
  if (t.host && t.seats.some(s => s.token === t.host)) return;
  const h = t.seats.find(s => s.state === 'human');
  t.host = h ? h.token : null;
};

// 離座：開局前就是空出座位；牌局中該座位改由電腦接手；真人全部離開時整桌重置
function leave(token) {
  const me = find(token);
  if (!me) return false;
  const { t, k } = me, s = t.seats[k];
  if (t.started && t.game && !t.game.over) {
    const pid = t.game.seatOf[k];
    t.seats[k] = { state: 'ai', cmd: s.cmd };
    for (const [id, q] of t.game.pending) if (q.pid === pid) t.game.pending.delete(id);
    if (t.game.worker) t.game.worker.postMessage({ t: 'standup', pid });
  } else {
    t.seats[k] = { state: 'open' };
  }
  ensureHost(t);
  if (!t.seats.some(x => x.state === 'human')) emptyTable(t); else broadcastLobby(t);
  return true;
}

/* ---- HTTP ---- */
function readJson(req) {
  return new Promise((resolve, reject) => {
    let n = 0; const chunks = [];
    req.on('data', d => { n += d.length; if (n > 64 * 1024) { reject(new Error('too large')); req.destroy(); } else chunks.push(d); });
    req.on('end', () => { try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}')); } catch (e) { reject(e); } });
  });
}
function json(res, code, obj) { res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }); res.end(JSON.stringify(obj)); }
const freeCmd = t => [0, 1, 2, 3].filter(c => !t.seats.some(s => s.state !== 'open' && s.cmd === c));

async function handleApi(req, res, url) {
  if (req.method === 'GET' && url.pathname === '/api/events') {
    const token = url.searchParams.get('token') || '';
    const me = find(token);
    const tp = url.searchParams.get('table') || '';
    let table = /^[0-9]+$/.test(tp) && +tp < NTABLES ? +tp : null;   // table=none：只看桌位列表
    if (me) table = me.t.id;                                          // 已入座者一律綁在自己的桌子上，才收得到自己的題目
    res.writeHead(200, { 'Content-Type': 'text/event-stream; charset=utf-8', 'Cache-Control': 'no-store', Connection: 'keep-alive' });
    const c = { res, token: me ? token : '', table };
    clients.add(c);
    send(c, tablesFor(c.token));
    if (table != null) {
      const t = tables[table];
      send(c, lobbyFor(t, c.token));
      const g = t.game;
      if (g) {
        g.logs.forEach(html => send(c, { type: 'log', html }));
        const v = viewFor(t, c.token);
        if (v) send(c, { type: 'view', view: v });
        const m = find(c.token), pid = m && m.t === t ? g.seatOf[m.k] : undefined;
        if (pid != null) for (const q of g.pending.values()) if (q.pid === pid) send(c, q.msg);   // 重新連線時補送未答的題目
        if (g.over) send(c, g.over);
      }
    }
    broadcastAll();
    const ping = setInterval(() => res.write(': ping\n\n'), 25000);
    req.on('close', () => {
      clearInterval(ping); clients.delete(c);
      if (c.token && find(c.token)) {   // 斷線太久就視為離座
        const timer = setTimeout(() => { if (find(c.token) && !online(c.token)) leave(c.token); }, GRACE_MS);
        if (timer.unref) timer.unref();
      }
      broadcastAll();
    });
    return;
  }
  if (req.method !== 'POST') return json(res, 405, { error: 'method' });
  let body;
  try { body = await readJson(req); } catch { return json(res, 400, { error: '格式錯誤' }); }
  const token = typeof body.token === 'string' ? body.token : '';
  const me = find(token);

  if (url.pathname === '/api/join') {
    const t = Number.isInteger(body.table) ? tables[body.table] : null, k = body.seat, cmd = body.cmd;
    if (!t) return json(res, 400, { error: '桌號錯誤' });
    if (t.started) return json(res, 409, { error: '遊戲已經開始' });
    if (me) return json(res, 409, { error: '你已經有座位了' });
    if (!Number.isInteger(k) || !t.seats[k] || t.seats[k].state !== 'open') return json(res, 409, { error: '這個座位已有人' });
    if (!freeCmd(t).includes(cmd)) return json(res, 409, { error: '這位主帥已被選走' });
    const tk = crypto.randomBytes(16).toString('hex');
    t.seats[k] = { state: 'human', cmd, token: tk };
    if (!t.host || !t.seats.some(s => s.token === t.host)) t.host = tk;
    broadcastLobby(t);
    return json(res, 200, { token: tk, table: t.id });
  }

  if (url.pathname === '/api/leave') {
    leave(token);
    return json(res, 200, { ok: true });
  }

  if (url.pathname === '/api/lobby') {
    if (!me) return json(res, 403, { error: '請先入座' });
    const t = me.t, isHost = token === t.host, op = body.op;
    if (op === 'reset') {
      // 遊戲結束後任何已入座的玩家都可回到大廳（避免房主離開後卡住）
      if (!(t.game && t.game.over)) return json(res, 403, { error: '遊戲結束後才能開新局' });
      stopGame(t);
      t.game = null; t.started = false;
      ensureHost(t);
      sendTable(t, { type: 'reset' });
      if (!t.seats.some(s => s.state === 'human')) emptyTable(t); else broadcastLobby(t);
      return json(res, 200, { ok: true });
    }
    if (t.started) return json(res, 409, { error: '遊戲已經開始' });
    const k = body.seat;
    if (op === 'open') {   // 房主移除電腦座位
      const s = t.seats[k];
      if (!isHost || !s || s.state !== 'ai') return json(res, 403, { error: '無權變更此座位' });
      t.seats[k] = { state: 'open' };
    } else if (op === 'ai') {
      if (!isHost) return json(res, 403, { error: '只有房主可設定電腦' });
      if (!t.seats[k] || t.seats[k].state !== 'open') return json(res, 409, { error: '座位不是空的' });
      if (!freeCmd(t).includes(body.cmd)) return json(res, 409, { error: '沒有可用的主帥' });
      t.seats[k] = { state: 'ai', cmd: body.cmd };
    } else if (op === 'fillai') {   // 空位全部由電腦補上
      if (!isHost) return json(res, 403, { error: '只有房主可設定電腦' });
      t.seats.forEach((s, j) => { if (s.state === 'open') { const c = freeCmd(t)[0]; if (c != null) t.seats[j] = { state: 'ai', cmd: c }; } });
    } else if (op === 'theme') {
      if (!isHost) return json(res, 403, { error: '只有房主可選擇主題' });
      if (!Object.hasOwn(E.THEMES, body.theme)) return json(res, 400, { error: '未知的主題' });
      t.theme = body.theme;
    } else if (op === 'start') {
      if (!isHost) return json(res, 403, { error: '只有房主可開始遊戲' });
      if (t.seats.filter(s => s.state !== 'open').length < 2) return json(res, 409, { error: '至少需要 2 位（可把空位設為電腦）' });
      t.speed = [120, 450, 900].includes(+body.speed) ? +body.speed : 450;
      if (Object.hasOwn(E.THEMES, body.theme)) t.theme = body.theme;
      startGame(t);
      return json(res, 200, { ok: true });
    } else return json(res, 400, { error: '未知的操作' });
    broadcastLobby(t);
    return json(res, 200, { ok: true });
  }

  if (url.pathname === '/api/answer') {
    const g = me && me.t.game;
    const pid = g ? g.seatOf[me.k] : undefined;
    const q = g && g.pending.get(body.id);
    if (!g || g.over || pid == null || !q || q.pid !== pid || !g.worker) return json(res, 403, { error: '這題不是給你的' });
    const rid = crypto.randomUUID();
    const result = await new Promise(resolve => {
      g.waiters.set(rid, resolve);
      setTimeout(() => { if (g.waiters.delete(rid)) resolve({ ok: false, error: '逾時' }); }, 10000);
      g.worker.postMessage({ t: 'answer', id: body.id, btn: body.btn, inputs: body.inputs, rid });
    });
    if (result.errors) return json(res, 200, { errors: result.errors });
    return json(res, result.ok ? 200 : 400, result.ok ? { ok: true } : { error: result.error || '失敗' });
  }
  return json(res, 404, { error: 'not found' });
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');
  if (url.pathname.startsWith('/api/')) {
    handleApi(req, res, url).catch(err => { console.error(err); if (!res.headersSent) json(res, 500, { error: 'server' }); });
    return;
  }
  const f = FILES[url.pathname];
  if (!f || req.method !== 'GET') { res.writeHead(404); res.end('not found'); return; }
  fs.readFile(path.join(ROOT, f[0]), (err, data) => {
    if (err) { res.writeHead(500); res.end(); return; }
    res.writeHead(200, { 'Content-Type': f[1], 'Cache-Control': 'no-cache' });
    res.end(data);
  });
});
server.listen(PORT, HOST, () => console.log(`三國風雲連線伺服器：http://${HOST === '::1' ? '[::1]' : HOST}:${PORT}/（只限本機，${NTABLES} 桌）`));
const shutdown = () => { tables.forEach(stopGame); process.exit(0); };
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
