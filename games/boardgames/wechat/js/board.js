'use strict';
/* 直式棋盤：版面座標、縮放平移、格子上的印章／城池／旗幟／骰子 */
const { COLOR, font, fillR, rrect } = require('./gfx.js');

// 棋盤掃描圖（2122×3000）上每一格的位置 [x, y, 寬, 高]，順序同引擎 TILES（與 client.js 相同）
const SCAN = { x: 45, y: 255 };
const BW = 1900, BH = 2630; // 直式棋盤大小（棋盤單位）
const BOXES = [[1297,290,610,525],[1690,890,210,142],[1312,840,310,175],[1307,1080,210,140],[1592,1050,310,170],[1690,1285,212,142],
  [1312,1240,310,177],[1307,1480,210,140],[1592,1445,310,177],[1692,1688,208,140],[1690,1895,210,140],[1277,1630,385,420],
  [1309,2088,210,137],[1590,2055,307,170],[1690,2293,207,140],[1307,2243,310,175],[1305,2482,210,140],[1587,2452,308,173],
  [1685,2692,209,140],[1307,2640,307,175],[1097,2623,143,205],[893,2620,142,205],[880,2130,405,490],[680,2253,142,204],
  [700,2520,175,305],[488,2623,139,210],[490,2253,173,310],[275,2253,145,202],[288,2520,177,308],[73,2623,145,205],
  [78,2253,180,310],[75,2047,213,143],[372,1895,393,300],[75,1892,213,140],[75,1687,213,140],[348,1700,320,170],
  [455,1492,213,145],[75,1497,323,170],[75,1290,205,142],[348,1300,320,175],[455,1098,213,142],[75,1095,323,175],
  [75,890,213,140],[75,687,213,140],[320,690,320,350],[457,477,211,143],[75,490,315,175],[75,285,217,142],
  [355,285,313,170],[735,285,141,202],[688,553,175,309],[928,660,138,207],[895,285,171,305],[1137,282,137,206],[1137,557,137,190]]
  .map(([x, y, w, h]) => [x - SCAN.x, y - SCAN.y, w, h]);
const DECK = { emergency: [760, 990, 450, 304], general: [734, 1384, 506, 336], strategy: [764, 1814, 452, 300] };
Object.keys(DECK).forEach(k => { const [x, y, w, h] = DECK[k]; DECK[k] = [x - SCAN.x, y - SCAN.y, w, h]; });
const PIPS = { 1: [[0, 0]], 2: [[-1, -1], [1, 1]], 3: [[-1, -1], [0, 0], [1, 1]], 4: [[-1, -1], [1, -1], [-1, 1], [1, 1]], 5: [[-1, -1], [1, -1], [0, 0], [-1, 1], [1, 1]], 6: [[-1, -1], [1, -1], [-1, 0], [1, 0], [-1, 1], [1, 1]] };

class BoardView {
  constructor(onChange) {
    this.onChange = onChange;    // 需要重畫時呼叫
    this.img = null;
    this.rect = { x: 0, y: 0, w: 1, h: 1 };
    this.s = 1; this.ox = 0; this.oy = 0;
    this.touch = null; this.lastTap = 0;
    this.anim = null;
    this.flashes = {};           // 牌堆閃爍
    this.dice = null;            // 最近一次擲骰結果
  }
  get fitScale() { return Math.min(this.rect.w / BW, this.rect.h / BH); }
  setRect(x, y, w, h) {
    const keep = this.s > this.fitScale * 1.01 && this.rect.w > 1;
    this.rect = { x, y, w, h };
    if (!keep) this.fit();
    else this.clamp();
  }
  fit() {
    this.s = this.fitScale;
    this.ox = this.rect.x + (this.rect.w - BW * this.s) / 2;
    this.oy = this.rect.y + (this.rect.h - BH * this.s) / 2;
  }
  zoomed() { return this.s > this.fitScale * 1.02; }
  clamp() {
    const r = this.rect, w = BW * this.s, h = BH * this.s;
    this.ox = w <= r.w ? r.x + (r.w - w) / 2 : Math.min(r.x, Math.max(r.x + r.w - w, this.ox));
    this.oy = h <= r.h ? r.y + (r.h - h) / 2 : Math.min(r.y, Math.max(r.y + r.h - h, this.oy));
  }
  zoomAt(px, py, s) {
    const lo = this.fitScale, hi = this.fitScale * 3.2;
    s = Math.max(lo, Math.min(hi, s));
    const bx = (px - this.ox) / this.s, by = (py - this.oy) / this.s;
    this.s = s; this.ox = px - bx * s; this.oy = py - by * s;
    this.clamp();
  }
  // 放大時把某一格移到畫面中央（緩動）
  focusTile(i) {
    if (!this.zoomed()) return;
    const [x, y, w, h] = BOXES[i], r = this.rect;
    const tx = r.x + r.w / 2 - (x + w / 2) * this.s, ty = r.y + r.h / 2 - (y + h / 2) * this.s;
    const save = [this.ox, this.oy];
    this.ox = tx; this.oy = ty; this.clamp();
    const to = [this.ox, this.oy];
    [this.ox, this.oy] = save;
    this.anim = { from: save, to, t0: Date.now(), dur: 350 };
    this.onChange();
  }
  step() { // 回傳是否仍在動畫中
    let busy = false;
    if (this.anim) {
      const k = Math.min(1, (Date.now() - this.anim.t0) / this.anim.dur), e = 1 - Math.pow(1 - k, 3);
      this.ox = this.anim.from[0] + (this.anim.to[0] - this.anim.from[0]) * e;
      this.oy = this.anim.from[1] + (this.anim.to[1] - this.anim.from[1]) * e;
      if (k >= 1) this.anim = null; else busy = true;
    }
    const now = Date.now();
    for (const k in this.flashes) { if (now - this.flashes[k] > 900) delete this.flashes[k]; else busy = true; }
    return busy;
  }
  flash(k) { this.flashes[k] = Date.now(); this.onChange(); }
  tileAt(px, py) {
    const bx = (px - this.ox) / this.s, by = (py - this.oy) / this.s;
    for (let i = 0; i < BOXES.length; i++) { const [x, y, w, h] = BOXES[i]; if (bx >= x && bx <= x + w && by >= y && by <= y + h) return i; }
    return -1;
  }
  inside(px, py) { const r = this.rect; return px >= r.x && px <= r.x + r.w && py >= r.y && py <= r.y + r.h; }

