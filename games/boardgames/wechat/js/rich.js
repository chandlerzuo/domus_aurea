'use strict';
/* 引擎對話框內容（少量 HTML）→ 畫布排版
 * 支援引擎與本程式用到的標籤：p div span b i small label input br ul ol li h4 table tr td
 * 以及 class：cards copt opt mini cw err slip hd vs cmdbadge
 * 表單欄位（單選、複選、數字）以可點按的元件呈現，作答時交給 server/form.js 的 makeForm 讀取。 */
const { SIZE, COLOR, font, fillR } = require('./gfx.js');

/* ---------------- 解析 ---------------- */
const VOID = new Set(['input', 'br', 'img', 'hr']);
const ENT = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', '#39': "'" };
const decode = s => s.replace(/&(#?\w+);/g, (m, k) => ENT[k] ?? (k[0] === '#' ? String.fromCodePoint(+k.slice(1)) : m));
function parseAttrs(s) {
  const a = {};
  const re = /([\w-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g;
  let m;
  while ((m = re.exec(s))) a[m[1].toLowerCase()] = decode(m[2] ?? m[3] ?? m[4] ?? '');
  return a;
}
function parse(html) {
  const root = { tag: 'root', attrs: {}, cls: new Set(), kids: [] };
  const stack = [root];
  const re = /<!--[\s\S]*?-->|<\/([\w]+)\s*>|<([\w]+)((?:[^>"']|"[^"]*"|'[^']*')*)>|([^<]+)/g;
  let m;
  while ((m = re.exec(String(html)))) {
    const top = stack[stack.length - 1];
    if (m[4] != null) { top.kids.push({ text: decode(m[4]) }); continue; }
    if (m[1]) { // 結束標籤
      const t = m[1].toLowerCase();
      for (let k = stack.length - 1; k > 0; k--) if (stack[k].tag === t) { stack.length = k; break; }
      continue;
    }
    if (!m[2]) continue;
    const tag = m[2].toLowerCase(), attrs = parseAttrs(m[3] || '');
    const node = { tag, attrs, cls: new Set((attrs.class || '').split(/\s+/).filter(Boolean)), style: parseStyle(attrs.style || ''), kids: [] };
    top.kids.push(node);
    if (!VOID.has(tag) && !/\/\s*$/.test(m[3] || '')) stack.push(node);
  }
  return root;
}
function parseStyle(s) {
  const o = {};
  s.split(';').forEach(d => { const k = d.indexOf(':'); if (k > 0) o[d.slice(0, k).trim()] = d.slice(k + 1).trim(); });
  return o;
}
// 純文字（記錄訊息等）
function plainText(html) {
  const out = [];
  (function walk(n) { if (n.text != null) out.push(n.text); else if (n.tag === 'br') out.push(' '); else n.kids.forEach(walk); })(parse(html));
  return out.join('').replace(/\s+/g, ' ').trim();
}

/* ---------------- 表單 ---------------- */
// 為每個 input 建立狀態物件；回傳 inputs 陣列（格式同 form.js）
function collectInputs(root) {
  const inputs = [];
  (function walk(n) {
    if (n.tag === 'input') {
      const a = n.attrs, type = (a.type || 'text').toLowerCase();
      n.state = { id: a.id, name: a.name, type, value: a.value ?? (type === 'checkbox' ? 'on' : ''), checked: 'checked' in a, k: a['data-k'],
        min: a.min != null ? +a.min : null, max: a.max != null ? +a.max : null, step: a.step != null ? +a.step : 1 };
      inputs.push(n.state);
    }
    (n.kids || []).forEach(walk);
  })(root);
  return inputs;
}
function setRadio(inputs, st) { inputs.forEach(i => { if (i.type === 'radio' && i.name === st.name) i.checked = i === st; }); }
const firstInput = n => { if (n.tag === 'input') return n; for (const k of n.kids || []) { const f = firstInput(k); if (f) return f; } return null; };
const findCard = n => { if (n.cls && n.cls.has('cw')) return n; for (const k of n.kids || []) { const f = findCard(k); if (f) return f; } return null; };

/* ---------------- 排版 ---------------- */
const CARD_RATIO = 350 / 250;
const LINE = 1.5;

/* layout(root, width, ctx, env) → { h, ops, hits }
 * env: { inputs, errors, cardW, onChange(), onCard(id) } */
function layout(root, width, ctx, env) {
  const ops = [], hits = [];
  const cardW = env.cardW || 72;
  let y = 0;

  // ---- 行內排版 ----
  // items: { text, font, color, size } 或 { atom: { w, h, draw(x, y), tap } }
  function inline(items, x0, w0, align) {
    if (!items.length) return;
    const lines = [];
    let line = { w: 0, h: 0, parts: [] };
    const newLine = () => { lines.push(line); line = { w: 0, h: 0, parts: [] }; };
    for (const it of items) {
      if (it.br) { if (!line.parts.length) line.h = it.size * LINE; newLine(); continue; }
      if (it.atom) {
        if (line.w + it.atom.w > w0 && line.parts.length) newLine();
        line.parts.push({ atom: it.atom, x: line.w, w: it.atom.w });
        line.w += it.atom.w + 4; line.h = Math.max(line.h, it.atom.h + 4);
        continue;
      }
      ctx.font = it.font;
      const re = /[A-Za-z0-9.,%+\-×:]+|\s+|./gu;
      let m;
      while ((m = re.exec(it.text))) {
        const tk = m[0], tw = ctx.measureText(tk).width, ws = /^\s+$/.test(tk);
        // 行尾保留一個字寬給不能放在行首的標點，避免標點超出邊界
        const punct = tk.length === 1 && '，。、；：？！）」』…,.;:?!)'.includes(tk);
        if (line.parts.length && !ws && line.w + tw > (punct ? w0 : w0 - it.size)) newLine();
        if (ws && !line.parts.length) continue;
        const prev = line.parts[line.parts.length - 1];
        if (prev && !prev.atom && prev.font === it.font && prev.color === it.color) { prev.text += tk; prev.w += tw; }
        else line.parts.push({ text: tk, font: it.font, color: it.color, x: line.w, w: tw, size: it.size });
        line.w += tw; line.h = Math.max(line.h, it.size * LINE);
      }
    }
    if (line.parts.length) newLine();
    for (const ln of lines) {
      const dx = align === 'center' ? Math.max(0, (w0 - ln.w) / 2) : 0;
      for (const p of ln.parts) {
        if (p.atom) {
          const ax = x0 + dx + p.x, ay = y + (ln.h - p.atom.h) / 2;
          ops.push({ draw: p.atom.draw, x: ax, y: ay });
          if (p.atom.tap) hits.push({ x: ax, y: ay, w: p.atom.w, h: p.atom.h, tap: p.atom.tap });
          if (p.atom.tapsAt) hits.push(...p.atom.tapsAt(ax, ay));
        } else ops.push({ text: p.text, font: p.font, color: p.color, x: x0 + dx + p.x, y: y + ln.h / 2 });
      }
      y += ln.h;
    }
  }

  // 樣式繼承
  function styleOf(n, st) {
    const s = { ...st };
    if (n.tag === 'b' || n.tag === 'h4' || (n.cls && n.cls.has('hd'))) s.bold = true;
    if (n.tag === 'small') { s.size = Math.min(s.size, SIZE.small); s.color = COLOR.sub; }
    if (n.tag === 'h4') s.size = SIZE.body + 1;
    if (n.cls && n.cls.has('err')) s.color = COLOR.err;
    if (n.cls && n.cls.has('cmdbadge')) { s.color = '#a8740a'; s.bold = true; s.size = SIZE.tiny; }
    if (n.style) {
      if (n.style.color) s.color = n.style.color;
      if (n.style['font-size']) s.size = Math.max(SIZE.small, Math.min(30, parseFloat(n.style['font-size'])));
    }
    return s;
  }
  const fontOf = s => font(s.size, s.bold ? 700 : 400);

  // 牌圖元件
  const cardAtom = (id, w, tap) => ({ w, h: Math.round(w * CARD_RATIO), draw: (c, x, yy) => env.drawCard(c, id, x, yy, w), tap });
  // 數字欄位元件：［最少］［−］ 數值 ［＋］［最多］
  function stepperAtom(st, avail) {
    const bw = 44, vw = 84, h = 44, w = Math.min(avail, bw * 4 + vw + 8);
    const step = st.step || 1, lo = st.min ?? 0, hi = st.max ?? 1e9;
    const set = v => { st.value = String(Math.max(lo, Math.min(hi, v))); env.onChange(); };
    const val = () => +st.value || 0;
    const btns = [['最少', () => set(lo)], ['−', () => set(val() - step)], null, ['＋', () => set(val() + step)], ['最多', () => set(hi)]];
    return {
      w, h,
      draw: (c, x, yy) => {
        let bx = x;
        btns.forEach(b => {
          if (!b) { fillR(c, bx, yy, vw, h, 8, '#fff', COLOR.line, 1.5); c.fillStyle = COLOR.ink; c.font = font(18, 700); c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(st.value, bx + vw / 2, yy + h / 2); c.textAlign = 'left'; bx += vw + 2; return; }
          fillR(c, bx, yy, bw, h, 8, COLOR.btn, COLOR.line, 1.5);
          c.fillStyle = COLOR.btnInk; c.font = font(b[0].length > 1 ? SIZE.tiny : 22, 700); c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(b[0], bx + bw / 2, yy + h / 2 + 1); c.textAlign = 'left';
          bx += bw + 2;
        });
      },
      taps: (x, yy) => {
        let bx = x; const out = [];
        btns.forEach(b => { if (!b) { bx += vw + 2; return; } out.push({ x: bx, y: yy, w: bw, h, tap: b[1] }); bx += bw + 2; });
        return out;
      },
    };
  }
  // 單選／複選指示器
  const indicator = (st, size = 24) => (c, x, yy) => {
    if (st.type === 'radio') {
      c.beginPath(); c.arc(x + size / 2, yy + size / 2, size / 2 - 1, 0, Math.PI * 2); c.fillStyle = '#fff'; c.fill(); c.lineWidth = 2; c.strokeStyle = st.checked ? COLOR.pri : '#9a8a6a'; c.stroke();
      if (st.checked) { c.beginPath(); c.arc(x + size / 2, yy + size / 2, size / 2 - 6, 0, Math.PI * 2); c.fillStyle = COLOR.pri; c.fill(); }
    } else {
      fillR(c, x + 1, yy + 1, size - 2, size - 2, 5, st.checked ? COLOR.pri : '#fff', st.checked ? COLOR.pri : '#9a8a6a', 2);
      if (st.checked) { c.beginPath(); c.moveTo(x + 6, yy + size / 2); c.lineTo(x + size / 2 - 1, yy + size - 7); c.lineTo(x + size - 5, yy + 6); c.lineWidth = 3; c.strokeStyle = '#fff'; c.stroke(); }
    }
  };
  const toggle = st => { if (st.type === 'radio') setRadio(env.inputs, st); else st.checked = !st.checked; env.onChange(); };

  // 收集行內內容
  function collect(n, st, items, x0, w0) {
    if (n.text != null) { items.push({ text: n.text, font: fontOf(st), color: st.color, size: st.size }); return; }
    if (n.tag === 'br') { items.push({ br: true, size: st.size }); return; }
    if (n.cls.has('cw')) {
      const id = +n.attrs['data-cid'], cls = n.attrs['data-cls'] || '';
      const w = cls === 'mini' ? 30 : cls === 'big' ? Math.min(240, w0) : cardW;
      items.push({ atom: cardAtom(id, w, () => env.onCard(id)) });
      return;
    }
    if (n.tag === 'input') {
      const s = n.state;
      if (s.type === 'number' || s.type === 'text') {
        const a = stepperAtom(s, w0);
        items.push({ atom: { w: a.w, h: a.h, draw: a.draw, tapsAt: a.taps } });
      } else items.push({ atom: { w: 26, h: 26, draw: indicator(s), tap: () => toggle(s) } });
      return;
    }
    const s2 = styleOf(n, st);
    n.kids.forEach(k => collect(k, s2, items, x0, w0));
  }

  const BLOCK = new Set(['p', 'div', 'label', 'ul', 'ol', 'li', 'h4', 'table', 'tr', 'fieldset']);
  const isBlock = n => n.tag && BLOCK.has(n.tag);
  const errText = n => n.attrs && n.attrs.id && env.errors[n.attrs.id];

  // 卡片格（.cards）：子項目為 label.copt、div.copt 或牌
  function cardsBlock(n, x0, w0, st) {
    const gap = 8, cw = cardW, ch = Math.round(cw * CARD_RATIO);
    const tiles = n.kids.filter(k => k.tag || (k.text && k.text.trim()));
    const per = Math.max(1, Math.floor((w0 + gap) / (cw + gap)));
    const center = n.style && n.style['justify-content'] === 'center';
    let col = 0, rowH = 0, rowStart = y;
    const rows = Math.ceil(tiles.length / per);
    tiles.forEach((t, k) => {
      const inRow = Math.min(per, tiles.length - Math.floor(k / per) * per);
      const left = center || rows === 1 ? x0 + (w0 - (inRow * cw + (inRow - 1) * gap)) / 2 : x0;
      const tx = left + col * (cw + gap), ty = rowStart;
      const card = findCard(t), inp = firstInput(t);
      const st2 = inp && inp.state;
      // 牌以外的文字（例如「★主帥」）放在牌下方
      const extra = [];
      const walk = m => { if (m === card || m === inp) return; if (m.text != null) { if (m.text.trim()) extra.push(m.text.trim()); } else (m.kids || []).forEach(walk); };
      walk(t);
      const capH = extra.length ? 20 : 0;
      const sel = st2 && st2.checked;
      if (card) {
        const id = +card.attrs['data-cid'];
        ops.push({ draw: (c, x, yy) => {
          if (sel) fillR(c, x - 4, yy - 4, cw + 8, ch + 8 + capH, 9, 'rgba(176,58,46,.15)', COLOR.pri, 3);
          env.drawCard(c, id, x, yy, cw);
          if (capH) { c.font = font(SIZE.tiny, 700); c.fillStyle = '#a8740a'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(extra.join(' '), x + cw / 2, yy + ch + 11); c.textAlign = 'left'; }
          if (st2) indicator(st2, 22)(c, x + cw - 24, yy + 2);
        }, x: tx, y: ty });
        hits.push({ x: tx - 4, y: ty - 4, w: cw + 8, h: ch + 8 + capH, tap: st2 ? () => toggle(st2) : () => env.onCard(id), hold: () => env.onCard(id) });
      }
      rowH = Math.max(rowH, ch + capH + (st2 ? 8 : 0));
      col++;
      if (col >= per) { col = 0; rowStart += rowH + gap; rowH = 0; }
    });
    y = rowStart + (col ? rowH : -gap) + 4;
  }

  function blockKids(kids, x0, w0, st, align) {
    let items = [];
    const flush = () => { inline(items, x0, w0, align); items = []; };
    for (const k of kids) {
      if (k.text != null && !k.text.trim() && !items.length) continue;
      if (isBlock(k)) { flush(); block(k, x0, w0, st); }
      else collect(k, st, items, x0, w0);
    }
    flush();
  }

  function block(n, x0, w0, st) {
    const s = styleOf(n, st);
    if (errText(n)) { const y0 = y; inline([{ text: errText(n), font: fontOf({ ...s, bold: true }), color: COLOR.err, size: s.size }], x0, w0); if (y === y0) y += 4; return; }
    const c = n.cls;
    if (n.tag === 'p' || n.tag === 'h4') { y += 2; blockKids(n.kids, x0, w0, s); y += 8; return; }
    if (n.tag === 'ul' || n.tag === 'ol') {
      let k = 0;
      for (const li of n.kids.filter(m => m.tag === 'li')) {
        k++;
        const by = y;
        ops.push({ text: n.tag === 'ol' ? `${k}.` : '•', font: font(s.size, 700), color: COLOR.sub, x: x0, y: by + s.size * LINE / 2 });
        blockKids(li.kids, x0 + 22, w0 - 22, s);
        y += 6;
      }
      return;
    }
    if (n.tag === 'table') { for (const tr of n.kids.filter(m => m.tag === 'tr')) block(tr, x0, w0, s); y += 6; return; }
    if (n.tag === 'tr') {
      const tds = n.kids.filter(m => m.tag === 'td' || m.tag === 'th');
      const y0 = y, cw0 = Math.round(w0 * 0.42);
      blockKids(tds[0] ? tds[0].kids : [], x0, cw0 - 8, { ...s, color: COLOR.sub });
      const y1 = y; y = y0;
      blockKids(tds[1] ? tds[1].kids : [], x0 + cw0, w0 - cw0, { ...s, bold: true });
      y = Math.max(y, y1) + 2;
      ops.push({ draw: (cx, x, yy) => { cx.fillStyle = COLOR.line; cx.fillRect(x, yy, w0, 1); }, x: x0, y: y }); y += 3;
      return;
    }
    if (c.has('cards')) { cardsBlock(n, x0, w0, s); return; }
    if (n.tag === 'label' && c.has('opt')) {
      const inp = firstInput(n); const st2 = inp && inp.state;
      const y0 = y, pad = 10;
      const opIdx = ops.length;
      y += pad;
      blockKids(n.kids.filter(k => k !== inp), x0 + 40, w0 - 48, s);
      y += pad;
      const h = Math.max(46, y - y0); y = y0 + h;
      ops.splice(opIdx, 0, { draw: (cx, x, yy) => {
        fillR(cx, x, yy, w0, h, 10, st2 && st2.checked ? '#f6e3d8' : '#fff', st2 && st2.checked ? COLOR.pri : COLOR.line, st2 && st2.checked ? 2 : 1);
        if (st2) indicator(st2)(cx, x + 9, yy + h / 2 - 12);
      }, x: x0, y: y0 });
      if (st2) hits.push({ x: x0, y: y0, w: w0, h, tap: () => toggle(st2) });
      y += 6;
      return;
    }
    if (c.has('slip')) {
      const y0 = y, pad = 12, idx = ops.length;
      y += pad;
      for (const k of n.kids) {
        if (k.cls && k.cls.has('hd')) {
          const txt = collectText(k).trim();
          ops.push({ draw: (cx, x, yy) => {
            cx.font = font(SIZE.title, 700); const tw = cx.measureText(txt).width;
            fillR(cx, x, yy, tw + 28, 34, 17, '#fff', '#333', 2);
            cx.fillStyle = COLOR.ink; cx.textBaseline = 'middle'; cx.fillText(txt, x + 14, yy + 17);
          }, x: x0 + pad, y });
          y += 42;
        } else if (k.tag) block(k, x0 + pad, w0 - pad * 2, { ...s, size: SIZE.body + 1 });
      }
      y += pad;
      const h = y - y0;
      ops.splice(idx, 0, { draw: (cx, x, yy) => fillR(cx, x, yy, w0, h, 10, '#d3d0c8', '#8d8a82', 2), x: x0, y: y0 });
      y += 6;
      return;
    }
    if (c.has('vs')) {
      const cols = n.kids.filter(k => k.tag);
      const gap = 8, cw = (w0 - gap * (cols.length - 1)) / cols.length;
      const y0 = y; let yMax = y0;
      cols.forEach((col, k) => {
        y = y0;
        const big = col.style && col.style['font-size'];
        const cx0 = x0 + k * (cw + gap);
        blockKids(col.kids, cx0 + 4, cw - 8, styleOf(col, s), 'center');
        yMax = Math.max(yMax, y);
      });
      y = yMax + 6;
      return;
    }
    blockKids(n.kids, x0, w0, s);
  }
  const collectText = n => n.text != null ? n.text : (n.kids || []).map(collectText).join('');

  blockKids(root.kids, 0, width, { size: SIZE.body, bold: false, color: COLOR.ink });
  return { h: Math.ceil(y), ops, hits };
}

function drawOps(ctx, ops, ox, oy) {
  for (const op of ops) {
    if (op.draw) { op.draw(ctx, ox + op.x, oy + op.y); continue; }
    ctx.font = op.font; ctx.fillStyle = op.color || COLOR.ink; ctx.textBaseline = 'middle'; ctx.textAlign = 'left';
    ctx.fillText(op.text, ox + op.x, oy + op.y);
  }
}

module.exports = { parse, plainText, collectInputs, layout, drawOps };
