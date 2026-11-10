'use strict';
/* 在瀏覽器中模擬本遊戲用到的微信小遊戲 API（僅供預覽與測試） */
(() => {
  const q = new URLSearchParams(location.search);
  const notch = q.has('notch');
  const W = innerWidth, H = innerHeight;
  const top = notch ? 47 : 20, bottom = notch ? 34 : 0;
  const BASE = '../../wechat/';
  let mainCanvas = null;
  const handlers = { start: [], move: [], end: [], cancel: [] };
  const conv = list => Array.from(list).map(t => ({ identifier: t.identifier, clientX: t.clientX, clientY: t.clientY }));
  const fire = (k, e) => handlers[k].forEach(f => f(e));
  let mouseDown = false;
  function bind(c) {
    c.addEventListener('touchstart', e => { e.preventDefault(); fire('start', { touches: conv(e.touches), changedTouches: conv(e.changedTouches) }); }, { passive: false });
    c.addEventListener('touchmove', e => { e.preventDefault(); fire('move', { touches: conv(e.touches), changedTouches: conv(e.changedTouches) }); }, { passive: false });
    c.addEventListener('touchend', e => { e.preventDefault(); fire('end', { touches: conv(e.touches), changedTouches: conv(e.changedTouches) }); }, { passive: false });
    c.addEventListener('touchcancel', e => fire('cancel', { touches: [], changedTouches: conv(e.changedTouches) }));
    const m = e => [{ identifier: 0, clientX: e.clientX, clientY: e.clientY }];
    c.addEventListener('mousedown', e => { mouseDown = true; fire('start', { touches: m(e), changedTouches: m(e) }); });
    addEventListener('mousemove', e => { if (mouseDown) fire('move', { touches: m(e), changedTouches: m(e) }); });
    addEventListener('mouseup', e => { if (!mouseDown) return; mouseDown = false; fire('end', { touches: [], changedTouches: m(e) }); });
  }
  window.wx = {
    getWindowInfo: () => ({ windowWidth: W, windowHeight: H, pixelRatio: devicePixelRatio || 2, statusBarHeight: top,
      safeArea: { top, bottom: H - bottom, left: 0, right: W, width: W, height: H - top - bottom } }),
    getMenuButtonBoundingClientRect: () => ({ top: top + 4, bottom: top + 36, height: 32, width: 87, right: W - 7, left: W - 94 }),
    createCanvas: () => {
      const c = document.createElement('canvas');
      if (!mainCanvas) { mainCanvas = c; c.style.width = W + 'px'; c.style.height = H + 'px'; document.body.appendChild(c); bind(c); }
      return c;
    },
    createImage: () => {
      const im = new Image();
      const desc = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src');
      Object.defineProperty(im, 'src', { get: () => desc.get.call(im), set: v => desc.set.call(im, /^(data:|https?:)/.test(v) ? v : BASE + v) });
      return im;
    },
    onTouchStart: f => handlers.start.push(f), onTouchMove: f => handlers.move.push(f),
    onTouchEnd: f => handlers.end.push(f), onTouchCancel: f => handlers.cancel.push(f),
    getStorageSync: k => { try { return JSON.parse(localStorage.getItem('wx:' + k)); } catch (e) { return ''; } },
    setStorageSync: (k, v) => localStorage.setItem('wx:' + k, JSON.stringify(v)),
    showShareMenu: () => {}, setKeepScreenOn: () => {},
    // 分包：預覽時檔案都在本機，稍等一下就算下載完成
    loadSubpackage: ({ success }) => { const t = { cb: null, onProgressUpdate(f) { this.cb = f; } };
      setTimeout(() => { if (t.cb) t.cb({ progress: 100 }); success && success(); }, 150); return t; },
  };
})();
