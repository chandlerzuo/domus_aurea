'use strict';
// 楚漢傳奇主題：人物特徵、介紹文與特別卡圖（於 cards.js、theme-shuihu-art.js 之後載入）
(() => {

/* ---- 人物特徵（鍵同 cards.js 之 FIG） ---- */
const FIG = {
  // 主帥
  SA: { body: 'robe', hat: ['crown', '#8b1a1a', '#f2c200'], cloth: ['#c0392b', '#f2c200'], beard: ['long', '#1b1b1b'], weapon: 'jian', brow: 'kind', mouth: 'smile' },  // 劉邦：赤霄劍
  HA: { body: 'armor', hat: ['helm', '#1b1b1b', '#c0392b'], cloth: ['#1b1b1b', '#c0392b'], beard: ['full', '#1b1b1b'], weapon: 'halberd', cape: '#c0392b', brow: 'angry' }, // 項羽：霸王戟
  DA: { body: 'armor', hat: ['helm', '#2b5fc1', '#f1c40f'], cloth: ['#2b5fc1', '#f1c40f'], beard: ['goatee', '#1b1b1b'], weapon: 'jian', cape: '#2b5fc1', brow: 'thick' }, // 韓信
  CA: { body: 'robe', fat: 1, hat: ['crown', '#1b1b1b', '#f2c200'], cloth: ['#1b1b1b', '#c0392b'], fold: 1, eyes: 'narrow', mouth: 'grin' },                            // 秦二世
  // 2 點：身懷異術者
  S2: { body: 'robe', old: 1, hat: ['band', '#5d4037'], cloth: ['#d7ccc8', '#5d4037'], beard: ['long', '#ffffff'], weapon: 'staff', stones: 1, brow: 'kind' },          // 黃石公：圯上授書
  H2: { body: 'robe', old: 1, hair: ['topknot', '#ecf0f1'], cloth: ['#c0392b', '#f5f0e1'], beard: ['long', '#ecf0f1'], weapon: 'fan', cloud: 1, brow: 'kind' },        // 赤松子
  D2: { body: 'robe', hat: ['daoist', '#1f3f8f', '#f1c40f'], cloth: ['#2e86c1', '#f5f0e1'], beard: ['goatee', '#1b1b1b'], weapon: 'brush', wave: 1, mouth: 'smile' },  // 徐福：東渡求仙
  C2: { body: 'robe', old: 1, hat: ['daoist', '#5b2c6f', '#f1c40f'], cloth: ['#d2b4de', '#5b2c6f'], beard: ['long', '#e8e8e8'], weapon: 'staff', halo: 1, brow: 'kind' }, // 安期生
  // ♠ 漢
  S3: { body: 'armor', hat: ['round', '#c0392b', '#f1c40f'], cloth: ['#c0392b', '#f1c40f'], weapon: 'spear', mouth: 'smile' },                                           // 盧綰
  S4: { body: 'armor', hat: ['helm', '#c0392b', '#f1c40f'], cloth: ['#a93226', '#f1c40f'], beard: ['mustache', '#1b1b1b'], weapon: 'whip', brow: 'kind' },              // 夏侯嬰：為劉邦駕車
  S5: { body: 'robe', hat: ['scholar', '#8b1a1a', '#f1c40f'], cloth: ['#8b1a1a', '#f5f0e1'], beard: ['long', '#1b1b1b'], weapon: 'brush', brow: 'kind' },              // 蕭何
  S6: { body: 'armor', hat: ['helm', '#922b21', '#f1c40f'], cloth: ['#922b21', '#2c3e50'], beard: ['full', '#1b1b1b'], weapon: 'blade', brow: 'thick' },               // 周勃
  S7: { body: 'robe', hat: ['scholar', '#1f3f8f', '#f1c40f'], cloth: ['#5dade2', '#f5f0e1'], beard: ['goatee', '#1b1b1b'], weapon: 'fan', brow: 'kind', mouth: 'smile' }, // 張良
  S8: { body: 'armor', hat: ['helm', '#c0392b', '#ecf0f1'], cloth: ['#c0392b', '#ecf0f1'], beard: ['full', '#1b1b1b'], weapon: 'spear', brow: 'thick' },               // 王陵
  S9: { body: 'armor', hat: ['helm', '#e74c3c', '#f1c40f'], cloth: ['#e74c3c', '#2c3e50'], beard: ['mustache', '#1b1b1b'], weapon: 'halberd', brow: 'angry' },         // 酈商
  S10: { body: 'armor', hat: ['helm', '#b03a2e', '#f1c40f'], cloth: ['#b03a2e', '#f1c40f'], beard: ['long', '#1b1b1b'], weapon: 'guandao', brow: 'thick' },            // 曹參
  SJ: { body: 'armor', fat: 1, hair: ['wild', '#1b1b1b'], cloth: ['#7b241c', '#f1c40f'], beard: ['full', '#111111'], weapon: 'dao', shield: '#7b241c', brow: 'angry', mouth: 'open' }, // 樊噲：持盾闖鴻門
  // ♥ 楚
  H3: { body: 'lady', hair: ['bun', '#1b1b1b'], cloth: ['#ecf0f1', '#c0392b'], brow: 'kind', mouth: 'smile' },                                                            // 虞姬
  H4: { body: 'robe', old: 1, hat: ['cap', '#1b1b1b', '#c0392b'], cloth: ['#5d6d7e', '#c0392b'], beard: ['long', '#9e9e9e'], brow: 'kind', mouth: 'smile' },          // 項伯
  H5: { body: 'robe', hat: ['scholar', '#2c3e50', '#c0392b'], cloth: ['#2c3e50', '#f5f0e1'], beard: ['goatee', '#1b1b1b'], weapon: 'brush', eyes: 'narrow' },          // 武涉
  H6: { body: 'armor', hat: ['helm', '#1b1b1b', '#c0392b'], cloth: ['#2c3e50', '#c0392b'], weapon: 'jian', brow: 'angry', mouth: 'grin' },                              // 項莊：舞劍
  H7: { body: 'robe', old: 1, hat: ['scholar', '#1b1b1b', '#c0392b'], cloth: ['#4d5656', '#c0392b'], beard: ['long', '#ffffff'], weapon: 'staff', brow: 'thick', mouth: 'frown' }, // 范增
  H8: { body: 'armor', hat: ['helm', '#424949', '#c0392b'], cloth: ['#424949', '#c0392b'], beard: ['goatee', '#1b1b1b'], weapon: 'spear', brow: 'kind' },              // 季布
  H9: { body: 'armor', hat: ['helm', '#17202a', '#e74c3c'], cloth: ['#17202a', '#e74c3c'], beard: ['full', '#1b1b1b'], weapon: 'blade', brow: 'angry' },               // 鍾離眜
  H10: { body: 'armor', old: 1, hat: ['helm', '#1b1b1b', '#f1c40f'], cloth: ['#641e16', '#f1c40f'], beard: ['long', '#bdbdbd'], weapon: 'jian', brow: 'thick' },       // 項梁
  HJ: { body: 'armor', hat: ['horn', '#1b1b1b', '#e74c3c'], cloth: ['#1b1b1b', '#e74c3c'], beard: ['full', '#111111'], weapon: 'twinspear', brow: 'angry', mouth: 'open' }, // 龍且
  // ♦ 諸侯
  D3: { body: 'robe', hat: ['scholar', '#7d6608', '#f1c40f'], cloth: ['#b7950b', '#f5f0e1'], beard: ['goatee', '#1b1b1b'], fold: 1, mouth: 'smile' },                   // 叔孫通：制朝儀
  D4: { body: 'robe', hat: ['cap', '#1e8449', '#f1c40f'], cloth: ['#1e8449', '#f5f0e1'], beard: ['mustache', '#1b1b1b'], weapon: 'fan', mouth: 'smile' },             // 隨何
  D5: { body: 'robe', hat: ['scholar', '#117864', '#f1c40f'], cloth: ['#117864', '#f5f0e1'], beard: ['long', '#1b1b1b'], weapon: 'brush', eyes: 'narrow' },           // 蒯通
  D6: { body: 'robe', old: 1, hat: ['crown', '#1f618d', '#f2c200'], cloth: ['#1f618d', '#f1c40f'], beard: ['long', '#9e9e9e'], weapon: 'jian', brow: 'kind' },         // 張耳
  D7: { body: 'robe', hat: ['tall', '#4a235a', '#f1c40f'], cloth: ['#7d3c98', '#f5f0e1'], beard: ['goatee', '#1b1b1b'], weapon: 'brush', eyes: 'wink', brow: 'kind' },  // 陳平：六出奇計
  D8: { body: 'armor', hat: ['helm', '#1a5276', '#f1c40f'], cloth: ['#1a5276', '#f1c40f'], weapon: 'bow', brow: 'thick' },                                               // 灌嬰：騎將
  D9: { body: 'armor', hat: ['helm', '#a04000', '#f1c40f'], cloth: ['#a04000', '#f1c40f'], beard: ['full', '#1b1b1b'], weapon: 'spear', brow: 'thick', mouth: 'smile' }, // 紀信
  D10: { body: 'armor', hat: ['band', '#1b1b1b'], cloth: ['#145a32', '#f1c40f'], beard: ['full', '#1b1b1b'], weapon: 'oar', brow: 'angry' },                           // 彭越：起於巨野澤
  DJ: { body: 'armor', face: '#c98f62', hat: ['helm', '#1b1b1b', '#f1c40f'], cloth: ['#212f3d', '#f1c40f'], beard: ['full', '#111111'], weapon: 'blade', mark: ['face', '#2c3e50'], brow: 'angry', mouth: 'open' }, // 英布：黥面
  // ♣ 秦
  C3: { body: 'armor', hat: ['round', '#1b1b1b', '#7f8c8d'], cloth: ['#1b1b1b', '#7f8c8d'], weapon: 'dao', brow: 'angry' },                                              // 閻樂
  C4: { body: 'armor', hat: ['helm', '#2c3e50', '#7f8c8d'], cloth: ['#2c3e50', '#7f8c8d'], weapon: 'spear', brow: 'kind' },                                              // 李由
  C5: { body: 'robe', hat: ['tall', '#1b1b1b', '#f1c40f'], cloth: ['#1b1b1b', '#c0392b'], beard: ['long', '#1b1b1b'], weapon: 'brush', brow: 'thick' },                // 李斯
  C6: { body: 'armor', hat: ['helm', '#4d5656', '#f1c40f'], cloth: ['#4d5656', '#c0392b'], beard: ['mustache', '#1b1b1b'], weapon: 'blade', brow: 'thick' },           // 董翳
  C7: { body: 'robe', hat: ['tall', '#4a235a', '#f1c40f'], cloth: ['#4a235a', '#f1c40f'], eyes: 'narrow', brow: 'angry', mouth: 'grin' },                              // 趙高：指鹿為馬
  C8: { body: 'armor', hat: ['helm', '#1b2631', '#e74c3c'], cloth: ['#1b2631', '#e74c3c'], beard: ['goatee', '#1b1b1b'], weapon: 'jian', brow: 'angry' },              // 司馬欣
  C9: { body: 'armor', hat: ['helm', '#212121', '#f1c40f'], cloth: ['#212121', '#f1c40f'], beard: ['full', '#1b1b1b'], weapon: 'halberd', brow: 'thick' },             // 王離
  C10: { body: 'armor', hat: ['helm', '#424242', '#f1c40f'], cloth: ['#424242', '#c0392b'], beard: ['long', '#1b1b1b'], weapon: 'spear', cape: '#7b241c', brow: 'thick' }, // 蒙恬
  CJ: { body: 'armor', hat: ['horn', '#1b1b1b', '#f1c40f'], cloth: ['#1b1b1b', '#f1c40f'], beard: ['full', '#1b1b1b'], weapon: 'guandao', cape: '#1b1b1b', brow: 'angry', mouth: 'frown' }, // 章邯
};

/* ---- 介紹文 ---- */
const TEXT = {
  SA: '沛縣亭長起家，約法三章、知人善任，終敗項羽，建立漢朝。',
  HA: '西楚霸王，力能扛鼎，破釜沉舟大敗秦軍於鉅鹿，終於垓下兵敗。',
  DA: '兵仙，受胯下之辱而不改其志，暗度陳倉、背水一戰，用兵多多益善。',
  CA: '秦始皇少子胡亥，聽信趙高篡位登基，昏庸殘暴，秦亡於其手。',
  S2: '隱士，於下邳圯上三試張良，授以《太公兵法》。',
  H2: '上古仙人，張良功成身退後願從其遊。',
  D2: '秦代方士，奉始皇之命率童男童女東渡求長生不老藥。',
  C2: '傳說中的海上仙人，賣藥東海邊，人稱〔千歲翁〕。',
  S3: '劉邦同鄉好友，與劉邦同日出生，後封燕王。',
  S4: '劉邦的車夫與好友，彭城兵敗時護劉邦子女脫險。',
  S5: '漢初三傑之一，月下追韓信，坐鎮關中供應糧草，定律令。',
  S6: '漢初功臣，為人質樸剛毅，後平定諸呂之亂。',
  S7: '漢初三傑之一，運籌帷幄之中，決勝千里之外，圯上受書。',
  S8: '沛縣豪傑，率眾歸漢，為人剛直。',
  S9: '漢將，屢立戰功，為酈食其之弟。',
  S10: '漢初功臣，攻城略地無數，繼蕭何為相，蕭規曹隨。',
  SJ: '屠狗出身，劉邦連襟。鴻門宴上持盾闖帳，怒目而視，護主脫險。',
  H3: '項羽寵姬，垓下之圍中與霸王訣別，留下〈霸王別姬〉的故事。',
  H4: '項羽叔父，鴻門宴前通報張良，席間以身護劉邦。',
  H5: '項羽謀士，曾奉命遊說韓信三分天下。',
  H6: '項羽堂弟，鴻門宴上拔劍起舞，意在沛公。',
  H7: '項羽亞父，屢勸項羽除去劉邦，後被陳平離間而去。',
  H8: '楚將，重信守諾，人稱〔一諾千金〕。',
  H9: '項羽麾下驍將，勇猛善戰，屢次擊敗漢軍。',
  H10: '項羽叔父，與項羽起兵吳中，立楚懷王以號令天下。',
  HJ: '楚國大將，率二十萬大軍救齊，於濰水被韓信水淹大敗。',
  D3: '儒者，為漢高祖制定朝儀，使群臣知禮。',
  D4: '漢初謀士，奉命出使九江，說服英布叛楚歸漢。',
  D5: '辯士，曾勸韓信自立，與楚、漢三分天下。',
  D6: '趙王，原為魏國名士，與陳餘為刎頸之交，後反目。',
  D7: '六出奇計，離間項羽與范增，解滎陽之圍，後為丞相。',
  D8: '漢初騎兵大將，率軍追擊項羽至烏江。',
  D9: '漢將，滎陽被圍時假扮劉邦出城詐降，為主赴死。',
  D10: '起於巨野澤的梁地豪強，擅長游擊，斷楚軍糧道。',
  DJ: '受黥刑故稱黥布，驍勇善戰，先為楚將，後歸漢封淮南王。',
  C3: '趙高女婿，咸陽令，奉趙高之命逼殺秦二世。',
  C4: '李斯長子，三川郡守，與起義軍激戰。',
  C5: '秦朝丞相，輔佐始皇統一文字、度量衡，後被趙高陷害。',
  C6: '秦將，隨章邯投降項羽，被封為翟王。',
  C7: '秦朝宦官，矯詔逼死扶蘇，指鹿為馬，獨攬朝政。',
  C8: '秦將，隨章邯降楚，被封為塞王。',
  C9: '秦將王翦之孫，率長城軍團圍鉅鹿，被項羽所破。',
  C10: '秦朝名將，北擊匈奴、修築長城，威震塞外。',
  CJ: '秦朝少府，率驪山刑徒平定陳勝起義，鉅鹿之戰後降楚。',
  X1: '力拔山兮氣蓋世，西楚霸王所向無敵。',
  X2: '力拔山兮氣蓋世，西楚霸王所向無敵。',
};

// 武器、陣式沿用三國版的圖（霹靂車←火鏞炮、赤霄劍←巨魔劍、火牛陣、火燒棧道←烈焰陣、
// 十面埋伏←五行八卦陣、四面楚歌←轟雷術）；大黃弩、迷魂香用水滸毒藥弩、蒙汗藥的圖；鬼牌畫成西楚霸王大旗
window.registerCardTheme('chuhan', { fig: FIG, text: TEXT, art: { ogre: () => window.cardBanner(['西', '楚', '霸', '王']) }, alias: { DQ: 'shuihu:DQ', CQ: 'shuihu:CQ' } });
})();
