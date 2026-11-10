#!/usr/bin/env python3
"""依棋盤掃描量得之格子位置，為每個主題繪製向量版棋盤 board-<主題>.svg。

座標與 index.html 的 BOXES 相同（掃描圖 2122×3000 座標，扣除裁切偏移 SCAN 後逆時針轉 90 度成橫式）。
執行：python3 tools/make_board_svg.py  → 輸出 board-sanguo.svg、board-shuihu.svg
"""
import os
import re

SCAN_X, SCAN_Y, W, H = 45, 255, 1900, 2630
BOXES = [[1297,290,610,525],[1690,890,210,142],[1312,840,310,175],[1307,1080,210,140],[1592,1050,310,170],[1690,1285,212,142],
  [1312,1240,310,177],[1307,1480,210,140],[1592,1445,310,177],[1692,1688,208,140],[1690,1895,210,140],[1277,1630,385,420],
  [1309,2088,210,137],[1590,2055,307,170],[1690,2293,207,140],[1307,2243,310,175],[1305,2482,210,140],[1587,2452,308,173],
  [1685,2692,209,140],[1307,2640,307,175],[1097,2623,143,205],[893,2620,142,205],[880,2130,405,490],[680,2253,142,204],
  [700,2520,175,305],[488,2623,139,210],[490,2253,173,310],[275,2253,145,202],[288,2520,177,308],[73,2623,145,205],
  [78,2253,180,310],[75,2047,213,143],[372,1895,393,300],[75,1892,213,140],[75,1687,213,140],[348,1700,320,170],
  [455,1492,213,145],[75,1497,323,170],[75,1290,205,142],[348,1300,320,175],[455,1098,213,142],[75,1095,323,175],
  [75,890,213,140],[75,687,213,140],[320,690,320,350],[457,477,211,143],[75,490,315,175],[75,285,217,142],
  [355,285,313,170],[735,285,141,202],[688,553,175,309],[928,660,138,207],[895,285,171,305],[1137,282,137,206],[1137,557,137,190]]
DECKS = {'emergency': [760, 990, 450, 304], 'general': [734, 1384, 506, 336], 'strategy': [764, 1814, 452, 300]}

# 與 index.html 的 TILES 同順序
def load_theme_names():
    """從 themes.js 讀出各主題的 55 個格子名稱，確保與遊戲一致"""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'themes.js'), encoding='utf8').read()
    out = {}
    # 主題順序取自 order: [...]；格子名稱陣列命名為 <主題>_TILES（如 FENGSHEN_TILES）
    keys = re.findall(r"'(\w+)'", re.search(r'order: \[(.*?)\]', src).group(1))
    for key in keys:
        var = key.upper() + '_TILES'
        body = re.search(r'const ' + var + r' = \[(.*?)\];', src, re.S).group(1)
        names = re.findall(r"'([^']+)'", body)
        assert len(names) == 55, (key, len(names))
        out[key] = names
    return out

THEME_NAMES = load_theme_names()
NAMES = THEME_NAMES['sanguo']          # 由 main() 依主題換掉
def nm(i): return NAMES[i]
def paren(s_):                          # 起點名稱「起點（武將風雲錄）」取括號內的字
    m = re.search(r'（(.+?)）', s_)
    return m.group(1) if m else s_

# 每一格的種類與畫法所需資料（順序同 engine.js 的 TILES）；格子名稱一律來自 themes.js
R, Hh, E, K = ('recruit',), ('hire',), ('emergency',), ('strategy',)
def C(p, g): return ('city', p, g)
def F(): return ('field', 1000, 'field')
def SH(fee): return ('shop', fee)
TILES = [('start',),
  R, C(1500,'orange'), E, C(1000,'orange'), Hh, C(2000,'orange'), K, C(1000,'orange'), SH(500), F(),
  ('rest', 500),
  E, C(1000,'blue'), R, C(2000,'blue'), K, C(1000,'blue'), Hh, C(1500,'blue'), SH(500), F(),
  ('rest', 800),
  E, C(1000,'yellow'), R, C(1500,'yellow'), K, C(1000,'yellow'), Hh, C(2000,'yellow'), SH(400),
  ('island',), F(),
  R, C(2000,'magenta'), E, C(1000,'magenta'), Hh, C(1500,'magenta'), K, C(1000,'magenta'), SH(300), F(),
  ('cottage',),
  E, C(1000,'green'), R, C(2000,'green'), Hh, C(1500,'green'), K, C(1000,'green'), SH(200), F()]
assert len(TILES) == len(BOXES) == 55

COL = {'orange': '#ef5a28', 'blue': '#2f7fd8', 'yellow': '#f6d43a', 'green': '#3aa655', 'magenta': '#d8345f', 'field': '#a0452a'}
FONT = "'PingFang TC','Heiti TC','Microsoft JhengHei','Noto Sans TC',sans-serif"

# 橫式棋盤（電腦版）：把直式掃描座標逆時針轉 90 度（起點移到左上角）
# 直式棋盤（手機版）：保留掃描圖的直式方向，由 main(portrait=True) 切換
PORTRAIT = False
# 手機版：直式，格內文字放大（在手機寬度下不小於約 12pt），商店不畫品牌標誌，圖畫格加名稱橫幅
MOBILE = False
MOBILE_MIN = 64   # 手機版主要文字的最小字級（棋盤單位；棋盤寬 1900 縮到 360pt 時約 12pt）
OUT_W, OUT_H = H, W

def rot(x, y, w, h):
    cx, cy = x - SCAN_X, y - SCAN_Y
    if PORTRAIT:
        return cx, cy, w, h
    return cy, W - cx - w, h, w

def box(i):
    return rot(*BOXES[i])

def t(x, y, s, size, fill='#111', weight=700, anchor='middle', extra=''):
    return f'<text x="{x:.0f}" y="{y:.0f}" font-size="{size:.0f}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" {extra}>{s}</text>'

def fit(s, w, h, max_size):
    """字級：讓文字在寬 w 內放得下"""
    return min(max_size, w * 0.9 / max(1, len(s)), h)

def frame(x, y, w, h, fill, inner=None, r=8):
    out = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="#1a1a1a" stroke-width="5"/>'
    if inner:
        out += f'<rect x="{x+8}" y="{y+8}" width="{w-16}" height="{h-16}" rx="{r-3}" fill="none" stroke="{inner}" stroke-width="2"/>'
    return out

def picture(kind, cx, cy, s):
    """小圖示，s 為邊長；以 <use> 引用 defs 中的符號"""
    return f'<use href="#{kind}" x="{cx - s/2:.0f}" y="{cy - s/2:.0f}" width="{s:.0f}" height="{s:.0f}"/>'

def tint(hex_, k):
    """把顏色與白色混合，k 為白色比例"""
    r, g_, b = (int(hex_[j:j+2], 16) for j in (1, 3, 5))
    return '#%02x%02x%02x' % tuple(round(c + (255 - c) * k) for c in (r, g_, b))

def city(i, name, price, g):
    """城市：只畫顏色與大字城名（價格、稅金改由滑鼠懸停顯示）"""
    x, y, w, h = box(i)
    out = frame(x, y, w, h, COL[g])
    out += f'<rect x="{x+10}" y="{y+10}" width="{w-20}" height="{h-20}" rx="6" fill="{tint(COL[g], 0.62)}" stroke="#1a1a1a" stroke-width="2.5"/>'
    out += f'<rect x="{x+16}" y="{y+16}" width="{w-32}" height="{h-32}" rx="4" fill="none" stroke="{COL[g]}" stroke-width="3"/>'
    if h > w * 1.15:  # 直式格子：城名直書
        fs = min(w * 0.58, (h - 40) / len(name) * 0.92)
        y0 = y + h / 2 - fs * len(name) / 2 + fs * 0.86
        for k, ch in enumerate(name):
            out += t(x + w / 2, y0 + k * fs, ch, fs, '#1a1a1a', 900)
    else:
        fs = min(h * 0.56, (w - 40) / len(name) * 0.92)
        out += t(x + w / 2, y + h / 2 + fs * 0.36, name, fs, '#1a1a1a', 900)
    return out

def field(i, name):
    x, y, w, h = box(i)
    out = frame(x, y, w, h, COL['field'], '#f3c9a9')
    out += t(x + w / 2, y + min(w, h) * 0.2, '古戰場', min(w, h) * 0.14, '#ffe3c2')
    if h > w * 1.15:
        fs = min(w * 0.55, (h * 0.75) / len(name))
        y0 = y + h * 0.58 - fs * len(name) / 2 + fs * 0.86
        for k, ch in enumerate(name):
            out += t(x + w / 2, y0 + k * fs, ch, fs, '#fff', 900, extra='stroke="#3a1206" stroke-width="2"')
    else:
        fs = min(h * 0.5, (w * 0.9) / len(name))
        out += t(x + w / 2, y + h * 0.6 + fs * 0.36, name, fs, '#fff', 900, extra='stroke="#3a1206" stroke-width="2"')
    return out

def small(i, kind):
    x, y, w, h = box(i)
    m = min(w, h)
    if kind == 'recruit':
        out = frame(x, y, w, h, '#f6d43a')
        out += t(x + w/2, y + h * 0.25, nm(i), fit(nm(i), w, h, m * 0.2))
        out += f'<rect x="{x + w/2 - m*0.25:.0f}" y="{y + h*0.32:.0f}" width="{m*0.5:.0f}" height="{m*0.42:.0f}" rx="6" fill="#111"/>'
        out += picture('soldiers', x + w/2, y + h * 0.53, m * 0.4)
        out += t(x + w/2, y + h * 0.92, '500', m * 0.17)
    elif kind == 'hire':
        out = frame(x, y, w, h, '#6b5bd6', '#c9c1ff')
        out += t(x + w/2, y + h * 0.24, nm(i), fit(nm(i), w, h, m * 0.17), '#fff')
        out += picture('people', x + w/2, y + h * 0.55, m * 0.48)
        out += t(x + w/2, y + h * 0.92, '1000', m * 0.16, '#fff')
    elif kind in ('emergency', 'strategy'):
        out = frame(x, y, w, h, '#2f7fd8')
        iw, ih = m * 0.62, m * 0.62
        inner = '#e8457a' if kind == 'emergency' else '#ffe14d'
        out += f'<rect x="{x + w/2 - iw/2:.0f}" y="{y + h/2 - ih/2:.0f}" width="{iw:.0f}" height="{ih:.0f}" fill="{inner}" stroke="#1a1a1a" stroke-width="3"/>'
        out += picture('horse' if kind == 'emergency' else 'pouch', x + w/2, y + h/2, iw * 0.9)
        name = nm(i)
        fs = min(m * 0.15, m * 0.6 / max(1, len(name)))
        if w > h:  # 橫式：左側直書名稱，右側「抽牌」
            for k, ch in enumerate(name):
                out += t(x + (w - iw) / 4, y + h/2 - fs * 1.5 + k * fs * 1.05, ch, fs, '#fff')
            for k, ch in enumerate('抽牌'):
                out += t(x + w - (w - iw) / 4, y + h/2 - fs * 0.2 + k * fs * 1.1, ch, fs, '#fff')
        else:
            out += t(x + w/2, y + (h - ih) / 2 - 6, name, fit(name, w, h, fs), '#fff')
            out += t(x + w/2, y + h - (h - ih) / 4 + fs * 0.35, '抽牌', fs, '#fff')
    return out

def shop(i, fee):
    """商店：名稱、通用的攤販圖示（條紋遮陽篷與櫃台，不使用任何品牌標誌）與消費金額"""
    x, y, w, h = box(i)
    m = min(w, h)
    out = frame(x, y, w, h, '#f6d43a')
    out += t(x + w/2, y + h * 0.22, nm(i), fit(nm(i), w, h, m * 0.19), '#111')
    lw, lh = m * 0.62, m * 0.45
    lx, ly = x + w/2 - lw/2, y + h * 0.3
    out += f'<rect x="{lx:.0f}" y="{ly:.0f}" width="{lw:.0f}" height="{lh:.0f}" fill="#fff" stroke="#1a1a1a" stroke-width="2"/>'
    # 遮陽篷：紅白相間的條紋，下緣呈波浪
    ah, n = lh * 0.42, 5
    sw_ = (lw - 8) / n
    for k in range(n):
        sx_ = lx + 4 + k * sw_
        out += (f'<path d="M{sx_:.1f},{ly + 4:.1f} h{sw_:.1f} v{ah:.1f} q{-sw_ / 2:.1f},{lh * 0.12:.1f} {-sw_:.1f},0z" '
                f'fill="{"#d8282b" if k % 2 == 0 else "#fff"}" stroke="#1a1a1a" stroke-width="1.5"/>')
    # 櫃台與貨品
    cy0 = ly + 4 + ah + lh * 0.1
    out += f'<rect x="{lx + 8:.1f}" y="{cy0:.1f}" width="{lw - 16:.1f}" height="{ly + lh - 4 - cy0:.1f}" fill="#a8743f" stroke="#1a1a1a" stroke-width="1.5"/>'
    for k, c in enumerate(('#f2c200', '#3aa655', '#e8457a')):
        out += f'<circle cx="{lx + lw * (0.3 + k * 0.2):.1f}" cy="{cy0 - lh * 0.02:.1f}" r="{lh * 0.07:.1f}" fill="{c}" stroke="#1a1a1a" stroke-width="1.2"/>'
    out += t(x + w/2, y + h * 0.93, f'消費{fee}', m * 0.15, '#111')
    return out

