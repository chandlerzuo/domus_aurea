'use strict';
/* 繪圖小工具：字型、圓角矩形、中文斷行 */

// 字級（邏輯像素）：本文不小於 16，次要說明不小於 13（參考 Apple HIG 17pt 本文、微信設計規範 17/15/14pt）
const SIZE = { title: 20, body: 16, small: 14, tiny: 13, button: 17 };
const COLOR = {
  bg: '#3b2618', paper: '#fbf3dc', ink: '#2a1a10', sub: '#6b4f2a', line: '#d9c49a',
  pri: '#b03a2e', priInk: '#fff', btn: '#efe2c2', btnInk: '#2a1a10', disabled: '#cfc6b4', err: '#c0392b',
  dim: 'rgba(20,10,4,.55)', gold: '#f2c200',
};

const font = (size, weight = 400) => `${weight >= 700 ? 'bold ' : ''}${size}px sans-serif`;

function rrect(ctx, x, y, w, h, r) {
  r = Math.max(0, Math.min(r, w / 2, h / 2));
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}
function fillR(ctx, x, y, w, h, r, fill, stroke, lw = 1) {
  rrect(ctx, x, y, w, h, r);
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw; ctx.stroke(); }
}

/* ---- 斷行 ---- */
// 不可放在行首的標點、不可放在行尾的標點
const NO_START = new Set('，。、；：？！）」』】》〉…—,.;:?!)]%');
const NO_END = new Set('（「『【《〈([');
// 把文字切成「不可再分」的單位：連續的英數字為一個單位，其餘每個字一個單位
function tokens(s) {
  const out = [];
  const re = /[A-Za-z0-9.,%+\-×]+|\s+|./gu;
  let m;
  while ((m = re.exec(s))) out.push(m[0]);
  return out;
}
/* 把一連串文字段落斷成多行。
 * runs: [{ text, font, color }]，maxW：行寬。回傳 [{ w, parts: [{ text, font, color, x, w }] }] */
function breakRuns(ctx, runs, maxW) {
  const lines = [];
  let line = { w: 0, parts: [] };
  const push = () => { lines.push(line); line = { w: 0, parts: [] }; };
  for (const r of runs) {
    ctx.font = r.font;
    if (r.text === '\n') { push(); continue; }
    for (const tk of tokens(r.text)) {
      const w = ctx.measureText(tk).width;
      const ws = /^\s+$/.test(tk);
      if (line.w + w > maxW && line.parts.length && !ws) {
        // 標點不放行首：把標點留在上一行（允許稍微超出）
        if (!(tk.length === 1 && NO_START.has(tk))) {
          // 上一個字若是開括號，連同它一起換行
          const last = line.parts[line.parts.length - 1];
          let carry = null;
          if (last && last.text.length === 1 && NO_END.has(last.text) && line.parts.length > 1) { carry = line.parts.pop(); line.w -= carry.w; }
          push();
          if (carry) { carry.x = 0; line.parts.push(carry); line.w = carry.w; }
        }
      }
      if (ws && !line.parts.length) continue; // 行首空白不畫
      const prev = line.parts[line.parts.length - 1];
      if (prev && prev.font === r.font && prev.color === r.color && !prev.atom) { prev.text += tk; prev.w += w; }
      else line.parts.push({ text: tk, font: r.font, color: r.color, x: line.w, w });
      line.w += w;
    }
  }
  if (line.parts.length || !lines.length) push();
  return lines;
}
// 單一字型的簡單斷行
function wrapText(ctx, text, f, maxW) {
  return breakRuns(ctx, [{ text, font: f, color: '' }], maxW).map(l => l.parts.map(p => p.text).join(''));
}
// 文字縮到放得進寬度（加省略號）
function ellipsize(ctx, text, f, maxW) {
  ctx.font = f;
  if (ctx.measureText(text).width <= maxW) return text;
  let s = text;
  while (s.length > 1 && ctx.measureText(s + '…').width > maxW) s = s.slice(0, -1);
  return s + '…';
}

module.exports = { SIZE, COLOR, font, rrect, fillR, breakRuns, wrapText, ellipsize };