  /* ---- 觸控：單指拖曳（放大時）、雙指縮放、點一下看格子、點兩下放大／還原 ---- */
  touchStart(ts) {
    if (ts.length >= 2) {
      const [a, b] = ts;
      this.touch = { pinch: true, d0: Math.hypot(a.x - b.x, a.y - b.y), s0: this.s, moved: true };
    } else this.touch = { x0: ts[0].x, y0: ts[0].y, ox0: this.ox, oy0: this.oy, moved: false, t0: Date.now() };
    this.anim = null;
  }
  touchMove(ts) {
    const t = this.touch; if (!t) return;
    if (t.pinch && ts.length >= 2) {
      const [a, b] = ts, d = Math.hypot(a.x - b.x, a.y - b.y);
      this.zoomAt((a.x + b.x) / 2, (a.y + b.y) / 2, t.s0 * d / Math.max(1, t.d0));
      this.onChange(); return;
    }
    if (t.pinch) return;
    const dx = ts[0].x - t.x0, dy = ts[0].y - t.y0;
    if (Math.hypot(dx, dy) > 8) t.moved = true;
    if (t.moved && this.zoomed()) { this.ox = t.ox0 + dx; this.oy = t.oy0 + dy; this.clamp(); this.onChange(); }
  }
  // 回傳點到的格子編號（沒有點到格子回傳 -1；拖曳、縮放回傳 null）
  touchEnd(x, y) {
    const t = this.touch; this.touch = null;
    if (!t || t.moved) return null;
    const now = Date.now();
    if (now - this.lastTap < 300) { // 點兩下：放大或還原
      this.lastTap = 0;
      if (this.zoomed()) this.fit(); else this.zoomAt(x, y, this.fitScale * 2.2);
      this.onChange();
      return null;
    }
    this.lastTap = now;
    return this.tileAt(x, y);
  }