DEFS = '''
<linearGradient id="gSky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5fb4ec"/><stop offset=".55" stop-color="#bfe6fb"/><stop offset="1" stop-color="#fff2c2"/></linearGradient>
<radialGradient id="gSun" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fffde6"/><stop offset=".45" stop-color="#ffd84a"/><stop offset=".8" stop-color="#ff9a1f"/><stop offset="1" stop-color="#ff7a00" stop-opacity="0"/></radialGradient>
<radialGradient id="gParch" cx=".5" cy=".45" r=".7"><stop offset="0" stop-color="#fffbe6"/><stop offset=".6" stop-color="#f6e2a8"/><stop offset="1" stop-color="#d9ae63"/></radialGradient>
<linearGradient id="gGrass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9ad86a"/><stop offset="1" stop-color="#3c8f37"/></linearGradient>
<radialGradient id="gGround" cx=".5" cy=".35" r=".65"><stop offset="0" stop-color="#b7e27f"/><stop offset=".7" stop-color="#6cb94b"/><stop offset="1" stop-color="#4f9a3a" stop-opacity="0"/></radialGradient>
<linearGradient id="gSea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5ccdf2"/><stop offset=".6" stop-color="#2a8fd4"/><stop offset="1" stop-color="#17609f"/></linearGradient>
<radialGradient id="gSand" cx=".45" cy=".35" r=".7"><stop offset="0" stop-color="#fff4cc"/><stop offset=".6" stop-color="#efcd84"/><stop offset="1" stop-color="#c99a4f"/></radialGradient>
<linearGradient id="gWood" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#5a3415"/><stop offset=".35" stop-color="#a8743f"/><stop offset=".7" stop-color="#8a5a2b"/><stop offset="1" stop-color="#4e2c10"/></linearGradient>
<linearGradient id="gWoodV" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b07a43"/><stop offset=".5" stop-color="#8a5a2b"/><stop offset="1" stop-color="#5a3415"/></linearGradient>
<linearGradient id="gPillar" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#7d1010"/><stop offset=".35" stop-color="#ef5a42"/><stop offset=".6" stop-color="#c8281e"/><stop offset="1" stop-color="#6e0d0d"/></linearGradient>
<linearGradient id="gGold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff6b8"/><stop offset=".5" stop-color="#e0a812"/><stop offset="1" stop-color="#fff0a0"/></linearGradient>
<linearGradient id="gGoldText" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff7a8"/><stop offset=".5" stop-color="#ffc61a"/><stop offset="1" stop-color="#e08a00"/></linearGradient>
<linearGradient id="gRoof" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6fdc87"/><stop offset=".5" stop-color="#26954a"/><stop offset="1" stop-color="#11602b"/></linearGradient>
<linearGradient id="gRoofB" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7cc4f5"/><stop offset=".5" stop-color="#2a6fc4"/><stop offset="1" stop-color="#173f86"/></linearGradient>
<linearGradient id="gShadeH" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity=".35"/><stop offset=".45" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".32"/></linearGradient>
<linearGradient id="gShadeV" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".35"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".3"/></linearGradient>
<linearGradient id="gStone" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f6ead0"/><stop offset="1" stop-color="#cdb486"/></linearGradient>
<linearGradient id="gWall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e0ad62"/><stop offset="1" stop-color="#a86b2c"/></linearGradient>
<linearGradient id="gMarble" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f4f9ff"/><stop offset="1" stop-color="#9fb8cf"/></linearGradient>
<linearGradient id="gSign" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8fd3ff"/><stop offset=".5" stop-color="#3b8de0"/><stop offset="1" stop-color="#1d5aa8"/></linearGradient>
<linearGradient id="gMud" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ecd09a"/><stop offset="1" stop-color="#c39257"/></linearGradient>
<linearGradient id="gThatch" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f1d27a"/><stop offset=".6" stop-color="#c99a3e"/><stop offset="1" stop-color="#8d6524"/></linearGradient>
<linearGradient id="gBamboo" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#2f7d32"/><stop offset=".4" stop-color="#8fd36a"/><stop offset="1" stop-color="#2a6b2c"/></linearGradient>
<linearGradient id="gMount" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8aa6d8"/><stop offset="1" stop-color="#c9d9ef"/></linearGradient>
<linearGradient id="gFireP" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#e53935"/><stop offset=".55" stop-color="#ff9800"/><stop offset="1" stop-color="#ffeb3b"/></linearGradient>
<radialGradient id="gGlow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fffbd0" stop-opacity=".95"/><stop offset=".4" stop-color="#ffe066" stop-opacity=".55"/><stop offset="1" stop-color="#ffb000" stop-opacity="0"/></radialGradient>
<radialGradient id="gWarm" cx=".5" cy=".6" r=".7"><stop offset="0" stop-color="#fff6c4"/><stop offset=".6" stop-color="#ffb347"/><stop offset="1" stop-color="#c2561b"/></radialGradient>
<radialGradient id="gLantern" cx=".4" cy=".35" r=".7"><stop offset="0" stop-color="#ffd36b"/><stop offset=".45" stop-color="#ef3b2c"/><stop offset="1" stop-color="#8e0f0f"/></radialGradient>
<radialGradient id="gBall" cx=".35" cy=".3" r=".75"><stop offset="0" stop-color="#fff" stop-opacity=".75"/><stop offset=".35" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".3"/></radialGradient>
<radialGradient id="gShadow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#000" stop-opacity=".35"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
<radialGradient id="gSkin" cx=".38" cy=".32" r=".75"><stop offset="0" stop-color="#fff1e2"/><stop offset=".6" stop-color="#f8d2ad"/><stop offset="1" stop-color="#d9a07a"/></radialGradient>
<linearGradient id="gMetal" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".45" stop-color="#b7c4cc"/><stop offset=".55" stop-color="#8d9ba5"/><stop offset="1" stop-color="#eef3f6"/></linearGradient>
<pattern id="pBrick" width="26" height="14" patternUnits="userSpaceOnUse"><path d="M0,.5 h26 M0,7.5 h26 M6,0 v7 M19,7 v7" stroke="#6b3d14" stroke-opacity=".45" stroke-width="1.2" fill="none"/></pattern>
<pattern id="pStoneW" width="22" height="12" patternUnits="userSpaceOnUse"><path d="M0,.5 h22 M0,6.5 h22 M5,0 v6 M16,6 v6" stroke="#8a7350" stroke-opacity=".55" stroke-width="1" fill="none"/></pattern>
<pattern id="pThatch" width="9" height="22" patternUnits="userSpaceOnUse"><path d="M1,0 q1.5,11 0,22 M4.5,-2 q1.5,12 .5,24 M7.5,0 q1,11 -.5,22" stroke="#7a5418" stroke-opacity=".55" stroke-width="1.1" fill="none"/><path d="M3,2 q1,9 0,18 M6,4 q1,8 0,14" stroke="#fff3b8" stroke-opacity=".55" stroke-width=".9" fill="none"/></pattern>
<pattern id="pThatch2" width="9" height="22" patternUnits="userSpaceOnUse" patternTransform="skewX(28)"><path d="M1,0 q1.5,11 0,22 M4.5,-2 q1.5,12 .5,24 M7.5,0 q1,11 -.5,22" stroke="#5e3f10" stroke-opacity=".6" stroke-width="1.1" fill="none"/><path d="M3,2 q1,9 0,18" stroke="#fff3b8" stroke-opacity=".4" stroke-width=".9" fill="none"/></pattern>
<pattern id="pMud" width="18" height="18" patternUnits="userSpaceOnUse"><path d="M2,4 l5,1 M11,12 l4,-2 M6,15 l3,1 M14,3 l2,2" stroke="#8d6230" stroke-opacity=".5" stroke-width="1" fill="none"/></pattern>
<pattern id="pWave" width="34" height="18" patternUnits="userSpaceOnUse"><path d="M2,12 q6,-7 12,0 q6,-7 12,0" stroke="#fff" stroke-opacity=".6" stroke-width="1.6" fill="none"/><path d="M19,4 q4,-4 8,0" stroke="#fff" stroke-opacity=".4" stroke-width="1.2" fill="none"/></pattern>
<pattern id="pGrain" width="40" height="8" patternUnits="userSpaceOnUse"><path d="M0,3 q10,-2 20,0 t20,0 M0,6.5 q12,1.5 24,0 t16,0" stroke="#3e2108" stroke-opacity=".35" stroke-width=".8" fill="none"/></pattern>
<pattern id="pBarber" width="18" height="18" patternUnits="userSpaceOnUse" patternTransform="rotate(-35)"><rect width="18" height="18" fill="#fff"/><rect width="6" height="18" fill="#d8282b"/><rect x="9" width="5" height="18" fill="#1f5fbf"/></pattern>
<pattern id="pLattice" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M0,5 h10 M5,0 v10" stroke="#7a2a0c" stroke-width="1.8"/></pattern>
<pattern id="pCloud" width="40" height="30" patternUnits="userSpaceOnUse"><path d="M6,20 q0,-8 8,-6 q2,-7 9,-4 q6,-2 7,5 q6,1 4,6z" fill="#fff" fill-opacity=".22"/></pattern>
<symbol id="soldiers" viewBox="0 0 100 100">
  <g stroke="#111" stroke-width="1.6" stroke-linejoin="round">
  <path d="M74 6 l4 10 l-4 3 l-4 -3z M74 18 v78" stroke="#fff" stroke-width="3.5" fill="#fff"/>
  <path d="M70 26 q4 6 8 0" stroke="#e53935" stroke-width="3" fill="none"/>
  <path d="M56 34 q9-14 18 0 v4 h-18z" fill="#fff"/><path d="M65 20 q-6 -2 -4 -8 q4 4 4 8z" fill="#e53935" stroke="none"/>
  <circle cx="65" cy="42" r="8" fill="#fff"/><path d="M61 42 h2 M67 42 h2" stroke-width="2"/>
  <path d="M54 52 h22 l4 24 h-7 l-1 20 h-6 l-2-16 l-2 16 h-6 l-1-20 h-6z" fill="#fff"/><path d="M57 60 h16 M57 66 h16" fill="none"/>
  <path d="M18 30 q12-18 24 0 v5 h-24z" fill="#fff"/><path d="M30 12 q-8 -3 -5 -11 q6 6 5 11z" fill="#e53935" stroke="none"/>
  <circle cx="30" cy="38" r="10" fill="#fff"/><path d="M25 38 h3 M33 38 h3 M27 44 q3 2 6 0" stroke-width="2" fill="none"/>
  <path d="M15 51 h30 l5 30 h-9 l-2 15 h-7 l-2-13 l-2 13 h-7 l-2-15 h-9z" fill="#fff"/><path d="M19 60 h22 M19 67 h22 M30 51 v14" fill="none"/>
  <circle cx="13" cy="66" r="12" fill="#fff"/><circle cx="13" cy="66" r="7" fill="none"/><circle cx="13" cy="66" r="2.5" fill="#111"/>
  </g>
</symbol>
<symbol id="people" viewBox="0 0 100 100">
  <g fill="#111"><circle cx="32" cy="26" r="13"/><path d="M19 22 q13 -16 26 0 q-6 -6 -13 -4 q-8 -2 -13 4z" fill="#3a2a5a"/>
  <path d="M10 94 v-28 q0-18 22-18 q22 0 22 18 v28z"/><path d="M26 48 l6 12 l6 -12z" fill="#fff"/><path d="M31 52 h2 l2 14 l-3 4 l-3 -4z" fill="#c62828"/>
  <circle cx="70" cy="32" r="11"/><path d="M58 30 q12 -16 24 0 q-4 -8 -12 -6 q-8 -2 -12 6z" fill="#3a2a5a"/>
  <path d="M50 94 v-24 q0-16 20-16 q20 0 20 16 v24z"/><path d="M65 54 l5 10 l5 -10z" fill="#fff"/><path d="M69 57 h2 l2 12 l-3 3 l-3 -3z" fill="#f6d43a"/>
  <rect x="40" y="70" width="34" height="24" rx="3" fill="#5a3a1a" stroke="#111" stroke-width="2"/><rect x="51" y="65" width="12" height="6" rx="2" fill="none" stroke="#5a3a1a" stroke-width="2.5"/><rect x="40" y="78" width="34" height="3" fill="#c9a227"/></g>
</symbol>
<symbol id="horse" viewBox="0 0 100 100">
  <path d="M60 28 l2 -20 M60 8 q12 -2 20 4 q-8 4 -20 6" stroke="#111" stroke-width="2.5" fill="#e53935"/>
  <path fill="#111" d="M28 90 l7-22 q-14-6-12-24 q2-10 10-14 l-7-11 l11 5 q8-8 22-6 q14 2 20 14 l10 4 q-2 6-8 6 q2 10-6 16 l5 20 h-6 l-7-16 q-8 4-16 2 l-9 26z"/>
  <path d="M55 24 q-2 -10 6 -14 q6 0 6 8 q-2 6 -8 8z M53 36 q6 -6 14 -2" fill="#111" stroke="#111" stroke-width="2"/>
  <path d="M44 22 q-8 -2 -12 4 M40 28 q-8 0 -10 6 M38 34 q-8 2 -8 8" stroke="#444" stroke-width="2.5" fill="none"/>
  <circle cx="76" cy="33" r="2" fill="#fff"/>
  <path d="M20 46 q-12 4-14 18 q8-8 16-8" fill="#111"/>
  <path d="M8 66 q-6 10 4 18 M4 60 q-4 14 6 24" fill="none" stroke="#c0392b" stroke-width="3.5" stroke-linecap="round"/>
  <path d="M44 50 q8 4 16 0" stroke="#555" stroke-width="2" fill="none"/>
</symbol>
<symbol id="pouch" viewBox="0 0 100 100">
  <path d="M30 40 q-24 30 -6 46 q26 14 52 0 q16-16 -6-46z" fill="url(#gGoldText)" stroke="#111" stroke-width="4.5"/>
  <path d="M30 40 q-24 30 -6 46 q26 14 52 0 q16-16 -6-46z" fill="url(#gShadeH)"/>
  <path d="M38 38 q-14-22 -4-28 q10-2 12 14 q4-20 16-16 q8 6-6 30" fill="url(#gGoldText)" stroke="#111" stroke-width="4.5"/>
  <path d="M28 40 q22 10 44 0" fill="none" stroke="#c62828" stroke-width="6"/><path d="M28 40 q22 10 44 0" fill="none" stroke="#111" stroke-width="1.2"/>
  <path d="M47 44 q-6 14 -12 22 M53 44 q6 14 12 22" fill="none" stroke="#c62828" stroke-width="3"/>
  <circle cx="52" cy="64" r="12" fill="none" stroke="#111" stroke-width="4.5"/><circle cx="52" cy="64" r="5" fill="#c62828" stroke="#111" stroke-width="1.5"/>
  <path d="M30 76 q22 8 44 0" fill="none" stroke="#a86d00" stroke-width="1.5" stroke-dasharray="3 3"/>
</symbol>
<symbol id="arrow" viewBox="0 0 100 100"><path d="M10 35 h45 v-22 l40 37 l-40 37 v-22 h-45z" fill="#e8452c"/></symbol>
<pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="4" cy="4" r="1.2" fill="#e7d98a"/></pattern>
'''

import math

OL = '#1a1a1a'
def P(d, fill='none', sw=3, stroke=OL, extra=''):
    s = f' stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"' if sw else ''
    return f'<path d="{d}" fill="{fill}"{s} {extra}/>'
def PS(d, fill, shade='gShadeH', sw=3):
    """填色＋描邊，再疊明暗"""
    return P(d, fill, sw) + f'<path d="{d}" fill="url(#{shade})"/>'
def EL(cx, cy, rx, ry, fill, sw=2.5, stroke=OL, extra=''):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if sw else ''
    return f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{fill}"{s} {extra}/>'
def LN(x1, y1, x2, y2, c=OL, w=2.5, extra=''):
    return f'<path d="M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}" stroke="{c}" stroke-width="{w}" stroke-linecap="round" {extra}/>'
def RC(x, y, w, h, fill, sw=2.5, rx=0, extra=''):
    s = (f' stroke-width="{sw}"' if 'stroke=' in extra else f' stroke="{OL}" stroke-width="{sw}"') if sw else ''
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"{s} {extra}/>'
def TX(x, y, s, size, fill, stroke='#fff', sw=5, font='', extra=''):
    ff = f' font-family="{font}"' if font else ''
    return f'<text x="{x:.0f}" y="{y:.0f}" font-size="{size:.0f}" fill="{fill}" font-weight="900" text-anchor="middle" stroke="{stroke}" stroke-width="{sw}" paint-order="stroke" stroke-linejoin="round"{ff} {extra}>{s}</text>'
def place(i, W0, H0, inner):
    x, y, w, h = box(i)
    if PORTRAIT:  # 圖畫依橫式格子比例繪製；直式格子改用等比縮放並置中，避免變形
        k = min(w / W0, h / H0)
        return f'<g transform="translate({x + (w - W0 * k) / 2:.1f},{y + (h - H0 * k) / 2:.1f}) scale({k:.4f})">{inner}</g>'
    return f'<g transform="translate({x},{y}) scale({w / W0:.4f},{h / H0:.4f})">{inner}</g>'
def star4(cx, cy, r, c='#fff'):
    return f'<path d="M{cx},{cy - r} Q{cx + r * .18},{cy - r * .18} {cx + r},{cy} Q{cx + r * .18},{cy + r * .18} {cx},{cy + r} Q{cx - r * .18},{cy + r * .18} {cx - r},{cy} Q{cx - r * .18},{cy - r * .18} {cx},{cy - r}z" fill="{c}"/>'
def tree(cx, cy, r, c='#3f9a3a'):
    """圓形樹冠的樹"""
    out = P(f'M{cx - 4},{cy + r * 1.6} L{cx - 3},{cy + r * .3} L{cx + 3},{cy + r * .3} L{cx + 4},{cy + r * 1.6}z', 'url(#gWood)', 2)
    for dx, dy, rr in ((-r * .5, r * .15, r * .7), (r * .5, r * .2, r * .68), (0, -r * .35, r * .8)):
        out += EL(cx + dx, cy + dy, rr, rr * .9, c, 2.2) + EL(cx + dx, cy + dy, rr, rr * .9, 'url(#gBall)', 0)
    return out

def cn_roof(rl, rr, top, xl, xr, bot, n=10, fill='url(#gRoof)', dark='#0f5426', light='#8ff0a6', tip=18, sag=12, ends='#f7d038', orn=.5):
    """中式翹簷屋頂：rl..rr 為屋脊，xl..xr 為簷口，bot 為簷口高度"""
    d = (f'M{rl},{top} L{rr},{top} C{rr + .25 * (xr - rr)},{top + .6 * (bot - top)} {xr - .3 * (xr - rr)},{bot} {xr},{bot - tip} '
         f'L{xr - 7},{bot + 3} Q{(xl + xr) / 2},{bot + 3 + 2 * sag} {xl + 7},{bot + 3} L{xl},{bot - tip} '
         f'C{xl + .3 * (rl - xl)},{bot} {rl - .25 * (rl - xl)},{top + .6 * (bot - top)} {rl},{top}z')
    out = P(d, fill, 3.5)
    ex0, ex1 = xl + 12, xr - 12
    for k in range(1, n):
        t_ = k / n
        tx_ = rl + (rr - rl) * t_
        bx = ex0 + (ex1 - ex0) * t_
        by = bot + 3 + 2 * t_ * (1 - t_) * 2 * sag - 3
        cxq = tx_ + (bx - tx_) * .55 + (bx - tx_) * .12
        out += f'<path d="M{tx_:.1f},{top + 2} Q{cxq:.1f},{top + (by - top) * .6:.1f} {bx:.1f},{by:.1f}" stroke="{dark}" stroke-width="3.2" fill="none"/>'
        out += f'<path d="M{tx_ + 3:.1f},{top + 3} Q{cxq + 3:.1f},{top + (by - top) * .6:.1f} {bx + 3.5:.1f},{by - 1:.1f}" stroke="{light}" stroke-width="1.6" fill="none" stroke-opacity=".8"/>'
        out += EL(bx, by + 1, 4.2, 3.6, ends, 1.2)
    out += f'<path d="{d}" fill="url(#gShadeH)"/>'
    # 屋脊與兩端鴟吻
    out += RC(rl - 4, top - 7, rr - rl + 8, 9, 'url(#gGold)', 2, 3)
    for sx, sgn in ((rl - 4, -1), (rr + 4, 1)):
        out += P(f'M{sx},{top - 3} q{sgn * 14 * orn},-2 {sgn * 14 * orn},{-18 * orn} q{-sgn * 8 * orn},{2 * orn} {-sgn * 6 * orn},{-10 * orn} q{sgn * 14 * orn},{2 * orn} {sgn * 14 * orn},{16 * orn} q0,{14 * orn} {-sgn * 14 * orn},{16 * orn}z', 'url(#gGold)', 1.8)
    # 簷角風鈴
    for x0 in (xl + 2, xr - 2):
        out += LN(x0, bot - tip + 2, x0, bot - tip + 12, OL, 1.5) + P(f'M{x0 - 4},{bot - tip + 18} q4,-10 8,0z', 'url(#gGold)', 1.4)
    return out

