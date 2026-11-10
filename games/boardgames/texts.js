'use strict';
/* 說明文字：格子說明、領地所有證、遊戲說明書。網頁版（client.js）與微信小遊戲共用。
 * 瀏覽器中為全域 SanguoTexts；Node／小遊戲中以 require 取得。
 * E：遊戲引擎（engine.js 匯出的物件）。 */
(function (root, factory) {
  const m = factory();
  if (typeof module === 'object' && module.exports) module.exports = m; else root.SanguoTexts = m;
})(typeof self !== 'undefined' ? self : this, function () {
'use strict';

// 非領地格的說明
function spaceHelp(E, T) {
  const { S, HIRE_COST, fmt } = E;
  const H = {
    start: () => `經過起點可向國庫支領 ${fmt(S.passStart)} 軍費，停留起點時加倍領取。`,
    recruit: () => '可在此自由徵兵，每名士兵一兩，徵兵數量不限。',
    hire: () => `每次以 ${fmt(HIRE_COST)} 取得一名武將，一律從在野武將中抽選，不得自由選取。`,
    emergency: T => `抽取${T.n}卡一張，並依照指示辦理。`,
    strategy: T => `抽取${T.n}卡一張，並依照指示辦理。保留卡可留待日後使用，限用一次。`,
    shop: T => `${T.n}消費 ${fmt(T.fee)}。`,
    rest: T => `繳 ${fmt(T.fee)} 休息一次，其間不得向他人收取過路稅（可進行防禦戰鬥）。`,
    island: () => '重擲一次骰子，向國庫領取擲出點數 ×1000 兩之軍費。',
    cottage: () => '重擲三次骰子，合計 10–12 點免費得武將 1 名，13–15 點 2 名，16–18 點 3 名。',
  };
  return H[T.t] ? H[T.t](T) : '';
}

/* 格子的詳細說明（領地顯示所有證）
 * view：目前局面（viewFor）；pname(p)：玩家名稱 HTML；levelName(i)：格子現況名稱 */
function tileInfoHtml(E, i, view, pname, levelName) {
  const { TILES, GROUPS, CITY_TOLL, FIELD_TOLL, BUILD_COST, LEVEL_NAME, fmt, isProp } = E;
  const T = TILES[i], t = view.tiles[i], P = id => view.players[id];
  let body = `<p>${spaceHelp(E, T)}</p>`;
  if (isProp(i)) {
    const tolls = T.t === 'field'
      ? FIELD_TOLL.map((v, k) => `<tr><td>${'一二三四五'[k]}座古戰場</td><td>${fmt(v)}</td></tr>`).join('')
      : `<tr><td>建城費用</td><td>${fmt(BUILD_COST)}</td></tr>` + CITY_TOLL[T.p].map((v, k) => `<tr><td>${LEVEL_NAME[k]}稅金</td><td>${fmt(v)}</td></tr>`).join('');
    body = `<h4 style="margin:0 0 6px">${T.n}　領地所有證</h4><table>
      <tr><td>顏色</td><td>${GROUPS[T.g]}</td></tr><tr><td>領地價格</td><td>${fmt(T.p)}</td></tr>${tolls}
      <tr><td>主權</td><td>${t.owner == null ? '無（國庫所有）' : pname(P(t.owner))}</td></tr>
      <tr><td>現況</td><td>${t.owner == null ? '空白領地' : levelName(i)}</td></tr>
      <tr><td>目前過路稅</td><td>${t.owner == null ? '—' : fmt(t.toll)}</td></tr>
      <tr><td>攻城所需兵力</td><td>${T.t === 'field' ? 1000 : E.SIEGE_NEED[t.level]} 名</td></tr></table>
      ${T.t === 'field' ? '<p><small>古戰場不得建設城池。</small></p>' : ''}`;
  }
  return body;
}

// 遊戲說明書
function rulesHtml(E) {
  const { S, TILES, BUILD_COST, DEF_TROOPS, HIRE_COST, RANSOM, SALE_TAX, GEN_BASE, SPECIAL_BASE, KIND_LABEL, fmt, tn } = E;
  return `<ol style="padding-left:20px;line-height:1.6">
  <li><b>準備</b>：每位參加者領取軍費 ${fmt(S.startCash)}、兵力 ${S.startTroops} 名，自由選取主帥（四張 A）一名後再抽選三張武將撲克牌。主帥全場公開，各人其餘手牌不公開。棋盤上以寫有主帥姓氏的旗幟代表各人位置，購得的領地蓋上主帥姓氏印章。</li>
  <li><b>開始</b>：依照順序擲骰子前進。經由起點可向國庫支領 ${fmt(S.passStart)} 軍費，停留起點時加倍領取。</li>
  <li><b>空白領地</b>：依定價自由向國庫購買。<b>自軍領地</b>：繳交建城費用 ${fmt(BUILD_COST)} 建設城池，領地可建小城，小城可改建大城。<b>古戰場</b>：規定與領地相同，但不得建設城池，稅金依地主擁有古戰場座數計算。</li>
  <li><b>他人領地</b>：繳交過路稅，或進行<b>武將單挑</b>（免交過路稅），或進行<b>攻城戰</b>（佔領敵城）。
    <ul><li><b>武將單挑</b>：雙方各派一名武將，以攻方武將攻擊力對抗守方武將防禦力，力量大者為勝，並可俘虜敗方武將；平手則同歸於盡，繳回國庫。守方可自由選擇是否出戰，不論勝負，該次過路稅守方不得收取。</li>
    <li><b>攻城戰</b>：攻領地需 500 兵、攻小城或古戰場需 1000 兵、攻大城需 1500 兵；守方需 ${DEF_TROOPS} 兵。守方兵力不足或不願出戰時，領地棄守。不論勝負，攻方損失所派兵力、守方損失 ${DEF_TROOPS} 兵。勝者擁有領地主權並俘虜敗方武將；平手時武將同歸於盡，領地主權仍為守方所有。</li></ul></li>
  <li><b>出戰一張牌</b>：單挑或攻城時，雙方各出一張牌——一名武將，或以一張特別卡取代武將（限用一次）。武器卡（Q）——雙方出戰之牌同歸於盡，平手；陣式卡（K）——俘虜敵方出戰之武將並獲勝，雙方都用陣式則抵消；${KIND_LABEL.overlord}（鬼牌）——獲勝，並將敵方所出之牌、攻城損失之士兵及領地占為己有，雙方同時使用則平手。</li>
  <li><b>主帥</b>：被敵人俘虜或同歸於盡時，需以 ${fmt(RANSOM)} 向敵軍或國庫贖回；無軍費贖回時即為失敗，該主帥成為一般武將。</li>
  <li><b>特殊格子</b>：<b>${tn('recruit')}</b>每名士兵一兩・<b>${tn('hire')}</b>每次 ${fmt(HIRE_COST)} 抽一名在野武將・<b>${tn('shop')}</b>依標示消費・<b>${TILES.filter(T => T.t === 'rest').map(T => T.n).join('／')}</b>繳 500／800 兩休息一次，其間不得收取過路稅・<b>${tn('island')}</b>重擲骰子，領取點數 ×1000 兩・<b>${tn('cottage')}</b>重擲三次骰子，10–12 點得武將 1 名、13–15 點 2 名、16–18 點 3 名・<b>${tn('emergency')}／${tn('strategy')}</b>抽牌並依指示辦理，其中的保留卡可留待日後使用。</li>
  <li><b>記憶</b>：玩家看不到別人的牌，只會記得公開被俘虜或被奪走的牌；但對方一出牌，這些記憶就失效。</li>
  <li><b>賣出</b>：軍費不足時，可隨時賣出武將、特別卡、士兵（每 500 名換 500 兩）或領地（地價加建城費）給國庫，每次賣出需繳 ${fmt(SALE_TAX)} 交易稅。</li>
  <li><b>勝利</b>：其他所有對手全部失敗；或佔有同色全部之領地（含古戰場）任一種；或佔有領地總數達 ${S.winTerr} 處。</li></ol>
  <p><small>補充規則：武將賣價 ${fmt(GEN_BASE)}、特別卡賣價 ${fmt(SPECIAL_BASE)}；其他債務無力支付時亦視為破產；賣出僅限賣給國庫，暫不支援玩家間拍賣。</small></p>`;
}

return { spaceHelp, tileInfoHtml, rulesHtml };
});
