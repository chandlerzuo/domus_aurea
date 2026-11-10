#!/usr/bin/env node
'use strict';
/* 輸出各主題起點格三位人物的圖（取自牌面人物，與牌上的模樣一致），供 tools/make_board_svg.py 使用。
 * 輸出 JSON：{ defs: 牌圖共用漸層, themes: { 主題: [{ svg, fy }, …] } }，順序為左、右、中。 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
// 起點格人物：左、右、中（持帥旗者站中間）
const TRIO = {
  sanguo: ['HJ', 'H10', 'HA'],    // 關羽、張飛、劉備
  shuihu: ['HJ', 'H10', 'SA'],    // 林沖、秦明、宋江
  fengshen: ['SJ', 'HJ', 'SA'],   // 楊戩、哪吒、姜子牙
  xiyou: ['HA', 'DA', 'SA'],      // 孫悟空、豬八戒、唐三藏
  chuhan: ['SJ', 'DA', 'SA'],     // 樊噲、韓信、劉邦
};

const ctx = { console };
ctx.window = ctx; ctx.self = ctx;
vm.createContext(ctx);
const load = f => vm.runInContext(fs.readFileSync(path.join(ROOT, f), 'utf8'), ctx, { filename: f });
load('cards.js');
for (const f of fs.readdirSync(ROOT).filter(f => /^theme-[a-z]+-art\.js$/.test(f)).sort((a, b) => (a === 'theme-shuihu-art.js' ? -1 : b === 'theme-shuihu-art.js' ? 1 : 0))) load(f);

const out = { defs: ctx.cardDefs(), themes: {} };
for (const [theme, codes] of Object.entries(TRIO)) out.themes[theme] = codes.map(c => ctx.cardFigure(theme, c));
process.stdout.write(JSON.stringify(out));