def mini_general(cx, foot, s, helm, armor, skin='url(#gSkin)', beard=None, weapon='spear', plume='#e53935', cape='#c62828', brow='angry', flagch='帥'):
    """起點卷軸上的 Q 版武將（s 為比例，foot 為腳底 y）"""
    def M(v):
        return v * s
    hy = foot - M(118)      # 頭中心
    r = M(30)
    out = EL(cx, foot + M(2), M(34), M(7), 'url(#gShadow)', 0)
    # 披風
    out += PS(f'M{cx - M(22)},{hy + M(30)} q{-M(16)},{M(40)} {-M(20)},{M(82)} q{M(42)},{M(10)} {M(84)},0 q{-M(4)},{-M(42)} {-M(20)},{-M(82)}z', cape)
    # 兵器（背後）
    if weapon == 'spear':
        out += LN(cx + M(30), foot - M(4), cx + M(30), hy - M(56), OL, M(5)) + LN(cx + M(30), foot - M(4), cx + M(30), hy - M(56), '#8a5a2b', M(3))
        out += P(f'M{cx + M(30)},{hy - M(76)} l{M(6)},{M(16)} l{-M(6)},{M(5)} l{-M(6)},{-M(5)}z', 'url(#gMetal)', 1.6)
        out += P(f'M{cx + M(26)},{hy - M(54)} q{-M(4)},{M(10)} {-M(2)},{M(16)} M{cx + M(30)},{hy - M(54)} v{M(18)} M{cx + M(34)},{hy - M(54)} q{M(4)},{M(10)} {M(2)},{M(16)}', 'none', M(2.5), '#e53935')
    elif weapon == 'guandao':
        out += LN(cx + M(30), foot - M(4), cx + M(30), hy - M(40), OL, M(5)) + LN(cx + M(30), foot - M(4), cx + M(30), hy - M(40), '#8a5a2b', M(3))
        out += P(f'M{cx + M(30)},{hy - M(36)} q{-M(26)},{-M(12)} {-M(14)},{-M(48)} q{M(8)},{M(8)} {M(14)},{M(6)} q{M(10)},{M(16)} 0,{M(42)}z', 'url(#gMetal)', 1.8)
        out += EL(cx + M(30), hy - M(36), M(5), M(3), '#1e8e3e', 1.2)
    elif weapon == 'flag':
        out += LN(cx + M(32), foot - M(4), cx + M(32), hy - M(80), OL, M(4)) + LN(cx + M(32), foot - M(4), cx + M(32), hy - M(80), '#8a5a2b', M(2.4))
        out += PS(f'M{cx + M(34)},{hy - M(78)} q{M(18)},{-M(6)} {M(34)},{M(2)} q{-M(4)},{M(16)} 0,{M(32)} q{-M(16)},{-M(8)} {-M(34)},{-M(2)}z', '#f6c90e', 'gShadeV')
        out += TX(cx + M(51), hy - M(52), flagch, M(18), '#c62828', '#fff', 0)
    # 腿與靴
    for dx in (-M(10), M(10)):
        out += RC(cx + dx - M(7), foot - M(26), M(14), M(18), '#3b3b5c', 1.8)
        out += P(f'M{cx + dx - M(8)},{foot - M(10)} h{M(14)} q{M(8)},0 {M(8)},{M(8)} v{M(2)} h{-M(22)}z', '#2b1a10', 1.8)
    # 甲裙
    out += PS(f'M{cx - M(22)},{foot - M(44)} l{-M(4)},{M(22)} h{M(52)} l{-M(4)},{-M(22)}z', armor)
    for k in range(3):
        out += LN(cx - M(23), foot - M(37) + k * M(6), cx + M(23), foot - M(37) + k * M(6), '#000', 1, 'stroke-opacity=".35"')
    # 胴甲
    out += PS(f'M{cx - M(20)},{hy + M(28)} q{-M(4)},{M(20)} {M(-2)},{M(42)} h{M(44)} q{M(2)},{-M(22)} {-M(2)},{-M(42)}z', armor)
    for k in range(4):
        y0 = hy + M(34) + k * M(8)
        out += f'<path d="M{cx - M(18)},{y0} ' + ' '.join(f'q{M(3)},{M(5)} {M(6)},0' for _ in range(6)) + '" stroke="#000" stroke-opacity=".35" stroke-width="1" fill="none"/>'
    out += EL(cx, hy + M(46), M(8), M(8), 'url(#gMetal)', 1.6) + EL(cx, hy + M(46), M(4), M(4), 'url(#gGold)', 1)
    out += RC(cx - M(22), hy + M(66), M(44), M(8), '#5d3a1a', 1.8) + EL(cx, hy + M(70), M(6), M(5), 'url(#gGold)', 1.4)
    # 肩甲與手
    for sg in (-1, 1):
        out += PS(f'M{cx + sg * M(14)},{hy + M(28)} q{sg * M(18)},{-M(4)} {sg * M(22)},{M(14)} q{-sg * M(10)},{M(4)} {-sg * M(20)},{-M(2)}z', 'url(#gGold)')
        out += P(f'M{cx + sg * M(20)},{hy + M(36)} q{sg * M(8)},{M(14)} {sg * M(10)},{M(26)}', 'none', M(9), OL) + P(f'M{cx + sg * M(20)},{hy + M(36)} q{sg * M(8)},{M(14)} {sg * M(10)},{M(26)}', 'none', M(6), armor)
        out += EL(cx + sg * M(30), hy + M(64), M(6), M(6), skin, 1.8)
    # 頭
    out += EL(cx, hy, r, r * .95, skin, 2.5)
    out += EL(cx - M(26), hy + M(6), M(5), M(7), skin, 2) + EL(cx + M(26), hy + M(6), M(5), M(7), skin, 2)
    ey = hy + M(4)
    for sg in (-1, 1):
        ex = cx + sg * M(11)
        out += EL(ex, ey, M(5.5), M(6.5), '#fff', 1.6) + EL(ex + sg * .5, ey + M(1), M(4), M(5), '#3b2314', 0) + EL(ex + sg * .5, ey + M(1.5), M(2), M(2.6), '#000', 0)
        out += EL(ex + M(1.6), ey - M(1.6), M(1.4), M(1.6), '#fff', 0)
        out += P(f'M{ex - M(6)},{ey - M(3)} q{M(6)},{-M(6)} {M(12)},0', 'none', M(2.2))
        if brow == 'angry':
            out += P(f'M{ex - sg * M(7)},{ey - M(11)} l{sg * M(12)},{M(4)}', 'none', M(3), '#2b1a10')
        else:
            out += P(f'M{ex - M(6)},{ey - M(10)} q{M(6)},{-M(4)} {M(12)},0', 'none', M(2.4), '#2b1a10')
        out += EL(cx + sg * M(19), hy + M(14), M(5), M(3), '#ff8a80', 0, extra='fill-opacity=".6"')
    out += P(f'M{cx - M(1)},{hy + M(10)} q{M(3)},{M(3)} 0,{M(5)}', 'none', 1.6, '#a0522d')
    if beard == 'long':
        out += PS(f'M{cx - M(14)},{hy + M(16)} q{-M(4)},{M(22)} {M(14)},{M(44)} q{M(18)},{-M(22)} {M(14)},{-M(44)} q{-M(14)},{M(8)} {-M(28)},0z', '#1b1b1b')
        out += P(f'M{cx - M(6)},{hy + M(28)} q{M(2)},{M(14)} {M(4)},{M(24)} M{cx + M(5)},{hy + M(28)} q0,{M(12)} {-M(2)},{M(22)}', 'none', .9, '#666')
    elif beard == 'full':
        out += PS(f'M{cx - M(26)},{hy + M(4)} q{-M(4)},{M(30)} {M(26)},{M(36)} q{M(30)},{-M(6)} {M(26)},{-M(36)} q{-M(6)},{M(10)} {-M(12)},{M(10)} q{-M(14)},{-M(6)} {-M(28)},0 q{-M(8)},0 {-M(12)},{-M(10)}z', '#1b1b1b')
        out += P(f'M{cx - M(8)},{hy + M(19)} q{M(8)},{M(4)} {M(16)},0', '#8b1a1a', 1.5)
    else:
        out += P(f'M{cx - M(7)},{hy + M(19)} q{M(7)},{M(6)} {M(14)},0', '#8b1a1a', 1.6)
    # 頭盔
    out += PS(f'M{cx - r - M(4)},{hy + M(4)} q{-M(2)},{-r - M(18)} {r + M(4)},{-r - M(18)} q{r + M(6)},0 {r + M(4)},{r + M(18)} l{-M(6)},{-M(4)} q{-r + M(4)},{-M(14)} {-2 * r + M(4)},0z', helm, 'gShadeH')
    out += RC(cx - r + M(2), hy - M(14), 2 * r - M(4), M(7), 'url(#gGold)', 1.6, 2)
    for k in range(5):
        out += EL(cx - r + M(8) + k * (2 * r - M(16)) / 4, hy - M(10.5), M(1.8), M(1.8), '#fff8c0', .8)
    out += P(f'M{cx - M(3)},{hy - r - M(14)} h{M(6)} l{-M(1)},{-M(10)} h{-M(4)}z', 'url(#gGold)', 1.4)
    out += P(f'M{cx},{hy - r - M(22)} q{-M(14)},{-M(4)} {-M(8)},{-M(22)} q{M(4)},{M(8)} {M(8)},{M(4)} q{M(4)},{M(4)} {M(8)},{-M(4)} q{M(6)},{M(18)} {-M(8)},{M(22)}z', plume, 1.6)
    return out