  /* ---- 繪製 ---- */
  draw(ctx, view, players) {
    const r = this.rect, s = this.s;
    ctx.save();
    rrect(ctx, r.x, r.y, r.w, r.h, 0); ctx.clip();
    if (this.img && this.img.width) ctx.drawImage(this.img, this.ox, this.oy, BW * s, BH * s);
    else { ctx.fillStyle = '#fbf3a6'; ctx.fillRect(this.ox, this.oy, BW * s, BH * s); }
    const X = bx => this.ox + bx * s, Y = by => this.oy + by * s;

    // 牌堆閃爍
    for (const k in this.flashes) {
      const [x, y, w, h] = DECK[k], a = 1 - (Date.now() - this.flashes[k]) / 900;
      fillR(ctx, X(x), Y(y), w * s, h * s, 10 * s, `rgba(255,255,255,${0.55 * a})`, `rgba(242,194,0,${a})`, 6);
    }
    if (view) {
      // 中央：骰子與在野武將張數
      const [gx, gy, gw, gh] = DECK.general;
      fillR(ctx, X(gx), Y(gy), gw * s, gh * s, 14 * s, '#2e8b3e', '#111', 2);
      const ds = this.dice || [];
      const dsz = Math.min(gh * s * 0.5, (gw * s - 16) / Math.max(1, ds.length) - 10);
      ds.forEach((d, k) => {
        const cx = X(gx) + gw * s / 2 + (k - (ds.length - 1) / 2) * (dsz + 10), cy = Y(gy) + gh * s * 0.4;
        fillR(ctx, cx - dsz / 2, cy - dsz / 2, dsz, dsz, dsz * 0.18, '#fff', '#111', 2);
        ctx.fillStyle = d === 1 ? '#d0021b' : '#111';
        for (const [px, py] of PIPS[d]) { ctx.beginPath(); ctx.arc(cx + px * dsz * 0.27, cy + py * dsz * 0.27, dsz * (d === 1 ? 0.14 : 0.09), 0, Math.PI * 2); ctx.fill(); }
      });
      ctx.fillStyle = '#fff'; ctx.font = font(Math.max(11, Math.min(16, gh * s * 0.14)), 700); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(`在野武將 ${view.pile} 張`, X(gx) + gw * s / 2, Y(gy) + gh * s * 0.84);
      ctx.textAlign = 'left';

      view.tiles.forEach((t, i) => {
        const [x, y, w, h] = BOXES[i], m = Math.min(w, h);
        // 地主印章（右上角）
        if (t.owner != null) {
          const o = players[t.owner], z = Math.max(16, m * 0.42 * s);
          const sx = X(x + w) - z - 3 * s, sy = Y(y) + 3 * s;
          fillR(ctx, sx, sy, z, z, z * 0.18, o.color, '#fff', 2);
          ctx.fillStyle = '#fff'; ctx.font = font(z * 0.66, 700); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
          ctx.fillText(o.family, sx + z / 2, sy + z / 2 + 1); ctx.textAlign = 'left';
        }
        // 城池（左下角）：小城一層、大城三層
        if (t.level) {
          const z = Math.max(16, m * 0.4 * s), cx = X(x) + 4 * s, cy = Y(y + h) - z - 4 * s;
          fillR(ctx, cx, cy, z, z, z * 0.2, 'rgba(255,255,255,.85)', '#2a1a10', 1.5);
          const tiers = t.level === 2 ? 3 : 1;
          for (let k = 0; k < tiers; k++) {
            const ww = z * (0.8 - k * 0.18), hh = z * (tiers === 1 ? 0.5 : 0.24);
            const yy = cy + z - 4 - (k + 1) * hh - k;
            ctx.fillStyle = ['#c62828', '#1565c0', '#2e7d32'][k]; ctx.fillRect(cx + (z - ww) / 2, yy, ww, hh * 0.45);
            ctx.fillStyle = '#f8f1d8'; ctx.fillRect(cx + (z - ww) / 2 + 1, yy + hh * 0.45, ww - 2, hh * 0.55);
          }
        }
      });
      // 目前玩家所在格加框
      if (view.cur != null) {
        const p = players[view.cur], [x, y, w, h] = BOXES[p.pos];
        fillR(ctx, X(x) - 3, Y(y) - 3, w * s + 6, h * s + 6, 8, null, COLOR.gold, 4);
      }
      // 旗幟
      const byPos = {};
      players.filter(p => p.alive).forEach(p => (byPos[p.pos] = byPos[p.pos] || []).push(p));
      for (const pos in byPos) {
        const list = byPos[pos], [x, y, w, h] = BOXES[pos];
        // 旗幟約 24–36 點大；同一格多人時疊放，不超出格子
        const z = Math.max(24, Math.min(36, Math.min(w, h) * 0.5 * s));
        const step = list.length > 1 ? Math.min(z * 0.7, Math.max(z * 0.35, (w * s - z) / (list.length - 1))) : 0;
        const total = step * (list.length - 1) + z;
        list.forEach((p, k) => {
          const fx = X(x + w / 2) - total / 2 + k * step, fy = Y(y + h / 2) - z / 2;
          drawFlag(ctx, fx, fy, z, p.color, p.family, view.cur === p.id);
        });
      }
    }
    ctx.restore();
  }
}

function drawFlag(ctx, x, y, z, color, ch, cur) {
  ctx.save();
  ctx.lineCap = 'round';
  ctx.strokeStyle = '#3b2a1a'; ctx.lineWidth = Math.max(2, z * 0.07);
  ctx.beginPath(); ctx.moveTo(x + z * 0.1, y); ctx.lineTo(x + z * 0.1, y + z); ctx.stroke();
  const fx = x + z * 0.13, fw = z * 0.82, fh = z * 0.6;
  ctx.beginPath(); ctx.moveTo(fx, y + z * 0.04); ctx.lineTo(fx + fw, y + z * 0.04); ctx.lineTo(fx + fw - z * 0.1, y + z * 0.04 + fh / 2); ctx.lineTo(fx + fw, y + z * 0.04 + fh); ctx.lineTo(fx, y + z * 0.04 + fh); ctx.closePath();
  ctx.fillStyle = color; ctx.fill(); ctx.lineWidth = cur ? 3 : 1.5; ctx.strokeStyle = cur ? COLOR.gold : '#1a0f08'; ctx.stroke();
  ctx.font = font(fh * 0.72, 700); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.lineWidth = 3; ctx.strokeStyle = '#1a0f08'; ctx.strokeText(ch, fx + fw * 0.45, y + z * 0.04 + fh / 2 + 1);
  ctx.fillStyle = '#fff'; ctx.fillText(ch, fx + fw * 0.45, y + z * 0.04 + fh / 2 + 1);
  ctx.restore();
}

module.exports = { BoardView, BOXES, DECK, BW, BH, drawFlag };
