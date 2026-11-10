'use strict';
// 包在函式內，避免與主程式的全域名稱衝突；只公開 cardSvg 與 cardInfoHtml
(() => {
/* 武將撲克牌之向量圖。牌面只畫人物（或特別卡圖案）與點數花色；
 * 姓名、攻擊力、防禦力及介紹另以滑鼠懸停顯示（見 cardInfoHtml）。
 * 人物為 Q 版造型，保留原圖主要特徵。 */

const CARD_TEXT = {
  SA: '三國時代魏國君主，〔挾天子以令諸侯〕，掌握天下三分之二。',
  HA: '中山靖王劉勝之子，唯德唯賢，寬厚仁義，三顧茅廬得諸葛亮（孔明），自立蜀地。',
  DA: '三國時代吳國君主，權謀幹略，出類拔萃，對待部屬視如己出。',
  CA: '東漢末年掌實權，廢少帝，立獻帝。',
  S2: '諸葛亮之岳父，熟知八陣圖變化，曾引陸遜走出魚腹浦石陣。',
  H2: '南蠻八納洞洞主，騎白象、搖金鈴，能呼風喚雨，驅使虎豹豺狼上陣。',
  D2: '道士，往來吳會，燒香讀道書、以符水救人，能祈雨；孫策殺之，冤魂纏身。',
  C2: '太平道教主，自稱〔天公將軍〕，得天書能呼風喚雨，率黃巾起事。',
  S3: '曹操將領，關羽過五關斬六將時被殺。',
  H3: '蜀將，忠於劉備，曾與黃忠用〔驕兵之計〕打敗夏侯惇。',
  D3: '吳將，臉方口大，為孫權甚愛之將。',
  C3: '傾國傾城國色天香，三國時代著名美女並為中國歷代四大美人之一。',
  S4: '魏武將，盡忠職守，為曹操效命沙場。',
  H4: '蜀將，平漢有功，曾任尚書令，護國將軍。',
  D4: '吳國三朝元老，〔赤壁之戰〕時施苦肉計詐降曹操。',
  C4: '董卓將領，威勇剛強，善於帶兵。',
  S5: '魏國謀略家，飽藏經史，善計略，獲曹操所賞識重用。',
  H5: '蜀國謀士，與孔明有〔伏龍、鳳雛〕之稱，曾用〔連環計〕使魏軍戰船重創。',
  D5: '吳國謀略家，為諸葛亮之兄長，博學多才，忠吳不二。',
  C5: '謀略家，事母至孝，天下奇才，德才兼備，曾推薦孔明與劉備。',
  S6: '魏武將，以神力及俠義聞名，〔淯水之難〕保護曹操時中箭死亡。',
  H6: '蜀將，曾被孔明以激將法刺激下，計奪天蕩山，勇斬夏侯淵。',
  D6: '吳將，英勇計略過人。',
  C6: '董卓女婿牛輔之將領，武術高強，勇猛善戰。',
  S7: '魏國謀略家，善曉兵機，深識諸葛亮用兵之法。',
  H7: '絕代奇才，神機妙算，為蜀國第一之謀略軍師。',
  D7: '吳國軍師，胸懷韜略，腹隱機謀，因〔榻上策〕助孫權而成名。',
  C7: '三國時代知名戰略家，深謀略，善兵法。',
  S8: '英勇善戰，膽識兼優，為魏國之良將義士。',
  H8: '蜀將，個性剛強，視惡如仇是條英雄好漢。',
  D8: '吳將，出身行伍，曾任〔橫野中郎將〕，曾被議為莽夫，因而勤學，故有〔非復吳下阿蒙〕之語。',
  C8: '董卓將領，曾助董卓以厚禮說服呂布投效其下。',
  S9: '魏名將，萬夫之勇，破蜀先鋒。',
  H9: '蜀國大將，長阪之戰，救劉備阿斗，一身是膽，英勇無雙。',
  D9: '運籌帷幄，決勝千里，為文武兼備之吳國大將。',
  C9: '董卓之大將，衝鋒陷陣，殺敵無數。',
  S10: '魏國猛將，力大無窮，被稱為〔虎痴〕。',
  H10: '性如火，聲如雷，曾經獨自喝退曹軍雄兵。',
  D10: '吳將，濡須之戰救孫權時，身中數十槍，面不改色，毫無所懼。',
  C10: '勇貫三軍，有忠義之氣，後被曹操軍俘虜，曾助關羽。',
  SJ: '曹操姻親，與呂布作戰時遭流箭刺瞎左眼，是曹操陣營中的大將。',
  HJ: '神勇威武，義氣浩然，與劉備、張飛桃園三結義，被稱為〔萬人敵〕。',
  DJ: '吳國大將，智多謀，英勇雙全，曾任江東水陸總督。',
  CJ: '氣宇軒昂，羽扇綸巾，驍銳善戰，為董卓之義子。',
  X1: '本卡使用時，可將敵軍將領、士兵、武器、陣勢卡及領地占為己有。',
  X2: '本卡使用時，可將敵軍將領、士兵、武器、陣勢卡及領地占為己有。',
};

/* 人物特徵
 *  body: armor 鎧甲 | robe 長袍 | lady 女裝
 *  face 膚色、hat [樣式, 主色, 副色]、hair [樣式, 色]、beard [樣式, 色]、cloth [主色, 副色]
 *  brow: kind 溫和 | thick 粗眉 | angry 怒眉；eyes: glasses 墨鏡 | goggles 護目鏡 | eyepatch 眼罩 | wink 眨眼 | mask 面罩
 *  mouth: smile | grin | open | laugh | frown；weapon 兵器；ride 坐騎 */
const FIG = {
  SA: { body: 'armor', hat: ['round', '#2b5fc1', '#f2c200'], eyes: 'glasses', cloth: ['#d63a2a', '#2b5fc1'], ride: 'moto', beard: ['goatee', '#2b2b2b'], mouth: 'grin' },
  HA: { body: 'robe', hat: ['crown', '#1f3f8f', '#f2c200'], cloth: ['#f2c200', '#c0392b'], beard: ['long', '#2b2b2b'], fold: 1, brow: 'kind' },
  DA: { body: 'armor', hat: ['helm', '#c0392b', '#f2c200'], cloth: ['#c0392b', '#2b5fc1'], weapon: 'spear', ride: 'rock', mouth: 'smile' },
  CA: { body: 'robe', hat: ['cap', '#e84393', '#f1c40f'], fat: 1, cloth: ['#3b4a3a', '#8b6d3a'], ride: 'tank', beard: ['mustache', '#2b2b2b'], brow: 'angry', mouth: 'frown' },
  // 2 點：身懷異術者
  // 黃承彥：白髮老者，持杖，身旁八陣圖亂石飛轉
  S2: { body: 'robe', old: 1, hat: ['scholar', '#4e5b31', '#f1c40f'], cloth: ['#6b7f3a', '#f5f0e1'], beard: ['long', '#e8e8e8'], weapon: 'staff', stones: 1, brow: 'kind', mouth: 'smile' },
  // 木鹿大王：南蠻洞主，膚黑亂髮，豹皮披風，手持三股叉
  H2: { body: 'robe', fat: 1, face: '#9c6b3f', hair: ['wild', '#141414'], beard: ['full', '#111111'], cloth: ['#7a4a22', '#f1c40f'], weapon: 'fork', cape: '#d9a93a', leo: 1, bare: 1, tattoo: 1, brow: 'angry', mouth: 'open' },
  // 于吉：白髮道士，持杖，腳踏祥雲
  D2: { body: 'robe', old: 1, hat: ['daoist', '#6d4c2f', '#f1c40f'], cloth: ['#e8e2d0', '#6d4c2f'], beard: ['long', '#e8e8e8'], weapon: 'staff', cloud: 1, brow: 'kind' },
  // 張角：黃巾黃袍，仗劍作法，風起雲湧
  C2: { body: 'robe', hat: ['band', '#f1c40f'], cloth: ['#f1c40f', '#8b1a1a'], beard: ['full', '#1b1b1b'], weapon: 'jian', charm: 1, brow: 'angry', mouth: 'open' },
  S3: { body: 'armor', hat: ['round', '#2b5fc1', '#f2c200'], cloth: ['#2e86de', '#f1c40f'], weapon: 'hammer', brow: 'angry', mouth: 'open' },
  H3: { body: 'robe', hat: ['scholar', '#1f3f8f', '#f2c200'], fat: 1, cloth: ['#3c6fd1', '#e67e22'], weapon: 'spear', ride: 'skate', beard: ['mustache', '#2b2b2b'], mouth: 'smile' },
  D3: { body: 'armor', hat: ['tall', '#c0392b', '#f1c40f'], cloth: ['#c0392b', '#27ae60'], weapon: 'staff', mouth: 'open', brow: 'thick' },
  C3: { body: 'lady', hair: ['bun', '#1b1b1b'], cloth: ['#e74c3c', '#f8c8dc'], mouth: 'smile', brow: 'kind' },
  S4: { body: 'armor', hat: ['cat', '#f1c40f', '#e74c3c'], cloth: ['#e67e22', '#2c3e50'], weapon: 'sling', braid: '#c0392b', eyes: 'wink' },
  H4: { body: 'armor', hat: ['band', '#e67e22'], cloth: ['#2c3e50', '#e67e22'], shield: '#c0392b', mouth: 'laugh', weapon: 'spear' },
  D4: { body: 'robe', hair: ['bald'], cloth: ['#e84393', '#3498db'], weapon: 'axe', beard: ['goatee', '#eeeeee'], old: 1, mouth: 'smile', brow: 'thick' },
  C4: { body: 'armor', hat: ['round', '#2b5fc1', '#e74c3c'], eyes: 'goggles', cloth: ['#c0392b', '#16a085'], weapon: 'bow' },
  S5: { body: 'robe', hat: ['mouse', '#c0392b'], cloth: ['#222222', '#f1c40f'], tail: 1, mouth: 'laugh' },
  H5: { body: 'robe', hat: ['scholar', '#c0392b', '#f1c40f'], cloth: ['#c0392b', '#2b5fc1'], beard: ['long', '#f2f2f2'], old: 1, fold: 1, brow: 'kind', eyes: 'closed' },
  D5: { body: 'armor', hat: ['helm', '#f39c12', '#2b5fc1'], cloth: ['#f1c40f', '#e74c3c'], beard: ['mustache', '#2b2b2b'], mouth: 'smile' },
  C5: { body: 'robe', hat: ['cap', '#c0392b', '#f1c40f'], cloth: ['#c0392b', '#f1c40f'], beard: ['goatee', '#dddddd'], old: 1, fold: 1, brow: 'kind' },
  S6: { body: 'armor', hat: ['horn', '#2b5fc1', '#ffffff'], cloth: ['#2b5fc1', '#e74c3c'], ride: 'trike', weapon: 'teapot', beard: ['full', '#1b1b1b'], brow: 'thick' },
  H6: { body: 'armor', hat: ['helm', '#3498db', '#ffffff'], cloth: ['#e74c3c', '#f1c40f'], beard: ['long', '#f5f5f5'], old: 1, weapon: 'bow', brow: 'thick' },
  D6: { body: 'robe', hair: ['topknot', '#1b1b1b'], cloth: ['#2b5fc1', '#f1c40f'], weapon: 'sword', eyes: 'wink', mouth: 'smile' },
  C6: { body: 'robe', hat: ['cap', '#27ae60', '#f1c40f'], fat: 1, cloth: ['#f5cba7', '#f1c40f'], shield: '#2b5fc1', weapon: 'axe', mouth: 'smile' },
  S7: { body: 'robe', face: '#ec8a78', hat: ['tall', '#c0392b', '#f1c40f'], cloth: ['#c0392b', '#2c3e50'], ride: 'chair', weapon: 'pipe', brow: 'angry', mouth: 'frown' },
  H7: { body: 'robe', hat: ['hood', '#2b5fc1'], cloth: ['#c0392b', '#f1c40f'], weapon: 'fan', beard: ['goatee', '#2b2b2b'], brow: 'kind' },
  D7: { body: 'robe', hair: ['white'], hat: ['cap', '#e74c3c', '#ffffff'], cloth: ['#e3ecf2', '#74b9ff'], beard: ['long', '#f2f2f2'], old: 1, brow: 'kind', eyes: 'closed' },
  C7: { body: 'robe', hat: ['bear', '#f1c40f'], eyes: 'glasses', cloth: ['#c0392b', '#2b5fc1'], weapon: 'staff', cape: '#c0392b', mouth: 'smile' },
  S8: { body: 'armor', hat: ['helm', '#f39c12', '#c0392b'], cloth: ['#e74c3c', '#f1c40f'], weapon: 'axe', sweat: 1, mouth: 'open' },
  H8: { body: 'armor', hair: ['topknot', '#2b5fc1'], cloth: ['#2b5fc1', '#e67e22'], weapon: 'bow', brow: 'thick' },
  D8: { body: 'armor', hair: ['buns', '#1b1b1b'], cloth: ['#2b5fc1', '#e74c3c'], weapon: 'sword', brow: 'angry', mouth: 'frown' },
  C8: { body: 'robe', face: '#ec8a78', hat: ['tall', '#f1c40f', '#c0392b'], cloth: ['#c0392b', '#2b5fc1'], weapon: 'spear', beard: ['mustache', '#1b1b1b'], brow: 'thick' },
  S9: { body: 'armor', hat: ['helm', '#f1c40f', '#c0392b'], cloth: ['#e74c3c', '#2b5fc1'], weapon: 'mace', brow: 'angry' },
  H9: { body: 'armor', hat: ['prop', '#2b5fc1', '#f1c40f'], cloth: ['#2c3e50', '#8e44ad'], weapon: 'sword', eyes: 'glasses', mouth: 'smile' },
  D9: { body: 'armor', hat: ['helm', '#2b5fc1', '#c0392b'], cloth: ['#2b5fc1', '#f1c40f'], beard: ['mustache', '#1b1b1b'], cape: '#f1c40f', brow: 'angry', mouth: 'frown' },
  C9: { body: 'armor', face: '#ec8a78', hat: ['tall', '#c0392b', '#2b5fc1'], cloth: ['#2b5fc1', '#c0392b'], ride: 'jet', beard: ['full', '#1b1b1b'], brow: 'angry' },
  S10: { body: 'armor', hair: ['ponytail', '#2b5fc1'], cloth: ['#c0392b', '#2b5fc1'], brow: 'angry', mouth: 'frown' },
  H10: { body: 'armor', face: '#b86048', hat: ['band', '#2b5fc1'], cloth: ['#2b5fc1', '#c0392b'], beard: ['full', '#111111'], weapon: 'snake', brow: 'angry', mouth: 'open' },
  D10: { body: 'armor', hat: ['horn', '#c0392b', '#ffffff'], hair: ['white'], cloth: ['#f1c40f', '#2b5fc1'], weapon: 'blade', sweat: 1, brow: 'thick' },
  C10: { body: 'armor', hair: ['bald'], cloth: ['#2c3e50', '#c0392b'], weapon: 'gun', cape: '#c0392b', heart: 1, brow: 'angry', mouth: 'grin' },
  SJ: { body: 'armor', face: '#ec8a78', hat: ['helm', '#c0392b', '#f1c40f'], eyes: 'eyepatch', cloth: ['#2b5fc1', '#c0392b'], weapon: 'blade', beard: ['full', '#1b1b1b'], brow: 'angry' },
  HJ: { body: 'robe', face: '#d8433a', hat: ['cap', '#27ae60', '#f1c40f'], cloth: ['#27ae60', '#f1c40f'], beard: ['long', '#111111'], weapon: 'guandao', brow: 'thick', eyes: 'narrow' },
  DJ: { body: 'armor', hat: ['helm', '#c0392b', '#f1c40f'], cloth: ['#27ae60', '#f39c12'], weapon: 'blade', beard: ['mustache', '#1b1b1b'], cape: '#9fe0a0', brow: 'thick' },
  CJ: { body: 'armor', hat: ['feather', '#c0392b', '#ffffff'], eyes: 'mask', cloth: ['#2c3e50', '#c0392b'], weapon: 'halberd' },
};

/* ---- 共用漸層與花紋（注入文件一次，各張牌以 url(#…) 引用） ---- */
const CARD_DEFS = `<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
  <linearGradient id="cgSh" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity=".42"/><stop offset=".38" stop-color="#fff" stop-opacity="0"/><stop offset=".7" stop-color="#000" stop-opacity=".08"/><stop offset="1" stop-color="#000" stop-opacity=".34"/></linearGradient>
  <linearGradient id="cgShV" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".4"/><stop offset=".45" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".3"/></linearGradient>
  <radialGradient id="cgFace" cx=".38" cy=".3" r=".8"><stop offset="0" stop-color="#fff" stop-opacity=".55"/><stop offset=".4" stop-color="#fff" stop-opacity="0"/><stop offset=".85" stop-color="#7a3b1c" stop-opacity=".16"/><stop offset="1" stop-color="#7a3b1c" stop-opacity=".32"/></radialGradient>
  <radialGradient id="cgBall" cx=".35" cy=".3" r=".75"><stop offset="0" stop-color="#fff" stop-opacity=".8"/><stop offset=".3" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".35"/></radialGradient>
  <radialGradient id="cgIris" cx=".5" cy=".62" r=".6"><stop offset="0" stop-color="#b0733a"/><stop offset=".55" stop-color="#5a2c10"/><stop offset="1" stop-color="#1e0d04"/></radialGradient>
  <linearGradient id="cgEyeW" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9fb4c8" stop-opacity=".6"/><stop offset=".4" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <radialGradient id="cgBlush" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ff6f7d" stop-opacity=".6"/><stop offset="1" stop-color="#ff6f7d" stop-opacity="0"/></radialGradient>
  <radialGradient id="cgHalo" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fff4c2" stop-opacity=".95"/><stop offset=".6" stop-color="#ffe7a0" stop-opacity=".45"/><stop offset="1" stop-color="#ffe7a0" stop-opacity="0"/></radialGradient>
  <radialGradient id="cgGround" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#3a2a10" stop-opacity=".38"/><stop offset="1" stop-color="#3a2a10" stop-opacity="0"/></radialGradient>
  <linearGradient id="cgHairSh" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".3" stop-color="#fff" stop-opacity=".28"/><stop offset=".42" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".25"/></linearGradient>
  <linearGradient id="cgMetal" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".4" stop-color="#c3cfd6"/><stop offset=".55" stop-color="#7f8e99"/><stop offset=".7" stop-color="#c9d4da"/><stop offset="1" stop-color="#f4f8fa"/></linearGradient>
  <linearGradient id="cgBlade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#eef3f6"/><stop offset=".48" stop-color="#ffffff"/><stop offset=".52" stop-color="#93a3ad"/><stop offset="1" stop-color="#cfd9df"/></linearGradient>
  <linearGradient id="cgGold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff8c4"/><stop offset=".35" stop-color="#f2c230"/><stop offset=".6" stop-color="#b9820a"/><stop offset="1" stop-color="#ffe680"/></linearGradient>
  <linearGradient id="cgBronze" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f3c27a"/><stop offset=".45" stop-color="#b8722e"/><stop offset="1" stop-color="#6e3a12"/></linearGradient>
  <linearGradient id="cgWood" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#b07a43"/><stop offset=".5" stop-color="#7a4a22"/><stop offset="1" stop-color="#5a3415"/></linearGradient>
  <linearGradient id="cgFire" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#d32f2f"/><stop offset=".5" stop-color="#ff9800"/><stop offset="1" stop-color="#ffee58"/></linearGradient>
  <radialGradient id="cgFireR" cx=".5" cy=".7" r=".6"><stop offset="0" stop-color="#fffde7"/><stop offset=".35" stop-color="#ffeb3b"/><stop offset=".7" stop-color="#ff9800"/><stop offset="1" stop-color="#e53935"/></radialGradient>
  <linearGradient id="cgGlass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4a5d7a"/><stop offset=".35" stop-color="#0d1420"/><stop offset=".6" stop-color="#1b2a44"/><stop offset="1" stop-color="#3d6a9a"/></linearGradient>
  <linearGradient id="cgLens" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".4" stop-color="#b2ebf2"/><stop offset="1" stop-color="#4fb3c8"/></linearGradient>
  <radialGradient id="cgGlowY" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fffde0"/><stop offset=".5" stop-color="#ffe14d"/><stop offset="1" stop-color="#ffb300"/></radialGradient>
  <radialGradient id="cgGlowB" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ffffff"/><stop offset=".45" stop-color="#7fe3ff"/><stop offset="1" stop-color="#1e88e5"/></radialGradient>
  <radialGradient id="cgAura" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset=".5" stop-color="#ff5252" stop-opacity=".45"/><stop offset="1" stop-color="#ff1744" stop-opacity="0"/></radialGradient>
  <radialGradient id="cgPoison" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ccff90" stop-opacity=".9"/><stop offset="1" stop-color="#64dd17" stop-opacity="0"/></radialGradient>
  <radialGradient id="cgSkinG" cx=".38" cy=".32" r=".75"><stop offset="0" stop-color="#d7f27a"/><stop offset=".6" stop-color="#9ccc3a"/><stop offset="1" stop-color="#5c8a1a"/></radialGradient>
  <linearGradient id="cgStorm" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6a4a8c"/><stop offset=".6" stop-color="#3d2456"/><stop offset="1" stop-color="#1e1030"/></linearGradient>
  <pattern id="cgScale" width="10" height="8" patternUnits="userSpaceOnUse"><path d="M0,8 q5,-9 10,0" fill="none" stroke="#000" stroke-opacity=".38" stroke-width="1.2"/><path d="M2,6 q3,-4 6,0" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width=".9"/></pattern>
  <pattern id="cgLam" width="8" height="7" patternUnits="userSpaceOnUse"><path d="M0,6.5 h8 M4,0 v6.5" stroke="#000" stroke-opacity=".35" stroke-width="1"/><path d="M1,1.5 h2 M5,1.5 h2" stroke="#fff" stroke-opacity=".45" stroke-width="1"/><circle cx="2" cy="4" r=".7" fill="#fff" fill-opacity=".6"/><circle cx="6" cy="4" r=".7" fill="#fff" fill-opacity=".6"/></pattern>
  <pattern id="cgCloth" width="14" height="14" patternUnits="userSpaceOnUse"><path d="M0,14 l14,-14" stroke="#fff" stroke-opacity=".1" stroke-width="3"/></pattern>
  <pattern id="cgBrocade" width="22" height="22" patternUnits="userSpaceOnUse"><path d="M4,11 a4,4 0 1,1 7,-3 a3,3 0 1,1 4,3" fill="none" stroke="#fff" stroke-opacity=".28" stroke-width="1.3"/><circle cx="17" cy="18" r="1.4" fill="#fff" fill-opacity=".3"/><path d="M15,4 l2,-2 l2,2 l-2,2z" fill="#fff" fill-opacity=".22"/></pattern>
  <pattern id="cgCloud" width="20" height="10" patternUnits="userSpaceOnUse"><path d="M1,9 q0,-6 5,-5 q1,-4 5,-2 q4,-1 4,3 q4,0 4,4" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="1.2"/></pattern>
  <pattern id="cgTread" width="8" height="8" patternUnits="userSpaceOnUse"><rect width="4" height="8" fill="#000" fill-opacity=".35"/></pattern>
  <pattern id="cgGrain" width="30" height="7" patternUnits="userSpaceOnUse"><path d="M0,2 q8,-2 15,0 t15,0 M0,5.5 q9,1.5 18,0 t12,0" stroke="#3e2108" stroke-opacity=".35" stroke-width=".8" fill="none"/></pattern>
  <pattern id="cgBar" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(30)"><rect width="9" height="4" fill="#3e2723" fill-opacity=".55"/></pattern>
  <linearGradient id="wmWater" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#bde6fb"/><stop offset=".45" stop-color="#48a3d8"/><stop offset="1" stop-color="#17537f"/></linearGradient>
  <linearGradient id="wmBanner" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#a9741a"/><stop offset=".16" stop-color="#f3cc4c"/><stop offset=".48" stop-color="#fff6c4"/><stop offset=".84" stop-color="#eebf33"/><stop offset="1" stop-color="#8d5f12"/></linearGradient>
  <linearGradient id="wmSteel" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#eaf3f8"/><stop offset=".35" stop-color="#8fa6b4"/><stop offset=".58" stop-color="#46606f"/><stop offset=".78" stop-color="#9fb6c4"/><stop offset="1" stop-color="#e4eef4"/></linearGradient>
  <radialGradient id="wmSmoke" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#e8f5c8" stop-opacity=".9"/><stop offset=".5" stop-color="#aed581" stop-opacity=".42"/><stop offset="1" stop-color="#9ccc65" stop-opacity="0"/></radialGradient>
  <radialGradient id="wmWine" cx=".4" cy=".3" r=".8"><stop offset="0" stop-color="#8d6e3a"/><stop offset=".55" stop-color="#5d4a1e"/><stop offset="1" stop-color="#2e2408"/></radialGradient>
  <pattern id="wmLeo" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M4,5 q6,-4 8,1 q2,6 -5,6 q-6,0 -3,-7z" fill="#2b1a10" fill-opacity=".5"/><path d="M13,14 q5,-3 6,2 q0,5 -5,4 q-4,-1 -1,-6z" fill="#2b1a10" fill-opacity=".42"/><path d="M1,15 q3,-2 4,1 q0,3 -3,3 q-3,-1 -1,-4z" fill="#2b1a10" fill-opacity=".35"/></pattern>
  <pattern id="wmChain" width="16" height="10" patternUnits="userSpaceOnUse"><ellipse cx="8" cy="5" rx="6" ry="3.4" fill="none" stroke="#4a5a63" stroke-width="2.6"/><ellipse cx="8" cy="5" rx="6" ry="3.4" fill="none" stroke="#cfdbe2" stroke-width="1"/></pattern>
</defs></svg>`;
function ensureCardDefs() {
  if (typeof document === 'undefined' || document.getElementById('cgSh')) return;
  const holder = document.createElement('div'); holder.innerHTML = CARD_DEFS;
  (document.body || document.documentElement).appendChild(holder.firstChild);
}

/* ---- 繪圖小工具 ---- */
const OL = '#2a1a10';
const st = (w = 2.4) => `stroke="${OL}" stroke-width="${w}" stroke-linejoin="round" stroke-linecap="round"`;
// 填色＋描邊，再疊一層明暗漸層
const shp = (d, fill, sh = 'cgSh', w) => `<path d="${d}" fill="${fill}" ${st(w)}/>` + (sh ? `<path d="${d}" fill="url(#${sh})"/>` : '');
const fl = (d, fill, op) => `<path d="${d}" fill="${fill}"${op != null ? ` fill-opacity="${op}"` : ''}/>`;
const elp = (cx, cy, rx, ry) => `M${cx - rx},${cy} a${rx},${ry} 0 1,0 ${2 * rx},0 a${rx},${ry} 0 1,0 ${-2 * rx},0z`;
const E = (cx, cy, rx, ry, fill, sh = 'cgSh', w) => shp(elp(cx, cy, rx, ry), fill, sh, w);
const EF = (cx, cy, rx, ry, fill, op) => fl(elp(cx, cy, rx, ry), fill, op);
const line = (x1, y1, x2, y2, c = OL, w = 2.4) => `<path d="M${x1},${y1} L${x2},${y2}" stroke="${c}" stroke-width="${w}" stroke-linecap="round" fill="none"/>`;
const curve = (d, c = OL, w = 2.4, op) => `<path d="${d}" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" fill="none"${op != null ? ` stroke-opacity="${op}"` : ''}/>`;
// 以 x=ax 為軸左右鏡射
const mir = (svg, ax = 125) => `<g transform="matrix(-1,0,0,1,${2 * ax},0)">${svg}</g>`;
const both = (svg, ax = 125) => svg + mir(svg, ax);
// 依折線產生粗細漸變的肢體
function limb(p, w0, w1, fill, sh = 'cgSh', sw = 2.4) {
  const n = p.length, L = [], Rr = [];
  for (let i = 0; i < n; i++) {
    const a = p[Math.max(0, i - 1)], b = p[Math.min(n - 1, i + 1)];
    let dx = b[0] - a[0], dy = b[1] - a[1]; const len = Math.hypot(dx, dy) || 1; dx /= len; dy /= len;
    const w = (w0 + (w1 - w0) * i / (n - 1)) / 2;
    L.push([p[i][0] - dy * w, p[i][1] + dx * w]); Rr.push([p[i][0] + dy * w, p[i][1] - dx * w]);
  }
  const d = n === 3 ? `M${L[0]} Q${L[1]} ${L[2]} L${Rr[2]} Q${Rr[1]} ${Rr[0]}z` : `M${L.join(' L')} L${Rr.reverse().join(' L')}z`;
  return shp(d, fill, sh, sw);
}
// 直桿：直線的外框寬度為零，漸層無法套用，改用實色加高光線
const shaft = (x0, y0, x1, y1, wd = 6, col = '#8a5a2b', hi = '#c48a4f', rings = '#c9a227') => `<path d="M${x0},${y0} L${x1},${y1}" stroke="${OL}" stroke-width="${wd + 3}" stroke-linecap="round"/><path d="M${x0},${y0} L${x1},${y1}" stroke="${col}" stroke-width="${wd}" stroke-linecap="round"/><path d="M${x0 - wd / 4},${y0} L${x1 - wd / 4},${y1}" stroke="${hi}" stroke-width="${wd / 3}" stroke-linecap="round"/>`
  + (rings ? [0.2, 0.45, 0.7].map(t => `<path d="M${x0 + (x1 - x0) * t - wd / 2 - 1},${y0 + (y1 - y0) * t} h${wd + 2}" stroke="${OL}" stroke-width="4.2"/><path d="M${x0 + (x1 - x0) * t - wd / 2 - .5},${y0 + (y1 - y0) * t} h${wd + 1}" stroke="${rings}" stroke-width="2.6"/>`).join('') : '');
const tassel = (cx, cy, c, len = 26) => [-6, -3, 0, 3, 6].map(dx => curve(`M${cx + dx * .6},${cy} q${dx * 1.2},${len * .5} ${dx * .4},${len + Math.abs(dx) * -.6}`, c, 2.6)).join('')
  + curve(`M${cx - 3},${cy + 4} q${-2},${len * .5} 0,${len - 4}`, '#fff', 1, .45) + E(cx, cy, 7, 4, 'url(#cgGold)', null, 1.4) + E(cx, cy - 4, 3, 3, c, null, 1.2);
const beast = (cx, cy, r) => E(cx, cy, r * 1.15, r * 1.05, '#c9861a', null, 1.4) + [0, 45, 90, 135, 180, 225, 270, 315].map(a => { const t = a * Math.PI / 180; return E(cx + r * Math.cos(t), cy + r * .95 * Math.sin(t), r * .3, r * .3, '#e0a52a', null, .8); }).join('')
  + E(cx, cy, r * .8, r * .75, 'url(#cgGold)', null, 1.2) + E(cx - r * .32, cy - r * .12, r * .14, r * .14, OL, null, 0) + E(cx + r * .32, cy - r * .12, r * .14, r * .14, OL, null, 0)
  + curve(`M${cx - r * .55},${cy - r * .35} l${r * .35},${r * .12} M${cx + r * .55},${cy - r * .35} l${-r * .35},${r * .12}`, '#7a4a00', 1) + shp(`M${cx - r * .38},${cy + r * .2} q${r * .38},${r * .45} ${r * .76},0z`, '#8b1a1a', null, 1)
  + fl(`M${cx - r * .3},${cy + r * .22} l${r * .1},${r * .2} l${r * .1},${-r * .2}z M${cx + r * .3},${cy + r * .22} l${-r * .1},${r * .2} l${-r * .1},${-r * .2}z`, '#fff');
const star4 = (cx, cy, r, c = '#fff') => fl(`M${cx},${cy - r} Q${cx + r * .18},${cy - r * .18} ${cx + r},${cy} Q${cx + r * .18},${cy + r * .18} ${cx},${cy + r} Q${cx - r * .18},${cy + r * .18} ${cx - r},${cy} Q${cx - r * .18},${cy - r * .18} ${cx},${cy - r}z`, c);

const HX = 125, HY = 118;

/* ---- 兵器（以右手 x,y 為握點） ---- */
function weaponSvg(w, x, y) {
  switch (w) {
    case 'spear': return shaft(x + 4, 312, x + 4, 72) + tassel(x + 4, 82, '#e53935')
      + shp(`M${x + 4},28 q8,18 10,34 q-4,6 -10,10 q-6,-4 -10,-10 q2,-16 10,-34z`, 'url(#cgBlade)', null, 2) + curve(`M${x + 4},34 v34`, '#7f8e99', 1.2) + shp(`M${x - 4},70 h16 l-3,7 h-10z`, 'url(#cgGold)', null, 1.6);
    case 'snake': return shaft(x + 4, 312, x + 4, 76) + tassel(x + 4, 86, '#e53935')
      + shp(`M${x + 4},76 q-10,-8 0,-16 q10,-8 0,-16 q-8,-6 0,-14 l4,-12 l4,12 q8,8 0,14 q-10,8 0,16 q10,8 0,16z`, 'url(#cgBlade)', null, 2) + curve(`M${x + 6},72 q-8,-8 0,-16 q8,-8 0,-16 q-6,-6 2,-14`, '#7f8e99', 1.2)
      + shp(`M${x - 5},74 h18 l-3,8 h-12z`, 'url(#cgGold)', null, 1.6);
    case 'guandao': return shaft(x + 4, 318, x + 4, 76, 7, '#2e7d32', '#81c784') + shp(`M${x + 4},80 q-44,-20 -26,-70 q4,8 12,10 q-2,-8 4,-16 q16,30 16,76z`, 'url(#cgBlade)', null, 2.2)
      + curve(`M${x - 14},20 q-6,26 12,52`, '#8d9ba5', 1.6) + shp(`M${x + 4},50 q8,-10 2,-24 l6,4 q4,12 -4,22z`, 'url(#cgBlade)', null, 1.6)
      + shp(`M${x - 6},74 q10,-14 22,-2 q4,8 -4,12 q-8,-6 -18,-10z`, '#2e7d32', null, 1.6) + E(x + 8, 74, 2.2, 2.2, '#ffeb3b', null, .8)
      + curve(`M${x - 4},78 q-6,4 -4,10 M${x},80 q-3,6 0,10`, 'url(#cgGold)', 2) + tassel(x + 4, 92, '#e53935', 30) + E(x + 4, 316, 6, 4, 'url(#cgGold)', null, 1.4);
    case 'halberd': return shaft(x + 4, 316, x + 4, 66, 6, '#5d3a1a') + shp(`M${x + 4},18 q7,16 8,30 q-4,6 -8,8 q-4,-2 -8,-8 q1,-14 8,-30z`, 'url(#cgBlade)', null, 2)
      + shp(`M${x + 4},60 q-36,-10 -34,26 q8,-8 18,-10 q-4,8 0,14 q4,-12 16,-14z`, 'url(#cgBlade)', null, 2) + shp(`M${x + 4},60 q36,-10 34,26 q-8,-8 -18,-10 q4,8 0,14 q-4,-12 -16,-14z`, 'url(#cgBlade)', null, 2)
      + shp(`M${x - 4},56 h16 v8 h-16z`, 'url(#cgGold)', null, 1.6) + E(x + 4, 60, 3, 3, '#e53935', null, 1) + tassel(x + 4, 92, '#e53935');
    case 'sword': return `<g transform="rotate(-28 ${x} ${y})">` + shp(`M${x - 5},${y - 10} L${x - 5},${y - 96} L${x},${y - 110} L${x + 5},${y - 96} L${x + 5},${y - 10}z`, 'url(#cgBlade)', null, 2)
      + line(x, y - 16, x, y - 98, '#8d9ba5', 1.2) + shp(`M${x - 18},${y - 12} q18,-8 36,0 v6 q-18,-5 -36,0z`, 'url(#cgGold)', null, 1.8) + E(x, y - 10, 4, 4, '#e53935', null, 1)
      + shp(`M${x - 4},${y - 5} h8 v22 h-8z`, '#5d3a1a', null, 1.8) + curve(`M${x - 4},${y} l8,4 M${x - 4},${y + 6} l8,4 M${x - 4},${y + 12} l8,4`, '#c9a227', 1.4) + E(x, y + 20, 6, 6, 'url(#cgGold)', null, 1.8)
      + curve(`M${x},${y + 26} q-6,10 -2,20 M${x + 2},${y + 26} q4,10 2,18`, '#e53935', 2.4) + '</g>';
    case 'saber': return `<g transform="rotate(-24 ${x} ${y})">` + `<path d="M${x},${y - 14} L${x},${y - 120}" stroke="#ff1744" stroke-opacity=".35" stroke-width="18" stroke-linecap="round"/><path d="M${x},${y - 14} L${x},${y - 120}" stroke="#ff5252" stroke-width="9" stroke-linecap="round"/><path d="M${x},${y - 14} L${x},${y - 118}" stroke="#fff" stroke-width="3.5" stroke-linecap="round"/>`
      + shp(`M${x - 6},${y - 16} h12 v36 h-12z`, 'url(#cgMetal)', null, 1.8) + [0, 8, 16].map(k => line(x - 6, y - 6 + k, x + 6, y - 6 + k, '#222', 2)).join('') + shp(`M${x - 7},${y - 18} h14 v5 h-14z`, '#333', null, 1.4) + E(x + 3, y - 10, 1.6, 1.6, '#ff5252', null, 0) + '</g>';
    case 'blade': return shaft(x + 4, y + 34, x + 4, y - 58, 7) + shp(`M${x + 4},${y - 56} q42,-16 34,-86 q-8,10 -18,6 q-24,30 -16,80z`, 'url(#cgBlade)', null, 2.2)
      + curve(`M${x + 8},${y - 62} q22,-20 22,-68`, '#93a3ad', 1.3) + shp(`M${x + 20},${y - 120} l6,-4 l2,8z`, '#fff', null, 0) + shp(`M${x - 4},${y - 60} h16 v8 h-16z`, 'url(#cgGold)', null, 1.6) + E(x + 4, y - 56, 4, 3, '#e53935', null, 1)
      + tassel(x + 4, y - 48, '#e53935', 22);
    case 'axe': return shaft(x + 4, y + 34, x + 4, y - 92) + E(x + 4, y - 96, 5, 5, 'url(#cgGold)', null, 1.6)
      + shp(`M${x + 6},${y - 86} q24,-10 30,-22 q12,20 6,50 q-14,-8 -36,-6z`, 'url(#cgBlade)', null, 2.2) + curve(`M${x + 34},${y - 104} q8,18 4,40`, '#7f8e99', 1.4)
      + shp(`M${x + 2},${y - 84} q-16,0 -20,-10 q-4,12 0,24 q10,-6 20,-2z`, 'url(#cgBlade)', null, 2) + E(x + 18, y - 72, 4, 4, 'url(#cgGold)', null, 1.2) + shp(`M${x - 2},${y - 90} h12 v26 h-12z`, 'url(#cgGold)', null, 1.6);
    case 'fan': return `<g transform="rotate(12 ${x} ${y})">` + shp(`M${x - 3.5},${y + 2} h7 v-24 h-7z`, '#7a4a22', null, 1.8) + curve(`M${x - 3},${y - 4} h6 M${x - 3},${y - 10} h6`, '#c9a227', 1.4)
      + Array.from({ length: 9 }, (_, k) => { const a = (-60 + k * 15) * Math.PI / 180, L = 66; const tx = x + L * Math.sin(a), ty = y - 22 - L * Math.cos(a), mx = x + L * .5 * Math.sin(a), my = y - 22 - L * .5 * Math.cos(a);
        return shp(`M${x},${y - 22} Q${mx - 9 * Math.cos(a)},${my - 9 * Math.sin(a)} ${tx},${ty} Q${mx + 9 * Math.cos(a)},${my + 9 * Math.sin(a)} ${x},${y - 22}z`, k % 2 ? '#ffffff' : '#eef2f3', null, 1.4) + curve(`M${x},${y - 22} L${tx},${ty}`, '#9e9e9e', .9)
          + curve(`M${mx},${my} l${-6 * Math.cos(a) + 3 * Math.sin(a)},${-6 * Math.sin(a) - 3 * Math.cos(a)} M${mx},${my} l${6 * Math.cos(a) + 3 * Math.sin(a)},${6 * Math.sin(a) - 3 * Math.cos(a)}`, '#cfd8dc', .8); }).join('')
      + E(x, y - 22, 7, 5, 'url(#cgGold)', null, 1.4) + curve(`M${x},${y + 2} q-4,12 0,20 M${x},${y + 2} q4,12 2,22`, '#e53935', 2) + '</g>';
    case 'bow': return curve(`M${x + 14},${y - 84} q44,30 4,66 q40,34 -4,68`, OL, 9) + curve(`M${x + 14},${y - 84} q44,30 4,66 q40,34 -4,68`, '#a0682c', 5) + curve(`M${x + 16},${y - 80} q38,28 4,58`, '#d9a066', 1.6)
      + shp(`M${x + 12},${y - 26} h12 v16 h-12z`, '#c0392b', null, 1.6) + line(x + 14, y - 84, x + 10, y + 50, '#eee', 1.4) + E(x + 14, y - 84, 3, 3, 'url(#cgGold)', null, 1) + E(x + 10, y + 50, 3, 3, 'url(#cgGold)', null, 1)
      + line(x - 24, y - 18, x + 56, y - 18, OL, 4.5) + line(x - 24, y - 18, x + 56, y - 18, '#a0682c', 2.6) + shp(`M${x + 54},${y - 24} l16,6 l-16,6 l3,-6z`, 'url(#cgBlade)', null, 1.6)
      + shp(`M${x - 24},${y - 18} l-10,-8 h9 l6,8z M${x - 24},${y - 18} l-10,8 h9 l6,-8z`, '#e74c3c', null, 1.4);
    case 'hammer': return `<g transform="rotate(14 ${x} ${y})">` + shaft(x + 4, y + 26, x + 4, y - 70, 7) + shp(`M${x - 26},${y - 114} h60 a7,7 0 0 1 7,7 v34 a7,7 0 0 1 -7,7 h-60 a7,7 0 0 1 -7,-7 v-34 a7,7 0 0 1 7,-7z`, '#e67e22', 'cgShV', 2.4)
      + shp(`M${x - 33},${y - 104} h-6 v20 h6z M${x + 41},${y - 104} h6 v20 h-6z`, 'url(#cgMetal)', null, 1.8) + line(x - 22, y - 108, x + 30, y - 108, '#fff', 2) + E(x - 20, y - 76, 2, 2, OL, null, 0) + E(x + 28, y - 76, 2, 2, OL, null, 0)
      + `<text x="${x + 4}" y="${y - 84}" font-size="16" text-anchor="middle" fill="#fff" font-weight="900" stroke="${OL}" stroke-width="1" paint-order="stroke">1000</text></g>`;
    case 'mace': return curve(`M${x},${y} q24,-26 12,-62`, '#555', 3) + Array.from({ length: 7 }, (_, k) => E(x + 2 + k * 1.5, y - 8 - k * 9, 3.2, 2.6, 'url(#cgMetal)', null, 1)).join('')
      + [0, 45, 90, 135, 180, 225, 270, 315].map(a => { const r = a * Math.PI / 180; return shp(`M${x + 12 + 15 * Math.cos(r - .25)},${y - 80 + 15 * Math.sin(r - .25)} L${x + 12 + 27 * Math.cos(r)},${y - 80 + 27 * Math.sin(r)} L${x + 12 + 15 * Math.cos(r + .25)},${y - 80 + 15 * Math.sin(r + .25)}z`, 'url(#cgMetal)', null, 1.4); }).join('')
      + E(x + 12, y - 80, 18, 18, '#2b5fc1', 'cgSh', 2.2) + EF(x + 6, y - 86, 6, 4, '#fff', .5);
    case 'sling': return curve(`M${x + 4},${y + 14} v-26 l-14,-24 M${x + 4},${y - 12} l14,-24`, OL, 8) + curve(`M${x + 4},${y + 14} v-26 l-14,-24 M${x + 4},${y - 12} l14,-24`, '#a0682c', 4.5)
      + curve(`M${x - 10},${y - 36} q14,18 28,0`, '#c0392b', 2.5) + E(x + 4, y - 26, 5, 5, '#9e9e9e', 'cgSh', 1.4);
    case 'gun': return shp(`M${x - 10},${y - 12} h58 a5,5 0 0 1 5,5 v10 h-34 l-6,24 h-16 l4,-24 h-11z`, '#455a64', 'cgShV', 2.2) + shp(`M${x + 36},${y - 18} h18 v6 h-18z`, '#90a4ae', null, 1.5)
      + line(x - 4, y - 7, x + 44, y - 7, '#b0bec5', 1.5) + [0, 1, 2, 3].map(k => line(x + 18 + k * 6, y - 11, x + 18 + k * 6, y - 3, '#263238', 1.2)).join('') + E(x + 56, y - 6, 3, 3, '#ff5252', null, 1) + EF(x + 62, y - 6, 6, 3, '#ffeb3b', .6);
    case 'staff': return shaft(x + 4, 316, x + 4, 84, 6, '#6d4c2f') + shp(`M${x + 4},46 q-22,4 -18,26 q8,10 18,12 q12,-4 16,-16 q4,-20 -16,-22z`, 'url(#cgGold)', null, 2)
      + E(x + 4, 66, 7, 7, '#e53935', 'cgSh', 1.4) + E(x + 2, 64, 2, 2, '#fff', null, 0) + [-10, 0, 10].map(d => curve(`M${x + 4 + d},84 v6`, OL, 1.2) + E(x + 4 + d, 92, 3, 3, 'url(#cgGold)', null, 1)).join('');
    case 'pipe': return curve(`M${x + 2},${y - 4} Q${x + 18},${y - 18} ${x + 30},${y - 44}`, OL, 7) + curve(`M${x + 2},${y - 4} Q${x + 18},${y - 18} ${x + 30},${y - 44}`, '#6d4c41', 4)
      + shp(`M${x + 22},${y - 62} h18 v14 a9,9 0 0 1 -18,0z`, '#5d4037', 'cgSh', 2) + EF(x + 31, y - 62, 7, 2.4, '#ff7043', .95) + E(x + 2, y - 4, 3, 3, 'url(#cgGold)', null, 1)
      + curve(`M${x + 30},${y - 66} q-8,-12 4,-20 q12,-8 0,-20 q-8,-8 4,-14`, '#b0bec5', 3, .8);
      + EF(x - 60, y - 48, 6, 2, '#ff7043', .9) + curve(`M${x - 60},${y - 52} q-8,-12 4,-20 q12,-8 0,-20 q-8,-8 4,-14`, '#b0bec5', 3, .8) + E(x - 6, y - 4, 3, 3, 'url(#cgGold)', null, 1);
    case 'teapot': return curve(`M${x + 38},${y - 8} q10,-4 16,-16`, OL, 6) + curve(`M${x + 38},${y - 8} q10,-4 16,-16`, '#fff', 3) + curve(`M${x + 2},${y - 12} q-14,6 0,18`, OL, 4)
      + E(x + 20, y - 4, 21, 16, '#ffffff', 'cgSh', 2.4) + shp(`M${x + 8},${y - 18} q12,-6 24,0z`, '#e3f2fd', null, 1.8) + E(x + 20, y - 22, 4, 3, '#e74c3c', null, 1.4)
      + curve(`M${x + 6},${y - 2} q14,8 28,0`, '#2b5fc1', 2.4) + curve(`M${x + 12},${y + 4} q8,4 16,0`, '#2b5fc1', 1.4) + EF(x + 12, y - 10, 5, 3, '#fff', .8)
      + curve(`M${x + 56},${y - 28} q-6,-8 2,-14 q6,-6 0,-12`, '#cfd8dc', 2, .8);
    /* ---- 水滸傳新增兵器 ---- */
    // 禪杖：月牙鏟（魯智深、鄧元覺）
    case 'monkstaff': {
      const cx = x + 10;
      return shaft(cx, 318, cx, 88, 7, '#6d4c2f', '#a1763f', '#c9a227')
        + shp(`M${cx - 33},50 A33,33 0 0,0 ${cx + 33},50 L${cx + 17},50 A17,17 0 0,1 ${cx - 17},50z`, 'url(#cgMetal)', null, 2.4)
        + curve(`M${cx - 25},57 A25,25 0 0,0 ${cx + 25},57`, '#7f8e99', 1.8)
        + E(cx - 33, 50, 4, 4, 'url(#cgMetal)', null, 1.4) + E(cx + 33, 50, 4, 4, 'url(#cgMetal)', null, 1.4)
        + shp(`M${cx},8 q8,22 7,42 h-14 q-1,-20 7,-42z`, 'url(#cgBlade)', null, 2)
        + E(cx, 82, 11, 8, 'url(#cgGold)', null, 1.8) + EF(cx - 3, 80, 3, 2, '#fff', .7)
        + shp(`M${cx - 11},298 q11,-8 22,0 l-4,26 h-14z`, 'url(#cgMetal)', null, 2)
        + tassel(cx, 98, '#e53935', 26);
    }
    // 鋼叉：三股叉（解珍、阮小二）
    case 'fork': {
      const cx = x + 4;
      return shaft(cx, 316, cx, 80, 6, '#5d4037', '#8d6e63', null)
        + shp(`M${cx - 19},74 h38 l-4,13 h-30z`, 'url(#cgGold)', null, 1.8)
        + [[-16, 44], [0, 18], [16, 44]].map(([dx, ty]) => shp(`M${cx + dx - 6},76 L${cx + dx * 1.2},${ty} L${cx + dx + 6},76z`, 'url(#cgBlade)', null, 2)
          + curve(`M${cx + dx},72 L${cx + dx * 1.16},${ty + 10}`, '#93a3ad', 1.2)).join('')
        + tassel(cx, 94, '#e53935', 22);
    }
    // 蹴鞠：皮球（高俅）
    case 'ball': {
      const bx = x + 8, by = y - 34;
      return E(bx, by, 23, 23, '#c08a3e', 'cgSh', 2.4) + fl(elp(bx, by, 23, 23), 'url(#cgBall)')
        + [0, 72, 144, 216, 288].map(a => { const t = (a - 90) * Math.PI / 180; return line(bx + 9 * Math.cos(t), by + 9 * Math.sin(t), bx + 22 * Math.cos(t), by + 22 * Math.sin(t), '#7a4a22', 2); }).join('')
        + E(bx, by, 9, 9, '#a9762e', null, 1.6) + curve(`M${bx - 20},${by - 10} q6,-12 18,-14`, '#fff', 2, .5)
        + curve(`M${bx - 32},${by - 26} q12,-16 32,-18 M${bx + 30},${by + 14} q14,-8 18,-24`, '#c9a227', 2.4, .75)
        + star4(bx + 26, by - 30, 6, '#ffeb3b');
    }
    // 托塔：掌中寶塔（晁蓋）
    case 'pagoda': {
      const px = x + 16, base = y - 10;
      let g = shp(`M${px - 25},${base} h50 l-7,13 h-36z`, 'url(#cgBronze)', 'cgShV', 2.2) + curve(`M${px - 22},${base + 5} h44`, '#f3c27a', 1.6);
      for (let k = 0; k < 3; k++) {
        const w = 18 - k * 4, yy = base - 6 - k * 30;
        g += shp(`M${px - w},${yy} h${2 * w} v-20 h-${2 * w}z`, 'url(#cgGold)', 'cgShV', 2)
          + E(px, yy - 10, 4, 5.5, '#5d3a1a', null, 1.4)
          + shp(`M${px - w - 11},${yy - 20} q${w + 11},-4 ${2 * w + 22},0 l-6,-10 q-${w + 5},-3 -${2 * w + 10},0z`, '#b03a2e', 'cgShV', 2.2)
          + curve(`M${px - w - 13},${yy - 20} q${w + 13},-5 ${2 * w + 26},0`, '#f1c40f', 2.2);
      }
      const ty = base - 95;
      return g + shaft(px, ty + 8, px, ty - 14, 3.4, '#c9a227', '#fff8c4', null) + E(px, ty - 17, 5.5, 5.5, 'url(#cgGold)', null, 1.6)
        + EF(px, ty - 17, 20, 20, 'url(#cgHalo)') + star4(px + 16, ty - 4, 6, '#fff59d');
    }
    // 寶刀：單手彎刀（楊志、聞達）
    case 'dao': return `<g transform="rotate(13 ${x} ${y})">`
      + shp(`M${x - 7},${y - 16} C${x + 6},${y - 62} ${x + 17},${y - 98} ${x + 11},${y - 126} C${x + 32},${y - 92} ${x + 27},${y - 46} ${x + 9},${y - 16}z`, 'url(#cgBlade)', null, 2.2)
      + curve(`M${x},${y - 24} C${x + 11},${y - 60} ${x + 19},${y - 90} ${x + 13},${y - 116}`, '#93a3ad', 1.4)
      + shp(`M${x - 14},${y - 16} h28 a4,4 0 0 1 0,8 h-28 a4,4 0 0 1 0,-8z`, 'url(#cgGold)', null, 1.8)
      + shp(`M${x - 5},${y - 7} h11 v27 h-11z`, '#4e342e', null, 1.8) + Array.from({ length: 4 }, (_, k) => curve(`M${x - 5},${y - 3 + k * 7} l11,4`, '#c9a227', 1.3)).join('')
      + E(x, y + 25, 7, 7, 'url(#cgGold)', null, 2) + E(x, y + 25, 3, 3, '#5d3a1a', null, 0)
      + curve(`M${x + 6},${y + 28} q10,10 6,22 M${x + 10},${y + 28} q4,12 0,20`, '#e53935', 2.4) + '</g>';
    // 寶劍：直刃古劍（公孫勝、李成）
    case 'jian': return `<g transform="rotate(12 ${x} ${y})">`
      + shp(`M${x - 7},${y - 18} L${x - 7},${y - 110} L${x},${y - 130} L${x + 7},${y - 110} L${x + 7},${y - 18}z`, 'url(#cgBlade)', null, 2.2)
      + line(x, y - 24, x, y - 116, '#8d9ba5', 1.4) + curve(`M${x - 4},${y - 30} v-80`, '#ffffff', 1.4, .7)
      + shp(`M${x - 18},${y - 20} q18,-7 36,0 l-2,9 q-16,-5 -32,0z`, 'url(#cgGold)', null, 1.8)
      + shp(`M${x - 5},${y - 11} h11 v28 h-11z`, '#2e4a3a', null, 1.8) + Array.from({ length: 4 }, (_, k) => curve(`M${x - 5},${y - 6 + k * 7} l11,4`, '#c9a227', 1.3)).join('')
      + E(x, y + 22, 6.5, 6, 'url(#cgGold)', null, 1.8) + E(x, y + 22, 2.6, 2.6, '#8b1a1a', null, 0)
      + curve(`M${x + 5},${y + 26} q9,10 5,22 M${x + 9},${y + 26} q3,12 0,19`, '#f1c40f', 2.4) + '</g>';
    // 雙戒刀（武松）
    case 'twindao': { const one = weaponSvg('dao', x, y); return mir(one, HX) + one; }
    // 雙槍（董平）
    case 'twinspear': { const one = shaft(x + 4, 312, x + 4, 98, 6) + tassel(x + 4, 106, '#e53935', 18)
      + shp(`M${x + 4},54 q9,20 11,38 q-5,7 -11,11 q-7,-4 -11,-11 q2,-18 11,-38z`, 'url(#cgBlade)', null, 2)
      + curve(`M${x + 4},60 v38`, '#7f8e99', 1.2) + shp(`M${x - 5},96 h18 l-3,8 h-12z`, 'url(#cgGold)', null, 1.6);
      return mir(one, HX) + one; }
    // 鋼鞭：竹節鞭（呼延灼）
    case 'whip': return `<g transform="rotate(20 ${x} ${y})">`
      + shp(`M${x - 6},${y + 18} h12 v-28 h-12z`, '#4e342e', null, 1.8) + curve(`M${x - 6},${y + 10} h12 M${x - 6},${y + 2} h12`, '#c9a227', 1.3)
      + Array.from({ length: 9 }, (_, k) => { const w = 7.4 - k * .35, yy = y - 10 - k * 11; return shp(`M${x - w},${yy} h${2 * w} v-11 h-${2 * w}z`, 'url(#wmSteel)', null, 1.6) + curve(`M${x - w - 1},${yy - 11} h${2 * w + 2}`, '#cfdbe2', 1.2, .8); }).join('')
      + E(x, y - 112, 5, 4, 'url(#cgMetal)', null, 1.4) + E(x, y - 8, 9, 4, 'url(#cgGold)', null, 1.6) + '</g>';
    case 'whips': { const one = weaponSvg('whip', x, y); return mir(one, HX) + one; }
    // 狼牙棒（秦明）
    case 'club': {
      const cx = x + 4, hb = y - 44, ht = y - 112;
      const head = `M${cx - 12},${hb} q12,10 24,0 l-3,${ht - hb} q-9,-8 -18,0z`;
      return `<g transform="rotate(16 ${x} ${y})">` + shaft(cx, y + 32, cx, hb + 4, 7, '#6d4c2f', '#a1763f', null)
        + Array.from({ length: 6 }, (_, k) => { const yy = hb - 6 - k * 11, w = 11.5 - k * .5;
          return shp(`M${cx - w},${yy + 5} L${cx - w - 14},${yy - 1} L${cx - w},${yy - 6}z`, 'url(#cgMetal)', null, 1.4) + shp(`M${cx + w},${yy + 5} L${cx + w + 14},${yy - 1} L${cx + w},${yy - 6}z`, 'url(#cgMetal)', null, 1.4); }).join('')
        + shp(`M${cx - 8},${ht + 4} l8,-20 l8,20z`, 'url(#cgMetal)', null, 1.6)
        + shp(head, '#7a4a22', 'cgShV', 2.4) + fl(head, 'url(#cgGrain)')
        + E(cx, hb, 13, 6, 'url(#cgGold)', null, 1.8) + curve(`M${cx - 5},${ht + 10} v${hb - ht - 16}`, '#c48a4f', 2, .6) + '</g>';
    }
    // 板斧（李逵雙斧）
    case 'bax': return `<g transform="rotate(15 ${x} ${y})">` + shaft(x + 4, y + 32, x + 4, y - 86, 6, '#6d4c2f', '#a1763f', null)
      + shp(`M${x + 8},${y - 84} C${x + 56},${y - 82} ${x + 60},${y - 18} ${x + 10},${y - 12} C${x + 21},${y - 40} ${x + 21},${y - 58} ${x + 8},${y - 84}z`, 'url(#cgMetal)', null, 2.4)
      + curve(`M${x + 16},${y - 74} C${x + 48},${y - 70} ${x + 50},${y - 26} ${x + 18},${y - 20}`, '#93a3ad', 1.6)
      + curve(`M${x + 50},${y - 66} q8,22 0,40`, '#ffffff', 1.8, .7)
      + shp(`M${x - 2},${y - 80} h11 v36 h-11z`, 'url(#cgGold)', null, 1.6) + E(x + 4, y - 88, 5, 5, 'url(#cgMetal)', null, 1.6)
      + shp(`M${x + 1},${y - 70} q-13,2 -15,-6 q-3,11 0,20 q7,-7 15,-5z`, 'url(#cgMetal)', null, 1.8)
      + E(x + 4, y - 36, 4, 4, 'url(#cgGold)', null, 1.4) + '</g>';
    case 'axes': { const one = weaponSvg('bax', x, y); return mir(one, HX) + one; }
    // 川弩／毒弩（燕青）
    case 'crossbow': return `<g transform="rotate(-12 ${x} ${y}) scale(1.16) translate(${-x * .138} ${-y * .138})">`
      + shp(`M${x - 30},${y - 7} h80 l-5,15 h-70 a7,7 0 0 1 -5,-15z`, 'url(#cgWood)', 'cgShV', 2.2) + fl(`M${x - 28},${y - 5} h76 l-4,11 h-68z`, 'url(#cgGrain)')
      + curve(`M${x + 42},${y - 36} q24,36 0,70`, OL, 9) + curve(`M${x + 42},${y - 36} q24,36 0,70`, '#8d6e63', 5.5) + curve(`M${x + 44},${y - 30} q18,28 0,56`, '#d9a066', 1.4)
      + line(x + 42, y - 36, x + 42, y + 34, '#eee', 1.6) + E(x + 42, y - 36, 4, 4, 'url(#cgGold)', null, 1.2) + E(x + 42, y + 34, 4, 4, 'url(#cgGold)', null, 1.2)
      + shp(`M${x + 4},${y - 4} h48 l14,5 l-14,5 h-48z`, '#a0682c', null, 1.6) + shp(`M${x + 64},${y - 2} l16,3 l-16,3z`, '#76ff03', null, 1.4)
      + shp(`M${x - 2},${y + 8} q3,12 -5,15 q-2,-8 -2,-15z`, '#5d4037', null, 1.8) + E(x - 20, y - 1, 5, 5, 'url(#cgGold)', null, 1.4)
      + curve(`M${x + 10},${y - 4} h30`, '#5d4037', 1.4) + '</g>';
    // 篙櫓（李俊）
    case 'oar': return shaft(x + 20, 292, x - 14, 68, 8, '#8a5a2b', '#c48a4f', null)
      + shp(`M${x + 20},288 q-17,8 -17,25 q0,17 17,23 q17,-6 17,-23 q0,-18 -17,-25z`, '#a1763f', 'cgShV', 2.2)
      + fl(`M${x + 20},288 q-17,8 -17,25 q0,17 17,23 q17,-6 17,-23 q0,-18 -17,-25z`, 'url(#cgGrain)')
      + curve(`M${x + 20},294 v40`, '#6d4c2f', 1.6) + E(x - 14, 68, 5, 5, 'url(#cgGold)', null, 1.4);
    // 文筆（宋江）
    case 'brush': return shaft(x + 4, y + 26, x + 4, y - 58, 7, '#3e2723', '#6d4c41', '#c9a227')
      + shp(`M${x - 7},${y - 56} h22 v-16 h-22z`, 'url(#cgGold)', null, 1.8) + curve(`M${x - 5},${y - 64} h18`, '#fff8c4', 1.4)
      + shp(`M${x + 4},${y - 128} q14,46 12,58 q-12,7 -24,0 q-2,-12 12,-58z`, '#f0e2c0', 'cgSh', 2.2)
      + fl(`M${x + 4},${y - 128} q6,20 7,30 q-7,4 -14,0 q-1,-10 7,-30z`, '#3e2723')
      + curve(`M${x - 2},${y - 104} q-3,16 -2,28 M${x + 10},${y - 104} q3,16 2,28`, '#b89a6a', 1.5, .8)
      + EF(x - 1, y - 100, 2, 14, '#fff', .18) + star4(x + 24, y - 104, 6, '#fff59d') + E(x + 4, y + 28, 5, 5, 'url(#cgGold)', null, 1.4);
    // 鉤鎌槍（徐寧）
    case 'hookspear': return weaponSvg('spear', x, y)
      + shp(`M${x + 2},70 q-16,-2 -25,-14 q-11,-14 -7,-28 q3,18 16,25 q9,5 16,5z`, 'url(#cgBlade)', null, 2)
      + curve(`M${x - 2},64 q-13,-4 -19,-15`, '#93a3ad', 1.3);
    // 三尖兩刃刀（史進）
    case 'sanjian': return shaft(x + 4, 316, x + 4, 92, 7, '#5d3a1a', '#8d6e63', '#c9a227')
      + shp(`M${x + 4},12 L${x + 15},46 L${x + 34},26 L${x + 18},62 L${x + 4},94 L${x - 10},62 L${x - 26},26 L${x - 7},46z`, 'url(#cgBlade)', null, 2.2)
      + curve(`M${x + 4},20 v68`, '#93a3ad', 1.6) + curve(`M${x + 8},44 l18,-14 M${x},44 l-18,-14`, '#93a3ad', 1.2)
      + shp(`M${x - 6},88 h20 v9 h-20z`, 'url(#cgGold)', null, 1.6) + tassel(x + 4, 104, '#e53935', 24);
    // 棗陽槊：金釘長槊（索超）
    case 'shuo': {
      const cx = x + 4, head = `M${cx - 15},100 q15,10 30,0 l-4,-64 q-11,-8 -22,0z`;
      return shaft(cx, 316, cx, 104, 7, '#5d3a1a', '#8d6e63', null)
        + shp(head, 'url(#wmSteel)', null, 2.6) + fl(head, 'url(#cgShV)')
        + [0, 1, 2, 3, 4].map(k => [-8, 0, 8].map(dx => E(cx + dx, 92 - k * 14, 3.8, 3.8, 'url(#cgGold)', null, 1.2) + EF(cx + dx - 1.2, 90.6 - k * 14, 1.4, 1.4, '#fff')).join('')).join('')
        + E(cx, 101, 16, 7, 'url(#cgGold)', null, 2) + shp(`M${cx - 8},34 l8,-24 l8,24 q-8,5 -16,0z`, 'url(#cgMetal)', null, 2)
        + tassel(cx, 116, '#e53935', 22);
    }
    default: return '';
  }
}

/* ---- 帽盔 ---- */
function hatSvg(h, R) {
  const [type, c1, c2 = '#f1c40f'] = h;
  const top = HY - R;
  const studs = (y, n = 5, w = R * 1.4) => Array.from({ length: n }, (_, k) => E(HX - w / 2 + k * (w / (n - 1)), y, 3, 3, 'url(#cgGold)', null, 1.1) + EF(HX - w / 2 + k * (w / (n - 1)) - 1, y - 1, 1, 1, '#fff')).join('');
  const plume = (y0, c = '#e53935') => shp(`M${HX - 4},${y0} h8 l-1,-14 h-6z`, 'url(#cgGold)', null, 1.6) + E(HX, y0 - 15, 5, 4, 'url(#cgGold)', null, 1.4)
    + shp(`M${HX},${y0 - 18} q-20,-6 -12,-28 q4,10 8,6 q-2,-12 4,-18 q6,6 4,18 q4,4 8,-6 q8,22 -12,28z`, c, 'cgSh', 1.8) + curve(`M${HX - 5},${y0 - 24} q-2,-8 0,-14 M${HX + 4},${y0 - 24} q2,-8 0,-14`, '#fff', 1, .5);
  switch (type) {
    case 'round': return both(shp(`M${HX - R - 1},${HY - 6} q-6,16 2,28 q8,-8 8,-26z`, c1, 'cgSh', 1.8))
      + shp(`M${HX - R - 4},${HY - 2} q0,-${R + 18} ${R + 4},-${R + 18} q${R + 4},0 ${R + 4},${R + 18}z`, c1)
      + curve(`M${HX},${top - 18} q-22,10 -30,${R + 6} M${HX},${top - 18} q22,10 30,${R + 6} M${HX},${top - 18} v${R + 6}`, '#000', 1.4, .35)
      + [[-24, top + 4], [-30, top + 22], [24, top + 4], [30, top + 22], [0, top + 2], [0, top + 22]].map(([dx, yy]) => E(HX + dx, yy, 2.2, 2.2, 'url(#cgGold)', null, .8)).join('')
      + EF(HX - 20, top - 4, 12, 7, '#fff', .35)
      + shp(`M${HX - R - 8},${HY - 12} h${2 * R + 16} a6,6 0 0 1 0,12 h-${2 * R + 16} a6,6 0 0 1 0,-12z`, c2, 'cgShV') + studs(HY - 6, 7, 2 * R + 6)
      + E(HX, HY - 9, 7, 7, '#e53935', 'cgSh', 1.6) + EF(HX - 2, HY - 11, 2, 2, '#fff')
      + E(HX, top - 18, 7, 7, 'url(#cgGold)', null, 1.8) + curve(`M${HX},${top - 26} q-6,-8 -2,-14 M${HX},${top - 26} q6,-8 2,-14 M${HX},${top - 26} v-16`, '#e53935', 3);
    case 'helm': return both(shp(`M${HX - R - 6},${HY - 10} q-8,22 2,40 q10,-4 14,-14 q-8,-10 -6,-26z`, c1, 'cgSh', 1.8) + curve(`M${HX - R - 6},${HY + 2} q4,4 10,2 M${HX - R - 4},${HY + 12} q4,4 10,2`, '#000', 1, .4))
      + shp(`M${HX - R - 7},${HY + 2} q-4,-${R + 24} ${R + 7},-${R + 26} q${R + 11},2 ${R + 7},${R + 26} l-10,-6 q-${R - 6},-16 -${2 * R - 6},0z`, c1)
      + curve(`M${HX},${top - 24} v${R + 4}`, '#000', 2.4, .3) + curve(`M${HX + 2},${top - 24} v${R + 4}`, '#fff', 1.2, .5) + EF(HX - 22, top - 4, 12, 8, '#fff', .3)
      + shp(`M${HX - R + 2},${HY - 12} q${R - 2},-14 ${2 * R - 4},0 v9 q-${R - 2},-14 -${2 * R - 4},0z`, c2, 'cgShV', 1.8) + studs(HY - 9)
      + shp(`M${HX - 12},${HY - 18} l12,-12 l12,12 l-12,6z`, 'url(#cgGold)', null, 1.4) + E(HX, HY - 19, 3, 3, '#e53935', null, .8) + plume(top - 18);
    case 'horn': return hatSvg(['helm', c1, '#f1c40f'], R)
      + both(shp(`M${HX - 26},${top + 2} q-34,-8 -32,-44 q12,22 38,26z`, '#f5f0e1', 'cgSh') + curve(`M${HX - 34},${top - 2} l4,-6 M${HX - 42},${top - 8} l5,-5 M${HX - 50},${top - 18} l6,-3`, '#a1887f', 1.4) + E(HX - 26, top + 2, 6, 5, 'url(#cgGold)', null, 1.4));
    case 'cap': return shp(`M${HX - R + 2},${HY - 8} q-4,-${R + 14} ${R - 2},-${R + 14} q${R + 2},0 ${R - 2},${R + 14}z`, c1) + `<path d="M${HX - R + 2},${HY - 8} q-4,-${R + 14} ${R - 2},-${R + 14} q${R + 2},0 ${R - 2},${R + 14}z" fill="url(#cgBrocade)"/>`
      + curve(`M${HX - 18},${top - 4} q18,12 36,0 M${HX - 30},${top + 14} q6,-10 14,-12`, '#000', 1.2, .4)
      + shp(`M${HX - R},${HY - 15} h${2 * R} v12 h-${2 * R}z`, c2, 'cgShV', 1.8) + curve(`M${HX - R + 4},${HY - 9} h${2 * R - 8}`, '#fff', 1, .5)
      + shp(`M${HX + R - 10},${HY - 16} q24,-4 28,20 q-12,-6 -22,0z`, c1, 'cgSh', 1.8) + shp(`M${HX + R - 6},${HY - 12} q14,8 16,30 q-8,-6 -14,-6z`, c1, 'cgSh', 1.6)
      + E(HX, HY - 22, 8, 7, 'url(#cgGold)', null, 1.6) + E(HX, HY - 22, 4, 3.5, '#2ecc71', null, 1) + EF(HX - 1, HY - 23.5, 1.2, 1, '#fff');
    case 'tall': return shp(`M${HX - R + 8},${HY - 14} v-${R + 34} a8,8 0 0 1 8,-8 h${2 * R - 32} a8,8 0 0 1 8,8 v${R + 34}z`, c1, 'cgSh')
      + `<path d="M${HX - R + 8},${HY - 14} v-${R + 34} a8,8 0 0 1 8,-8 h${2 * R - 32} a8,8 0 0 1 8,8 v${R + 34}z" fill="url(#cgBrocade)"/>`
      + both(shp(`M${HX - R + 10},${HY - 18} v-${R + 30} h5 v${R + 30}z`, c2, null, 1.2)) + shp(`M${HX - R + 2},${top - 54} h${2 * R - 4} v7 h-${2 * R - 4}z`, c2, 'cgShV', 1.8)
      + shp(`M${HX - R + 2},${HY - 18} h${2 * R - 4} v12 h-${2 * R - 4}z`, c2, 'cgShV', 1.8) + E(HX, top - 18, 10, 10, c2, 'cgSh', 1.8) + E(HX, top - 18, 5, 5, '#e53935', 'cgSh', 1) + EF(HX - 1.5, top - 20, 1.5, 1.5, '#fff')
;
    case 'crown': return shp(`M${HX - R + 4},${HY - 6} q-2,-${R + 10} ${R - 4},-${R + 10} q${R},0 ${R - 4},${R + 10}z`, '#1b1b1b', 'cgHairSh')
      + shp(`M${HX - 28},${top + 4} l6,-26 l10,14 l12,-24 l12,24 l10,-14 l6,26z`, 'url(#cgGold)', null, 2) + [-18, 0, 18].map(dx => E(HX + dx, top - 4, 3.6, 3.6, dx ? '#2b5fc1' : '#e53935', 'cgSh', 1)).join('')
      + shp(`M${HX - 46},${top - 6} h92 l-4,7 h-84z`, c1, 'cgShV', 1.8) + curve(`M${HX - 44},${top - 3} h88`, '#f1c40f', 1)
      + Array.from({ length: 6 }, (_, k) => { const xx = HX - 40 + k * 16; return curve(`M${xx},${top + 1} v18`, '#c9a227', 1) + [6, 12, 18].map(dy => E(xx, top + dy, 2.2, 2.2, ['#e53935', '#f1c40f', '#2ecc71'][(k + dy / 6) % 3], null, .6)).join(''); }).join('')
      + shp(`M${HX - R},${HY - 15} h${2 * R} v10 h-${2 * R}z`, c1, 'cgShV', 1.8) + curve(`M${HX - R + 3},${HY - 10} h${2 * R - 6}`, '#f1c40f', 1.2)
      + both(curve(`M${HX - R - 2},${HY - 8} q-6,20 -2,40`, '#c0392b', 2.4) + E(HX - R - 2, HY + 34, 3, 3, 'url(#cgGold)', null, 1));
    case 'scholar': return shp(`M${HX - R + 6},${HY - 10} v-${R - 4} a10,10 0 0 1 10,-10 h${2 * R - 32} a10,10 0 0 1 10,10 v${R - 4}z`, c1, 'cgSh')
      + `<path d="M${HX - R + 6},${HY - 10} v-${R - 4} a10,10 0 0 1 10,-10 h${2 * R - 32} a10,10 0 0 1 10,10 v${R - 4}z" fill="url(#cgBrocade)"/>`
      + both(shp(`M${HX - R + 6},${top + 2} h-36 a4.5,4.5 0 0 1 0,-9 h36z`, c1, 'cgShV', 1.8) + E(HX - R - 30, top - 2.5, 3, 3, c2, null, 1))
      + shp(`M${HX - R + 2},${HY - 16} h${2 * R - 4} v10 h-${2 * R - 4}z`, c2, 'cgShV', 1.8) + shp(`M${HX - 14},${top - 4} h28 v8 h-28z`, c2, 'cgShV', 1.4) + E(HX, top, 4, 3, '#e53935', null, 1);
    case 'hood': return shp(`M${HX - R - 10},${HY + 40} q-12,-${R + 50} ${R + 10},-${R + 38} q${R + 22},-10 ${R + 10},${R + 38} l-12,-8 q6,-${R + 10} -${R - 2},-${R + 10} q-${R - 8},0 -${R - 2},${R + 10}z`, c1)
      + `<path d="M${HX - R - 10},${HY + 40} q-12,-${R + 50} ${R + 10},-${R + 38} q${R + 22},-10 ${R + 10},${R + 38} l-12,-8 q6,-${R + 10} -${R - 2},-${R + 10} q-${R - 8},0 -${R - 2},${R + 10}z" fill="url(#cgBrocade)"/>`
      + curve(`M${HX - R - 4},${HY + 20} q-6,-30 6,-50 M${HX + R + 4},${HY + 20} q6,-30 -6,-50 M${HX - 10},${top - 6} q-20,10 -30,40 M${HX + 10},${top - 6} q20,10 30,40`, '#000', 1.2, .4)
      + shp(`M${HX - R + 2},${HY - 22} q${R - 2},-16 ${2 * R - 4},0 v8 q-${R - 2},-16 -${2 * R - 4},0z`, '#1f3f8f', 'cgShV', 1.6) + shp(`M${HX - 12},${top - 6} q12,-10 24,0 v8 h-24z`, '#1f3f8f', null, 1.6)
      + shp(`M${HX + R + 2},${HY + 30} q14,14 10,36 q-6,-10 -12,-14z M${HX + R - 4},${HY + 34} q4,18 -4,34 q-2,-12 -4,-16z`, c1, 'cgSh', 1.6);
    case 'band': return shp(`M${HX - R - 2},${HY - 8} q${R + 2},-${R + 22} ${2 * R + 4},0 q-${R + 2},-14 -${2 * R + 4},0z`, '#1b1b1b', 'cgHairSh')
      + curve(`M${HX - 20},${top + 2} q6,-10 16,-12 M${HX + 4},${top} q10,-8 20,-4 M${HX - 34},${top + 16} q6,-10 12,-12`, '#555', 1.4)
      + shp(`M${HX - R - 4},${HY - 21} h${2 * R + 8} v13 h-${2 * R + 8}z`, c1, 'cgShV', 2) + curve(`M${HX - R},${HY - 14} h${2 * R}`, '#fff', 1, .4)
      + E(HX, HY - 15, 7, 6, 'url(#cgGold)', null, 1.4) + shp(`M${HX + R},${HY - 16} q22,-4 32,16 q-12,-4 -18,6 q-6,-14 -14,-16z`, c1, 'cgSh', 1.8)
      + shp(`M${HX + R + 4},${HY - 12} q14,10 12,32 q-8,-8 -16,-10z`, c1, 'cgSh', 1.8);
    case 'mouse': return E(HX - R + 2, top + 4, 25, 25, c1) + E(HX + R - 2, top + 4, 25, 25, c1) + E(HX - R + 2, top + 6, 14, 14, '#f8bbd0', 'cgSh', 1.2) + E(HX + R - 2, top + 6, 14, 14, '#f8bbd0', 'cgSh', 1.2)
      + EF(HX - R - 6, top - 6, 6, 4, '#fff', .45) + EF(HX + R - 10, top - 6, 6, 4, '#fff', .45)
      + shp(`M${HX - R + 2},${HY - 4} q-2,-${R + 6} ${R - 2},-${R + 6} q${R},0 ${R - 2},${R + 6} q-${R - 2},-20 -${2 * R - 4},0z`, '#1b1b1b', 'cgHairSh')
      + curve(`M${HX - 6},${top - 2} q-10,14 -24,18 M${HX + 4},${top - 2} q8,12 22,16 M${HX},${top} q-2,12 -8,20`, '#555', 1.3);
    case 'bear': return E(HX - R + 8, top + 6, 15, 15, c1) + E(HX + R - 8, top + 6, 15, 15, c1) + E(HX - R + 8, top + 8, 7, 7, '#c0392b', 'cgSh', 1) + E(HX + R - 8, top + 8, 7, 7, '#c0392b', 'cgSh', 1)
      + shp(`M${HX - R - 2},${HY - 4} q${R + 2},-${R + 24} ${2 * R + 4},0 q-${R + 2},-10 -${2 * R + 4},0z`, c1) + curve(`M${HX - R},${HY - 6} q${R},-10 ${2 * R},0`, '#fff', 3, .6) + studs(HY - 14, 5)
      + E(HX, top - 6, 7, 6, 'url(#cgGold)', null, 1.4) + curve(`M${HX - 20},${top} q-4,10 -2,18 M${HX + 20},${top} q4,10 2,18`, '#000', 1, .3);
    case 'cat': return shp(`M${HX - R - 2},${HY - 4} q${R + 2},-${R + 22} ${2 * R + 4},0 q-${R + 2},-10 -${2 * R + 4},0z`, c1)
      + both(shp(`M${HX - R + 2},${HY - 22} l-7,-36 l26,20z`, c1) + shp(`M${HX - R + 6},${HY - 28} l-2,-18 l11,9z`, '#f8bbd0', null, 1)) + studs(HY - 12, 5)
      + both(curve(`M${HX - 30},${HY - 18} q-10,-2 -18,2 M${HX - 30},${HY - 14} q-10,2 -16,8`, '#7a4a00', 1.2))
      + E(HX, top - 4, 9, 9, c2, 'cgSh', 1.8) + E(HX, top - 4, 4, 4, '#fff59d', null, 1) + EF(HX - 20, top + 2, 10, 6, '#fff', .35);
    case 'prop': return hatSvg(['round', c1, '#f1c40f'], R).replace(/<path d="M125,\d+ q-6,-8[^>]*>/, '') + shaft(HX, top - 20, HX, top - 34, 3, '#90a4ae', '#fff', null)
      + E(HX - 24, top - 36, 24, 6, c2, 'cgShV', 1.8) + E(HX + 24, top - 36, 24, 6, c2, 'cgShV', 1.8) + curve(`M${HX - 52},${top - 44} q-6,8 0,14 M${HX + 52},${top - 44} q6,8 0,14`, '#90a4ae', 1.4, .8)
      + E(HX, top - 36, 6, 6, '#e53935', 'cgSh', 1.5);
    case 'feather': return hatSvg(['helm', c1, '#f1c40f'], R)
      + both(shp(`M${HX - 12},${top - 10} q-44,-14 -60,-66 q6,2 9,7 q14,36 51,47z`, '#a1887f', null, 1.8) + `<path d="M${HX - 12},${top - 10} q-44,-14 -60,-66 q6,2 9,7 q14,36 51,47z" fill="url(#cgBar)"/>`
        + curve(`M${HX - 14},${top - 14} q-36,-14 -52,-56`, '#fff', 1, .6) + E(HX - 12, top - 10, 6, 6, '#e53935', null, 1.4))
      + E(HX, top - 6, 12, 10, 'url(#cgGold)', null, 1.6) + E(HX, top - 6, 6, 5, '#e53935', 'cgSh', 1);
    // 道冠：道士混元巾（公孫勝）
    case 'daoist': {
      const cap = `M${HX - R + 2},${HY - 10} q-2,-${R + 10} ${R - 2},-${R + 10} q${R},0 ${R - 2},${R + 10}z`;
      return both(shp(`M${HX - R - 2},${HY - 6} q-10,26 -4,52 q10,-6 12,-18 q-6,-14 -2,-30z`, c1, 'cgSh', 1.8))
        + shp(cap, c1) + fl(cap, 'url(#cgCloud)')
        + shp(`M${HX - 21},${top + 2} h42 v-20 a6,6 0 0 0 -6,-6 h-30 a6,6 0 0 0 -6,6z`, c1, 'cgSh', 2)
        + curve(`M${HX - 15},${top - 20} v22 M${HX},${top - 22} v24 M${HX + 15},${top - 20} v22`, '#000', 1.2, .35)
        + shp(`M${HX - R + 2},${HY - 17} h${2 * R - 4} v12 h-${2 * R - 4}z`, c2, 'cgShV', 1.8) + curve(`M${HX - R + 5},${HY - 11} h${2 * R - 10}`, '#fff', 1, .45)
        + E(HX, HY - 20, 11, 11, '#f5f5f5', null, 1.8) + `<path d="M${HX},${HY - 31} a5.5,5.5 0 0,1 0,11 a5.5,5.5 0 0,0 0,11 a11,11 0 0,1 0,-22" fill="#1b1b1b"/>`
        + E(HX, HY - 25.5, 1.9, 1.9, '#f5f5f5', null, 0) + E(HX, HY - 14.5, 1.9, 1.9, '#1b1b1b', null, 0)
        + both(curve(`M${HX - R + 4},${HY - 14} q-14,30 -8,58`, '#f5f0e1', 3.4) + curve(`M${HX - R + 2},${HY - 10} q-12,28 -7,52`, '#c9bfa6', 1.2));
    }
    default: return '';
  }
}

/* ---- 髮型（back 為臉後層、front 為臉前層） ---- */
function hairSvg(h, R, layer) {
  const [type, c = '#1b1b1b'] = h;
  if (layer === 'back') {
    if (type === 'bun') return shp(`M${HX - R - 8},${HY + 40} q-16,-${R + 34} ${R + 8},-${R + 26} q${R + 24},-8 ${R + 8},${R + 26} q-6,8 -14,4 q-${R - 6},6 -${2 * R - 12},0 q-8,4 -14,-4z`, c, 'cgHairSh')
      + curve(`M${HX - R},${HY + 30} q-6,-30 6,-60 M${HX + R},${HY + 30} q6,-30 -6,-60`, '#555', 1.2);
    if (type === 'ponytail') return shp(`M${HX + 14},${HY - R + 2} q44,-12 46,30 q-4,30 18,50 q-30,-2 -36,-30 q-4,-24 -26,-34z`, c, 'cgHairSh') + curve(`M${HX + 30},${HY - R} q20,8 18,34 q0,20 14,34`, '#fff', 1, .4);
    return '';
  }
  switch (type) {
    case 'bun': return shp(`M${HX - R},${HY + 4} q-2,-${R + 12} ${R},-${R + 12} q${R + 2},0 ${R},${R + 12} q-12,-${R - 6} -${R},-${R - 14} q-${R - 12},-8 -${R},${R - 14}z`, c, 'cgHairSh')
      + curve(`M${HX - 4},${HY - R - 6} q-20,10 -30,${R - 4} M${HX + 4},${HY - R - 6} q20,10 30,${R - 4} M${HX},${HY - R - 6} q-8,14 -14,22`, '#555', 1.1)
      + E(HX, HY - R - 20, 24, 19, c, 'cgHairSh') + E(HX - 28, HY - R - 4, 13, 13, c, 'cgHairSh') + E(HX + 28, HY - R - 4, 13, 13, c, 'cgHairSh')
      + curve(`M${HX - 14},${HY - R - 26} q14,-8 28,0 M${HX - 12},${HY - R - 16} q12,-6 24,0`, '#555', 1.1)
      + shp(`M${HX - 30},${HY - R - 40} L${HX + 40},${HY - R - 22} l-2,4 L${HX - 31},${HY - R - 36}z`, 'url(#cgGold)', null, 1.2) + E(HX + 42, HY - R - 20, 5, 5, '#e53935', 'cgSh', 1.2)
      + curve(`M${HX + 40},${HY - R - 16} v14 M${HX + 44},${HY - R - 16} v10`, '#c9a227', 1) + E(HX + 40, HY - R, 2.4, 2.4, '#e53935', null, .8) + E(HX + 44, HY - R - 4, 2, 2, '#7fe3ff', null, .8)
      + [0, 72, 144, 216, 288].map(a => { const r = a * Math.PI / 180; return E(HX - 30 + 7 * Math.cos(r), HY - R - 18 + 7 * Math.sin(r), 4.5, 4.5, '#ff7aa2', null, 1); }).join('') + E(HX - 30, HY - R - 18, 3, 3, '#ffeb3b', null, .8)
      + [0, 90, 180, 270].map(a => { const r = a * Math.PI / 180; return E(HX + 20 + 4 * Math.cos(r), HY - R - 34 + 4 * Math.sin(r), 3, 3, '#fff', null, .8); }).join('') + E(HX + 20, HY - R - 34, 2, 2, '#ffeb3b', null, .6)
      + E(HX, HY - R + 14, 3, 3, '#e53935', null, 0);
    case 'topknot': return shp(`M${HX - R - 1},${HY - 2} q0,-${R + 14} ${R + 1},-${R + 14} q${R + 1},0 ${R + 1},${R + 14} q-14,-${R - 12} -${R + 1},-${R - 16} q-${R - 14},4 -${R + 1},${R - 16}z`, c, 'cgHairSh')
      + curve(`M${HX - 6},${HY - R - 10} q-18,8 -30,${R - 8} M${HX + 6},${HY - R - 10} q18,8 30,${R - 8}`, '#555', 1.1)
      + E(HX, HY - R - 16, 14, 13, c, 'cgHairSh') + shp(`M${HX - 16},${HY - R - 10} h32 v7 h-32z`, 'url(#cgGold)', null, 1.6) + shp(`M${HX + 12},${HY - R - 13} l28,-6 l-9,15z`, '#ffffff', 'cgShV', 1.6)
      + shp(`M${HX - 14},${HY - R - 4} q-10,10 -6,26 q4,-12 10,-18z`, '#e53935', null, 1.2);
    case 'buns': return shp(`M${HX - R - 1},${HY - 2} q0,-${R + 14} ${R + 1},-${R + 14} q${R + 1},0 ${R + 1},${R + 14} q-${R + 1},-${R - 10} -${2 * R + 2},0z`, c, 'cgHairSh')
      + curve(`M${HX},${HY - R - 12} q-18,8 -30,${R - 6} M${HX},${HY - R - 12} q18,8 30,${R - 6}`, '#555', 1.1)
      + both(E(HX - R + 2, HY - R + 4, 17, 17, c, 'cgHairSh') + curve(`M${HX - R - 8},${HY - R + 2} q10,-8 20,0`, '#555', 1) + shp(`M${HX - R - 9},${HY - R + 10} h22 v6 h-22z`, '#e53935', 'cgShV', 1.4) + curve(`M${HX - R + 12},${HY - R + 16} q4,10 0,18`, '#e53935', 2));
    case 'white': return both(shp(`M${HX - R - 4},${HY + 18} q-12,-28 2,-44 q2,8 4,12 q2,-6 4,-6 q-2,14 4,30z`, '#f4f4f4', 'cgHairSh', 1.6) + curve(`M${HX - R - 2},${HY + 8} q-4,-12 2,-24`, '#bdbdbd', 1));
    case 'ponytail': return shp(`M${HX - 8},${HY - R + 6} q-6,-36 26,-42 q30,-2 34,34 q-18,-12 -26,0 q-8,-14 -34,8z`, c, 'cgHairSh') + curve(`M${HX + 4},${HY - R - 10} q14,-14 32,0 M${HX + 10},${HY - R - 2} q12,-10 24,2`, '#fff', 1, .5)
      + shp(`M${HX - 10},${HY - R + 4} h18 v9 h-18z`, '#e53935', 'cgShV', 1.4) + shp(`M${HX - R + 4},${HY - 6} q0,-${R - 6} ${R - 4},-${R - 6} q-${R - 20},10 -${R - 14},${R - 4}z`, c, 'cgHairSh', 1.4);
    case 'bald': return EF(HX - 16, HY - R + 16, 13, 7, '#fff', .55) + EF(HX + 4, HY - R + 10, 4, 3, '#fff', .45) + both(shp(`M${HX - R + 2},${HY + 2} q-4,-12 2,-22 q4,8 8,10 q-6,6 -10,12z`, '#3b2a1a', 'cgHairSh', 1.2));
    // 亂髮：蓬鬆亂翹（李逵、劉唐）
    case 'wild': {
      const pts = Array.from({ length: 15 }, (_, k) => { const a = Math.PI * (1 + k / 14), r = (k % 2 ? R + 27 : R + 5);
        return `${(HX + r * Math.cos(a)).toFixed(1)},${(HY + r * .96 * Math.sin(a)).toFixed(1)}`; });
      return shp(`M${HX - R - 2},${HY + 8} L${pts.join(' L')} L${HX + R + 2},${HY + 8} q-${R},-${R - 14} -${2 * R + 4},0z`, c, 'cgHairSh', 2)
        + curve(`M${HX - 24},${HY - R + 4} q-10,-16 -22,-22 M${HX},${HY - R - 4} q0,-16 -6,-26 M${HX + 24},${HY - R + 4} q10,-16 22,-22`, light2(c), 1.3)
        + both(shp(`M${HX - R + 2},${HY + 6} q-12,16 -8,34 q10,-8 12,-22z`, c, 'cgHairSh', 1.6));
    }
    default: return '';
  }
}
// 亂髮內側線條色
const light2 = c => c === '#c0392b' ? '#7b241c' : '#555';

/* ---- 臉上胎記／刺青斑（水滸：青面獸、赤髮鬼） ---- */
function markSvg(m) {
  const [kind, col = '#4e9a86'] = m;
  if (kind === 'face') return fl(`M${HX - 42},${HY - 24} q22,-16 42,0 q14,24 2,48 q-20,16 -40,0 q-14,-24 -4,-48z`, col, .6)
    + curve(`M${HX - 32},${HY - 8} q14,8 24,-2 M${HX - 34},${HY + 12} q14,10 28,-2 M${HX - 26},${HY - 20} q10,6 18,0`, '#2f6f5e', 1.5, .45);
  return fl(`M${HX + 24},${HY - 28} q15,-8 19,6 q2,13 -11,15 q-13,0 -8,-21z`, col, .62)
    + curve(`M${HX + 30},${HY - 20} q8,4 9,-2`, '#7b241c', 1.3, .5);
}

/* ---- 鬍鬚 ---- */
function beardSvg(b, R) {
  const [type, c] = b;
  const light = c === '#f2f2f2' || c === '#f5f5f5' || c === '#eeeeee' || c === '#dddddd';
  const sc = light ? '#9e9e9e' : '#000', so = light ? .7 : .6;
  const strands = (x0, y0, n, len, gap = 5) => Array.from({ length: n }, (_, k) => curve(`M${x0 + k * gap},${y0} q${2 + (k % 2) * 2},${len / 2} ${-1 + (k % 3) - 1},${len - Math.abs(k - n / 2) * 2}`, light ? '#bdbdbd' : '#555', 1, .9)).join('');
  const must = (w = 26, curl = 1) => both(shp(`M${HX},${HY + 26} q-10,-8 -${w * .6},-3 q-${w * .3},2 -${w * .45},10 q${curl * -6},6 ${curl * -10},2 q6,8 14,4 q${w * .3},-6 ${w * .52},-8z`, c, 'cgHairSh', 1.6) + curve(`M${HX - 6},${HY + 26} q-8,-2 -14,2`, sc, .8, so));
  switch (type) {
    case 'long': return shp(`M${HX - 26},${HY + 22} q-10,30 2,62 q8,20 24,40 q16,-20 24,-40 q12,-32 2,-62 q-12,12 -26,12 q-14,0 -26,-12z`, c, 'cgHairSh')
      + shp(`M${HX - 26},${HY + 22} q-12,6 -14,20 q8,-6 14,-4z M${HX + 26},${HY + 22} q12,6 14,20 q-8,-6 -14,-4z`, c, null, 1.4)
      + strands(HX - 16, HY + 42, 7, 44) + EF(HX - 8, HY + 60, 3, 20, '#fff', light ? .3 : .12) + must(30, 1.4) + shp(`M${HX - 5},${HY + 36} q5,6 10,0 q-2,10 -5,12 q-3,-2 -5,-12z`, c, null, 1.2);
    case 'full': return shp(`M${HX - R + 2},${HY + 4} q-8,${R + 4} ${R - 2},${R + 18} q${R + 10},-14 ${R - 2},-${R + 18} q-4,10 -10,14 l-4,-6 l-6,8 l-6,-6 l-6,8 l-6,-8 l-6,8 l-6,-8 l-6,6 l-4,-6 q-6,-4 -10,-14z`, c, 'cgHairSh')
      + Array.from({ length: 9 }, (_, k) => curve(`M${HX - 36 + k * 9},${HY + 26 + Math.abs(k - 4) * -2} q${(k - 4) * .8},14 ${(k - 4) * 1.6},${24 - Math.abs(k - 4) * 3}`, '#555', 1.1)).join('')
      + both(Array.from({ length: 4 }, (_, k) => fl(`M${HX - R + 4 + k * 6},${HY + 34 + k * 6} l-4,10 l6,-4z`, c)).join('')) + must(28, 1.6) + shp(`M${HX - 7},${HY + 31} q7,6 14,0 q-1,6 -7,7 q-6,-1 -7,-7z`, '#8b1a1a', null, 1.2);
    case 'goatee': return shp(`M${HX - 10},${HY + 38} q2,22 10,32 q8,-10 10,-32 q-10,6 -20,0z`, c, 'cgHairSh', 1.8) + strands(HX - 5, HY + 42, 3, 22) + must(22, 1);
    case 'mustache': return must(30, 1.6) + shp(`M${HX - 4},${HY + 39} q4,8 8,0 q-4,2 -8,0z`, c, null, 1);
    default: return '';
  }
}

/* ---- 坐騎與載具 ---- */
function rideSvg(ride) {
  const wheel = (cx, cy, r, rim = '#b0bec5', n = 6) => E(cx, cy, r, r, '#2b2b2b', 'cgSh') + `<circle cx="${cx}" cy="${cy}" r="${r - 2}" fill="none" stroke="#555" stroke-width="2" stroke-dasharray="3 3"/>` + E(cx, cy, r * 0.6, r * 0.6, rim, 'cgSh', 1.6)
    + Array.from({ length: n }, (_, k) => { const t = k * Math.PI / n; return line(cx - r * 0.55 * Math.cos(t), cy - r * 0.55 * Math.sin(t), cx + r * 0.55 * Math.cos(t), cy + r * 0.55 * Math.sin(t), '#78909c', 1.2); }).join('') + E(cx, cy, r * .2, r * .2, 'url(#cgMetal)', null, 1.2);
  switch (ride) {
    case 'moto': return EF(HX - 104, 262, 10, 8, '#cfd8dc', .8) + EF(HX - 118, 254, 7, 6, '#cfd8dc', .6) + EF(HX - 128, 244, 5, 4, '#cfd8dc', .4)
      + wheel(HX - 56, 290, 23) + wheel(HX + 60, 290, 23)
      + shp(`M${HX - 80},280 q-2,-30 28,-30`, 'none', null, 0) + curve(`M${HX - 82},283 q-4,-36 34,-36`, OL, 9) + curve(`M${HX - 82},283 q-4,-36 34,-36`, '#c62828', 5)
      + shp(`M${HX - 98},268 h40 l10,8 h-48 a5,5 0 0 1 -2,-8z`, 'url(#cgMetal)', null, 1.8) + shp(`M${HX - 104},266 h8 v12 h-8z`, '#555', null, 1.4)
      + shp(`M${HX - 70},274 q6,-36 50,-36 h44 q36,-2 56,30 l-10,10 h-130z`, '#e53935', 'cgShV', 2.4) + shp(`M${HX - 6},240 q24,-14 52,0 q2,14 -6,18 h-40 q-8,-4 -6,-18z`, '#ef5350', 'cgSh', 2) + EF(HX + 6, 244, 14, 4, '#fff', .55)
      + shp(`M${HX - 40},262 h70 v8 h-70z`, '#ffeb3b', null, 1.2) + E(HX + 2, 280, 10, 10, 'url(#cgMetal)', null, 1.6) + curve(`M${HX - 6},280 h16 M${HX + 2},272 v16`, '#78909c', 1.2)
      + shp(`M${HX + 54},238 l22,-30 l8,4 l-20,30z`, '#455a64', null, 1.8) + curve(`M${HX + 76},210 l-12,-8 M${HX + 76},210 l10,-4`, OL, 4) + E(HX + 66, 202, 3, 3, '#222', null, 1)
      + shp(`M${HX + 76},278 q12,-22 -2,-36`, 'none', null, 0) + curve(`M${HX + 60},290 L${HX + 72},236`, '#90a4ae', 4)
      + E(HX + 84, 242, 9, 8, '#fff59d', 'cgSh', 1.8) + EF(HX + 98, 242, 10, 5, '#fff59d', .55) + curve(`M${HX + 36},290 q24,-30 48,0`, OL, 6) + curve(`M${HX + 36},290 q24,-30 48,0`, '#c62828', 3);
    case 'tank': return curve(`M${HX + 52},226 L${HX + 70},150`, OL, 2) + shp(`M${HX + 70},150 l18,6 l-18,6z`, '#e53935', null, 1.2)
      + shp(`M${HX - 88},268 h176 a20,20 0 0 1 0,40 h-176 a20,20 0 0 1 0,-40z`, '#3d3d3d', 'cgShV') + `<path d="M${HX - 88},270 h176 a18,18 0 0 1 0,36 h-176 a18,18 0 0 1 0,-36z" fill="url(#cgTread)"/>`
      + Array.from({ length: 6 }, (_, k) => E(HX - 66 + k * 26, 288, 10, 10, '#8d8d8d', 'cgSh', 1.6) + E(HX - 66 + k * 26, 288, 4, 4, '#5d5d5d', null, 1)).join('')
      + shp(`M${HX - 76},272 h152 l-12,-24 h-128z`, '#5b7a3a', 'cgShV') + Array.from({ length: 8 }, (_, k) => E(HX - 60 + k * 17, 256, 1.8, 1.8, '#3e5228', null, .6)).join('')
      + shp(`M${HX - 54},250 h108 v-20 a12,12 0 0 0 -12,-12 h-84 a12,12 0 0 0 -12,12z`, '#6b8e3d', 'cgShV') + curve(`M${HX - 50},236 h100`, '#3e5228', 1.4)
      + shp(`M${HX - 114},226 h62 v12 h-62z`, '#5b7a3a', 'cgShV') + shp(`M${HX - 122},223 h10 v18 h-10z`, '#4a6630', null, 1.6) + EF(HX - 128, 232, 5, 5, '#ffcc80', .5)
      + `<path d="M${HX + 22},244 l3.5,7 7.5,1 -5.5,5 1.5,7.5 -7,-3.5 -7,3.5 1.5,-7.5 -5.5,-5 7.5,-1z" fill="#f1c40f" stroke="${OL}" stroke-width="1"/>`;
    case 'rock': return curve(`M${HX - 92},286 q92,40 184,0`, OL, 11) + curve(`M${HX - 92},286 q92,40 184,0`, '#a0682c', 6) + curve(`M${HX - 88},284 q88,36 176,0`, '#d9a066', 1.6)
      + shaft(HX - 52, 300, HX - 44, 262, 5, '#8a5a2b', '#c48a4f', null) + shaft(HX + 48, 300, HX + 40, 262, 5, '#8a5a2b', '#c48a4f', null)
      + shp(`M${HX - 98},236 q-14,10 -10,34 q6,-10 14,-14 q-2,10 6,16 q2,-20 2,-30z`, '#5d3a1a', 'cgSh', 1.6)
      + shp(`M${HX - 66},266 q-10,-36 30,-40 h52 q14,-38 46,-22 q10,8 4,18 l-16,6 l-4,38z`, '#c47a2c', 'cgShV') + `<path d="M${HX - 66},266 q-10,-36 30,-40 h52 q14,-38 46,-22 q10,8 4,18 l-16,6 l-4,38z" fill="url(#cgGrain)"/>`
      + Array.from({ length: 6 }, (_, k) => shp(`M${HX + 30 + k * 4},${228 - k * 5} q-10,-4 -8,-14 q6,4 12,4z`, '#5d3a1a', null, 1.2)).join('')
      + shp(`M${HX + 44},232 q-2,-26 14,-34 q16,-8 30,4 q8,8 4,16 q-4,6 -12,4 q-8,10 -16,14z`, '#c47a2c', 'cgSh', 2) + shp(`M${HX + 54},202 l0,-16 l10,12z M${HX + 64},198 l4,-14 l6,14z`, '#c47a2c', null, 1.5)
      + E(HX + 70, 208, 3.4, 3.4, OL, null, 0) + EF(HX + 71, 207, 1.2, 1.2, '#fff') + E(HX + 86, 214, 2, 1.5, OL, null, 0) + curve(`M${HX + 76},220 q6,2 10,-2`, '#8b1a1a', 2) + curve(`M${HX + 60},222 q8,2 14,-4`, '#5d3a1a', 1.4)
      + shp(`M${HX - 34},228 q30,-8 52,0 v14 q-26,-6 -52,0z`, '#c62828', 'cgShV', 1.8) + curve(`M${HX - 34},242 q26,-6 52,0`, '#f1c40f', 2)
      + curve(`M${HX + 18},232 q24,-4 48,-10`, '#5d3a1a', 2);
    case 'skate': return shp(`M${HX - 62},282 h124 a8,8 0 0 1 0,14 h-124 a8,8 0 0 1 0,-14z`, '#f39c12', 'cgShV')
      + shp(`M${HX - 40},284 q10,-6 18,4 q-8,-2 -10,6z M${HX + 10},284 q10,-6 18,4 q-8,-2 -10,6z`, '#e53935', null, 1) + curve(`M${HX - 56},285 h112`, '#fff', 1.2, .5)
      + shp(`M${HX - 44},296 h16 v4 h-16z M${HX + 28},296 h16 v4 h-16z`, 'url(#cgMetal)', null, 1.2) + wheel(HX - 36, 306, 8, '#ffeb3b', 3) + wheel(HX + 36, 306, 8, '#ffeb3b', 3)
      + curve(`M${HX - 90},290 h-14 M${HX - 84},300 h-20 M${HX - 88},280 h-10`, '#90a4ae', 2);
    case 'trike': return wheel(HX - 52, 294, 17) + wheel(HX + 56, 288, 24) + curve(`M${HX - 52},294 L${HX + 6},276 L${HX + 56},288 M${HX + 6},276 L${HX + 40},224 M${HX - 30},286 L${HX - 22},258`, OL, 9)
      + curve(`M${HX - 52},294 L${HX + 6},276 L${HX + 56},288 M${HX + 6},276 L${HX + 40},224 M${HX - 30},286 L${HX - 22},258`, '#e53935', 5)
      + shp(`M${HX - 40},256 h34 q4,6 -2,10 h-30 q-6,-4 -2,-10z`, '#263238', 'cgShV', 1.8) + curve(`M${HX + 30},220 h22`, OL, 6) + curve(`M${HX + 30},220 h22`, '#90a4ae', 3)
      + curve(`M${HX + 52},220 q12,4 18,14 M${HX + 52},220 q14,-2 22,6`, '#e84393', 2) + curve(`M${HX + 52},220 q10,10 12,20`, '#29b6f6', 2)
      + E(HX + 56, 288, 4, 4, '#ffeb3b', null, 1.2) + curve(`M${HX + 56},288 l10,-8 h6`, OL, 3);
    case 'chair': return shp(`M${HX - 70},${HY + 70} v-${92} a14,14 0 0 1 14,-14 h112 a14,14 0 0 1 14,14 v${172}h-140z`, '#a31d1d', 'cgSh')
      + `<path d="M${HX - 70},${HY + 70} v-92 a14,14 0 0 1 14,-14 h112 a14,14 0 0 1 14,14 v172 h-140z" fill="url(#cgBrocade)"/>`
      + both(shp(`M${HX},${HY - 34} h-62 q-16,2 -22,-10 q-4,-14 8,-18 q10,-2 12,8 q6,-12 18,-14 q20,-6 46,-6z`, 'url(#cgGold)', null, 2) + E(HX - 76, HY - 46, 4, 4, '#e53935', null, 1))
      + E(HX, HY - 52, 9, 9, '#e53935', 'cgSh', 1.6)
      + shp(`M${HX - 82},246 h164 v26 h-164z`, 'url(#cgGold)', null) + curve(`M${HX - 78},252 h156`, '#fff', 1, .6) + [-60, -30, 0, 30, 60].map(dx => E(HX + dx, 259, 4, 4, '#e53935', null, 1)).join('')
      + shp(`M${HX - 78},272 h18 v34 h-18z M${HX + 60},272 h18 v34 h-18z`, '#a31d1d', 'cgSh') + shp(`M${HX - 82},304 h26 v6 h-26z M${HX + 56},304 h26 v6 h-26z`, 'url(#cgGold)', null, 1.4)
      + both(shp(`M${HX - 90},${HY + 66} h30 v-12 q-10,-10 -24,-4 q-10,6 -6,16z`, 'url(#cgGold)', null, 1.8) + E(HX - 82, HY + 54, 2.2, 2.2, OL, null, 0));
    case 'jet': return shp(`M${HX - 110},272 q50,-32 150,-22 l54,-28 l-10,38 q-80,36 -194,12z`, '#5dade2', 'cgShV') + curve(`M${HX - 100},274 q90,-22 180,-18`, '#fff', 1.4, .6)
      + shp(`M${HX - 30},264 l-40,42 h26 l46,-38z`, '#2e86c1', 'cgSh') + E(HX - 40, 286, 5, 5, '#fff', null, 1) + E(HX - 40, 286, 2.5, 2.5, '#e53935', null, 0)
      + shp(`M${HX + 94},228 l16,-26 l7,4 l-8,30z`, '#2e86c1', null, 1.6) + shp(`M${HX + 30},270 h44 l6,6 h-50z`, '#cfd8dc', null, 1.4) + E(HX + 80, 273, 3, 3, '#e53935', null, 1)
      + shp(`M${HX + 104},252 q-6,-14 -22,-12 l-10,10z`, 'url(#cgLens)', null, 1.6)
      + E(HX - 110, 270, 11, 7, 'url(#cgFireR)', null, 1.4) + EF(HX - 122, 270, 6, 3.5, '#ffeb3b', .7);
    default: return '';
  }
}

/* ---- 臉部 ---- */
function faceSvg(f, R) {
  let s = '';
  const ex = 17, ey = HY + 8;
  const lady = f.body === 'lady';
  const eye = (x, closed) => {
    const o = x < HX ? -1 : 1;
    if (closed) return curve(`M${x - 9},${ey} q9,8 18,0`, OL, 3.2) + curve(`M${x + o * 8},${ey + 1} l${o * 4},-1 M${x + o * 5},${ey + 4} l${o * 3},2`, OL, 1.6);
    return E(x, ey, 8.5, 10, '#ffffff', null, 1.4) + fl(elp(x, ey, 8.5, 10), 'url(#cgEyeW)')
      + E(x, ey + 1.6, 6.4, 8, 'url(#cgIris)', null, 0) + E(x, ey + 2.2, 3.2, 4, '#0b0502', null, 0)
      + EF(x + 2.6, ey - 2.2, 2.6, 2.8, '#fff') + EF(x - 2.4, ey + 5, 1.3, 1.3, '#fff')
      + fl(`M${x - 10},${ey + 1} Q${x - 9},${ey - 12} ${x},${ey - 12} Q${x + 9},${ey - 12} ${x + 10},${ey + 1} Q${x + 8},${ey - 9} ${x},${ey - 9.6} Q${x - 8},${ey - 9} ${x - 10},${ey + 1}z`, OL)
      + curve(`M${x + o * 9.5},${ey - 3} l${o * 4},-3`, OL, 2) + (lady ? curve(`M${x + o * 7},${ey - 8} l${o * 3},-4 M${x + o * 3},${ey - 11} l${o * 1.5},-4`, OL, 1.4) : '')
      + curve(`M${x - 6},${ey + 11} q6,2.5 12,0`, '#b5684a', 1.1, .7) + curve(`M${x - 8},${ey - 14} q8,-4 16,0`, '#b5684a', .9, .5);
  };
  const glassFrame = (fill) => shp(`M${HX - 36},${ey - 8} h30 a4,4 0 0 1 4,4 v7 a9,9 0 0 1 -9,9 h-19 a9,9 0 0 1 -9,-9 v-7 a4,4 0 0 1 4,-4z M${HX + 6},${ey - 8} h30 a4,4 0 0 1 4,4 v7 a9,9 0 0 1 -9,9 h-19 a9,9 0 0 1 -9,-9 v-7 a4,4 0 0 1 4,-4z`, fill, null, 2)
    + line(HX - 6, ey - 4, HX + 6, ey - 4, OL, 3) + both(line(HX - 40, ey - 4, HX - R + 2, ey - 6, OL, 2.6)) + curve(`M${HX - 30},${ey - 4} l9,9 M${HX - 22},${ey - 5} l5,5 M${HX + 12},${ey - 4} l9,9 M${HX + 20},${ey - 5} l5,5`, '#fff', 1.6, .8);
  if (f.eyes === 'glasses') s += glassFrame('url(#cgGlass)');
  else if (f.eyes === 'goggles') s += both(line(HX - 28, ey - 2, HX - R - 2, ey - 6, '#5d4037', 5)) + E(HX - ex, ey, 13, 13, 'url(#cgMetal)', null, 2.2) + E(HX + ex, ey, 13, 13, 'url(#cgMetal)', null, 2.2)
    + E(HX - ex, ey, 9.5, 9.5, 'url(#cgLens)', null, 1.4) + E(HX + ex, ey, 9.5, 9.5, 'url(#cgLens)', null, 1.4) + E(HX - ex, ey + 1, 3.5, 4, '#2a1408', null, 0) + E(HX + ex, ey + 1, 3.5, 4, '#2a1408', null, 0)
    + EF(HX - ex + 3, ey - 3, 2.6, 2.6, '#fff') + EF(HX + ex + 3, ey - 3, 2.6, 2.6, '#fff') + line(HX - 4, ey, HX + 4, ey, OL, 3);
  else if (f.eyes === 'mask') s += shp(`M${HX - R + 1},${ey - 12} h${2 * R - 2} v14 q-${R - 2},18 -${2 * R - 2},0z`, '#c0392b', 'cgShV') + curve(`M${HX - R + 4},${ey - 9} h${2 * R - 8}`, '#f1c40f', 2)
    + both(shp(`M${HX - 27},${ey - 4} q10,-6 19,2 q-9,6 -19,-2z`, '#fff', null, 1.5) + E(HX - 17, ey - 2, 3, 3, '#111', null, 0) + EF(HX - 16, ey - 3, 1, 1, '#fff') + curve(`M${HX - 34},${ey + 4} q6,4 10,0`, '#f1c40f', 1.4));
  else if (f.eyes === 'eyepatch') s += eye(HX + ex) + line(HX - R + 2, ey - 16, HX + R - 4, ey - 8, '#111', 2.8) + shp(`M${HX - ex - 11},${ey - 7} q11,-6 22,0 q2,10 -11,16 q-13,-6 -11,-16z`, '#1b1b1b', 'cgSh', 1.6)
    + curve(`M${HX - ex - 7},${ey - 3} q7,4 14,0`, '#555', 1, .8) + curve(`M${HX - ex - 14},${ey + 10} l6,10 M${HX - ex - 10},${ey + 12} l-4,2`, '#b5684a', 1.6);
  else if (f.eyes === 'wink') s += eye(HX + ex) + curve(`M${HX - ex - 9},${ey + 1} q9,-9 18,0`, OL, 3.4) + curve(`M${HX - ex - 9},${ey + 1} l-3,-2`, OL, 1.6);
  else if (f.eyes === 'closed') s += eye(HX - ex, 1) + eye(HX + ex, 1);
  else if (f.eyes === 'narrow') s += [HX - ex, HX + ex].map(x => { const o = x < HX ? -1 : 1; return shp(`M${x - o * 10},${ey + 2} q${o * 10},-7 ${o * 21},-4 q${-o * 9},8 ${-o * 21},4z`, '#ffffff', null, 2)
    + E(x - o * 0.5, ey + 0.5, 3.4, 3.4, '#1e0d04', null, 0) + EF(x + 0.6, ey - 0.6, 1.2, 1.2, '#fff') + curve(`M${x - o * 11},${ey + 2} q${o * 10},-10 ${o * 23},-6`, OL, 3); }).join('');
  else s += eye(HX - ex) + eye(HX + ex);
  // 眉毛
  const by = ey - 16;
  const bc = f.old ? '#e8e8e8' : (f.beard?.[1] && !['#f2f2f2', '#f5f5f5', '#eeeeee', '#dddddd'].includes(f.beard[1]) ? f.beard[1] : '#2b1a10');
  if (f.eyes !== 'mask' && f.eyes !== 'glasses' && f.eyes !== 'goggles') {
    if (f.brow === 'angry') s += both(shp(`M${HX - 33},${by - 7} Q${HX - 18},${by - 7} ${HX - 6},${by + 2} L${HX - 8},${by + 6} Q${HX - 20},${by} ${HX - 33},${by - 2}z`, bc, null, 1.2));
    else if (f.brow === 'thick') s += both(shp(`M${HX - 33},${by + 2} Q${HX - 22},${by - 10} ${HX - 7},${by - 3} L${HX - 7},${by + 3} Q${HX - 20},${by - 3} ${HX - 33},${by + 5}z`, bc, null, 1.2) + curve(`M${HX - 29},${by + 1} l2,-3 M${HX - 23},${by - 2} l2,-3 M${HX - 16},${by - 2} l2,-3`, f.old ? '#bdbdbd' : '#555', .8));
    else if (f.brow === 'kind') s += both(shp(`M${HX - 30},${by + 3} Q${HX - 20},${by - 6} ${HX - 9},${by - 1} L${HX - 10},${by + 1.5} Q${HX - 20},${by - 3} ${HX - 30},${by + 3}z`, f.old ? '#cfcfcf' : '#2b1a10', null, 1.4));
    else s += both(shp(`M${HX - 30},${by + 1} Q${HX - 19},${by - 6} ${HX - 8},${by - 1} L${HX - 8},${by + 2} Q${HX - 19},${by - 3} ${HX - 30},${by + 2}z`, '#2b1a10', null, 1.2));
  }
  if (f.old) s += curve(`M${HX - 14},${HY - 24} q14,-4 28,0 M${HX - 10},${HY - 18} q10,-3 20,0`, '#9c6b4a', 1.2) + both(curve(`M${HX - 34},${ey + 2} l-6,0 M${HX - 34},${ey + 6} l-5,3`, '#9c6b4a', 1.1));
  // 鼻、腮紅
  s += curve(`M${HX - 2},${HY + 16} q6,5 1,8`, '#b5684a', 2.2) + EF(HX + 1.5, HY + 18, 1.6, 1.2, '#fff', .7);
  if (!f.beard || f.beard[0] !== 'full') s += EF(HX - 30, HY + 24, 10, 6, 'url(#cgBlush)') + EF(HX + 30, HY + 24, 10, 6, 'url(#cgBlush)');
  // 嘴
  const my = HY + 33;
  if (lady) s += shp(`M${HX - 7},${my - 1} q3.5,-3 7,-.5 q3.5,-2.5 7,.5 q-3,6 -7,6 q-4,0 -7,-6z`, '#e53950', null, 1.2) + EF(HX - 2, my + 1.5, 2, 1, '#fff', .7);
  else if (f.mouth === 'open') s += shp(`M${HX - 11},${my - 4} q11,-3 22,0 q-1,17 -11,17 q-10,0 -11,-17z`, '#7a1414', null, 2) + fl(`M${HX - 9},${my - 3} q9,-2 18,0 v4 q-9,2 -18,0z`, '#fff') + EF(HX, my + 9, 6, 3.6, '#ff7b7b');
  else if (f.mouth === 'laugh') s += shp(`M${HX - 15},${my - 5} q15,3 30,0 q-2,19 -15,19 q-13,0 -15,-19z`, '#7a1414', null, 2) + fl(`M${HX - 13},${my - 4} q13,3 26,0 v4 q-13,3 -26,0z`, '#fff') + EF(HX, my + 9, 8, 4.5, '#ff7b7b');
  else if (f.mouth === 'grin') s += shp(`M${HX - 14},${my - 4} q14,7 28,0 q-3,13 -14,13 q-11,0 -14,-13z`, '#ffffff', null, 2) + curve(`M${HX - 12},${my + 1} q12,4 24,0`, '#9e9e9e', 1) + [-7, 0, 7].map(dx => line(HX + dx, my - 1, HX + dx, my + 7, '#bdbdbd', 1)).join('');
  else if (f.mouth === 'frown') s += curve(`M${HX - 10},${my + 4} q10,-8 20,0`, OL, 2.8) + curve(`M${HX - 5},${my + 7} q5,2 10,0`, '#b5684a', 1, .7);
  else if (f.mouth === 'smile') s += shp(`M${HX - 11},${my - 2} q11,10 22,0 q-11,4 -22,0z`, '#7a1414', null, 2) + EF(HX, my + 3.4, 4, 1.8, '#ff7b7b');
  else s += curve(`M${HX - 8},${my - 1} q8,7 16,0`, OL, 2.6) + curve(`M${HX - 9},${my - 3} l-1.5,2 M${HX + 9},${my - 3} l1.5,2`, OL, 1.2);
  return s;
}

/* ---- 手臂與手 ---- */
const fist = (x, y, skin, o = 1) => E(x, y, 9.5, 9, skin, 'cgFace', 2.2) + curve(`M${x - 5 * o},${y - 5} q${3 * o},2 ${2 * o},6 M${x - 1 * o},${y - 6} q${3 * o},2 ${2 * o},7 M${x + 3 * o},${y - 5} q${3 * o},2 ${2 * o},6`, '#b5684a', 1) + curve(`M${x - 8 * o},${y + 1} q${5 * o},4 ${9 * o},1`, '#b5684a', 1.1);

/* ---- 人物 ---- */
function figureSvg(code) {
  const f = activeFig(code);
  const sp = f.special;
  const R = f.fat ? 52 : 48;
  const seated = ['moto', 'tank', 'rock', 'trike', 'chair', 'jet'].includes(f.ride);
  const [c1, c2] = sp === 'ultra' ? ['#e53935', '#dfe6e9'] : sp === 'vader' ? ['#1b1b1b', '#151515'] : sp === 'robo' ? ['#b4c4d4', '#6d7f92'] : sp === 'bat' ? ['#5a6b80', '#2c3e70'] : (f.cloth || ['#c0392b', '#2b5fc1']);
  const skin = f.face || (f.old ? '#f3d3b8' : '#f9d7b8');
  const bw = f.fat ? 50 : 38; // 肩寬一半
  const sy = HY + R - 6;      // 肩線
  const wy = sy + 54;         // 腰線
  const ly = seated ? wy + 22 : wy + 30; // 腿頂
  const fy = ly + 34;         // 腳底
  const armor = f.body === 'armor' && !sp;
  const robe = f.body === 'robe', lady = f.body === 'lady';
  let s = '';

  // 背景光暈與地面影子
  s += EF(HX, HY + 40, 104, 104, 'url(#cgHalo)');
  if (!f.ride || f.ride === 'chair' || f.ride === 'skate') s += EF(HX, fy + 2, f.ride === 'chair' ? 96 : 66, 11, 'url(#cgGround)');
  else s += EF(HX, 312, 110, 12, 'url(#cgGround)');
  // 寶光（鄧元覺）：頭後金光輪
  if (f.halo) s += EF(HX, HY - 2, 80, 80, 'url(#cgHalo)')
    + Array.from({ length: 16 }, (_, k) => { const t = k * Math.PI / 8; return line(HX + 58 * Math.cos(t), HY - 2 + 58 * Math.sin(t), HX + 76 * Math.cos(t), HY - 2 + 76 * Math.sin(t), '#f6d365', k % 2 ? 2 : 3.4); }).join('')
    + `<circle cx="${HX}" cy="${HY - 2}" r="60" fill="none" stroke="url(#cgGold)" stroke-width="5"/><circle cx="${HX}" cy="${HY - 2}" r="60" fill="none" stroke="${OL}" stroke-width="1.2"/>`;
  // 神行（戴宗）：疾風線
  if (f.charm) s += [[-116, 150, 54], [-124, 186, 68], [-110, 226, 46], [96, 168, 50], [104, 212, 40]].map(([dx, yy, L]) =>
    curve(`M${HX + dx},${yy} h${dx < 0 ? L : -L}`, '#8fd3f4', 5, .75) + curve(`M${HX + dx + (dx < 0 ? 10 : -10)},${yy + 10} h${dx < 0 ? L * .6 : -L * .6}`, '#cfeeff', 3.4, .7)).join('');

  // 背後層
  if (f.ride === 'chair') s += rideSvg('chair');
  if (f.cape) {
    const ch = seated ? 96 : 128;
    const cpd = `M${HX - bw + 4},${sy + 4} q-40,60 -28,${ch} q${bw + 24},16 ${2 * bw + 48},0 q12,-68 -28,-${ch}z`;
    s += shp(cpd, f.cape, 'cgSh') + (f.leo ? fl(cpd, 'url(#wmLeo)') : '')
      + curve(`M${HX - bw - 6},${sy + 40} q-10,40 -6,${ch - 40} M${HX + bw + 6},${sy + 40} q10,40 6,${ch - 40} M${HX - 20},${sy + ch - 10} q-2,10 -4,14`, '#000', 1.3, .3)
      + curve(`M${HX - bw - 22},${sy + ch} q${bw + 22},14 ${2 * bw + 44},0`, sp === 'vader' ? '#7a0000' : '#f1c40f', 2.4);
  }
  if (sp === 'bat') s += shp(`M${HX - 30},${sy + 22} q-56,-14 -94,-56 q12,42 -2,66 q16,-12 28,4 q12,-16 26,2 q12,-18 42,-6z M${HX + 30},${sy + 22} q56,-14 94,-56 q-12,42 2,66 q-16,-12 -28,4 q-12,-16 -26,2 q-12,-18 -42,-6z`, '#6c3483', 'cgSh')
    + curve(`M${HX - 34},${sy + 20} q-30,-20 -76,-42 M${HX - 34},${sy + 20} q-24,6 -42,26 M${HX + 34},${sy + 20} q30,-20 76,-42 M${HX + 34},${sy + 20} q24,6 42,26`, '#000', 1.2, .35);
  if (f.tail) s += curve(`M${HX + 30},${wy + 30} q48,14 38,-34 q-6,-22 14,-30`, OL, 6) + curve(`M${HX + 30},${wy + 30} q48,14 38,-34 q-6,-22 14,-30`, '#444', 3.5) + E(HX + 82, wy - 34, 3, 3, '#f8bbd0', null, 1);
  if (f.hair) s += hairSvg(f.hair, R, 'back');
  if (lady) s += shp(`M${HX - 28},${sy + 6} q-40,20 -46,70 q-2,30 -12,52 q14,-6 22,-24 q4,-50 36,-84z`, '#fde2ec', 'cgSh', 1.6) + shp(`M${HX + 28},${sy + 6} q40,20 46,70 q2,30 12,52 q-14,-6 -22,-24 q-4,-50 -36,-84z`, '#fde2ec', 'cgSh', 1.6);

  // 腿與靴
  if (!seated || f.ride === 'chair') {
    for (const dx of [-17, 17]) {
      const o = dx < 0 ? -1 : 1, bx = HX + dx;
      if (sp === 'ultra') s += shp(`M${bx - 11},${ly - 4} h22 l-1,${fy - ly - 10} h-20z`, '#dfe6e9', 'cgSh') + shp(`M${bx - 3},${ly - 4} h6 v${fy - ly - 10} h-6z`, '#e53935', null, 1.2);
      else if (sp === 'robo') s += shp(`M${bx - 12},${ly - 4} h24 l-2,${fy - ly - 10} h-20z`, 'url(#cgMetal)', null) + curve(`M${bx - 11},${ly + 10} h22`, '#546e7a', 1.4) + E(bx, ly + 10, 3, 3, '#546e7a', null, 1);
      else s += shp(`M${bx - 11},${ly - 4} h22 l-1,${fy - ly - 10} h-20z`, sp === 'vader' ? '#1b1b1b' : sp === 'bat' ? '#5a6b80' : c2, 'cgSh') + curve(`M${bx - 6},${ly + 4} q4,6 2,14`, '#000', 1, .3);
      const boot = sp === 'ultra' ? '#dfe6e9' : sp === 'robo' ? '#90a4ae' : sp === 'bat' ? '#2c3e70' : '#2d2d2d';
      const b = shp(`M${bx - 11},${fy - 22} h22 v12 q12,0 16,6 q2,5 -3,5 h-35 q-3,0 -3,-4z`, boot, 'cgShV', 2.2) + curve(`M${bx - 13},${fy - 1} h37`, '#9e9e9e', 1.4) + curve(`M${bx + 12},${fy - 7} q4,-2 6,2`, '#fff', 1, .5);
      s += o > 0 ? b : mir(b, bx);
      if (!sp) s += shp(`M${bx - 13},${fy - 25} h26 v6 h-26z`, 'url(#cgGold)', null, 1.4);
      if (sp === 'ultra') s += shp(`M${bx - 12},${fy - 22} h24 v4 h-24z`, '#e53935', null, 1.2);
    }
  }

  // 身軀
  if (lady) {
    const sk = `M${HX - 24},${wy - 2} q-34,50 -44,${ly - wy + 38} q60,14 136,0 q-10,-${ly - wy - 12} -44,-${ly - wy + 38}z`;
    s += shp(sk, c1, 'cgSh') + fl(sk, 'url(#cgBrocade)');
    s += shp(`M${HX - 70},${ly + 26} q70,16 140,0 l4,10 q-74,18 -148,0z`, c2, 'cgShV', 1.8) + fl(`M${HX - 70},${ly + 26} q70,16 140,0 l4,10 q-74,18 -148,0z`, 'url(#cgCloud)');
    s += curve(`M${HX - 14},${wy + 8} q-10,34 -22,${ly - wy + 26} M${HX + 14},${wy + 8} q10,34 22,${ly - wy + 26} M${HX},${wy + 10} v${ly - wy + 32}`, '#000', 1.2, .25);
    s += shp(`M${HX - 22},${sy} q-6,26 -4,${wy - sy} h52 q2,-${wy - sy - 26} -4,-${wy - sy}z`, c1, 'cgSh');
    s += shp(`M${HX - 22},${sy + 1} l22,26 l22,-26 l-6,0 l-16,18 l-16,-18z`, '#fff', null, 1.6) + curve(`M${HX - 18},${sy + 2} l18,22 M${HX + 18},${sy + 2} l-18,22`, c2, 3);
    s += shp(`M${HX - 34},${wy - 6} h68 v14 h-68z`, c2, 'cgShV', 2) + curve(`M${HX - 32},${wy - 1} h64`, '#fff', 1, .5);
    s += shp(`M${HX},${wy} q-16,-10 -18,2 q4,8 18,-2z M${HX},${wy} q16,-10 18,2 q-4,8 -18,-2z`, '#f8bbd0', null, 1.4) + curve(`M${HX - 2},${wy + 4} q-8,24 -14,42 M${HX + 2},${wy + 4} q8,24 14,42`, '#f8bbd0', 4) + E(HX, wy + 1, 4, 4, '#e53935', null, 1.2);
    s += curve(`M${HX - 4},${wy + 8} v26`, '#c9a227', 1.2) + E(HX - 4, wy + 38, 6, 6, '#4caf50', 'cgSh', 1.4) + E(HX - 4, wy + 38, 2, 2, '#fff', null, .8) + curve(`M${HX - 4},${wy + 44} q-2,8 0,14 M${HX - 4},${wy + 44} q2,8 2,14`, '#e53935', 1.8);
  } else if (robe) {
    const rb = `M${HX - bw + 6},${sy} q-14,${(ly - sy) / 2} -${bw * 0.25},${ly - sy + 30} h${2 * bw + bw * 0.5 - 12} q-${bw * 0.25 - 6},-${(ly - sy) / 2 + 30} -${bw * 0.25 + 6},-${ly - sy + 30}z`;
    const hb = ly + 30, hl = HX - bw * 1.25 + 6, hr = HX + bw * 1.25 - 6;
    s += shp(rb, c1, 'cgSh') + fl(rb, 'url(#cgBrocade)');
    s += shp(`M${hl - 1},${hb - 12} L${hr + 1},${hb - 12} L${hr},${hb} L${hl},${hb}z`, c2, 'cgShV', 1.8) + fl(`M${hl},${hb - 11} L${hr},${hb - 11} L${hr},${hb - 1} L${hl},${hb - 1}z`, 'url(#cgCloud)');
    s += curve(`M${HX - bw + 12},${wy + 14} q-6,20 -8,${ly - wy + 2} M${HX + bw - 12},${wy + 14} q6,20 8,${ly - wy + 2} M${HX - 16},${wy + 20} q-2,14 -4,${ly - wy - 6}`, '#000', 1.2, .25);
    s += shp(`M${HX + 16},${sy} L${HX - 16},${sy + 46} l-8,-5 L${HX + 6},${sy - 2}z`, c2, 'cgSh', 1.6) + fl(`M${HX + 16},${sy} L${HX - 16},${sy + 46} l-8,-5 L${HX + 6},${sy - 2}z`, 'url(#cgCloud)');
    s += shp(`M${HX - 20},${sy} l14,18 l4,-6 l-10,-14z`, '#fff', null, 1.4) + shp(`M${HX + 8},${sy - 1} l-14,22 l4,2 l14,-22z`, '#fff', null, 1.2);
    s += shp(`M${HX - bw + 2},${wy - 7} h${2 * bw - 4} v14 h-${2 * bw - 4}z`, c2, 'cgShV', 2) + curve(`M${HX - bw + 4},${wy - 3} h${2 * bw - 8} M${HX - bw + 4},${wy + 3} h${2 * bw - 8}`, '#fff', .9, .45);
    s += shp(`M${HX + 8},${wy} q-12,-10 -14,0 q2,8 14,0z M${HX + 8},${wy} q12,-10 14,0 q-2,8 -14,0z`, c2, 'cgSh', 1.4) + E(HX + 8, wy, 3.5, 3.5, c2, null, 1.2)
      + shp(`M${HX + 6},${wy + 4} q-4,22 -10,36 l8,0 q4,-16 6,-34z M${HX + 10},${wy + 4} q6,20 6,32 l7,-2 q-2,-16 -9,-30z`, c2, 'cgSh', 1.4);
    s += curve(`M${HX - 18},${wy + 6} v14`, '#c9a227', 1.2) + E(HX - 18, wy + 26, 6, 6, '#43a047', 'cgSh', 1.4) + E(HX - 18, wy + 26, 2, 2, '#fff', null, .8) + curve(`M${HX - 18},${wy + 32} q-2,8 0,14 M${HX - 18},${wy + 32} q2,8 2,14`, '#e53935', 1.8);
    if (!seated) s += both(shp(`M${HX - 30},${hb - 2} q-4,8 6,10 h12 q6,-2 2,-10z`, '#2d2d2d', 'cgShV', 1.6) + curve(`M${HX - 30},${hb + 1} q-4,-4 -2,-8`, '#2d2d2d', 2));
  } else {
    // 鎧甲：胴甲、護心鏡、腰帶、甲裙、披膊
    const torso = `M${HX - bw + 4},${sy} q-6,${(wy - sy) / 2} 2,${wy - sy} h${2 * bw - 12} q8,-${(wy - sy) / 2} 2,-${wy - sy}z`;
    const tL = `M${HX - bw + 2},${wy + 4} l-6,${ly - wy + 8} h${bw - 2} l2,-${ly - wy + 8}z`, tR = `M${HX + bw - 2},${wy + 4} l6,${ly - wy + 8} h-${bw - 2} l-2,-${ly - wy + 8}z`;
    if (!sp) {
      // 內襯衣擺
      s += shp(`M${HX - bw + 2},${wy + 2} l-4,${ly - wy + 16} q${bw},8 ${2 * bw},0 l-4,-${ly - wy + 16}z`, c1, 'cgSh', 1.8);
    }
    s += shp(tL, c2, 'cgSh') + shp(tR, c2, 'cgSh');
    if (!sp) s += fl(tL + tR, 'url(#cgLam)') + curve(`M${HX - bw - 4},${ly + 10} h${bw} M${HX + 2},${ly + 10} h${bw + 2}`, '#f1c40f', 2.4)
      + shp(`M${HX - 11},${wy + 6} h22 l3,${ly - wy + 10} h-28z`, c1, 'cgSh', 1.8) + fl(`M${HX - 11},${wy + 6} h22 l3,${ly - wy + 10} h-28z`, 'url(#cgBrocade)') + curve(`M${HX - 12},${ly + 14} h24`, '#f1c40f', 2) + beast(HX, wy + 26, 5);
    s += shp(torso, sp === 'robo' ? 'url(#cgMetal)' : c1, sp === 'robo' ? null : 'cgSh');
    if (!sp) {
      s += fl(torso, 'url(#cgScale)');
      s += curve(`M${HX - bw + 6},${sy + 2} L${HX - 10},${sy + 20} M${HX + bw - 6},${sy + 2} L${HX + 10},${sy + 20}`, OL, 7) + curve(`M${HX - bw + 6},${sy + 2} L${HX - 10},${sy + 20} M${HX + bw - 6},${sy + 2} L${HX + 10},${sy + 20}`, '#7a4a22', 4.5)
        + [0.3, 0.6].map(t => E(HX - bw + 6 + (bw - 16) * t, sy + 2 + 18 * t, 1.8, 1.8, 'url(#cgGold)', null, .8) + E(HX + bw - 6 - (bw - 16) * t, sy + 2 + 18 * t, 1.8, 1.8, 'url(#cgGold)', null, .8)).join('');
      s += E(HX, sy + 27, 14, 14, 'url(#cgMetal)', null, 2) + `<circle cx="${HX}" cy="${sy + 27}" r="10.5" fill="none" stroke="#c9a227" stroke-width="2"/>` + E(HX, sy + 27, 6, 6, 'url(#cgGold)', null, 1.2) + EF(HX - 5, sy + 22, 4, 2.6, '#fff', .8);
      s += shp(`M${HX - 22},${sy - 4} q22,16 44,0 q-2,8 -22,12 q-20,-4 -22,-12z`, c2, 'cgShV', 1.6) + curve(`M${HX - 20},${sy - 1} q20,14 40,0`, '#f1c40f', 1.6);
      s += shp(`M${HX - 18},${wy + 5} q18,20 36,0z`, 'url(#cgMetal)', null, 1.6);
    }
    // 腰帶與獸面扣
    s += shp(`M${HX - bw},${wy - 7} h${2 * bw} v14 h-${2 * bw}z`, sp ? '#3a3a3a' : '#5d3a1a', 'cgShV', 2);
    if (!sp) s += Array.from({ length: 6 }, (_, k) => E(HX - bw + 6 + k * ((2 * bw - 12) / 5), wy, 2, 2, 'url(#cgGold)', null, .8)).join('') + beast(HX, wy, 9);
    if (f.heart) s += shp(`M${HX},${sy + 36} q-14,-10 -8,-18 q5,-5 8,1 q3,-6 8,-1 q6,8 -8,18z`, '#e53935', 'cgSh', 1.4);
  }
  // 腰間佩刀（石寶等）
  if (f.sidearm) s += `<g transform="rotate(-24 ${HX - bw} ${wy})">`
    + shp(`M${HX - bw - 8},${wy - 2} h16 l-2,66 q-6,6 -12,0z`, '#355c45', 'cgShV', 2.2)
    + shp(`M${HX - bw - 12},${wy - 12} h24 v11 h-24z`, 'url(#cgGold)', null, 1.6)
    + shp(`M${HX - bw - 4},${wy - 30} h8 v19 h-8z`, '#4e342e', null, 1.8) + E(HX - bw, wy - 33, 5, 4, 'url(#cgGold)', null, 1.4)
    + curve(`M${HX - bw - 7},${wy + 22} h14 M${HX - bw - 6},${wy + 44} h12`, '#c9a227', 1.6)
    + shp(`M${HX - bw - 6},${wy + 60} h12 l-1,8 q-5,4 -10,0z`, 'url(#cgGold)', null, 1.4) + '</g>';
  // 赤膊／敞胸（李逵、阮小二、燕青、李俊、魯智深）
  if (f.bare && !lady && !sp) {
    const chest = `M${HX - 26},${sy - 8} q26,15 52,0 l-7,${wy - sy - 1} q-19,9 -38,0z`;
    s += shp(chest, skin, 'cgFace', 2.2)
      + curve(`M${HX - 17},${sy + 17} q17,11 34,0`, '#c98a66', 2.2) + curve(`M${HX},${sy + 24} v${wy - sy - 32}`, '#c98a66', 1.8)
      + curve(`M${HX - 13},${wy - 26} h26 M${HX - 12},${wy - 15} h24`, '#c98a66', 1.5)
      + both(shp(`M${HX - 31},${sy - 9} L${HX - 17},${wy - 2} l10,-1 L${HX - 23},${sy - 10}z`, c2, 'cgShV', 1.8));
    if (f.tattoo) s += curve(`M${HX - 14},${sy + 46} q-4,-20 10,-26 q14,-5 16,8 q1,10 -9,10 q-7,0 -6,-7`, '#2d4f8f', 2.4, .9)
      + curve(`M${HX + 4},${sy + 44} q12,-6 12,-20 M${HX - 16},${sy + 20} q10,-8 18,0 M${HX + 10},${sy + 16} q6,-6 12,-2`, '#2d4f8f', 2.2, .85)
      + curve(`M${HX - 6},${sy + 50} q-10,4 -16,-2 M${HX + 14},${sy + 30} q8,4 8,12`, '#3d6fb8', 2, .8)
      + E(HX + 4, sy + 24, 2.2, 2.2, '#2d4f8f', null, 0);
  }
  if (sp === 'ultra') {
    s += shp(`M${HX - bw + 4},${sy} q-6,26 2,${wy - sy} h${2 * bw - 12} q8,-26 2,-${wy - sy}z`, '#dfe6e9', 'cgSh');
    s += shp(`M${HX - bw + 6},${sy + 4} q14,30 ${bw - 12},${wy - sy - 10} q-6,8 -${bw - 18},4z M${HX + bw - 6},${sy + 4} q-14,30 -${bw - 12},${wy - sy - 10} q6,8 ${bw - 18},4z`, '#e53935', 'cgSh', 1.6);
    s += shp(`M${HX - 22},${sy - 2} q22,18 44,0 l-4,10 q-18,12 -36,0z`, '#e53935', null, 1.6) + E(HX, sy + 26, 9, 9, 'url(#cgGlowB)', null, 2) + EF(HX - 3, sy + 23, 3, 2, '#fff');
    s += shp(`M${HX - bw},${wy - 6} h${2 * bw} v10 h-${2 * bw}z`, '#dfe6e9', 'cgShV', 1.6);
  }
  if (sp === 'robo') s += shp(`M${HX - 24},${sy + 6} h48 v28 q-24,8 -48,0z`, 'url(#cgMetal)', null, 2) + line(HX, sy + 8, HX, sy + 36, '#78909c', 1.6) + curve(`M${HX - 22},${sy + 20} h44`, '#78909c', 1.2)
    + [[-16, sy + 12], [16, sy + 12], [-16, sy + 28], [16, sy + 28]].map(([dx, yy]) => E(HX + dx, yy, 1.6, 1.6, '#546e7a', null, 0)).join('') + shp(`M${HX - 30},${wy + 10} h12 v20 h-12z`, '#37474f', 'cgSh', 1.6);
  if (sp === 'vader') s += shp(`M${HX - bw + 4},${sy} q-6,26 2,${wy - sy} h${2 * bw - 12} q8,-26 2,-${wy - sy}z`, '#1b1b1b', 'cgSh') + curve(`M${HX - 14},${sy + 8} q14,8 28,0`, '#555', 1.4)
    + shp(`M${HX - 17},${sy + 14} h34 v20 h-34z`, '#37474f', 'cgShV', 2) + [0, 1, 2].map(k => E(HX - 10 + k * 10, sy + 20, 2.6, 2.6, ['#e53935', '#43a047', '#1e88e5'][k], null, .8)).join('')
    + [0, 1, 2, 3].map(k => line(HX - 12 + k * 8, sy + 28, HX - 8 + k * 8, sy + 28, '#bdbdbd', 1.6)).join('') + shp(`M${HX - 10},${wy - 6} h20 v12 h-20z`, 'url(#cgMetal)', null, 1.6) + E(HX - 4, wy, 1.6, 1.6, '#e53935', null, 0) + E(HX + 4, wy, 1.6, 1.6, '#1e88e5', null, 0);
  if (sp === 'bat') s += shp(`M${HX - bw + 4},${sy} q-6,26 2,${wy - sy} h${2 * bw - 12} q8,-26 2,-${wy - sy}z`, '#5a6b80', 'cgSh') + curve(`M${HX - 16},${sy + 34} q16,8 32,0`, '#000', 1.2, .3)
    + E(HX, sy + 22, 19, 11, '#f1c40f', 'cgSh', 1.6) + fl(`M${HX - 16},${sy + 22} q4,-7 8,-2 l3,-6 l2,4 h6 l2,-4 l3,6 q4,-5 8,2 q-4,-1 -6,3 q-2,-2 -5,0 q-3,4 -5,6 q-2,-2 -5,-6 q-3,-2 -5,0 q-2,-4 -6,-3z`, '#151515')
    + shp(`M${HX - bw},${wy - 7} h${2 * bw} v13 h-${2 * bw}z`, '#f1c40f', 'cgShV', 1.8) + [-24, -12, 12, 24].map(dx => shp(`M${HX + dx - 4},${wy - 6} h8 v11 h-8z`, '#e0b000', null, 1)).join('') + E(HX, wy, 7, 6, 'url(#cgGold)', null, 1.4);

  // 手臂
  const armColor = f.bare && !sp ? skin : robe || lady ? c1 : (sp ? (sp === 'ultra' ? '#dfe6e9' : sp === 'robo' ? '#b4c4d4' : sp === 'vader' ? '#1b1b1b' : '#5a6b80') : c1);
  const hip = f.hip != null ? !!f.hip : ['S3', 'D3', 'S8', 'D8', 'S9', 'H9', 'D9', 'S10', 'H10', 'D10', 'SJ', 'DJ', 'CJ', 'C4'].includes(code);
  const lh = hip ? [HX - bw + 4, wy - 4] : [HX - bw - 6, wy - 4], rh = [HX + bw + 8, wy - 2];
  const handSkin = sp === 'ultra' ? '#dfe6e9' : sp === 'vader' ? '#2b2b2b' : sp === 'robo' ? '#90a4ae' : sp === 'bat' ? '#2c3e70' : skin;
  if (f.fold) {
    s += both(limb([[HX - bw + 4, sy + 8], [HX - bw - 8, sy + 36], [HX - 18, wy - 6]], 22, 30, c1));
    s += shp(`M${HX - 34},${wy - 22} q34,-8 68,0 l2,22 q-36,10 -72,0z`, c1, 'cgShV') + fl(`M${HX - 34},${wy - 22} q34,-8 68,0 l2,22 q-36,10 -72,0z`, 'url(#cgBrocade)')
      + shp(`M${HX - 36},${wy - 2} q36,10 72,0 l0,6 q-36,10 -72,0z`, c2, null, 1.6) + E(HX - 7, wy - 12, 9, 8, skin, 'cgFace', 2) + E(HX + 7, wy - 13, 9, 8, skin, 'cgFace', 2)
      + curve(`M${HX - 2},${wy - 18} v10 M${HX + 2},${wy - 19} v10`, '#b5684a', 1);
  } else {
    for (const [o, [hx, hy]] of [[-1, lh], [1, rh]]) {
      const sx = HX + o * (bw - 4);
      if (robe || lady) {
        s += limb([[sx, sy + 6], [sx + o * 16, sy + 30], [hx + o * 2, hy - 8]], 20, 30, armColor);
        s += shp(`M${hx - 15},${hy - 15} l28,0 l2,8 l-32,0z`, c2, 'cgShV', 1.6) + fl(`M${hx - 15},${hy - 14} h29 v7 h-29z`, 'url(#cgCloud)');
        s += curve(`M${sx + o * 6},${sy + 16} q${o * 8},12 ${o * 10},26`, '#000', 1, .3);
      } else if (!sp) {
        const elb = hip && o < 0 ? [sx - 24, sy + 34] : [sx + o * 14, sy + 28];
        s += limb([[sx, sy + 6], elb, [hx, hy - 6]], 16, 14, c1);
        s += hip && o < 0 ? limb([[elb[0] + 6, elb[1] + 2], [elb[0] + 12, elb[1] + 6], [hx - 6, hy - 2]], 13, 15, 'url(#cgMetal)', null, 2) : limb([[sx + o * 9, sy + 26], [sx + o * 13, sy + 36], [hx, hy - 8]], 15, 17, 'url(#cgMetal)', null, 2) + curve(`M${hx - 8},${hy - 16} l16,2 M${sx + o * 6},${sy + 30} l${o * 14},-4`, '#c9a227', 2);
        s += shp(`M${sx - o * 4},${sy - 6} q${o * 32},-8 ${o * 36},${24} q${-o * 16},5 ${-o * 32},-2z`, c2, 'cgSh') + fl(`M${sx - o * 4},${sy - 6} q${o * 32},-8 ${o * 36},${24} q${-o * 16},5 ${-o * 32},-2z`, 'url(#cgLam)')
          + curve(`M${sx - o * 2},${sy - 4} q${o * 30},-6 ${o * 34},${22}`, '#f1c40f', 2) + curve(`M${sx + o * 4},${sy + 12} q${o * 12},-2 ${o * 26},${6}`, '#f1c40f', 1.6) + beast(sx + o * 12, sy + 2, 6.5);
      } else {
        s += limb([[sx, sy + 6], [sx + o * 14, sy + 28], [hx, hy - 6]], 17, 15, armColor, sp === 'robo' ? null : 'cgSh');
        if (sp === 'ultra') s += curve(`M${sx + o * 2},${sy + 10} q${o * 10},12 ${o * 12},28`, '#e53935', 4);
        if (sp === 'robo') s += E(sx + o * 4, sy + 6, 13, 11, 'url(#cgMetal)', null, 2) + curve(`M${sx + o * 12},${sy + 26} l${o * 6},6`, '#546e7a', 1.4);
        if (sp === 'bat') s += limb([[sx + o * 10, sy + 30], [sx + o * 13, sy + 38], [hx, hy - 6]], 15, 17, '#2c3e70', 'cgSh') + shp(`M${hx - o * 6},${hy - 18} l${o * -8},-6 l${o * 3},10z`, '#2c3e70', null, 1.2);
        if (sp === 'vader') s += shp(`M${sx - o * 4},${sy - 4} q${o * 26},-6 ${o * 30},${18} q${-o * 14},4 ${-o * 26},-2z`, '#2b2b2b', 'cgSh');
      }
    }
  }
  if (f.shield) s += E(lh[0] - 6, lh[1] - 10, 31, 31, f.shield) + `<circle cx="${lh[0] - 6}" cy="${lh[1] - 10}" r="25" fill="none" stroke="#f1c40f" stroke-width="3"/>` + E(lh[0] - 6, lh[1] - 10, 21, 21, f.shield, null, 1.2)
    + beast(lh[0] - 6, lh[1] - 10, 10) + [0, 45, 90, 135, 180, 225, 270, 315].map(a => { const t = a * Math.PI / 180; return E(lh[0] - 6 + 28 * Math.cos(t), lh[1] - 10 + 28 * Math.sin(t), 2.2, 2.2, 'url(#cgGold)', null, .8); }).join('') + EF(lh[0] - 18, lh[1] - 24, 8, 5, '#fff', .35);
  if (f.braid) s += curve(`M${HX - R + 8},${HY + 10} q-18,46 6,74`, OL, 10) + curve(`M${HX - R + 8},${HY + 10} q-18,46 6,74`, '#4e342e', 7) + Array.from({ length: 6 }, (_, k) => curve(`M${HX - R + 2 - k * .6},${HY + 18 + k * 11} q4,-2 9,4`, '#2b1a10', 1.4)).join('') + E(HX - R + 14, HY + 86, 6, 6, f.braid, 'cgSh', 1.6);
  // 飛石（沒羽箭張清）
  if (f.stones) s += [[-96, 150, 11], [-74, 196, 8], [-104, 232, 7]].map(([dx, yy, r]) =>
    curve(`M${HX + dx + r + 6},${yy - 4} q22,-6 40,-2`, '#b0bec5', 3, .65) + E(HX + dx, yy, r, r * .88, '#9aa7ae', 'cgSh', 2)
    + EF(HX + dx - r * .3, yy - r * .35, r * .35, r * .25, '#fff', .55)).join('');
  // 臂上刺青（史進、燕青、魯智深）
  if (f.tattoo && !sp) s += both(curve(`M${HX - bw - 14},${sy + 18} q10,8 5,16 M${HX - bw - 19},${sy + 32} q12,6 16,-2 M${HX - bw - 11},${sy + 42} q10,6 7,14`, '#2d4f8f', 2.3, .85));
  const wpn = sp === 'vader' && f.weapon === 'sword' ? 'saber' : f.weapon;
  if (wpn) s += weaponSvg(wpn, rh[0], rh[1]);
  if (!f.fold) s += mir(fist(...lh, handSkin, 1), lh[0]) + fist(...rh, handSkin, 1);

  // 頭
  s += shp(`M${HX - 10},${sy - 12} h20 v14 h-20z`, sp === 'ultra' ? '#dfe6e9' : sp === 'vader' ? '#222' : sp === 'robo' ? '#78909c' : skin, null, 2);
  if (sp === 'ultra') {
    s += E(HX, HY, R - 4, R + 6, '#dfe6e9', 'cgFace') + shp(`M${HX - 9},${HY - R - 8} q9,-6 18,0 v${R} q-9,6 -18,0z`, '#e53935', 'cgSh', 2) + curve(`M${HX - 3},${HY - R - 6} v${R - 4}`, '#fff', 1.4, .6)
      + both(shp(`M${HX - 34},${HY + 4} q2,-14 18,-12 q8,4 6,14 q-4,8 -14,6 q-10,-2 -10,-8z`, 'url(#cgGlowY)', null, 2.4) + EF(HX - 26, HY - 3, 4, 2.4, '#fff', .9)
        + shp(`M${HX - R + 2},${HY - 4} q-10,4 -8,16 q6,4 10,0z`, '#cfd8dc', 'cgSh', 1.6))
      + shp(`M${HX - 10},${HY + 28} q10,4 20,0 q-2,6 -10,6 q-8,0 -10,-6z`, '#b0bec5', null, 1.8) + EF(HX - 28, HY + 20, 8, 5, 'url(#cgBlush)') + EF(HX + 28, HY + 20, 8, 5, 'url(#cgBlush)');
  } else if (sp === 'vader') {
    s += shp(`M${HX - R - 12},${HY + 38} q-8,-${R + 54} ${R + 12},-${R + 48} q${R + 20},-6 ${R + 12},${R + 48} l-20,-10 v18 h-${2 * R - 24} v-18z`, '#151515', 'cgSh')
      + curve(`M${HX},${HY - R - 8} v26`, '#555', 1.6) + EF(HX - 24, HY - R + 4, 12, 8, '#fff', .25)
      + shp(`M${HX - 28},${HY - 6} q28,-16 56,0 l-8,14 h-40z`, '#424242', 'cgShV', 1.6) + both(shp(`M${HX - 24},${HY - 2} q8,-6 16,0 q-2,8 -8,8 q-6,0 -8,-8z`, '#111', null, 1.4) + EF(HX - 19, HY - 1, 3, 2, '#ff5252', .7))
      + shp(`M${HX - 14},${HY + 14} l14,18 l14,-18 q-14,-6 -28,0z`, 'url(#cgMetal)', null, 1.8) + Array.from({ length: 5 }, (_, k) => line(HX - 8 + k * 4, HY + 17, HX - 8 + k * 4, HY + 26 - Math.abs(k - 2) * 2, '#111', 1.2)).join('')
      + both(shp(`M${HX - 24},${HY + 12} l-6,12 l8,0z`, '#616161', null, 1.4));
  } else if (sp === 'robo') {
    s += E(HX, HY + 4, R, R, skin, 'cgFace') + shp(`M${HX - R - 3},${HY + 8} q0,-${R + 16} ${R + 3},-${R + 16} q${R + 3},0 ${R + 3},${R + 16}z`, 'url(#cgMetal)', null)
      + curve(`M${HX},${HY - R - 8} v${R}`, '#78909c', 1.6) + EF(HX - 22, HY - R + 4, 12, 8, '#fff', .6)
      + shp(`M${HX - R + 2},${HY - 6} h${2 * R - 4} v16 a6,6 0 0 1 -6,6 h-${2 * R - 16} a6,6 0 0 1 -6,-6z`, '#1c262b', null, 2) + fl(`M${HX - R + 10},${HY + 1} h${2 * R - 20} v4 h-${2 * R - 20}z`, '#ff5252') + EF(HX, HY + 3, R - 12, 5, '#ff8a80', .35)
      + curve(`M${HX - R + 8},${HY - 3} l12,0`, '#fff', 1.4, .5) + curve(`M${HX - 9},${HY + 30} q9,4 18,0`, OL, 2.6) + curve(`M${HX - 14},${HY + 22} q-4,6 0,12 M${HX + 14},${HY + 22} q4,6 0,12`, '#b5684a', 1)
      + both(E(HX - R - 2, HY + 8, 7, 12, 'url(#cgMetal)', null, 1.8) + E(HX - R - 2, HY + 8, 2.5, 2.5, '#546e7a', null, 0));
  } else if (sp === 'bat') {
    s += E(HX, HY, R, R, skin, 'cgFace') + shp(`M${HX - R - 3},${HY + 12} q0,-${R + 16} ${R + 3},-${R + 16} q${R + 3},0 ${R + 3},${R + 16} q-${R + 3},-10 -${2 * R + 6},0z`, '#2c3e70', 'cgSh')
      + both(shp(`M${HX - 32},${HY - 30} l-9,-32 l24,19z`, '#2c3e70', 'cgSh')) + EF(HX - 20, HY - R + 2, 10, 6, '#fff', .25)
      + shp(`M${HX - 34},${HY + 2} h28 v12 a4,4 0 0 1 -4,4 h-20 a4,4 0 0 1 -4,-4z M${HX + 6},${HY + 2} h28 v12 a4,4 0 0 1 -4,4 h-20 a4,4 0 0 1 -4,-4z`, 'url(#cgGlass)', null, 1.8) + line(HX - 6, HY + 6, HX + 6, HY + 6, OL, 3)
      + curve(`M${HX - 28},${HY + 5} l7,7 M${HX + 12},${HY + 5} l7,7`, '#fff', 1.4, .8) + both(shp(`M${HX - R - 2},${HY + 4} q2,14 14,18 l2,-8 q-10,-2 -16,-10z`, '#2c3e70', null, 1.4))
      + curve(`M${HX - 2},${HY + 20} q4,3 1,6`, '#b5684a', 1.8) + shp(`M${HX - 14},${HY + 30} q14,10 28,0 q-14,4 -28,0z`, '#7a1414', null, 2.4) + EF(HX - 28, HY + 26, 7, 4, 'url(#cgBlush)') + EF(HX + 28, HY + 26, 7, 4, 'url(#cgBlush)');
  } else if (f.animal === 'monkey') {
    // 猴（孫悟空、六耳獼猴）：圓耳、滿頭毛、淺色面盤與口鼻
    s += both(E(HX - R - 4, HY + 4, 15, 17, skin, 'cgFace', 2.2) + EF(HX - R - 4, HY + 5, 8, 10, '#f3c1a5'));
    s += E(HX, HY, R + 2, R, skin, 'cgFace');
    s += both(shp(`M${HX - 6},${HY - R + 2} q-10,-14 -24,-10 q10,4 12,14z`, skin, 'cgHairSh', 1.6));
    s += shp(`M${HX},${HY - 12} q-14,-16 -30,-6 q-12,10 -6,30 q4,20 36,26 q32,-6 36,-26 q6,-20 -6,-30 q-16,-10 -30,6z`, '#f6d2b0', 'cgFace', 2);
    s += E(HX, HY + 22, 20, 13, '#f9dcc4', null, 1.8) + EF(HX - 5, HY + 17, 2.4, 1.8, '#5d3a1a') + EF(HX + 5, HY + 17, 2.4, 1.8, '#5d3a1a');
    if (f.mark) s += markSvg(f.mark);
    s += faceSvg(f, R);
    if (f.hat) s += hatSvg(f.hat, R);
  } else if (f.animal === 'pig') {
    // 豬（豬八戒）：大垂耳、粉紅面、豬鼻
    s += both(shp(`M${HX - R + 8},${HY - R + 14} q-30,-6 -30,26 q14,4 34,-6z`, skin, 'cgFace', 2.2) + fl(`M${HX - R + 2},${HY - R + 20} q-18,0 -20,18 q10,0 20,-6z`, '#f48fb1', .7));
    s += E(HX, HY, R + 2, R - 1, skin, 'cgFace');
    s += faceSvg(f, R);
    s += E(HX, HY + 16, 17, 12, '#f48fb1', 'cgFace', 2.2) + E(HX - 6, HY + 16, 3, 4.5, '#8d3b5a', null, 0) + E(HX + 6, HY + 16, 3, 4.5, '#8d3b5a', null, 0);
    if (f.hat) s += hatSvg(f.hat, R);
  } else {
    s += both(E(HX - R + 2, HY + 10, 9, 12, skin, 'cgFace', 2.2) + curve(`M${HX - R + 1},${HY + 4} q-4,6 0,12`, '#b5684a', 1.2));
    s += E(HX, HY, R, R - 2, skin, 'cgFace');
    if (f.mark) s += markSvg(f.mark);
    if (f.hat && !f.hair) {
      const hc = f.old ? '#e0e0e0' : (f.beard?.[1] && !['#f2f2f2', '#f5f5f5', '#eeeeee', '#dddddd'].includes(f.beard[1]) ? f.beard[1] : '#1b1b1b');
      if (!['hood', 'mouse'].includes(f.hat[0])) s += both(shp(`M${HX - R + 4},${HY - 12} q-4,14 1,26 q3,-9 8,-15 q-2,-6 -2,-11z`, hc, 'cgHairSh', 1.2));
    }
    if (f.hair) s += hairSvg(f.hair, R, 'front');
    s += faceSvg(f, R);
    if (f.beard) s += beardSvg(f.beard, R);
    if (f.hat) s += hatSvg(f.hat, R);
    if (f.sweat) s += shp(`M${HX + R + 4},${HY - 26} q9,13 0,19 q-9,-6 0,-19z`, '#74b9ff', 'cgSh', 1.8) + EF(HX + R + 2, HY - 14, 1.6, 2.4, '#fff', .8);
  }
  if (f.ride && f.ride !== 'chair') s += rideSvg(f.ride);
  // 腳下祥雲（公孫勝）
  if (f.cloud) s += [[-70, fy - 10, 1], [64, fy - 20, .86], [-6, fy + 10, 1.18]].map(([dx, yy, sc]) =>
    `<g transform="translate(${HX + dx} ${yy}) scale(${sc})">` + shp('M-36,8 q-12,-18 6,-20 q5,-15 21,-9 q13,-11 24,2 q17,-2 15,15 q-7,12 -22,12z', '#eef6ff', 'cgSh', 2)
    + curve('M-26,4 q8,-8 18,-4 M4,2 q8,-7 16,-2', '#9fc4e8', 1.6) + '</g>').join('');
  // 水波（李俊、阮小二）
  if (f.wave) {
    const w = `M${HX - 104},${fy + 2} q26,-15 52,0 q26,15 52,0 q26,-15 52,0 v48 h-208z`;
    s += shp(w, 'url(#wmWater)', 'cgShV', 2.2) + curve(`M${HX - 88},${fy + 16} q20,-9 40,0 q20,9 40,0 q20,-9 40,0`, '#fff', 2.4, .7)
      + curve(`M${HX - 70},${fy + 26} q18,-7 36,0 M${HX + 24},${fy + 24} q18,-7 36,0`, '#dff2ff', 2, .8);
  }
  // 甲馬神符（戴宗）
  if (f.charm) s += [[-24, 1], [24, -1]].map(([dx, o]) => `<g transform="rotate(${o * 14} ${HX + dx} ${fy - 20})">`
    + shp(`M${HX + dx - 11},${fy - 34} h22 v28 h-22z`, '#f7e07a', 'cgShV', 2)
    + curve(`M${HX + dx},${fy - 30} v8 M${HX + dx - 5},${fy - 22} q5,6 10,0 M${HX + dx - 4},${fy - 14} q4,5 8,0`, '#c0392b', 2)
    + '</g>').join('');
  return s;
}

/* ---- 特別卡圖案 ---- */
const SPECIAL_ART = {
  // 火鏞炮：青銅大砲、木製砲架與燃燒的引信
  SQ: () => EF(125, 300, 96, 12, 'url(#cgGround)') + [[70, 296], [88, 296], [79, 282]].map(([x, y]) => E(x, y, 9, 9, '#37474f', 'cgSh', 2) + EF(x - 3, y - 3, 2.5, 2.5, '#fff', .6)).join('')
    + shp('M96,286 l60,-30 l46,40 h-30z', 'url(#cgWood)', 'cgShV', 2.4) + `<path d="M96,286 l60,-30 l46,40 h-30z" fill="url(#cgGrain)"/>`
    + `<g transform="rotate(-38 140 236)">` + shp('M86,220 h112 l10,-4 v40 l-10,-4 h-112 a16,16 0 0 1 0,-32z', 'url(#cgBronze)', null, 2.4) + curve('M92,226 h104', '#fff', 2, .45)
    + [104, 140, 176].map(x => shp(`M${x},218 h8 v36 h-8z`, 'url(#cgGold)', null, 1.6)).join('') + E(208, 236, 6, 20, '#3e2723', null, 2) + EF(208, 236, 3, 12, '#111')
    + E(78, 236, 10, 10, 'url(#cgBronze)', null, 2) + beast(150, 236, 7) + '</g>'
    + E(140, 270, 24, 24, '#5d3a1a', 'cgSh', 2.4) + `<circle cx="140" cy="270" r="17" fill="none" stroke="#3e2108" stroke-width="2"/>` + [0, 45, 90, 135].map(a => { const t = a * Math.PI / 180; return line(140 - 17 * Math.cos(t), 270 - 17 * Math.sin(t), 140 + 17 * Math.cos(t), 270 + 17 * Math.sin(t), '#3e2108', 2); }).join('') + E(140, 270, 5, 5, 'url(#cgGold)', null, 1.4)
    + curve('M82,248 q-14,-10 -10,-28', OL, 3) + curve('M82,248 q-14,-10 -10,-28', '#d7ccc8', 1.6) + EF(72, 218, 14, 14, 'url(#cgAura)') + star4(72, 218, 10, '#fff59d') + star4(64, 206, 5, '#ffeb3b') + star4(84, 210, 4, '#fff')
    + EF(222, 160, 20, 16, '#eceff1', .85) + EF(206, 174, 14, 12, '#eceff1', .75) + EF(236, 140, 12, 10, '#eceff1', .6) + EF(204, 180, 16, 16, 'url(#cgAura)') + star4(204, 182, 12, '#fff59d'),
  // 巨魔劍：寬刃巨劍、獸面護手、發光符文
  HQ: () => EF(125, 180, 110, 110, 'url(#cgAura)') + `<g transform="rotate(24 125 190)">`
    + shp('M108,236 L108,72 L125,30 L142,72 L142,236z', 'url(#cgBlade)', null, 2.6) + line(125, 44, 125, 232, '#7f8e99', 2) + curve('M112,74 L125,40', '#fff', 2, .8)
    + [96, 134, 172, 210].map(y => EF(125, y, 9, 9, 'url(#cgAura)') + shp(`M125,${y - 6} l4,6 l-4,6 l-4,-6z`, '#ff1744', null, 1)).join('')
    + shp('M74,236 q18,-14 51,-6 q33,-8 51,6 q-6,14 -16,14 q-14,-8 -35,-6 q-21,-2 -35,6 q-10,0 -16,-14z', 'url(#cgGold)', null, 2.2) + beast(125, 240, 11) + both(E(80, 238, 6, 6, '#e53935', 'cgSh', 1.4))
    + shp('M116,252 h18 v46 h-18z', '#4e342e', null, 2) + Array.from({ length: 6 }, (_, k) => curve(`M116,${256 + k * 7} l18,5`, '#c9a227', 1.6)).join('')
    + E(125, 306, 12, 12, 'url(#cgGold)', null, 2) + E(125, 306, 6, 6, '#e53935', 'cgSh', 1.2) + '</g>'
    + curve('M60,330 q-6,-20 6,-30 M196,90 q14,-6 18,-22', '#2ecc71', 4) + star4(70, 96, 9) + star4(188, 270, 7) + star4(205, 150, 5, '#ffeb3b'),
  // 淬毒弓：滴毒的長弓與骷髏標記
  DQ: () => EF(125, 186, 100, 100, 'url(#cgPoison)')
    + curve('M62,88 q118,36 68,190', OL, 13) + curve('M62,88 q118,36 68,190', '#6d4c41', 8) + curve('M66,92 q108,36 62,178', '#a1887f', 2) + shp('M112,170 l14,4 l-4,22 l-14,-4z', '#2e7d32', null, 1.6)
    + E(62, 88, 5, 5, 'url(#cgGold)', null, 1.4) + E(130, 278, 5, 5, 'url(#cgGold)', null, 1.4) + line(62, 88, 130, 278, '#eee', 1.6)
    + line(54, 272, 196, 92, OL, 6) + line(54, 272, 196, 92, '#8d6e63', 3) + shp('M198,90 l-28,6 l14,16z', '#76ff03', null, 1.8) + shp('M64,262 l-20,4 l7,-20z M70,270 l-4,20 l17,-11z', '#8e44ad', null, 1.6)
    + [[178, 122, 5], [170, 136, 4], [184, 140, 3.5], [160, 150, 3]].map(([x, y, r]) => shp(`M${x},${y - r * 2} q${r},${r * 1.6} ${r},${r * 2.6} a${r},${r} 0 1,1 ${-2 * r},0 q0,${-r} ${r},${-r * 2.6}z`, '#76ff03', 'cgSh', 1)).join('')
    + `<g transform="translate(166 228)">` + E(0, 0, 20, 18, '#f5f5f5', 'cgSh', 2) + shp('M-10,14 h20 v10 h-20z', '#f5f5f5', null, 1.8) + E(-7, -2, 5.5, 6, '#111', null, 0) + E(7, -2, 5.5, 6, '#111', null, 0) + EF(-6, -2, 2, 2, '#76ff03') + EF(8, -2, 2, 2, '#76ff03') + fl('M0,4 l-3,6 h6z', '#111') + [-6, -2, 2, 6].map(x => line(x, 15, x, 23, '#555', 1)).join('') + '</g>'
    + curve('M140,250 q30,30 60,4', '#2e7d32', 3, .6),
  // 迷魂彈：螺旋紋飛彈拖著迷幻煙霧
  CQ: () => [[78, 290, 22], [96, 268, 16], [62, 312, 18], [108, 248, 11]].map(([x, y, r], k) => E(x, y, r, r * .85, ['#e1bee7', '#f8bbd0', '#d1c4e9', '#fce4ec'][k], 'cgSh', 1.6)).join('')
    + `<g transform="rotate(-50 125 200)">` + shp('M60,184 h110 q34,0 48,16 q-14,16 -48,16 h-110z', '#eceff1', 'cgShV', 2.4)
    + shp('M150,184 h20 q34,0 48,16 q-14,16 -48,16 h-20z', '#e53935', 'cgShV', 2.2) + [0, 1, 2, 3].map(k => curve(`M${76 + k * 18},184 q8,16 0,32`, '#8e24aa', 3)).join('')
    + shp('M68,184 l-22,-24 h18 l22,24z M68,216 l-22,24 h18 l22,-24z', '#2b5fc1', 'cgSh', 2) + shp('M60,192 h-20 v16 h20z', 'url(#cgMetal)', null, 1.8)
    + E(40, 200, 14, 8, 'url(#cgFireR)', null, 1.4) + EF(24, 200, 12, 5, '#ffeb3b', .7) + E(196, 200, 3, 3, '#fff', null, 0) + '</g>'
    + `<g transform="translate(176 104)">` + curve('M0,0 m-2,0 a2,2 0 1,1 4,0 a5,5 0 1,1 -9,0 a8,8 0 1,1 15,0 a11,11 0 1,1 -21,0 a14,14 0 1,1 27,0', '#8e24aa', 2.6) + '</g>' + star4(206, 74, 6, '#f8bbd0') + star4(150, 74, 5, '#e1bee7'),
  // 火牛陣：角綁利刃、尾燃烈火的猛牛
  SK: () => EF(120, 296, 90, 10, 'url(#cgGround)')
    + shp('M150,214 q34,-22 40,-64 q-16,22 -24,10 q-8,30 -26,26 q2,14 10,28z', 'url(#cgFire)', null, 1.6) + shp('M162,200 q20,-24 18,-56 q-12,22 -16,10 q-6,24 -14,22 q4,14 12,24z', '#ffeb3b', null, 0)
    + curve('M154,212 q16,-6 22,-20', '#5d3a1a', 3)
    + [[80, 248], [100, 252], [132, 252], [152, 248]].map(([x, y], k) => shp(`M${x - 7},${y - 12} l${k % 2 ? 4 : -4},38 h12 l${k % 2 ? 2 : -2},-38z`, '#8e2b20', 'cgSh', 2) + shp(`M${x - 6 + (k % 2 ? 4 : -4)},${y + 24} h14 v6 h-14z`, '#3e2723', null, 1.6)).join('')
    + shp('M62,214 q4,-34 60,-36 q44,0 46,34 q0,34 -50,36 q-52,0 -56,-34z', '#c0392b', 'cgSh', 2.4) + curve('M78,196 q20,-6 30,4 M120,190 q14,6 18,20 M90,232 q14,4 26,0', '#7b1f12', 1.6)
    + shp('M88,200 q-12,-4 -12,10 q8,18 28,8z', '#f1c40f', 'cgShV', 1.6) + curve('M80,206 q10,6 20,2', '#c0392b', 1.2)
    + shp('M30,206 q-4,-30 26,-30 q22,0 24,20 q2,26 -22,30 q-24,2 -28,-20z', '#c0392b', 'cgSh', 2.4) + shp('M28,214 q2,12 18,12 q12,0 14,-10 q-14,6 -32,-2z', '#f5b7a4', null, 1.6) + E(34, 216, 2, 2.6, OL, null, 0) + E(46, 218, 2, 2.6, OL, null, 0)
    + E(46, 192, 6, 6, '#fff', null, 1.6) + E(47, 193, 3, 3, '#111', null, 0) + curve('M38,184 l14,4', OL, 3)
    + shp('M40,180 q-20,-6 -22,-30 q10,12 24,16z', '#fffde7', 'cgSh', 1.8) + shp('M64,180 q14,-14 34,-12 q-16,6 -24,20z', '#fffde7', 'cgSh', 1.8)
    + shp('M14,152 l-10,-22 l16,14z', 'url(#cgBlade)', null, 1.6) + shp('M96,168 l22,-12 l-12,18z', 'url(#cgBlade)', null, 1.6)
    + E(60, 176, 5, 4, '#c0392b', null, 1.4) + curve('M22,212 q-2,10 6,14', '#f1c40f', 2.4) + `<circle cx="27" cy="226" r="4" fill="none" stroke="#f1c40f" stroke-width="2.2"/>`,
  // 烈焰陣：盤旋的火龍
  HK: () => EF(125, 200, 112, 112, 'url(#cgAura)')
    + shp('M158,104 q-72,-26 -84,36 q-8,48 60,60 q60,16 36,72 q-24,48 -84,28 q48,-2 60,-36 q10,-36 -48,-44 q-72,-12 -56,-86 q20,-60 116,-30z', 'url(#cgFire)', null, 2)
    + curve('M150,106 q-58,-16 -68,34 q-6,40 52,50 q50,14 34,62', '#ffeb3b', 5, .9) + curve('M146,108 q-50,-12 -58,30', '#fffde7', 2.4, .9)
    + [[86, 112], [72, 168], [112, 196], [170, 222], [150, 280], [92, 300]].map(([x, y], k) => shp(`M${x},${y} q${k % 2 ? 14 : -14},-10 ${k % 2 ? 8 : -8},-26 q${k % 2 ? -2 : 2},12 ${k % 2 ? -10 : 10},14z`, '#ff9800', null, 1.2)).join('')
    + shp('M158,104 q14,-24 40,-14 q8,6 4,14 l-12,2 q4,8 -4,14 q-14,-2 -28,-16z', '#e53935', 'cgSh', 2) + shp('M186,92 l8,-18 l2,16z M174,94 l2,-20 l6,18z', '#ffeb3b', null, 1.4)
    + E(180, 100, 4, 4, '#ffeb3b', null, 1.2) + E(181, 100, 1.6, 2.6, '#111', null, 0) + fl('M196,108 l-4,8 l-4,-6z', '#fff') + curve('M200,106 q14,2 20,-8 M198,112 q12,8 22,4', '#ff9800', 2.4)
    + star4(60, 90, 6, '#fff59d') + star4(196, 300, 7, '#fff59d') + star4(210, 180, 5),
  // 五行八卦陣：八卦盤、太極與五行
  DK: () => {
    const pts = Array.from({ length: 8 }, (_, k) => { const a = (k * 45 + 22.5) * Math.PI / 180; return `${125 + 80 * Math.cos(a)},${212 + 80 * Math.sin(a)}`; }).join(' ');
    const pts2 = Array.from({ length: 8 }, (_, k) => { const a = (k * 45 + 22.5) * Math.PI / 180; return `${125 + 66 * Math.cos(a)},${212 + 66 * Math.sin(a)}`; }).join(' ');
    const tri = [[1, 1, 1], [0, 1, 1], [1, 0, 1], [0, 0, 1], [1, 1, 0], [0, 1, 0], [1, 0, 0], [0, 0, 0]];
    return EF(125, 212, 110, 110, 'url(#cgHalo)') + `<polygon points="${pts}" fill="#c0392b" ${st(3)}/><polygon points="${pts}" fill="url(#cgSh)"/><polygon points="${pts2}" fill="#fbe9c6" ${st(1.6)}/>`
      + tri.map((t, k) => `<g transform="rotate(${k * 45} 125 212)">${t.map((solid, j) => solid ? shp(`M108,${152 - j * 7} h34 v4.5 h-34z`, '#2b1a10', null, 0) : shp(`M108,${152 - j * 7} h14 v4.5 h-14z M128,${152 - j * 7} h14 v4.5 h-14z`, '#2b1a10', null, 0)).join('')}</g>`).join('')
      + E(125, 212, 34, 34, '#fff', null, 2.4) + `<path d="M125,178 a17,17 0 0,1 0,34 a17,17 0 0,0 0,34 a34,34 0 0,1 0,-68" fill="#111"/>` + E(125, 195, 5.5, 5.5, '#fff', null, 0) + E(125, 229, 5.5, 5.5, '#111', null, 0)
      + fl(elp(125, 212, 34, 34), 'url(#cgBall)')
      + [['火', '#e74c3c', 125, 62], ['水', '#2b5fc1', 186, 96], ['木', '#27ae60', 64, 96], ['金', '#f1c40f', 196, 306], ['土', '#e67e22', 54, 306]].map(([ch, c, x, y]) => E(x, y, 17, 17, c, 'cgSh', 2.4) + EF(x - 5, y - 6, 5, 3, '#fff', .55) + `<text x="${x}" y="${y + 7}" font-size="20" font-weight="900" text-anchor="middle" fill="#fff" stroke="${OL}" stroke-width="1" paint-order="stroke">${ch}</text>`).join('');
  },
  // 轟雷術：雷雲與閃電
  CK: () => EF(125, 170, 110, 90, 'url(#cgGlowB)', .25)
    + shp('M58,172 q-26,-44 22,-58 q12,-36 52,-24 q34,-24 62,12 q42,0 36,46 q14,36 -28,40 h-118 q-40,-4 -26,-16z', 'url(#cgStorm)', null, 2.6)
    + EF(96, 110, 22, 10, '#fff', .2) + EF(160, 102, 18, 8, '#fff', .2) + curve('M70,150 q20,-12 40,-2 M130,128 q20,-12 40,4', '#9575cd', 2, .7)
    + shp('M120,186 l-32,50 h28 l-36,70 l70,-86 h-28 l30,-34z', '#fff59d', null, 2.4) + shp('M118,192 l-22,38 h22 l-22,46 l46,-56 h-24 l22,-28z', '#ffffff', null, 0)
    + shp('M176,190 l-14,30 h14 l-16,36 l34,-44 h-14 l14,-22z', '#fff59d', null, 2) + shp('M76,190 l-10,22 h10 l-12,26 l26,-32 h-10 l10,-16z', '#fff59d', null, 2)
    + Array.from({ length: 9 }, (_, k) => line(64 + k * 16, 300 - (k % 3) * 6, 58 + k * 16, 316 - (k % 3) * 6, '#4fc3f7', 2)).join('') + star4(110, 300, 8, '#fff59d') + star4(184, 266, 6, '#fff59d'),
  // 霸王卡：獨眼綠巨魔手抱城池、扛狼牙棒
  ogre: () => EF(125, 318, 96, 12, 'url(#cgGround)')
    + shaft(196, 236, 208, 120, 9, '#5d3a1a', '#8d6e63', null) + E(210, 112, 22, 30, '#6d4c41', 'cgSh', 2.4) + [[-16, -10], [16, -12], [-14, 14], [18, 12], [0, -30], [-20, 2], [20, 0]].map(([dx, dy]) => shp(`M${210 + dx},${112 + dy} l${dx * .5},${dy * .5} l${dy * .15},${-dx * .15}z`, 'url(#cgMetal)', null, 1.2)).join('')
    + both(shp('M96,280 h26 v28 h-30z', '#7cb342', 'cgSh', 2.2) + shp('M88,306 h36 v8 h-36z', '#5d4037', null, 1.8))
    + shp('M74,214 q-16,54 18,74 h66 q34,-20 18,-74z', '#8bc34a', 'cgSh') + shp('M80,264 h90 l-6,26 h-78z', '#795548', 'cgSh', 2) + `<path d="M80,264 h90 l-6,26 h-78z" fill="url(#cgBar)"/>` + curve('M86,274 l6,12 M106,272 l4,14 M140,272 l-4,14 M160,274 l-6,12', '#4e342e', 1.4)
    + curve('M100,230 q25,10 50,0 M108,248 q17,6 34,0', '#558b2f', 1.6)
    + limb([[172, 218], [196, 240], [200, 230]], 24, 20, '#8bc34a') + E(200, 228, 13, 12, 'url(#cgSkinG)', null, 2.2)
    + E(125, 168, 58, 54, 'url(#cgSkinG)', null, 2.6) + both(shp('M76,146 q-24,-22 -16,-52 q12,24 30,34z', '#fffde7', 'cgSh', 2) + E(70, 172, 9, 12, '#9ccc3a', 'cgSh', 2))
    + shp('M90,140 q35,-18 70,0 l-4,8 q-31,-12 -62,0z', '#33691e', null, 1.6)
    + E(125, 158, 19, 17, '#ffffff', null, 2.4) + E(125, 160, 10, 10, 'url(#cgIris)', null, 0) + E(125, 161, 4.5, 5, '#111', null, 0) + EF(129, 155, 3.5, 3.5, '#fff') + fl('M106,150 q19,-14 38,0 q-19,-8 -38,0z', OL)
    + shp('M92,194 q33,30 66,0 l-6,16 q-27,16 -54,0z', '#5d1a1a', null, 2.2) + both(shp('M98,196 l6,14 l6,-12z', '#fff', null, 1.4)) + shp('M116,204 l4,8 l4,-8z M126,204 l4,8 l4,-8z', '#fff', null, 1)
    + curve('M118,180 q7,5 14,0', '#33691e', 2)
    + `<g transform="translate(32,214)">${shp('M0,22 h44 v36 h-44z', '#f5e6c8', 'cgSh')}${fl('M0,22 h44 v36 h-44z', 'url(#cgGrain)')}${shp('M-6,24 l28,-24 l28,24z', '#c0392b', 'cgSh')}${shp('M16,38 h12 v20 h-12z', '#3e2723', null, 1.4)}${shp('M4,30 h8 v8 h-8z M32,30 h8 v8 h-8z', '#4fc3f7', null, 1)}${line(22, 0, 22, -14, OL, 2)}${shp('M22,-14 l12,4 l-12,4z', '#f1c40f', null, 1)}</g>`
    + limb([[80, 220], [60, 248], [56, 270]], 24, 20, '#8bc34a') + E(58, 272, 13, 12, 'url(#cgSkinG)', null, 2.2),
};

/* ---- 牌面 ---- */
const RED_SUIT = { H: 1, D: 1 };
const SUIT_CH = { S: '♠', H: '♥', D: '♦', C: '♣' };
/* ---- 主題登記：各主題提供自己的人物特徵、介紹文與特別卡圖；未提供者沿用三國版 ---- */
const ART_THEMES = { sanguo: { fig: FIG, text: CARD_TEXT, art: SPECIAL_ART, alias: {} } };
let curTheme = 'sanguo';
const activeFig = code => ART_THEMES[curTheme].fig[code] || FIG[code];
const activeText = code => { const t = ART_THEMES[curTheme].text[code]; return t != null ? t : (CARD_TEXT[code] || ''); };
// alias：沿用其他主題的特別卡圖，例如 { SK: 'shuihu:SK', HQ: 'HQ' }（不寫主題即三國版）
const activeArt = code => {
  const t = ART_THEMES[curTheme];
  if (t.art[code]) return t.art[code];
  const a = t.alias[code];
  if (a) { const [th, c] = a.includes(':') ? a.split(':') : ['sanguo', a]; return (ART_THEMES[th] && ART_THEMES[th].art[c]) || SPECIAL_ART[c]; }
  return SPECIAL_ART[code];
};
// d: { fig, text, art }；art 中的鬼牌請用 'ogre' 這個鍵
function registerCardTheme(key, d) { ART_THEMES[key] = { fig: d.fig || {}, text: d.text || {}, art: d.art || {}, alias: d.alias || {} }; }
function setCardTheme(key) { if (ART_THEMES[key]) curTheme = key; }

const _cardCache = {};
// 把運算產生的長小數縮成一位，縮短字串
const tidy = svg => svg.replace(/(\d+\.\d{2,})/g, m => String(Math.round(+m * 10) / 10));
function cardSvg(c, cls = '') {
  ensureCardDefs();
  const key = curTheme + '|' + c.code + '|' + cls;
  if (_cardCache[key]) return _cardCache[key];
  const joker = c.code.startsWith('X');
  const suit = joker ? '' : SUIT_CH[c.code[0]], rank = joker ? '' : c.code.slice(1);
  const col = !joker && RED_SUIT[c.code[0]] ? '#d0021b' : '#111';
  const corner = joker
    ? `<g font-size="22" font-weight="700"><text x="15" y="34" fill="#d0021b">♦</text><text x="15" y="58" fill="#111">♠</text><text x="15" y="82" fill="#d0021b">♥</text><text x="15" y="106" fill="#111">♣</text></g>`
    : `<text x="14" y="42" font-size="34" fill="${col}" font-family="Georgia,'Times New Roman',serif">${rank}</text><text x="16" y="68" font-size="26" fill="${col}">${suit}</text>`;
  const art = tidy(c.kind === 'general' ? figureSvg(c.code) : c.kind === 'overlord' ? activeArt('ogre')() : activeArt(c.code)());
  const svg = `<svg class="cimg ${cls}" viewBox="0 0 250 350" xmlns="http://www.w3.org/2000/svg" font-family="'PingFang TC','Heiti TC','Microsoft JhengHei',sans-serif" role="img" aria-label="${suitOf_(c)}">`
    + `<rect x="2" y="2" width="246" height="346" rx="16" fill="#fffdf6" stroke="#b9b2a0" stroke-width="3"/>${corner}<g transform="rotate(180 125 175)">${corner}</g>`
    + `<g transform="translate(125 190) scale(0.92) translate(-125 -190)">${art}</g></svg>`;
  return (_cardCache[key] = svg);
}
const suitOf_ = c => c.code.startsWith('X') ? '鬼牌' : SUIT_CH[c.code[0]] + c.code.slice(1);

/* 懸停時顯示的資料 */
function cardInfoHtml(c, help) {
  const head = `<b>${c.name}</b>　<span style="color:${RED_SUIT[c.code[0]] ? '#d0021b' : '#111'}">${suitOf_(c)}</span>`;
  if (c.kind === 'general') return `${head}<div class="tipstats"><span>攻擊力 <b>${c.atk}</b></span><span>防禦力 <b>${c.def}</b></span></div><div>${activeText(c.code)}</div>`;
  if (c.kind === 'overlord') return `${head}<div>${activeText(c.code)}</div>${help ? `<div class="tiphelp">${help}</div>` : ''}`;
  return `${head}<div class="tipstats"><span>摧毀力 <b>${c.power}</b></span><span>（本卡限用一次）</span></div>${help ? `<div class="tiphelp">${help}</div>` : ''}`;
}

window.cardSvg = cardSvg;
// 單一人物圖（不含牌框），供棋盤起點格使用；fy 為腳底的 y 座標（牌面座標 250×350）
window.cardFigure = (theme, code) => {
  const prev = curTheme;
  setCardTheme(theme);
  const f = activeFig(code), R = f.fat ? 52 : 48, seated = ['moto', 'tank', 'rock', 'trike', 'chair', 'jet'].includes(f.ride);
  const fy = HY + R - 6 + 54 + (seated ? 22 : 30) + 34;
  const svg = tidy(figureSvg(code));
  curTheme = prev;
  return { svg, fy };
};
window.cardDefs = () => CARD_DEFS.replace(/^<svg[^>]*>/, '').replace(/<\/svg>\s*$/, '');
window.cardInfoHtml = cardInfoHtml;
window.registerCardTheme = registerCardTheme;
window.setCardTheme = setCardTheme;
})();