# 起點的三位人物取自牌面人物圖（tools/card_figures.js，需要 Node.js）；沒有 Node.js 時改畫下列簡易武將
def load_figures():
    import json, subprocess
    try:
        out = subprocess.run(['node', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'card_figures.js')], capture_output=True, check=True, timeout=60)
        return json.loads(out.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
FIGURES = load_figures()

# 簡易武將（左、右、中持帥旗者）：盔、甲、膚色、鬍鬚、兵器、盔纓、披風、眉、旗上文字
START_TRIO = {
    'sanguo': [('#2e7d32', '#2e7d32', '#e0503c', 'long', 'guandao', '#f6c90e', '#1b5e20', 'thick'),          # 關羽
               ('#1e5fbf', '#1e5fbf', 'url(#gSkin)', 'full', 'spear', '#e53935', '#0d3b8a', 'angry'),        # 張飛
               ('#c62828', '#d4a017', 'url(#gSkin)', None, 'flag', '#ffffff', '#b71c1c', 'kind', '帥')],     # 劉備
    'shuihu': [('#37474f', '#455a64', 'url(#gSkin)', 'full', 'spear', '#ffffff', '#263238', 'angry'),        # 林沖
               ('#c62828', '#c62828', '#d98a6a', 'full', 'guandao', '#f1c40f', '#7f1d1d', 'angry'),          # 秦明
               ('#1f2d5a', '#d4a017', '#c98f62', None, 'flag', '#f6c90e', '#1f2d5a', 'kind', '義')],          # 宋江
    'fengshen': [('#dfe6e9', '#90a4ae', 'url(#gSkin)', None, 'spear', '#2b5fc1', '#2b5fc1', 'thick'),        # 楊戩
                 ('#e53935', '#e53935', 'url(#gSkin)', None, 'spear', '#f1c40f', '#f1c40f', 'angry'),        # 哪吒
                 ('#2b5fc1', '#f5f0e1', 'url(#gSkin)', 'long', 'flag', '#ffffff', '#2b5fc1', 'kind', '周')], # 姜子牙
    'xiyou': [('#2c3e50', '#2c3e50', '#f4b6c2', None, 'guandao', '#f1c40f', '#1b1b1b', 'kind'),             # 豬八戒
              ('#5d6d7e', '#5d6d7e', '#a0785a', 'full', 'spear', '#c0392b', '#34495e', 'thick'),             # 沙悟淨
              ('#f1c40f', '#f1c40f', '#d9a066', None, 'flag', '#c0392b', '#c0392b', 'angry', '經')],         # 孫悟空
    'chuhan': [('#7b241c', '#7b241c', 'url(#gSkin)', 'full', 'guandao', '#f1c40f', '#3e2723', 'angry'),      # 樊噲
               ('#2b5fc1', '#2b5fc1', 'url(#gSkin)', None, 'spear', '#ffffff', '#0d3b8a', 'thick'),          # 韓信
               ('#c62828', '#d4a017', 'url(#gSkin)', 'long', 'flag', '#ffffff', '#b71c1c', 'kind', '漢')],   # 劉邦
}

# 起點城樓上兩面旗的文字
START_FLAGS = {'sanguo': '蜀吳', 'shuihu': '忠義', 'fengshen': '周商', 'xiyou': '唐佛', 'chuhan': '漢楚'}

def start(i):
    W0, H0 = 525, 610
    pts = []
    n = 44
    for k in range(n):
        a = 2 * math.pi * k / n
        rx, ry = W0 / 2 * (0.94 + 0.06 * ((k * 7) % 3) / 2), H0 / 2 * (0.94 + 0.06 * ((k * 5) % 3) / 2)
        pts.append(f'{W0/2 + rx * max(-1, min(1, 1.25 * math.cos(a))):.0f},{H0/2 + ry * max(-1, min(1, 1.25 * math.sin(a))):.0f}')
    poly = " ".join(pts)
    out = f'<polygon points="{poly}" fill="#7a4a22" transform="translate(6,8)" opacity=".35"/>'
    out += f'<polygon points="{poly}" fill="url(#gParch)" stroke="{OL}" stroke-width="7" stroke-linejoin="round"/>'
    out += f'<polygon points="{poly}" fill="none" stroke="#b07a33" stroke-width="3" transform="translate({W0*.03:.1f},{H0*.03:.1f}) scale(.94)" stroke-dasharray="14 6 3 6" stroke-opacity=".6"/>'
    for (sx, sy, rr) in ((470, 80, 22), (80, 560, 26), (450, 560, 16)):
        out += EL(sx, sy, rr, rr * .7, '#b07a33', 0, extra='fill-opacity=".15"')
    # 標題帶
    bx, bw = W0 * 0.06, W0 * 0.2
    ty, th = H0 * .07, H0 * .86
    out += RC(bx + 5, ty + 6, bw, th, '#000', 0, 6, 'fill-opacity=".2"')
    out += RC(bx, ty, bw, th, '#ef8fbd', 3, 6) + RC(bx, ty, bw * .35, th, '#7aa7e0', 0) + RC(bx, ty, bw, th, 'url(#pCloud)', 0) + RC(bx, ty, bw, th, 'url(#gShadeH)', 0, 6)
    out += RC(bx, ty, bw, th, 'none', 3, 6) + LN(bx + bw * .35, ty, bx + bw * .35, ty + th, '#fff', 2, 'stroke-opacity=".6"')
    for yy in (ty + 10, ty + th - 10):
        out += LN(bx + 6, yy, bx + bw - 6, yy, '#f6c90e', 3)
    for k, ch in enumerate(paren(nm(i))):
        out += TX(bx + bw / 2 + 3, H0 * 0.2 + k * H0 * 0.16 + 3, ch, bw * 0.75, '#7a1f45', '#7a1f45', 4, extra='fill-opacity=".5" stroke-opacity=".5"')
        out += TX(bx + bw / 2, H0 * 0.2 + k * H0 * 0.16, ch, bw * 0.75, 'url(#gGoldText)', '#b03060', 5)
    # 畫面
    X0, Y0, X1, Y1 = 152, 50, 438, 560
    sc = f'<clipPath id="cpStart"><rect x="{X0}" y="{Y0}" width="{X1 - X0}" height="{Y1 - Y0}" rx="12"/></clipPath>'
    s = RC(X0, Y0, X1 - X0, Y1 - Y0, 'url(#gSky)', 0)
    s += EL(392, 112, 58, 58, 'url(#gSun)', 0)
    for a in range(0, 360, 30):
        r_ = math.radians(a)
        s += LN(392 + 40 * math.cos(r_), 112 + 40 * math.sin(r_), 392 + 54 * math.cos(r_), 112 + 54 * math.sin(r_), '#ffb300', 3, 'stroke-opacity=".7"')
    for (cx, cy, k) in ((215, 90, 1), (330, 170, .8), (190, 190, .6)):
        s += P(f'M{cx - 34 * k},{cy + 8 * k} q-6,-16 12,-16 q4,-16 22,-12 q10,-14 26,-2 q18,-4 18,14 q12,4 4,16z', '#fff', 2, '#6b8fd1')
        s += P(f'M{cx - 10 * k},{cy + 2 * k} q6,-8 12,0 M{cx + 14 * k},{cy - 4 * k} q6,-8 12,0', 'none', 1.5, '#6b8fd1')
    s += P('M150,262 L190,206 L222,236 L262,190 L300,232 L340,198 L384,240 L420,204 L440,226 V270 H150z', 'url(#gMount)', 0)
    s += P('M150,270 L176,236 L206,256 L236,226 L276,262 V280 H150z M330,270 L372,232 L404,258 L440,236 V280 H330z', '#7f9fcf', 0, extra='fill-opacity=".7"')
    # 地面與道路
    s += RC(X0, 352, X1 - X0, Y1 - 352, 'url(#gGrass)', 0)
    s += P('M276,360 L316,360 Q340,450 400,560 L190,560 Q252,450 276,360z', '#e8cf95', 0)
    s += P('M276,360 Q252,450 190,560 M316,360 Q340,450 400,560', 'none', 2, '#b9955a')
    for gx, gy in ((170, 380), (420, 400), (175, 470), (430, 500), (240, 400), (360, 420)):
        s += P(f'M{gx - 6},{gy} q2,-10 4,-12 M{gx},{gy} v-14 M{gx + 6},{gy} q-2,-10 -4,-12', 'none', 2, '#2e7d32')
    # 城牆
    s += RC(X0 - 2, 262, X1 - X0 + 4, 98, 'url(#gWall)', 3) + RC(X0 - 2, 262, X1 - X0 + 4, 98, 'url(#pBrick)', 0)
    for k in range(11):
        s += RC(X0 + 2 + k * 27, 248, 16, 16, 'url(#gWall)', 2.5)
    s += RC(X0 - 2, 262, X1 - X0 + 4, 8, '#8d5524', 2)
    s += P('M262,360 V318 Q296,280 330,318 V360z', '#3a2410', 3)
    s += P('M266,360 V320 Q296,288 326,320 V360z', 'url(#gWood)', 2) + LN(296, 300, 296, 360, OL, 2)
    for yy in (326, 340, 354):
        for xx in (276, 286, 306, 316):
            s += EL(xx, yy, 2.2, 2.2, 'url(#gGold)', .8)
    s += P('M256,360 V316 Q296,270 336,316 V360', 'none', 6, '#f2d9a6') + P('M256,360 V316 Q296,270 336,316 V360', 'none', 1.5)
    # 城樓
    s += RC(222, 236, 148, 14, '#7a4a22', 2.5)
    for xx in range(226, 368, 10):
        s += LN(xx, 226, xx, 238, '#c62828', 2)
    s += LN(222, 226, 370, 226, '#c62828', 3)
    for xx in (236, 266, 322, 352):
        s += RC(xx - 5, 196, 10, 40, 'url(#gPillar)', 2)
    s += RC(254, 202, 84, 30, 'url(#gWarm)', 2) + RC(254, 202, 84, 30, 'url(#pLattice)', 0)
    s += cn_roof(244, 348, 172, 202, 390, 204, 9, 'url(#gRoofB)', '#13306b', '#a8d8ff', 14, 6)
    s += RC(258, 140, 76, 34, 'url(#gPillar)', 2) + RC(272, 150, 48, 16, '#1d3a7a', 1.5, 0, 'stroke="#f6c90e"')
    s += TX(296, 163, '風雲', 12, '#ffe14d', '#000', 0)
    s += cn_roof(256, 336, 110, 226, 366, 140, 7, 'url(#gRoofB)', '#13306b', '#a8d8ff', 12, 5)
    s += EL(296, 98, 6, 6, 'url(#gGold)', 2) + LN(296, 92, 296, 84, OL, 2) + EL(296, 82, 3, 3, '#e53935', 1)
    # 旗幟
    for (fx, c, ch) in ((170, '#2e7d32', START_FLAGS.get(THEME, '蜀吳')[0]), (420, '#1e5fbf', START_FLAGS.get(THEME, '蜀吳')[1])):
        top_ = 170 if fx != 212 else 190
        s += LN(fx, 262, fx, top_, OL, 4) + LN(fx, 262, fx, top_, '#8a5a2b', 2.2) + EL(fx, top_ - 2, 3, 3, 'url(#gGold)', 1.2)
        dirn = 1 if fx < 400 else -1
        d = f'M{fx},{top_ + 2} q{dirn * 14},-6 {dirn * 30},2 q{dirn * -4},14 0,28 q{dirn * -16},-6 {dirn * -30},0z'
        s += PS(d, c, 'gShadeV', 2.2) + P(f'M{fx},{top_ + 2} q{dirn * 14},-6 {dirn * 30},2', 'none', 3, '#f6c90e')
        s += TX(fx + dirn * 15, top_ + 22, ch, 15, '#fff', '#000', 0)
    # 三位武將
    figs = FIGURES['themes'].get(THEME) if FIGURES else None
    for k, ((gx, gfoot, gs), g) in enumerate(zip(((208, 548, .95), (382, 548, .95), (296, 556, 1.08)), START_TRIO.get(THEME, START_TRIO['sanguo']))):
        if figs:   # 用牌面人物（與該主題牌上的模樣一致）
            kk = .6 * gs
            s += f'<g transform="translate({gx - 125 * kk:.1f},{gfoot - figs[k]["fy"] * kk:.1f}) scale({kk:.3f})">{figs[k]["svg"]}</g>'
        else:
            s += mini_general(gx, gfoot, gs, *g)
    out += sc + f'<g clip-path="url(#cpStart)">{s}</g>'
    out += RC(X0, Y0, X1 - X0, Y1 - Y0, 'none', 4, 12) + RC(X0 + 5, Y0 + 5, X1 - X0 - 10, Y1 - Y0 - 10, 'none', 2, 9, 'stroke="#c28a2c"')
    # 由此前進
    for k, ch in enumerate('由此前進'):
        out += TX(W0 * 0.885, H0 * 0.6 + k * H0 * 0.08, ch, H0 * 0.07, '#1a3c8f', '#fff', 6)
    out += P(f'M{W0*.885 - 14},{H0*.92} l14,16 l14,-16z', '#e8452c', 2.5)
    return place(i, W0, H0, out)

def park(i):
    W0, H0 = 420, 385
    o = EL(230, 345, 200, 40, 'url(#gGround)', 0)
    o += P('M300,330 Q285,350 260,385 L330,385 Q318,350 316,330z', '#f3dfae', 0)
    # 摩天輪
    cx, cy, R = 130, 128, 86
    o += EL(135, 318, 70, 10, 'url(#gShadow)', 0)
    for x2 in (78, 186):
        o += LN(cx, cy, x2, 314, '#8e1b1b', 10) + LN(cx, cy, x2, 314, '#f1f1f1', 6) + LN(cx, cy, x2, 314, '#e53935', 6, 'stroke-dasharray="10 10"')
    for yy, half in ((220, 36), (270, 48)):
        o += LN(cx - half * 1.0, yy, cx + half * 1.05, yy, '#8e1b1b', 4)
    o += RC(64, 310, 136, 10, '#8d6e63', 2.5, 3)
    o += f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="#e9f6ff" fill-opacity=".35" stroke="#1e5fa8" stroke-width="9"/>'
    o += f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="#8fd0ff" stroke-width="4"/>'
    o += f'<circle cx="{cx}" cy="{cy}" r="{R - 14}" fill="none" stroke="#1e5fa8" stroke-width="3"/>'
    zz = ''
    for k in range(24):
        a = math.pi * 2 * k / 24
        rr = R if k % 2 == 0 else R - 14
        zz += ('M' if k == 0 else 'L') + f'{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}'
    o += P(zz + 'z', 'none', 1.5, '#5aa7e0')
    for k in range(12):
        a = math.pi * 2 * k / 12
        o += LN(cx, cy, cx + R * math.cos(a), cy + R * math.sin(a), '#1e5fa8', 2.2)
    for k in range(24):
        a = math.pi * 2 * (k + .5) / 24
        bx_, by_ = cx + R * math.cos(a), cy + R * math.sin(a)
        o += EL(bx_, by_, 6, 6, 'url(#gGlow)', 0) + EL(bx_, by_, 2.6, 2.6, '#fff59d', 0)
    o += EL(cx, cy, 13, 13, 'url(#gGold)', 2.5) + EL(cx, cy, 5, 5, '#8e1b1b', 1.5)
    cols = ['#e53935', '#fdd835', '#43a047', '#1e88e5', '#8e24aa', '#fb8c00']
    for k in range(12):
        a = math.pi * 2 * k / 12 - math.pi / 2
        px, py = cx + R * math.cos(a), cy + R * math.sin(a)
        c = cols[k % 6]
        o += LN(px, py, px, py + 7, OL, 1.8)
        o += PS(f'M{px - 11},{py + 7} h22 v9 q0,9 -11,9 q-11,0 -11,-9z', c, 'gShadeH', 2)
        o += P(f'M{px - 13},{py + 8} q13,-9 26,0z', c, 2) + RC(px - 7, py + 10, 14, 6, '#d6f1ff', 1.2, 1.5)
        o += EL(px - 3, py + 14, 2, 2.2, '#f8d2ad', 0) + EL(px + 3, py + 14, 2, 2.2, '#f8d2ad', 0)
    # 氣球
    for (bx_, by_, c) in ((236, 46, '#e53935'), (254, 30, '#fdd835'), (268, 54, '#1e88e5'), (248, 66, '#43a047')):
        o += P(f'M{bx_},{by_ + 14} q-6,30 4,60', 'none', 1.2, '#555')
        o += EL(bx_, by_, 11, 14, c, 2) + EL(bx_, by_, 11, 14, 'url(#gBall)', 0) + P(f'M{bx_ - 3},{by_ + 16} h6 l-3,-3z', c, 1.2)
    # 馬戲大帳篷
    ax, ay = 322, 30
    tent = f'M{ax},{ay} Q{ax - 40},{ay + 70} {ax - 100},{ay + 124} L{ax + 92},{ay + 124} Q{ax + 40},{ay + 70} {ax},{ay}z'
    o += f'<clipPath id="cpTent"><path d="{tent}"/></clipPath>'
    stripes = ''
    for k in range(9):
        x0 = ax - 100 + k * 192 / 9
        stripes += f'<path d="M{ax},{ay} L{x0:.1f},{ay + 130} L{x0 + 192 / 9:.1f},{ay + 130}z" fill="{["#e53935", "#fff3d6"][k % 2]}"/>'
    o += f'<g clip-path="url(#cpTent)">{stripes}<path d="{tent}" fill="url(#gShadeH)"/></g>' + P(tent, 'none', 3)
    # 帳篷牆
    o += PS(f'M{ax - 92},{ay + 124} h184 v68 h-184z', '#ffd54f', 'gShadeH', 2.5)
    for k in range(0, 10, 2):
        o += RC(ax - 92 + k * 18.4, ay + 124, 18.4, 68, '#e53935', 0)
    o += RC(ax - 92, ay + 124, 184, 68, 'url(#gShadeH)', 2.5)
    # 垂簾花邊
    for k in range(10):
        x0 = ax - 100 + k * 19.2
        o += P(f'M{x0:.1f},{ay + 124} q9.6,16 19.2,0z', ['#1e88e5', '#fdd835'][k % 2], 1.8)
    o += LN(ax, ay, ax, ay - 22, OL, 3) + EL(ax, ay - 22, 3.5, 3.5, 'url(#gGold)', 1.2)
    o += PS(f'M{ax},{ay - 22} q12,-6 26,0 q-6,6 -2,12 q-12,-6 -24,0z', '#1e5fbf', 'gShadeV', 1.8)
    # 城堡
    o += EL(300, 330, 112, 12, 'url(#gShadow)', 0)
    o += PS('M196,248 h208 v80 h-208z', 'url(#gStone)', 'gShadeH', 3) + RC(196, 248, 208, 80, 'url(#pStoneW)', 0)
    for k in range(10):
        o += RC(198 + k * 21, 238, 13, 12, 'url(#gStone)', 2)
    o += P('M282,328 V292 Q300,268 318,292 V328z', '#3a2410', 3)
    o += P('M286,328 V294 Q300,276 314,294 V328z', 'url(#gWood)', 1.5)
    for xx in (291, 300, 309):
        o += LN(xx, 282, xx, 328, '#ddd', 1.5)
    for yy in (300, 312):
        o += LN(286, yy, 314, yy, '#ddd', 1.5)
    o += P('M278,328 V292 Q300,262 322,292 V328', 'none', 5, '#e8d6ae') + P('M278,328 V292 Q300,262 322,292 V328', 'none', 1.2)
    # 中央主塔與洋蔥頂
    o += PS('M268,250 V170 h64 V250z', 'url(#gStone)', 'gShadeH', 3) + RC(268, 170, 64, 80, 'url(#pStoneW)', 0)
    o += P('M264,172 Q260,140 300,112 Q340,140 336,172z', '#8e44ad', 3) + P('M264,172 Q260,140 300,112 Q340,140 336,172z', 'url(#gShadeH)', 0)
    for dx in (-22, -8, 8, 22):
        o += P(f'M{300 + dx * .3},{116} Q{300 + dx * .9},{140} {300 + dx},{170}', 'none', 1.5, '#f6c90e')
    o += LN(300, 112, 300, 94, OL, 2.5) + EL(300, 102, 4, 4, 'url(#gGold)', 1.2) + PS('M300,94 q10,-4 18,2 q-8,4 -18,6z', '#e53935', 'gShadeV', 1.5)
    for wx, wy in ((288, 196), (312, 196), (300, 226)):
        o += P(f'M{wx - 6},{wy + 12} V{wy} q6,-8 12,0 V{wy + 12}z', 'url(#gWarm)', 2) + LN(wx, wy - 4, wx, wy + 12, '#7a2a0c', 1)
    # 兩側圓塔
    for (tx_, tw, top_, c) in ((216, 34, 196, '#1e88e5'), (384, 34, 200, '#e84393'), (250, 26, 222, '#fdd835'), (352, 26, 222, '#43a047')):
        o += PS(f'M{tx_ - tw / 2},{328} V{top_} h{tw} V328z', 'url(#gStone)', 'gShadeH', 2.5) + RC(tx_ - tw / 2, top_, tw, 328 - top_, 'url(#pStoneW)', 0)
        o += P(f'M{tx_ - tw / 2 - 5},{top_ + 2} L{tx_},{top_ - tw * 1.8} L{tx_ + tw / 2 + 5},{top_ + 2}z', c, 2.5)
        o += P(f'M{tx_ - tw / 2 - 5},{top_ + 2} L{tx_},{top_ - tw * 1.8} L{tx_ + tw / 2 + 5},{top_ + 2}z', 'url(#gShadeH)', 0)
        o += P(f'M{tx_ - tw / 2 - 5},{top_ + 2} q{tw / 2 + 5},8 {tw + 10},0', 'none', 2, '#fff', 'stroke-opacity=".7"')
        o += LN(tx_, top_ - tw * 1.8, tx_, top_ - tw * 1.8 - 14, OL, 2) + P(f'M{tx_},{top_ - tw * 1.8 - 14} l12,4 l-12,4z', '#e53935', 1.2)
        o += P(f'M{tx_ - 5},{top_ + 30} V{top_ + 20} q5,-7 10,0 V{top_ + 30}z', 'url(#gWarm)', 1.8)
    # 小樹叢與遊客
    o += tree(398, 300, 12, '#43a047') + tree(186, 310, 10, '#2e7d32')
    for (px, c, hc) in ((262, '#e53935', '#3b2314'), (338, '#1e88e5', '#f1c40f')):
        o += EL(px, 360, 9, 3, 'url(#gShadow)', 0)
        o += P(f'M{px - 6},{358} l2,-16 h8 l2,16z', c, 1.8) + EL(px, 336, 6, 6, 'url(#gSkin)', 1.6) + P(f'M{px - 6},{335} q6,-10 12,0z', hc, 1.2)
    o += P('M276,326 q-4,-20 4,-32', 'none', 1, '#555') + EL(280, 290, 5, 6, '#e84393', 1.2)
    # 名稱
    for k, ch in enumerate(nm(i) if not MOBILE else ''):
        o += TX(W0 * 0.07, H0 * (0.6 + k * 0.1), ch, H0 * 0.09, '#1f5fbf', '#fff', 6)
    return place(i, W0, H0, o)

def parlor(i):
    W0, H0 = 490, 405
    o = EL(245, 398, 240, 10, 'url(#gShadow)', 0)
    # 吊鏈
    for xx in (130, 360):
        o += LN(xx, 70, xx, 112, '#555', 2, 'stroke-dasharray="4 2"')
    # 招牌
    o += RC(56, 18, 378, 56, 'url(#gSign)', 4, 28) + RC(64, 25, 362, 42, 'none', 2.5, 21, 'stroke="#f6c90e"')
    o += RC(56, 18, 378, 28, '#fff', 0, 28, 'fill-opacity=".18"')
    bulbs = ['#ff5252', '#ffeb3b', '#69f0ae', '#40c4ff', '#ff80ab']
    for k in range(15):
        bx_ = 80 + k * 23.6
        for by_ in (18, 74):
            c = bulbs[(k + (by_ > 50)) % 5]
            o += EL(bx_, by_, 9, 9, 'url(#gGlow)', 0) + EL(bx_, by_, 4.5, 4.5, c, 1.2) + EL(bx_ - 1.4, by_ - 1.4, 1.4, 1.4, '#fff', 0)
    for by_ in (32, 46, 60):
        for bx_ in (56, 434):
            o += EL(bx_, by_, 4, 4, bulbs[by_ % 5], 1.2)
    _pn = nm(i); _ps = min(33, 165 / max(1, len(_pn)))
    if not MOBILE:
        o += TX(245, 58, _pn, _ps, '#fff', '#c0392b', 6)
        o += TX(245, 58, _pn, _ps, '#fff', '#fff', 0)
    # 屋脊寶珠
    o += P('M245,78 q-12,10 -6,22 q-10,-2 -14,8 q10,0 12,6 q8,8 16,0 q2,-6 12,-6 q-4,-10 -14,-8 q6,-12 -6,-22z', 'url(#gFireP)', 1.5)
    o += EL(245, 102, 17, 17, 'url(#gLantern)', 2.5) + EL(245, 102, 13, 13, 'none', 1.5, '#f6c90e')
    o += TX(245, 110, '純', 20, '#ffeb3b', '#7a0000', 2)
    # 上層屋頂
    o += cn_roof(150, 340, 124, 66, 424, 178, 11, 'url(#gRoof)', '#0f5426', '#8ff0a6', 22, 10)
    o += P('M100,182 Q245,198 390,182 L384,196 Q245,210 106,196z', '#1d3a7a', 2.5)
    for k in range(14):
        xx = 116 + k * 19.6
        o += RC(xx - 5, 186 + 3 * math.sin(k / 13 * math.pi), 10, 8, ['#e53935', '#f6c90e'][k % 2], 1)
    o += RC(134, 196, 222, 22, 'url(#gPillar)', 2.5) + RC(150, 199, 190, 16, 'url(#gWarm)', 1.5) + RC(150, 199, 190, 16, 'url(#pLattice)', 0)
    # 下層屋頂
    o += cn_roof(104, 386, 210, 6, 484, 262, 15, 'url(#gRoof)', '#0f5426', '#8ff0a6', 24, 12)
    # 彩繪樑枋
    o += P('M40,268 Q245,292 450,268 L450,288 Q245,310 40,288z', 'url(#gRoofB)', 2.5)
    for k in range(13):
        t_ = (k + .5) / 13
        xx = 40 + 410 * t_
        yy = 268 + 2 * t_ * (1 - t_) * 24 + 9
        o += P(f'M{xx - 10},{yy} l10,-7 l10,7 l-10,7z', '#f6c90e', 1) + EL(xx, yy, 3, 3, '#e53935', 0)
    # 柱
    pil = ((70, 'url(#pBarber)'), (165, 'url(#gPillar)'), (325, 'url(#gPillar)'), (420, 'url(#pBarber)'))
    # 門內暖光
    o += RC(178, 296, 134, 64, 'url(#gWarm)', 2.5)
    for k in range(9):
        xx = 186 + k * 15
        o += f'<path d="M{xx},{298} V{340 + (k % 3) * 6}" stroke="#ff80ab" stroke-width="2" stroke-dasharray="2 4" stroke-linecap="round"/>'
        o += EL(xx, 342 + (k % 3) * 6, 2.5, 2.5, '#f6c90e', 0)
    o += P('M178,296 h22 v64 h-22z M290,296 h22 v64 h-22z', '#a3221c', 2) + P('M182,300 h14 v56 h-14z M294,300 h14 v56 h-14z', 'url(#pLattice)', 1)
    for wx in (86, 340):
        o += RC(wx, 304, 64, 46, 'url(#gWarm)', 2.5) + RC(wx, 304, 64, 46, 'url(#pLattice)', 0) + RC(wx - 3, 301, 70, 52, 'none', 3.5, 0, 'stroke="#7a1d12"')
    for px, fill in pil:
        o += EL(px, 362, 18, 7, 'url(#gMarble)', 2)
        o += RC(px - 13, 288, 26, 72, fill, 2.5) + RC(px - 13, 288, 26, 72, 'url(#gShadeH)', 0)
        o += RC(px - 15, 286, 30, 8, 'url(#gGold)', 2) + RC(px - 15, 352, 30, 7, 'url(#gGold)', 2)
    # 燈籠
    for lx in (118, 372):
        o += LN(lx, 290, lx, 304, OL, 1.5)
        o += EL(lx, 324, 34, 34, 'url(#gGlow)', 0)
        o += RC(lx - 8, 302, 16, 5, 'url(#gGold)', 1.4) + EL(lx, 322, 15, 16, 'url(#gLantern)', 2.2)
        for dx in (-8, 0, 8):
            o += P(f'M{lx + dx * .5},{307} Q{lx + dx * 1.4},{322} {lx + dx * .5},{337}', 'none', 1, '#7a0000')
        o += RC(lx - 8, 336, 16, 5, 'url(#gGold)', 1.4) + P(f'M{lx - 4},{341} q-2,10 0,16 M{lx},{341} v18 M{lx + 4},{341} q2,10 0,16', 'none', 2, '#f6c90e')
        o += TX(lx, 328, '福', 13, '#ffe14d', '#000', 0)
    # 台階
    for (x0, y0, w_) in ((24, 362, 442), (12, 374, 466), (0, 386, 490)):
        o += RC(x0, y0, w_, 13, 'url(#gMarble)', 2.5) + LN(x0 + 4, y0 + 3, x0 + w_ - 4, y0 + 3, '#fff', 1.5)
    return place(i, W0, H0, o)

def island(i):
    W0, H0 = 300, 393
    # 羊皮紙藏寶圖
    sheet = 'M18,30 Q60,40 150,30 Q240,22 284,32 Q276,120 286,200 Q276,290 284,364 Q200,354 150,366 Q80,374 16,362 Q26,280 14,200 Q26,110 18,30z'
    o = P(sheet, '#7a4a22', 0, extra='transform="translate(5,6)" fill-opacity=".35"')
    o += P(sheet, 'url(#gParch)', 4, '#8b3a1a')
    o += P(sheet, 'none', 10, '#c27a3a', 'stroke-opacity=".25"')
    sea = 'M32,52 Q90,60 150,50 Q220,44 268,54 Q262,130 270,200 Q262,280 268,344 Q200,338 150,348 Q90,354 32,344 Q40,270 30,200 Q40,120 32,52z'
    o += P(sea, 'url(#gSea)', 2.5, '#1a4f7a') + P(sea, 'url(#pWave)', 0)
    # 捲軸兩端
    for yy in (18, 362):
        o += RC(4, yy, 292, 22, 'url(#gWoodV)', 3, 11) + RC(4, yy + 3, 292, 6, '#fff', 0, 3, 'fill-opacity=".25"')
        o += EL(4, yy + 11, 7, 11, '#5a3415', 2.5) + EL(296, yy + 11, 7, 11, '#5a3415', 2.5)
    # 海盜船
    o += P('M40,96 h62 q-4,16 -28,18 h-10 q-20,-2 -24,-18z', 'url(#gWood)', 2.2)
    o += LN(72, 96, 72, 48, OL, 2.5)
    o += P('M74,52 q18,10 0,38z', '#f5f0e0', 2) + P('M70,56 q-20,10 0,34z', '#f5f0e0', 2)
    o += P('M72,48 l14,4 l-14,4z', '#111', 1)
    o += EL(78, 70, 4, 4, '#111', 0) + LN(75, 76, 81, 78, '#111', 1.4)
    o += P('M36,114 q12,-6 24,0 t24,0 t24,0', 'none', 2, '#fff', 'stroke-opacity=".8"')
    # 海鷗
    o += P('M140,74 q5,-6 10,0 q5,-6 10,0 M176,94 q4,-5 8,0 q4,-5 8,0', 'none', 2)
    # 島
    isl = 'M28,284 Q36,232 96,226 Q172,214 208,252 Q232,292 184,316 Q122,336 62,322 Q22,308 28,284z'
    o += P(isl, 'none', 10, '#e8fbff', 'stroke-opacity=".8"') + P(isl, 'url(#gSand)', 2.5)
    o += P('M48,262 q20,-26 54,-26 q-24,8 -36,30z', '#5cb85c', 1.5) + P('M150,236 q30,0 44,22 q-20,-10 -40,-6z', '#5cb85c', 1.5)
    for (sx, sy) in ((70, 300), (178, 296), (120, 316), (190, 272)):
        o += EL(sx, sy, 6, 3.5, '#b5894a', 0, extra='fill-opacity=".6"')
    # 寶藏路線與 X
    o += P('M140,300 q30,8 50,-2 q16,-6 22,4', 'none', 2.5, '#c0392b', 'stroke-dasharray="5 4"')
    o += P('M206,296 l12,12 M218,296 l-12,12', 'none', 4.5, '#c0392b')
    # 椰子樹
    o += P('M50,300 Q40,240 60,170 L68,172 Q52,240 60,300z', 'url(#gWood)', 2)
    for k in range(7):
        yy = 290 - k * 18
        o += P(f'M{47 + k * 1.5},{yy} q6,4 12,0', 'none', 1.2, '#3e2108')
    for (ex, ey) in ((14, 150), (20, 196), (104, 148), (110, 192), (60, 122), (30, 132), (94, 128)):
        mx, my = (64 + ex) / 2, (170 + ey) / 2 - 12
        o += P(f'M64,170 Q{mx},{my - 8} {ex},{ey} Q{mx + 4},{my + 8} 64,170z', '#3aa655', 2) + P(f'M64,170 Q{mx},{my - 2} {ex},{ey}', 'none', 1, '#1b5e20')
    o += EL(60, 176, 6, 6, '#6d4c2f', 1.6) + EL(70, 178, 6, 6, '#6d4c2f', 1.6) + EL(65, 184, 6, 6, '#5a3d22', 1.6)
    # 海盜
    cx, hy = 156, 146
    o += EL(cx, 268, 30, 6, 'url(#gShadow)', 0)
    for dx in (-10, 10):
        o += RC(cx + dx - 7, 232, 14, 30, '#3b2a5a', 2)
    o += P(f'M{cx - 18},260 h16 q4,0 4,6 h-22z M{cx + 3},260 h16 q6,0 6,6 h-22z', '#2b1a10', 2)
    o += P(f'M{cx - 22},176 h44 l4,60 h-52z', '#fff', 2.5)
    for k in range(5):
        o += RC(cx - 22 - (k > 2), 182 + k * 11, 44 + 2 * (k > 2), 5, '#c62828', 0)
    o += P(f'M{cx - 22},176 h44 l4,60 h-52z', 'url(#gShadeH)', 2.5)
    o += P(f'M{cx - 24},176 l10,0 l-4,60 h-10z M{cx + 24},176 l-10,0 l4,60 h10z', '#3b2a5a', 2)
    o += RC(cx - 26, 222, 52, 8, '#2b1a10', 2) + RC(cx - 6, 220, 12, 12, 'url(#gGold)', 2)
    # 手：右手扠腰，左手舉刀
    o += P(f'M{cx + 22},182 q16,10 10,32 l-8,2', 'none', 9, OL) + P(f'M{cx + 22},182 q16,10 10,32 l-8,2', 'none', 6, '#fff')
    o += EL(cx + 26, 216, 6, 6, 'url(#gSkin)', 1.8)
    o += P(f'M{cx - 22},182 q-16,-6 -20,-24', 'none', 9, OL) + P(f'M{cx - 22},182 q-16,-6 -20,-24', 'none', 6, '#fff')
    o += P(f'M{cx - 46},154 q-6,-36 18,-66 q-2,30 -10,64z', 'url(#gMetal)', 2) + RC(cx - 54, 152, 20, 5, 'url(#gGold)', 1.6)
    o += P(f'M{cx - 46},157 q-4,6 2,10', 'none', 3, '#8b6914')
    o += EL(cx - 42, 160, 6, 6, 'url(#gSkin)', 1.8)
    # 頭
    o += EL(cx, hy, 28, 27, 'url(#gSkin)', 2.5)
    o += PS(f'M{cx - 24},{hy + 6} q-2,26 24,30 q26,-4 24,-30 q-8,8 -12,8 q-12,-6 -24,0 q-6,0 -12,-8z', '#2b1a10')
    o += P(f'M{cx - 8},{hy + 18} q8,5 16,0', '#8b1a1a', 1.5)
    o += P(f'M{cx - 12},{hy + 13} q12,-6 24,0 q-12,2 -24,0z', '#2b1a10', 1.2)
    o += EL(cx + 10, hy, 4.5, 5.5, '#fff', 1.4) + EL(cx + 10.5, hy + 1, 2.5, 3, '#111', 0) + EL(cx + 11.5, hy - .5, 1, 1, '#fff', 0)
    o += P(f'M{cx + 4},{hy - 9} l12,-3', 'none', 3)
    o += EL(cx - 10, hy, 7, 6.5, '#111', 1) + LN(cx - 27, hy - 12, cx + 26, hy - 4, '#111', 2)
    o += P(f'M{cx - 2},{hy + 5} q4,3 0,6', 'none', 1.8, '#a0522d')
    o += EL(cx + 27, hy + 10, 3, 3, 'none', 1.8, '#f6c90e')
    o += PS(f'M{cx - 30},{hy - 4} q0,-30 30,-30 q30,0 30,30 q-30,-12 -60,0z', '#c62828')
    for (dx, dy) in ((-14, -16), (0, -22), (14, -16), (-4, -10), (10, -8)):
        o += EL(cx + dx, hy + dy, 2.2, 2.2, '#fff', 0)
    o += P(f'M{cx + 26},{hy - 8} q14,0 18,14 q-8,-2 -12,4 q-2,-10 -6,-18z', '#c62828', 2)
    # 寶箱
    o += P('M78,262 L84,232 Q112,222 140,232 L146,262z', '#5a3415', 2.5)
    o += P('M84,262 Q112,236 142,262z', '#f6c90e', 0)
    for k in range(14):
        ccx = 84 + (k % 7) * 9.5 + (k // 7) * 4
        ccy = 258 - (k // 7) * 8 - abs(3 - k % 7) * -1.5
        o += EL(ccx, ccy, 6, 4, 'url(#gGold)', 1.2)
    o += P('M96,246 l5,-6 l5,6 l-5,6z', '#e53935', 1.2) + P('M118,244 l4,-5 l4,5 l-4,5z', '#1e88e5', 1.2) + EL(110, 238, 3.5, 3.5, '#43a047', 1.2)
    o += PS('M76,262 h72 v34 h-72z', 'url(#gWoodV)', 'gShadeH', 2.5) + RC(76, 262, 72, 34, 'url(#pGrain)', 0)
    o += RC(74, 260, 76, 7, 'url(#gGold)', 2) + RC(92, 262, 8, 34, 'url(#gGold)', 1.5) + RC(124, 262, 8, 34, 'url(#gGold)', 1.5)
    o += RC(106, 268, 12, 12, 'url(#gGold)', 1.6) + EL(112, 275, 1.6, 2.4, '#111', 0)
    o += P('M80,268 q16,18 36,12 q18,-4 28,6', 'none', 2.2, '#fff')
    for k in range(6):
        o += EL(84 + k * 11, 270 + [0, 6, 10, 10, 8, 5][k] + 2, 2.4, 2.4, '#fffde7', .8)
    for k in range(4):
        o += EL(70 + k * 26, 302 - (k % 2) * 4, 5.5, 3.5, 'url(#gGold)', 1.2)
    o += star4(84, 226, 8) + star4(144, 236, 6) + star4(110, 214, 5, '#fff59d')
    # 羅盤
    o += EL(246, 330, 19, 19, '#f6e2a8', 2) + EL(246, 330, 14, 14, 'none', 1, '#8b3a1a')
    o += P('M246,312 l4,14 l-4,4 l-4,-4z', '#c0392b', 1) + P('M246,348 l4,-14 l-4,-4 l-4,4z', '#333', 1)
    o += P('M228,330 l14,-4 l4,4 l-4,4z M264,330 l-14,-4 l-4,4 l4,4z', '#8b6914', 1)
    o += TX(246, 310, '北', 9, '#8b3a1a', '#fff', 0)
    # 名稱
    _in = nm(i) if not MOBILE else ''; _step = min(0.2, 0.74 / max(1, len(_in))); _top = 0.5 - _step * (len(_in) - 1) / 2
    for k, ch in enumerate(_in):
        o += TX(W0 * 0.82, H0 * (_top + k * _step), ch, H0 * 0.17, 'url(#gGoldText)', '#7a3a0a', 7)
        o += TX(W0 * 0.82, H0 * (_top + k * _step), ch, H0 * 0.17, 'url(#gGoldText)', '#fff3b0', 1.5)
    return place(i, W0, H0, o)

def cottage(i):
    W0, H0 = 350, 320
    o = EL(175, 286, 172, 30, 'url(#gGround)', 0)
    # 竹林
    for (bx_, top_, wd) in ((14, 40, 9), (30, 70, 8), (46, 30, 10), (334, 60, 9), (320, 95, 7)):
        o += RC(bx_ - wd / 2, top_, wd, 285 - top_, 'url(#gBamboo)', 1.6, 3)
        for yy in range(top_ + 24, 280, 30):
            o += LN(bx_ - wd / 2, yy, bx_ + wd / 2, yy, '#1b5e20', 2)
    for (lx, ly, a) in ((14, 46, -30), (24, 40, 20), (46, 34, -40), (52, 40, 30), (34, 76, -20), (40, 70, 35), (60, 90, 25), (334, 66, -150),
                        (326, 60, 160), (320, 100, -160), (316, 96, -130), (8, 100, -35), (342, 120, -145), (58, 140, 30)):
        o += f'<path d="M0,0 q14,-6 30,0 q-16,6 -30,0z" fill="#3f9a3a" stroke="#1b5e20" stroke-width="1.2" transform="translate({lx},{ly}) rotate({a})"/>'
    # 側牆（立體）
    o += PS('M232,178 L292,166 V250 L232,264z', '#b8854d', 'gShadeV', 2.5) + P('M232,178 L292,166 V250 L232,264z', 'url(#pMud)', 0)
    o += P('M250,196 L274,192 V214 L250,218z', '#3a2410', 2) + P('M250,196 L274,192 V214 L250,218z', 'url(#pLattice)', 0)
    # 正面牆
    o += PS('M68,178 H232 V264 H68z', 'url(#gMud)', 'gShadeV', 2.5) + RC(68, 178, 164, 86, 'url(#pMud)', 0)
    for px in (68, 150, 226):
        o += RC(px - 4, 176, 10, 90, 'url(#gWood)', 2) + RC(px - 4, 176, 10, 90, 'url(#pGrain)', 0)
    o += RC(64, 176, 172, 9, 'url(#gWoodV)', 2)
    o += RC(286, 164, 8, 88, 'url(#gWood)', 2)
    # 圓窗
    o += EL(108, 220, 22, 22, '#3a2410', 3) + EL(108, 220, 18, 18, 'url(#pLattice)', 0) + EL(108, 220, 22, 22, 'none', 3.5, '#7a4a22')
    o += EL(108, 220, 18, 18, 'url(#gWarm)', 0, extra='fill-opacity=".45"')
    # 門與竹簾
    o += RC(164, 200, 50, 64, '#2a1a0c', 2.5)
    o += RC(166, 202, 46, 34, '#d9b25a', 1.5)
    for yy in range(205, 236, 4):
        o += LN(167, yy, 211, yy, '#8d6524', 1)
    o += RC(164, 234, 50, 6, '#c99a3e', 1.8) + LN(176, 202, 176, 236, '#7a2a0c', 1.2) + LN(202, 202, 202, 236, '#7a2a0c', 1.2)
    # 石基與台階
    o += RC(60, 262, 236, 12, '#9e9e9e', 2.5)
    for k in range(9):
        o += RC(62 + k * 26, 264, 22, 8, '#bdbdbd', 1, 3)
    o += RC(158, 272, 62, 9, 'url(#gStone)', 2, 3)
    for (sx, sy, rx_) in ((186, 290, 14), (176, 304, 13), (190, 316, 12)):
        o += EL(sx, sy, rx_, 5, 'url(#gStone)', 1.8)
    # 茅草屋頂
    side = 'M246,192 Q282,186 318,172 L268,66 L226,74z'
    o += P(side, 'url(#gThatch)', 3) + P(side, 'url(#pThatch2)', 0) + P(side, 'url(#gShadeV)', 0) + P(side, '#000', 0, extra='fill-opacity=".14"')
    front = 'M30,190 Q140,202 252,192 L226,74 Q160,64 90,76z'
    o += P(front, 'url(#gThatch)', 3) + P(front, 'url(#pThatch)', 0)
    for yy, amp in ((108, 6), (142, 8), (172, 10)):
        x_l = 90 - (yy - 76) / 114 * 60
        x_r = 226 + (yy - 74) / 118 * 26
        o += P(f'M{x_l:.0f},{yy} Q{(x_l + x_r) / 2:.0f},{yy + amp} {x_r:.0f},{yy - 2}', 'none', 2.5, '#7a5418', 'stroke-opacity=".7"')
        o += P(f'M{x_l:.0f},{yy - 3} Q{(x_l + x_r) / 2:.0f},{yy + amp - 3} {x_r:.0f},{yy - 5}', 'none', 1.5, '#fff3b8', 'stroke-opacity=".6"')
    o += P(front, 'url(#gShadeH)', 0)
    # 草簷流蘇
    fr = ''
    for k in range(46):
        t_ = k / 45
        xx = 32 + 284 * t_
        if xx < 250:
            yy = 190 + 2 * (xx - 30) / 222 * (1 - (xx - 30) / 222) * 24
        else:
            yy = 192 - (xx - 250) / 68 * 18
        fr += f'M{xx:.1f},{yy:.1f} l{(k % 3) - 1},{7 + (k * 7) % 5}'
    o += P(fr, 'none', 1.8, '#8d6524')
    # 屋脊草束與繩
    o += P('M84,78 Q160,62 272,62 Q276,70 270,74 Q160,74 88,86 Q78,84 84,78z', '#b98a35', 2.5) + P('M84,78 Q160,62 272,62 Q276,70 270,74 Q160,74 88,86 Q78,84 84,78z', 'url(#pThatch2)', 0)
    for xx in (110, 150, 190, 230, 262):
        yy = 68 + (272 - xx) / 190 * 8
        o += P(f'M{xx},{yy - 6} q3,7 0,14', 'none', 2.5, '#5a3415')
    # 炊煙
    o += P('M250,58 q-10,-12 2,-22 q12,-10 0,-24 M262,52 q8,-12 -2,-20', 'none', 3, '#cfd8dc', 'stroke-opacity=".85"')
    # 竹籬笆
    for k in range(7):
        xx = 8 + k * 9
        o += RC(xx, 240 - (k % 2) * 4, 6, 46 + (k % 2) * 4, 'url(#gBamboo)', 1.4, 2)
    o += LN(4, 254, 70, 254, '#8d6524', 3) + LN(4, 270, 70, 270, '#8d6524', 3)
    # 花草
    for (fx, fy, c) in ((92, 292, '#e84393'), (110, 300, '#fdd835'), (240, 292, '#e84393'), (262, 300, '#ffffff'), (130, 284, '#ff7043')):
        o += P(f'M{fx},{fy + 8} v-8', 'none', 1.5, '#2e7d32')
        for a in range(0, 360, 72):
            o += EL(fx + 3 * math.cos(math.radians(a)), fy + 3 * math.sin(math.radians(a)), 2.4, 2.4, c, .6)
        o += EL(fx, fy, 1.6, 1.6, '#ffeb3b', 0)
    for (gx, gy) in ((40, 300), (70, 310), (230, 310), (290, 296), (140, 312)):
        o += P(f'M{gx - 5},{gy} q2,-8 3,-10 M{gx},{gy} v-12 M{gx + 5},{gy} q-2,-8 -3,-10', 'none', 1.8, '#2e7d32')
    # 飛鳥
    o += P('M130,30 q5,-6 10,0 q5,-6 10,0 M160,46 q4,-5 8,0 q4,-5 8,0', 'none', 2)
    # 題字與印章
    if not MOBILE:
        o += TX(W0 * 0.86, H0 * 0.95, nm(i), min(H0 * 0.11, W0 * 0.26 / max(1, len(nm(i)))), '#1a1a1a', '#fff8e1', 5, "'Kaiti TC','STKaiti','BiauKai','DFKai-SB',serif")
    return place(i, W0, H0, o)

def arrows():
    out = ''
    for i in range(55):
        a, b = box(i), box((i + 1) % 55)
        ax0, ay0, aw, ah = a; bx0, by0, bw, bh = b
        gx = max(bx0 - (ax0 + aw), ax0 - (bx0 + bw))  # 水平間距
        gy = max(by0 - (ay0 + ah), ay0 - (by0 + bh))  # 垂直間距
        if gx <= 0 and gy <= 0:
            continue
        if gx >= gy:  # 水平箭頭
            right = bx0 > ax0
            x = (ax0 + aw + bx0) / 2 if right else (bx0 + bw + ax0) / 2
            lo, hi = max(ay0, by0), min(ay0 + ah, by0 + bh)
            y = (lo + hi) / 2 if hi > lo else (ay0 + ah/2 + by0 + bh/2) / 2
            s = min(70, max(36, gx * 1.0))
            rot = 0 if right else 180
        else:
            down = by0 > ay0
            y = (ay0 + ah + by0) / 2 if down else (by0 + bh + ay0) / 2
            lo, hi = max(ax0, bx0), min(ax0 + aw, bx0 + bw)
            x = (lo + hi) / 2 if hi > lo else (ax0 + aw/2 + bx0 + bw/2) / 2
            s = min(70, max(36, gy * 1.0))
            rot = 90 if down else -90
        out += f'<use href="#arrow" x="{-s/2:.0f}" y="{-s/2:.0f}" width="{s:.0f}" height="{s:.0f}" transform="translate({x:.0f},{y:.0f}) rotate({rot})"/>'
    return out

def decks():
    out = ''
    for k, b in DECKS.items():
        x, y, w, h = rot(*b)
        fill = {'emergency': '#e8457a', 'general': '#2e8b3e', 'strategy': '#ffe14d'}[k]
        out += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="#fff" stroke="#111" stroke-width="6"/>'
        out += f'<rect x="{x + 12}" y="{y + 12}" width="{w - 24}" height="{h - 24}" rx="8" fill="{fill}" stroke="#111" stroke-width="3"/>'
        if k == 'general':
            continue
        # 牌堆名稱沿用該主題的格子名稱（緊急軍情／江湖告急等）
        name = NAMES[next(i for i, tl in enumerate(TILES) if tl[0] == k)]
        if h > w:  # 直式：名稱在上、圖在下
            out += t(x + w / 2, y + h * 0.2, name, w * 0.17)
            out += picture('horse' if k == 'emergency' else 'pouch', x + w / 2, y + h * 0.6, w * 0.72)
        else:
            out += picture('horse' if k == 'emergency' else 'pouch', x + w * 0.66, y + h / 2, h * 0.75)
            for n, ch in enumerate(name):
                out += t(x + w * 0.2, y + h * 0.22 + n * h * 0.2, ch, h * 0.17)
    return out

# ---------------- 各主題圖畫格（休息處、寶地、招賢處） ----------------
# 每個主題四個圖畫格的畫法，依格子名稱繪製；三國的三顧茅廬沿用 cottage()。
# 畫布大小同原圖：休息處一 420×385、休息處二 490×405、寶地 300×393、招賢處 350×320
SLOT_SIZE = {'rest0': (420, 385), 'rest1': (490, 405), 'island': (300, 393), 'cottage': (350, 320)}

def s_label(W0, H0, name, y=None):
    """網頁版：圖上方的木匾寫地名（手機版改用下方橫幅，不畫）"""
    if MOBILE:
        return ''
    fs = min(40, (W0 * 0.62) / max(1, len(name)))
    w = fs * len(name) + 36
    y = 6 if y is None else y
    return (RC(W0 / 2 - w / 2, y, w, fs + 18, 'url(#gSign)', 3, 8) + RC(W0 / 2 - w / 2 + 5, y + 5, w - 10, fs + 8, 'none', 1.6, 5, 'stroke="#f6c90e"')
            + TX(W0 / 2, y + fs + 4, name, fs, '#fff3b0', '#5a2a0a', 4))
def s_ground(W0, H0, c='url(#gGround)'):
    return EL(W0 / 2, H0 - 26, W0 / 2 - 4, 26, c, 0)
def s_cloud(cx, cy, s=1.0, op=.95):
    return ''.join(EL(cx + dx * s, cy + dy * s, r * s, r * .7 * s, '#ffffff', 2, '#9fb6c9', f'fill-opacity="{op}"') for dx, dy, r in ((-22, 4, 18), (0, -6, 22), (24, 4, 17)))
def s_water(x, y, w, h):
    return RC(x, y, w, h, 'url(#gSea)', 2.5, 8) + RC(x, y, w, h, 'url(#pWave)', 0, 8)
def s_hall(x0, x1, base, wall_h, roof_h, fill='#c0392b', door=True, roof='url(#gRoof)', dark='#0f5426', light='#8ff0a6'):
    """一座中式殿堂：牆、柱、門、翹簷屋頂"""
    w = x1 - x0
    o = RC(x0, base - wall_h, w, wall_h, fill, 2.5) + RC(x0, base - wall_h, w, wall_h, 'url(#gShadeV)', 0)
    for k in range(5):
        px = x0 + 6 + k * (w - 12) / 4
        o += RC(px - 4, base - wall_h, 8, wall_h, 'url(#gPillar)', 1.6)
    if door:
        o += RC(x0 + w / 2 - w * .1, base - wall_h * .7, w * .2, wall_h * .7, '#5a2a0a', 2) + LN(x0 + w / 2, base - wall_h * .7, x0 + w / 2, base, '#2a1408', 1.6)
    o += cn_roof(x0 + w * .22, x1 - w * .22, base - wall_h - roof_h, x0 - 18, x1 + 18, base - wall_h + 4, 8, roof, dark, light)
    return o
def s_steps(cx, base, w, n=4, fill='url(#gMarble)'):
    o = ''
    for k in range(n):
        ww = w - k * w * .12
        o += RC(cx - ww / 2, base - (k + 1) * 10, ww, 10, fill, 1.8)
    return o
def s_flag(x, top, ch, c='#c0392b', h=70):
    return (LN(x, top, x, top + h + 50, '#5d3a1a', 4) + P(f'M{x},{top} h44 q-8,16 0,32 h-44z', c, 2.2)
            + TX(x + 20, top + 25, ch, 22, '#fff8e1', OL, 3))
def s_star(cx, cy, r):
    """金色四角星（有描邊，在淺色棋盤上也看得到）"""
    d = f'M{cx},{cy - r} Q{cx + r * .18},{cy - r * .18} {cx + r},{cy} Q{cx + r * .18},{cy + r * .18} {cx},{cy + r} Q{cx - r * .18},{cy + r * .18} {cx - r},{cy} Q{cx - r * .18},{cy - r * .18} {cx},{cy - r}z'
    return P(d, '#ffd54f', 1.6)

# ---- 三國 ----
def sc_tongque(W0, H0, name):      # 銅雀台：高台、三層樓閣、屋頂銅雀
    o = s_ground(W0, H0)
    o += P(f'M70,{H0 - 30} L110,{H0 - 130} H310 L350,{H0 - 30}z', 'url(#gStone)', 3) + P(f'M70,{H0 - 30} L110,{H0 - 130} H310 L350,{H0 - 30}z', 'url(#pBrick)', 0)
    o += s_steps(210, H0 - 30, 90, 6)
    o += s_hall(130, 290, H0 - 130, 60, 30, '#b03a2e')
    o += s_hall(160, 260, H0 - 222, 44, 26, '#b03a2e', False)
    # 銅雀
    bx, by = 210, H0 - 300
    o += P(f'M{bx - 30},{by + 12} q20,-30 44,-18 q10,-16 22,-8 q-6,6 -10,12 q14,4 18,16 q-30,-4 -44,6 q-14,4 -30,-8z', '#c88a2c', 2.4) + P(f'M{bx - 30},{by + 12} q20,-30 44,-18 q10,-16 22,-8 q-6,6 -10,12 q14,4 18,16 q-30,-4 -44,6 q-14,4 -30,-8z', 'url(#gGold)', 0, extra='fill-opacity=".55"')
    o += EL(bx + 22, by - 10, 2.5, 2.5, OL, 0)
    return o + s_label(W0, H0, name)
def sc_meiwu(W0, H0, name):        # 郿塢：城牆、角樓、城門；城門前戲台上舞姬起舞
    o = s_ground(W0, H0)
    base = H0 - 30
    o += RC(40, base - 190, W0 - 80, 150, 'url(#gWall)', 3) + RC(40, base - 190, W0 - 80, 150, 'url(#pBrick)', 0)
    for k in range(13):
        o += RC(40 + k * (W0 - 80) / 13 + 2, base - 206, (W0 - 80) / 13 - 8, 16, 'url(#gWall)', 2)
    for x in (70, W0 - 70):
        o += RC(x - 34, base - 250, 68, 60, '#8d5524', 2.5) + cn_roof(x - 16, x + 16, base - 290, x - 48, x + 48, base - 244, 5)
    o += P(f'M{W0 / 2 - 40},{base - 40} V{base - 100} q40,-40 80,0 V{base - 40}z', '#3a2410', 3)
    # 戲台與紅燈籠
    o += RC(90, base - 40, W0 - 180, 30, 'url(#gWood)', 2.5) + RC(90, base - 44, W0 - 180, 8, '#b03a2e', 2)
    for x in (110, W0 - 110):
        o += LN(x, base - 44, x, base - 170, '#5d3a1a', 4) + EL(x, base - 150, 12, 15, 'url(#gLantern)', 2)
    o += dancers(W0 / 2, base - 44, 120, 64)
    return o + s_label(W0, H0, name)

def sc_well(W0, H0, name):         # 洛陽甄官井：石井、轆轤、井中五色光與玉璽
    o = s_ground(W0, H0)
    cx, base = W0 / 2, H0 - 60
    for k, c in enumerate(('#ff8a80', '#ffd180', '#ffff8d', '#b9f6ca', '#82b1ff')):
        o += P(f'M{cx - 18 + k * 9},{base - 60} L{cx - 60 + k * 30},{base - 300} L{cx - 40 + k * 30},{base - 300}z', c, 0, extra='fill-opacity=".55"')
    o += EL(cx, base - 60, 96, 26, '#5d4a3a', 3) + EL(cx, base - 62, 78, 18, '#14212b', 2)
    o += P(f'M{cx - 96},{base - 60} V{base} q96,34 192,0 V{base - 60}', 'url(#gStone)', 3) + P(f'M{cx - 96},{base - 60} V{base} q96,34 192,0 V{base - 60}', 'url(#pStoneW)', 0)
    o += LN(cx - 80, base - 60, cx - 80, base - 170, '#5d3a1a', 7) + LN(cx + 80, base - 60, cx + 80, base - 170, '#5d3a1a', 7) + RC(cx - 90, base - 180, 180, 12, 'url(#gWood)', 2.5)
    o += LN(cx, base - 170, cx, base - 100, '#8d6e63', 2) + RC(cx - 22, base - 104, 44, 34, 'url(#gGold)', 2.5, 4) + TX(cx, base - 80, '璽', 22, '#8b1a1a', '#fff3b0', 2)
    o += s_star(cx - 100, base - 230, 10) + s_star(cx + 96, base - 260, 8)
    o += gold_pile(cx, H0 - 22, 190)   # 井邊堆滿撈起的金元寶
    return o + s_label(W0, H0, name, H0 - 310)   # 招牌緊貼畫面主體上方

# ---- 水滸 ----
def sc_shizilou(W0, H0, name):     # 獅子樓：兩層酒樓、酒旗、門口石獅
    o = s_ground(W0, H0)
    base = H0 - 40
    o += s_hall(90, 330, base, 90, 30, '#a0522d')
    o += RC(100, base - 160, 220, 50, '#8d4a1f', 2.5) + RC(100, base - 160, 220, 50, 'url(#pLattice)', 0, extra='opacity=".6"')
    o += cn_roof(150, 270, base - 210, 80, 340, base - 156, 9)
    o += s_flag(350, base - 230, '酒', '#c0392b', 60)
    for x in (70, W0 - 110):
        o += RC(x, base - 18, 40, 18, 'url(#gStone)', 2) + EL(x + 20, base - 44, 20, 24, '#bdbdbd', 2.5) + EL(x + 20, base - 70, 16, 14, '#cfcfcf', 2.2)
        o += EL(x + 14, base - 72, 2.5, 2.5, OL, 0) + EL(x + 26, base - 72, 2.5, 2.5, OL, 0) + P(f'M{x + 6},{base - 78} q14,-14 28,0', 'none', 2.2, '#757575')
    return o + s_label(W0, H0, name)
def sc_kuaihuolin(W0, H0, name):   # 快活林：林木、酒店、酒旗、酒罈；林間空地上舞姬起舞
    o = s_ground(W0, H0)
    base = H0 - 30
    for x, y, r in ((40, base - 200, 40), (110, base - 236, 46), (450, base - 220, 42), (30, base - 130, 32)):
        o += tree(x, y, r)
    o += s_hall(250, 440, base - 6, 80, 30, '#8d5524')
    o += s_flag(452, base - 210, '酒', '#e67e22', 56)
    for x in (270, 300):
        o += EL(x, base - 10, 14, 16, '#6d4c2f', 2.2) + RC(x - 7, base - 32, 14, 7, '#c0392b', 1.6)
    o += dancers(140, base - 4, 120, 58)
    return o + s_label(W0, H0, name)

def sc_huangnigang(W0, H0, name):  # 黃泥岡：黃土山岡、松樹、打開的箱籠與金元寶堆
    o = P(f'M0,{H0 - 20} Q{W0 * .3},{H0 - 230} {W0 * .55},{H0 - 160} Q{W0 * .8},{H0 - 100} {W0},{H0 - 140} V{H0} H0z', '#d4a24c', 3)
    o += P(f'M0,{H0 - 20} Q{W0 * .3},{H0 - 230} {W0 * .55},{H0 - 160} Q{W0 * .8},{H0 - 100} {W0},{H0 - 140} V{H0} H0z', 'url(#pMud)', 0)
    o += tree(W0 * .22, H0 - 240, 30, '#2e7d32') + tree(W0 * .8, H0 - 190, 24, '#2e7d32')
    o += LN(20, H0 - 150, 280, H0 - 170, '#6d4c2f', 5)
    for x in (30, 210):
        y = H0 - 100
        o += RC(x, y, 64, 40, '#8d4a1f', 2.5, 4) + P(f'M{x},{y} l10,-26 h44 l10,26z', '#6d3a17', 2.2)
    o += gold_pile(W0 / 2, H0 - 24, 200)
    return o + s_label(W0, H0, name, H0 - 330)   # 招牌緊貼畫面主體上方

def sc_shijie(W0, H0, name):       # 石碣村：湖岸漁村茅屋、漁船、蘆葦
    o = s_water(0, H0 * .56, W0, H0 * .44)
    o += P(f'M0,{H0 * .6} Q{W0 * .5},{H0 * .5} {W0},{H0 * .62} V{H0 * .34} H0z', '#9ccc65', 2.5) + P(f'M0,{H0 * .6} Q{W0 * .5},{H0 * .5} {W0},{H0 * .62} V{H0 * .34} H0z', 'url(#gShadeV)', 0)
    for hx, hw in ((40, 120), (200, 110)):
        hy = H0 * .52
        o += RC(hx, hy - 50, hw, 50, 'url(#gMud)', 2.5) + RC(hx, hy - 50, hw, 50, 'url(#pMud)', 0)
        o += P(f'M{hx - 14},{hy - 46} L{hx + hw / 2},{hy - 96} L{hx + hw + 14},{hy - 46}z', 'url(#gThatch)', 2.5) + P(f'M{hx - 14},{hy - 46} L{hx + hw / 2},{hy - 96} L{hx + hw + 14},{hy - 46}z', 'url(#pThatch)', 0)
        o += RC(hx + hw * .4, hy - 34, hw * .2, 34, '#3a2410', 2) + RC(hx + hw * .1, hy - 38, hw * .18, 16, '#3a2410', 1.6) + RC(hx + hw * .1, hy - 38, hw * .18, 16, 'url(#pLattice)', 0)
    for bx, by in ((90, H0 * .82), (250, H0 * .76)):
        o += P(f'M{bx - 50},{by} q50,26 100,0 l-12,14 h-76z', '#8d5524', 2.5) + LN(bx, by, bx, by - 56, '#5d3a1a', 3) + P(f'M{bx},{by - 54} l32,38 h-32z', '#f5e6c8', 2)
    for x in range(8, W0, 26):
        o += LN(x, H0 * .64, x + 4, H0 * .55, '#558b2f', 2.4) + EL(x + 4, H0 * .55, 2.5, 5, '#8d6e63', 0)
    return o + s_label(W0, H0, name, 4)

# ---- 封神 ----
def sc_zhaixing(W0, H0, name):     # 摘星樓：入雲高樓，樓頂摘星
    o = s_ground(W0, H0)
    base, cx = H0 - 40, W0 / 2
    o += EL(cx, 110, 190, 105, '#1f2a5a', 2.5) + EL(cx, 110, 190, 105, 'url(#gShadeV)', 0)   # 夜空
    for k in range(4):
        w = 170 - k * 32
        o += RC(cx - w / 2, base - 60 - k * 66, w, 56, '#7b1f3a', 2.5) + RC(cx - w / 2, base - 60 - k * 66, w, 56, 'url(#pLattice)', 0, extra='opacity=".5"')
        o += cn_roof(cx - w * .25, cx + w * .25, base - 84 - k * 66, cx - w / 2 - 16, cx + w / 2 + 16, base - 56 - k * 66, 6)
    o += RC(cx - 90, base - 10, 180, 10, 'url(#gMarble)', 2)
    for x, y, r in ((cx - 120, 90, 14), (cx + 110, 70, 12), (cx + 60, 34, 9), (cx - 70, 40, 9), (cx + 150, 130, 8), (cx - 150, 140, 7)):
        o += s_star(x, y, r)
    return o + s_label(W0, H0, name, H0 - 60)
def sc_jiuchi(W0, H0, name):       # 酒池肉林：鹿台宮殿、酒池、掛肉的樹林；池畔舞姬起舞
    o = s_ground(W0, H0)
    base = H0 - 30
    o += P(f'M150,{base - 80} L170,{base - 170} H320 L340,{base - 80}z', 'url(#gStone)', 3) + P(f'M150,{base - 80} L170,{base - 170} H320 L340,{base - 80}z', 'url(#pBrick)', 0)
    o += s_hall(190, 300, base - 170, 46, 24, '#c0392b')
    for x, y in ((50, base - 190), (440, base - 190)):
        o += tree(x, y, 40, '#558b2f')
        for dx in (-22, 0, 22):
            o += LN(x + dx, y + 8, x + dx, y + 30, '#5d3a1a', 1.4) + P(f'M{x + dx - 6},{y + 30} h12 l-2,18 h-8z', '#d7826b', 1.6)
    o += EL(140, base - 30, 110, 30, '#8e1b3a', 3) + EL(140, base - 32, 94, 21, '#d6336c', 0, extra='fill-opacity=".85"')
    o += P(f'M80,{base - 36} q20,-8 40,0 M150,{base - 26} q20,-8 40,0', 'none', 2, '#ffcdd2')
    o += dancers(360, base - 4, 116, 56)
    return o + s_label(W0, H0, name)

def sc_jinao(W0, H0, name):        # 金鰲島：海中仙山、宮觀、祥雲；岸邊堆滿金元寶
    o = s_water(0, H0 * .6, W0, H0 * .4)
    o += P(f'M10,{H0 * .82} L100,{H0 * .3} L150,{H0 * .42} L210,{H0 * .24} L290,{H0 * .82}z', '#3f7a5a', 3) + P(f'M10,{H0 * .82} L100,{H0 * .3} L150,{H0 * .42} L210,{H0 * .24} L290,{H0 * .82}z', 'url(#gShadeH)', 0)
    o += P(f'M10,{H0 * .82} Q150,{H0 * .72} 290,{H0 * .82} Q150,{H0 * .9} 10,{H0 * .82}z', 'url(#gSand)', 2.5)
    o += s_hall(105, 205, H0 * .5, 40, 22, '#b03a2e', False)
    o += s_cloud(50, H0 * .2, .8) + s_cloud(250, H0 * .14, .7)
    o += gold_pile(W0 / 2, H0 * .84, 180)
    return o + s_label(W0, H0, name, H0 * .24 - 66)   # 招牌緊貼畫面主體上方

def sc_weishui(W0, H0, name):      # 渭水釣台：河水、岸石、直鉤垂釣
    o = s_water(0, H0 * .55, W0, H0 * .45)
    o += P(f'M0,{H0 * .58} Q60,{H0 * .38} 150,{H0 * .5} L170,{H0 * .62} H0z', 'url(#gStone)', 3)
    o += LN(110, H0 * .44, 300, H0 * .2, '#6d4c2f', 4) + LN(300, H0 * .2, 300, H0 * .7, '#555', 1.4)
    o += LN(296, H0 * .7, 304, H0 * .7, '#555', 2)   # 直鉤
    o += EL(90, H0 * .44, 16, 16, 'url(#gSkin)', 2.2) + P(f'M64,{H0 * .44} q26,-30 52,0z', '#c9a227', 2) + P(f'M76,{H0 * .46} q14,30 28,0', 'none', 2, '#e8e8e8')
    o += RC(70, H0 * .46, 40, 46, '#2b5fc1', 2.2, 8)
    for x in (30, 200, 250):
        o += LN(x, H0 * .56, x + 4, H0 * .44, '#7cb342', 2.4)
    return o + s_label(W0, H0, name, 4)

# ---- 西遊 ----
def sc_pantao(W0, H0, name):       # 蟠桃園：仙桃樹、祥雲
    o = s_ground(W0, H0)
    base = H0 - 40
    for x, y, r in ((90, base - 140, 60), (210, base - 180, 70), (330, base - 140, 60)):
        o += tree(x, y, r, '#5fa83a')
        for dx, dy in ((-r * .4, -r * .1), (r * .3, -r * .3), (0, r * .25), (r * .5, r * .2), (-r * .2, -r * .5)):
            o += EL(x + dx, y + dy, 11, 10, '#ff8fa3', 1.8) + EL(x + dx - 3, y + dy - 3, 4, 3, '#fff', 0, extra='fill-opacity=".7"')
    o += s_cloud(60, 60, .8) + s_cloud(360, 50, .7)
    return o + s_label(W0, H0, name, H0 - 60)
def sc_pansi(W0, H0, name):        # 盤絲洞：山洞、洞頂蛛網；洞中舞姬起舞
    o = P(f'M10,{H0 - 10} L60,{H0 - 300} L180,{H0 - 360} L330,{H0 - 330} L470,{H0 - 260} L480,{H0 - 10}z', '#6d6a75', 3) + P(f'M10,{H0 - 10} L60,{H0 - 300} L180,{H0 - 360} L330,{H0 - 330} L470,{H0 - 260} L480,{H0 - 10}z', 'url(#gShadeH)', 0)
    o += P(f'M110,{H0 - 10} V{H0 - 180} Q245,{H0 - 330} 380,{H0 - 180} V{H0 - 10}z', '#2a1d36', 3)
    cx, cy = 245, H0 - 230
    for k in range(8):
        a = k * math.pi / 4
        o += LN(cx, cy, cx + 110 * math.cos(a), cy + 60 * math.sin(a), '#f5f5f5', 1.6, 'stroke-opacity=".8"')
    for r in (30, 60, 95):
        pts = ' '.join(f'{cx + r * math.cos(k * math.pi / 4):.0f},{cy + r * .55 * math.sin(k * math.pi / 4):.0f}' for k in range(9))
        o += f'<polyline points="{pts}" fill="none" stroke="#f5f5f5" stroke-width="1.6" stroke-opacity=".8"/>'
    o += EL(cx + 60, cy + 10, 9, 11, '#4a148c', 1.6) + EL(cx + 60, cy - 3, 6, 5, '#6a1b9a', 1.4)
    o += dancers(245, H0 - 18, 130, 64)
    return o + s_label(W0, H0, name)

def sc_longgong(W0, H0, name):     # 東海龍宮：海底宮殿、珊瑚、氣泡
    o = RC(0, 0, W0, H0, 'url(#gSea)', 3, 14)
    o += s_hall(60, 240, H0 - 140, 70, 36, '#2e86c1', roof='url(#gRoofB)', dark='#0b3c5d', light='#aed6f1')
    o += s_steps(150, H0 - 110, 150, 3) + P(f'M0,{H0 - 30} Q150,{H0 - 70} 300,{H0 - 30} V{H0} H0z', 'url(#gSand)', 2)
    o += gold_pile(150, H0 - 34, 190)   # 海底龍宮前的金元寶
    for x, c in ((30, '#ff7043'), (270, '#ec407a')):
        o += P(f'M{x},{H0 - 30} q-6,-40 -18,-60 M{x},{H0 - 30} q4,-50 14,-74 M{x},{H0 - 50} q12,-14 22,-12', 'none', 6, c)
    for x, y, r in ((50, 80, 8), (70, 50, 5), (250, 110, 9), (230, 70, 5), (150, 40, 6)):
        o += EL(x, y, r, r, '#e3f2fd', 1.6, '#90caf9', 'fill-opacity=".5"')
    return o + s_label(W0, H0, name, H0 - 316)   # 招牌緊貼畫面主體上方
def sc_luojia(W0, H0, name):       # 落伽山：南海普陀山、紫竹、蓮臺與佛光
    o = s_water(0, H0 * .7, W0, H0 * .3)
    o += P(f'M20,{H0 * .74} L100,{H0 * .3} L170,{H0 * .42} L240,{H0 * .22} L330,{H0 * .74}z', '#5c7a52', 3) + P(f'M20,{H0 * .74} L100,{H0 * .3} L170,{H0 * .42} L240,{H0 * .22} L330,{H0 * .74}z', 'url(#gShadeH)', 0)
    for bx_ in (40, 56, 300, 316):
        o += RC(bx_ - 4, H0 * .3, 8, H0 * .44, '#6a1b9a', 1.4, 3)
    cx, cy = 175, H0 * .5
    o += EL(cx, cy - 40, 44, 44, 'url(#gGlow)', 0) + EL(cx, cy - 40, 30, 30, 'none', 3, '#ffd54f')
    for k in range(-2, 3):
        o += P(f'M{cx + k * 14},{cy + 10} q-8,-26 0,-36 q8,10 0,36z', '#f8bbd0', 1.8)
    o += EL(cx, cy + 12, 40, 8, '#81c784', 2)
    return o + s_label(W0, H0, name, 4)

# ---- 楚漢 ----
def sc_hongmen(W0, H0, name):      # 鴻門：軍帳宴席、酒爵、劍
    o = s_ground(W0, H0)
    base = H0 - 40
    o += P(f'M60,{base} L80,{base - 150} Q210,{base - 260} 340,{base - 150} L360,{base}z', '#e8d5a8', 3) + P(f'M60,{base} L80,{base - 150} Q210,{base - 260} 340,{base - 150} L360,{base}z', 'url(#gShadeH)', 0)
    o += P(f'M150,{base} V{base - 110} Q210,{base - 150} 270,{base - 110} V{base}z', '#7a1f1f', 2.5)
    o += RC(120, base - 46, 180, 14, 'url(#gWood)', 2.5) + LN(140, base - 32, 140, base, '#5d3a1a', 4) + LN(280, base - 32, 280, base, '#5d3a1a', 4)
    for x in (165, 205, 245):
        o += P(f'M{x - 9},{base - 66} h18 l-4,20 h-10z', 'url(#gGold)', 2)
    o += s_flag(370, base - 240, '楚', '#1b1b1b', 70)
    o += f'<g transform="rotate(-30 210 {base - 120})">' + RC(206, base - 200, 8, 90, 'url(#gMetal)', 2) + RC(196, base - 112, 28, 6, 'url(#gGold)', 1.6) + '</g>'
    return o + s_label(W0, H0, name, H0 - 60)
def sc_epang(W0, H0, name):        # 阿房宮：連綿宮殿、複道；殿前階上舞姬起舞
    o = s_ground(W0, H0)
    base = H0 - 30
    o += s_hall(30, 180, base - 80, 70, 30, '#3b3b3b', roof='url(#gRoofB)', dark='#1b1b1b', light='#9e9e9e')
    o += s_hall(310, 460, base - 80, 70, 30, '#3b3b3b', roof='url(#gRoofB)', dark='#1b1b1b', light='#9e9e9e')
    o += s_hall(170, 320, base - 120, 100, 40, '#7b241c')
    o += RC(150, base - 186, 190, 10, 'url(#gWood)', 2)
    o += s_steps(245, base, 440, 4) + RC(25, base - 80, 440, 40, 'url(#gMarble)', 2)
    o += dancers(245, base - 42, 110, 60)
    return o + s_label(W0, H0, name)

def sc_lishan(W0, H0, name):       # 驪山陵：覆斗形陵丘、神道、石獸
    o = s_ground(W0, H0)
    base = H0 - 50
    o += P(f'M30,{base} L90,{base - 170} H210 L270,{base}z', '#7a9a5a', 3) + P(f'M30,{base} L90,{base - 170} H210 L270,{base}z', 'url(#gShadeH)', 0)
    o += P(f'M60,{base - 90} H240', 'none', 2, '#4e6b3a')
    o += RC(120, base - 60, 60, 60, '#5d4037', 2.5) + P(f'M120,{base - 60} q30,-22 60,0', 'none', 3) + RC(126, base - 50, 48, 50, '#2a1a10', 2)
    for x in (40, 238):
        o += RC(x, base - 6, 22, 30, 'url(#gStone)', 2) + EL(x + 11, base - 16, 14, 12, '#bdbdbd', 2)
    o += gold_pile(150, base + 22, 170)   # 陵門前的陪葬金寶
    return o + s_label(W0, H0, name, base - 236)   # 招牌緊貼畫面主體上方
def sc_baijiang(W0, H0, name):     # 築壇拜將：三層將壇、旌旗、帥印
    o = s_ground(W0, H0)
    base, cx = H0 - 36, W0 / 2
    for k in range(3):
        w = 260 - k * 60
        o += RC(cx - w / 2, base - (k + 1) * 34, w, 34, 'url(#gStone)', 2.5) + RC(cx - w / 2, base - (k + 1) * 34, w, 34, 'url(#pBrick)', 0)
    o += RC(cx - 20, base - 102 - 26, 40, 26, 'url(#gGold)', 2.5, 4) + TX(cx, base - 108, '帥', 20, '#8b1a1a', '#fff3b0', 2)
    o += s_flag(cx - 140, base - 220, '漢', '#c0392b', 80) + s_flag(cx + 100, base - 220, '將', '#c0392b', 80)
    return o + s_label(W0, H0, name)

# ---- 兩個共同的主圖案 ----
def dancer(cx, foot, s_, dress='#e91e63', trim='#f8bbd0', sleeve='#fce4ec', flip=False, fan=False):
    """翩翩起舞的舞姬：髮髻花飾、耳墜、雙層長裙、腰帶飄帶、揚起的水袖；s_ 為身高"""
    hy, wy, sy = foot - s_ * .86, foot - s_ * .5, foot - s_ * .7
    o = EL(cx, foot + 2, s_ * .26, s_ * .045, 'url(#gShadow)', 0)
    # 腰間飄帶
    o += P(f'M{cx - s_ * .1},{wy} q{-s_ * .3},{s_ * .05} {-s_ * .42},{-s_ * .24} q{s_ * .05},{s_ * .22} {s_ * .36},{s_ * .3}', 'none', s_ * .025, '#4fc3f7')
    # 外裙與內裙（向一側飄動）
    o += PS(f'M{cx - s_ * .1},{wy} q{-s_ * .2},{s_ * .3} {-s_ * .34},{s_ * .5} q{s_ * .32},{s_ * .07} {s_ * .74},{-s_ * .05} q{-s_ * .16},{-s_ * .22} {-s_ * .2},{-s_ * .45}z', dress, 'gShadeH', 2.2)
    o += P(f'M{cx - s_ * .06},{wy + s_ * .05} q{-s_ * .12},{s_ * .25} {-s_ * .2},{s_ * .43} q{s_ * .2},{s_ * .04} {s_ * .42},{-s_ * .03} q{-s_ * .08},{-s_ * .2} {-s_ * .12},{-s_ * .4}z', trim, 1.6)
    for k in range(3):
        o += P(f'M{cx - s_ * (.3 - k * .2)},{foot - s_ * .02} q{s_ * .04},{-s_ * .14} {s_ * .02},{-s_ * .3}', 'none', 1.4, '#ffffff', 'stroke-opacity=".6"')
    # 上衣、雲肩、腰帶
    o += PS(f'M{cx - s_ * .1},{wy} L{cx - s_ * .085},{sy} H{cx + s_ * .085} L{cx + s_ * .1},{wy}z', dress, 'gShadeH', 2)
    o += P(f'M{cx - s_ * .1},{sy + s_ * .01} q{s_ * .1},{s_ * .08} {s_ * .2},0 l{-s_ * .02},{s_ * .05} q{-s_ * .08},{s_ * .05} {-s_ * .16},0z', 'url(#gGold)', 1.4)
    o += RC(cx - s_ * .11, wy - s_ * .035, s_ * .22, s_ * .045, 'url(#gGold)', 1.4) + EL(cx, wy - s_ * .012, s_ * .025, s_ * .025, '#e53935', 1)
    # 水袖：一手高舉、一手橫展
    o += P(f'M{cx - s_ * .07},{sy + s_ * .02} q{-s_ * .12},{-s_ * .12} {-s_ * .16},{-s_ * .34} q{-s_ * .1},{s_ * .16} {-s_ * .02},{s_ * .42}z', sleeve, 1.8)
    o += P(f'M{cx + s_ * .07},{sy + s_ * .02} q{s_ * .22},{-s_ * .02} {s_ * .34},{-s_ * .2} q{s_ * .02},{s_ * .22} {-s_ * .22},{s_ * .3}z', sleeve, 1.8)
    if fan:  # 團扇
        o += EL(cx + s_ * .36, sy - s_ * .2, s_ * .07, s_ * .07, '#fff59d', 1.6) + LN(cx + s_ * .36, sy - s_ * .13, cx + s_ * .34, sy - s_ * .05, '#8d6e63', 1.6)
    # 頭、髮髻、花飾、耳墜、五官
    o += EL(cx, hy, s_ * .08, s_ * .09, 'url(#gSkin)', 2) + EL(cx, hy - s_ * .1, s_ * .075, s_ * .055, '#1b1b1b', 1.8)
    o += P(f'M{cx - s_ * .085},{hy - s_ * .015} q{s_ * .085},{-s_ * .12} {s_ * .17},0', '#1b1b1b', 1.8)
    o += EL(cx - s_ * .06, hy - s_ * .12, s_ * .025, s_ * .025, '#ff80ab', 1) + EL(cx + s_ * .05, hy - s_ * .14, s_ * .02, s_ * .02, '#ffd54f', 1)
    o += LN(cx + s_ * .03, hy - s_ * .13, cx + s_ * .12, hy - s_ * .18, '#f1c40f', 1.6) + EL(cx + s_ * .12, hy - s_ * .18, 2.4, 2.4, '#e53935', 0.8)
    o += EL(cx - s_ * .082, hy + s_ * .035, 1.8, 2.8, '#80deea', 0.8) + EL(cx + s_ * .082, hy + s_ * .035, 1.8, 2.8, '#80deea', 0.8)
    o += EL(cx - s_ * .03, hy, 1.6, 2, OL, 0) + EL(cx + s_ * .03, hy, 1.6, 2, OL, 0)
    o += EL(cx - s_ * .05, hy + s_ * .03, s_ * .018, s_ * .011, '#ff8a80', 0, extra='fill-opacity=".7"') + EL(cx + s_ * .05, hy + s_ * .03, s_ * .018, s_ * .011, '#ff8a80', 0, extra='fill-opacity=".7"')
    o += P(f'M{cx - s_ * .02},{hy + s_ * .045} q{s_ * .02},{s_ * .015} {s_ * .04},0', 'none', 1.4, '#c2185b')
    if flip:
        o = f'<g transform="translate({2 * cx},0) scale(-1,1)">{o}</g>'
    return o

def dancers(cx, foot, h, spread=None):
    """三位舞姬一組（中間者較高、站前），旁有音符"""
    d = spread or h * .5
    o = dancer(cx - d, foot - h * .04, h * .9, '#8e24aa', '#e1bee7', '#f3e5f5', flip=True)
    o += dancer(cx + d, foot - h * .04, h * .9, '#00897b', '#b2dfdb', '#e0f2f1', fan=True)
    o += dancer(cx, foot, h, '#e91e63', '#f8bbd0', '#fce4ec')
    o += music_note(cx - d * 1.6, foot - h * .95, h * .26) + music_note(cx + d * 1.25, foot - h * 1.05, h * .24, True)
    return o

def music_note(x, y, s_, double=False):
    """音符（八分音符或連桁的兩個音符）"""
    c, w = '#6a1b9a', max(2, s_ * .09)
    head = lambda hx, hy: f'<ellipse cx="{hx:.1f}" cy="{hy:.1f}" rx="{s_ * .2:.1f}" ry="{s_ * .14:.1f}" fill="{c}" stroke="#fff" stroke-width="2" transform="rotate(-20 {hx:.1f} {hy:.1f})"/>'
    if double:
        x2 = x + s_ * .55
        return (LN(x + s_ * .17, y, x + s_ * .17, y - s_ * .8, c, w) + LN(x2 + s_ * .17, y, x2 + s_ * .17, y - s_ * .8, c, w)
                + P(f'M{x + s_ * .17},{y - s_ * .8} L{x2 + s_ * .17},{y - s_ * .8} V{y - s_ * .66} L{x + s_ * .17},{y - s_ * .66}z', c, 1.5, '#fff') + head(x, y) + head(x2, y))
    return LN(x + s_ * .17, y, x + s_ * .17, y - s_ * .8, c, w) + P(f'M{x + s_ * .17},{y - s_ * .8} q{s_ * .3},{s_ * .12} {s_ * .22},{s_ * .45}', 'none', w, c) + head(x, y)
def gold_pile(cx, base, w):
    """金元寶堆：三層元寶、散落的金錢與閃光；w 為寬度"""
    u = w / 3.2
    def ingot(x, y):
        d = f'M{x - u * .55},{y - u * .3} q{u * .55},{u * .55} {u * 1.1},0 l{-u * .14},{u * .3} h{-u * .82}z'
        return (P(d, 'url(#gGold)', 2.2) + EL(x, y - u * .32, u * .26, u * .2, 'url(#gGold)', 2)
                + P(f'M{x - u * .5},{y - u * .3} q{u * .5},{u * .22} {u},0', 'none', 1.6, '#fff6b8'))
    o = EL(cx, base + 4, w * .55, w * .1, 'url(#gShadow)', 0)
    for k in range(3):
        o += ingot(cx + (k - 1) * u * 1.05, base)
    for k in range(2):
        o += ingot(cx + (k - .5) * u * 1.05, base - u * .55)
    o += ingot(cx, base - u * 1.1)
    for dx, dy in ((-1.7, .1), (1.7, .05), (-1.3, .35), (1.4, .35)):
        x, y = cx + dx * u, base + dy * u
        o += EL(x, y, u * .22, u * .1, 'url(#gGold)', 1.6) + RC(x - u * .05, y - u * .03, u * .1, u * .06, '#8d6e00', 0)
    for dx, dy, r in ((-1.1, -1.4, u * .18), (1.2, -1.2, u * .14), (0, -2.0, u * .16)):
        o += star4(cx + dx * u, base + dy * u, r, '#fffde7')
    return o

# 各主題的第二個休息處以舞姬與音符為主圖案、寶地以金元寶堆為主圖案，由各畫面安排位置
# 主題 → 格子 → 畫法（未列出者用原本的圖）
SCENES = {
    'sanguo': {'rest0': sc_tongque, 'rest1': sc_meiwu, 'island': sc_well},
    'shuihu': {'rest0': sc_shizilou, 'rest1': sc_kuaihuolin, 'island': sc_huangnigang, 'cottage': sc_shijie},
    'fengshen': {'rest0': sc_zhaixing, 'rest1': sc_jiuchi, 'island': sc_jinao, 'cottage': sc_weishui},
    'xiyou': {'rest0': sc_pantao, 'rest1': sc_pansi, 'island': sc_longgong, 'cottage': sc_luojia},
    'chuhan': {'rest0': sc_hongmen, 'rest1': sc_epang, 'island': sc_lishan, 'cottage': sc_baijiang},
}
THEME = 'sanguo'   # 由 main() 設定

def scene_tile(i, slot, default):
    f = SCENES.get(THEME, {}).get(slot)
    if not f:
        return default(i)
    W0, H0 = SLOT_SIZE[slot]
    return place(i, W0, H0, f(W0, H0, nm(i)))

# ---------------- 手機版格子 ----------------
MIN_SEEN = []   # 記錄手機版用到的字級，供檢查

def mlabel(x, y, w, h, s_, fill='#111', stroke=None, weight=900, pad=0.88):
    """在方框內以最大字級寫字：自動選擇單行、直書、兩行或兩直行"""
    n = len(s_)
    half = (n + 1) // 2
    cands = [('row', min(h * 0.78, w * pad / n)), ('col', min(w * 0.78, h * pad / n))]
    if n >= 3:
        # 兩直行（由右而左）較不直覺，只在明顯較大時才採用
        cands += [('rows2', min(h * pad / 2.15, w * pad / half)), ('cols2', 0.85 * min(w * pad / 2.15, h * pad / half))]
    if s_.isdigit():
        cands = [('row', min(h * 0.8, w * pad / (n * 0.6)))]
    mode, fs = max(cands, key=lambda c: c[1])
    MIN_SEEN.append((fs, s_))
    ex = f'stroke="{stroke}" stroke-width="{fs * 0.08:.1f}" paint-order="stroke"' if stroke else ''
    cx, cy = x + w / 2, y + h / 2
    out = ''
    if mode == 'row':
        out += t(cx, cy + fs * 0.36, s_, fs, fill, weight, extra=ex)
    elif mode == 'col':
        for k, ch in enumerate(s_):
            out += t(cx, cy - fs * n / 2 + fs * (k + 0.86), ch, fs, fill, weight, extra=ex)
    elif mode == 'rows2':
        for r, part in enumerate((s_[:half], s_[half:])):
            out += t(cx, cy + (r - 0.5) * fs * 1.08 + fs * 0.36, part, fs, fill, weight, extra=ex)
    else:  # 兩直行，由右而左
        for c, part in enumerate((s_[:half], s_[half:])):
            xx = cx + (0.5 - c) * fs * 1.08
            for k, ch in enumerate(part):
                out += t(xx, cy - fs * half / 2 + fs * (k + 0.86), ch, fs, fill, weight, extra=ex)
    return out

def m_small(i, kind):
    x, y, w, h = box(i)
    name = nm(i)
    if kind in ('emergency', 'strategy'):
        inner = '#e8457a' if kind == 'emergency' else '#ffe14d'
        out = frame(x, y, w, h, '#2f7fd8')
        out += f'<rect x="{x + 12}" y="{y + 12}" width="{w - 24}" height="{h - 24}" rx="5" fill="{inner}" stroke="#1a1a1a" stroke-width="3"/>'
        m = min(w, h)
        out += f'<g opacity=".22">{picture("horse" if kind == "emergency" else "pouch", x + w / 2, y + h / 2, m * 0.8)}</g>'
        short = name[-2:] if len(name) == 4 else name   # 緊急軍情 → 軍情、智取妙計 → 妙計
        return out + mlabel(x + 14, y + 14, w - 28, h - 28, short, '#fff' if kind == 'emergency' else '#1a1a1a',
                            '#1a1a1a' if kind == 'emergency' else None)
    bg, ink, icon = {'recruit': ('#f6d43a', '#1a1a1a', 'soldiers'), 'hire': ('#6b5bd6', '#fff', 'people')}[kind]
    if len(name) > 3:
        name = name[-3:]   # 職業介紹所 → 介紹所
    out = frame(x, y, w, h, bg, '#c9c1ff' if kind == 'hire' else None)
    # 先試「名稱 + 小圖示」；名稱太長放不下大字時，只寫名稱
    split = 0.62
    test = mlabel(x + 8, y + 8, w - 16, (h - 16) * split, name)
    fs_top = MIN_SEEN.pop()[0]
    if fs_top >= MOBILE_MIN and h - 16 - (h - 16) * split >= 44:
        out += mlabel(x + 8, y + 8, w - 16, (h - 16) * split, name, ink)
        ih = (h - 16) * (1 - split)
        out += f'<rect x="{x + w / 2 - ih * 0.62:.0f}" y="{y + 8 + (h - 16) * split:.0f}" width="{ih * 1.24:.0f}" height="{ih * 0.92:.0f}" rx="6" fill="#111"/>' if kind == 'recruit' else ''
        out += picture(icon, x + w / 2, y + 8 + (h - 16) * split + ih * 0.46, ih * 0.86)
    else:
        out += mlabel(x + 8, y + 8, w - 16, h - 16, name, ink)
    return out

def m_shop(i, fee):
    x, y, w, h = box(i)
    out = frame(x, y, w, h, '#f6d43a', '#b8860b')
    k = 0.5   # 上名稱、下金額
    name = nm(i)[:2]   # 商店街 → 商店
    out += mlabel(x + 8, y + 8, w - 16, (h - 16) * k, name)
    out += mlabel(x + 8, y + 8 + (h - 16) * k, w - 16, (h - 16) * (1 - k), str(fee), '#c0392b')
    return out

def m_field(i):
    x, y, w, h = box(i)
    out = frame(x, y, w, h, COL['field'], '#f3c9a9')
    return out + mlabel(x + 10, y + 10, w - 20, h - 20, nm(i), '#fff', '#3a1206')

def m_ribbon(i):
    """圖畫格（休息處、寶島、茅廬）上方的名稱橫幅（下方是畫面前景）"""
    x, y, w, h = box(i)
    rh = max(MOBILE_MIN * 1.25, h * 0.24)
    ry = y
    out = f'<rect x="{x + 6}" y="{ry:.0f}" width="{w - 12}" height="{rh:.0f}" rx="10" fill="#7a1f1f" stroke="#1a1a1a" stroke-width="3" fill-opacity=".92"/>'
    return out + mlabel(x + 12, ry + 4, w - 24, rh - 8, nm(i), '#fff3b0')

def main(theme='sanguo', portrait=False, out=None, mobile=False):
    global NAMES, PORTRAIT, OUT_W, OUT_H, MOBILE, THEME
    NAMES = THEME_NAMES[theme]
    THEME = theme
    MOBILE = mobile
    PORTRAIT = portrait or mobile
    portrait = PORTRAIT
    MIN_SEEN.clear()
    OUT_W, OUT_H = (W, H) if portrait else (H, W)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {OUT_W} {OUT_H}" font-family="{FONT}">',
             f'<defs>{DEFS}</defs>', FIGURES['defs'] if FIGURES else '',
             f'<rect width="{OUT_W}" height="{OUT_H}" fill="#fbf3a6"/><rect width="{OUT_W}" height="{OUT_H}" fill="url(#dots)"/>',
             decks(), arrows()]
    rest_idx = [i for i, tl in enumerate(TILES) if tl[0] == 'rest']
    for i, tile in enumerate(TILES):
        kind = tile[0]
        if kind == 'city': parts.append(city(i, nm(i), tile[1], tile[2]))
        elif MOBILE and kind == 'field': parts.append(m_field(i))
        elif MOBILE and kind == 'shop': parts.append(m_shop(i, tile[1]))
        elif MOBILE and kind in ('recruit', 'hire', 'emergency', 'strategy'): parts.append(m_small(i, kind))
        elif kind == 'field': parts.append(field(i, nm(i)))
        elif kind == 'shop': parts.append(shop(i, tile[1]))
        elif kind == 'start': parts.append(start(i))
        elif kind == 'rest': parts.append(scene_tile(i, 'rest0', park) if i == rest_idx[0] else scene_tile(i, 'rest1', parlor))
        elif kind == 'island': parts.append(scene_tile(i, 'island', island))
        elif kind == 'cottage': parts.append(scene_tile(i, 'cottage', cottage))
        else: parts.append(small(i, kind))
        if MOBILE and kind in ('rest', 'island', 'cottage'): parts.append(m_ribbon(i))
    parts.append('</svg>')
    out = out or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'board-%s.svg' % theme)
    svg = '\n'.join(parts)
    # 縮短過長的小數，減少檔案大小
    svg = re.sub(r'(?<![\d.])(\d+\.\d{2,})', lambda m: ('%.1f' % float(m.group(1))).rstrip('0').rstrip('.'), svg)
    with open(out, 'w', encoding='utf8') as f:
        f.write(svg)
    print('wrote', os.path.normpath(out), os.path.getsize(out), 'bytes')

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == '--mobile':
        # 手機版直式棋盤：python3 tools/make_board_svg.py --mobile 輸出資料夾
        for _t in THEME_NAMES:
            main(_t, mobile=True, out=os.path.join(sys.argv[2], 'board-%s-mobile.svg' % _t))
    else:
        for _t in THEME_NAMES:
            main(_t)
