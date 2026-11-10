'use strict';
// 封神演義主題：人物特徵、介紹文與特別卡圖（於 cards.js、theme-shuihu-art.js 之後載入）
(() => {

/* ---- 人物特徵（鍵同 cards.js 之 FIG） ---- */
const FIG = {
  // 主帥
  SA: { body: 'robe', old: 1, hat: ['daoist', '#2b5fc1', '#f1c40f'], cloth: ['#e8e2d0', '#2b5fc1'], beard: ['long', '#e8e8e8'], weapon: 'whip', brow: 'kind' },            // 姜子牙：打神鞭
  HA: { body: 'robe', hat: ['crown', '#8b1a1a', '#f2c200'], cloth: ['#c0392b', '#f2c200'], beard: ['goatee', '#1b1b1b'], weapon: 'jian', brow: 'kind', mouth: 'smile' }, // 姬發
  DA: { body: 'armor', hat: ['helm', '#f1c40f', '#c0392b'], cloth: ['#d4a017', '#8b1a1a'], beard: ['full', '#1b1b1b'], weapon: 'spear', brow: 'thick' },                // 黃飛虎
  CA: { body: 'robe', fat: 1, hat: ['crown', '#1b1b1b', '#f2c200'], cloth: ['#4a235a', '#f2c200'], beard: ['full', '#1b1b1b'], fold: 1, brow: 'angry', mouth: 'frown' }, // 紂王
  // 2 點：身懷異術者
  S2: { body: 'robe', hair: ['topknot', '#1b1b1b'], cloth: ['#8d6e63', '#5d4037'], weapon: 'club', stones: 1, mouth: 'grin', brow: 'thick' },                           // 土行孫：地行術
  H2: { body: 'robe', face: '#7cb342', hair: ['wild', '#e53935'], cloth: ['#2e7d32', '#f1c40f'], weapon: 'club', charm: 1, brow: 'angry', mouth: 'open' },              // 雷震子：風雷雙翅
  D2: { body: 'armor', hat: ['helm', '#c0392b', '#f1c40f'], cloth: ['#c0392b', '#f1c40f'], beard: ['full', '#1b1b1b'], weapon: 'mace', halo: 1, brow: 'angry', mouth: 'frown' }, // 鄭倫：哼
  C2: { body: 'armor', hat: ['helm', '#f1c40f', '#c0392b'], cloth: ['#f1c40f', '#8e44ad'], beard: ['full', '#1b1b1b'], weapon: 'fork', charm: 1, brow: 'angry', mouth: 'open' }, // 陳奇：哈
  // ♠ 闡教與西岐
  S3: { body: 'robe', hat: ['band', '#5d4037'], cloth: ['#6d4c2f', '#c9a227'], weapon: 'axe', bare: 1, mouth: 'smile' },                                                   // 武吉：樵夫
  S4: { body: 'armor', hat: ['helm', '#2b5fc1', '#f1c40f'], cloth: ['#2b5fc1', '#f1c40f'], beard: ['full', '#1b1b1b'], weapon: 'blade', brow: 'thick' },               // 南宮适
  S5: { body: 'robe', hat: ['scholar', '#1f3f8f', '#f1c40f'], cloth: ['#1f3f8f', '#f5f0e1'], beard: ['long', '#1b1b1b'], weapon: 'brush', brow: 'kind' },              // 散宜生
  S6: { body: 'armor', hat: ['helm', '#f1c40f', '#2b5fc1'], cloth: ['#2b5fc1', '#f1c40f'], weapon: 'mace', halo: 1, brow: 'thick' },                                    // 韋護：降魔杵
  S7: { body: 'robe', old: 1, hat: ['daoist', '#c0392b', '#f1c40f'], cloth: ['#f5f0e1', '#c0392b'], beard: ['long', '#e8e8e8'], weapon: 'staff', cloud: 1, brow: 'kind' }, // 太乙真人
  S8: { body: 'armor', hat: ['helm', '#f1c40f', '#c0392b'], cloth: ['#f1c40f', '#2b5fc1'], weapon: 'jian', brow: 'kind' },                                               // 金吒
  S9: { body: 'armor', hat: ['helm', '#27ae60', '#f1c40f'], cloth: ['#27ae60', '#f1c40f'], weapon: 'twindao', brow: 'kind', mouth: 'smile' },                           // 木吒：吳鉤雙劍
  S10: { body: 'armor', hat: ['helm', '#f1c40f', '#e74c3c'], cloth: ['#e67e22', '#f1c40f'], weapon: 'mace', brow: 'angry' },                                            // 黃天化
  SJ: { body: 'armor', hat: ['helm', '#dfe6e9', '#f1c40f'], cloth: ['#ecf0f1', '#2b5fc1'], weapon: 'sanjian', mark: ['face', '#c0392b'], cape: '#2b5fc1', brow: 'thick' }, // 楊戩：天眼、三尖兩刃刀
  // ♥ 周室
  H3: { body: 'lady', hair: ['ponytail', '#1b1b1b'], cloth: ['#e74c3c', '#f8c8dc'], stones: 1, mouth: 'smile', brow: 'kind' },                                           // 鄧嬋玉：五光石
  H4: { body: 'armor', hat: ['helm', '#e74c3c', '#f1c40f'], cloth: ['#e74c3c', '#f1c40f'], weapon: 'spear', mouth: 'grin' },                                             // 黃天祥
  H5: { body: 'robe', hat: ['cap', '#8b1a1a', '#f1c40f'], cloth: ['#f5f0e1', '#c0392b'], fold: 1, brow: 'kind', mouth: 'smile' },                                       // 伯邑考
  H6: { body: 'armor', hat: ['helm', '#8e44ad', '#f1c40f'], cloth: ['#8e44ad', '#f1c40f'], beard: ['long', '#1b1b1b'], weapon: 'pagoda', brow: 'thick' },              // 李靖：玲瓏寶塔
  H7: { body: 'robe', old: 1, hat: ['daoist', '#f1c40f', '#8b1a1a'], cloth: ['#f9e79f', '#8b1a1a'], beard: ['long', '#bdbdbd'], weapon: 'jian', halo: 1, brow: 'kind' }, // 廣成子
  H8: { body: 'armor', hat: ['crown', '#1b1b1b', '#f2c200'], cloth: ['#2c3e50', '#f1c40f'], weapon: 'halberd', brow: 'angry' },                                          // 殷郊
  H9: { body: 'lady', hair: ['bun', '#1b1b1b'], cloth: ['#5dade2', '#f5f0e1'], cloud: 1, mouth: 'smile', brow: 'kind' },                                                 // 龍吉公主
  H10: { body: 'armor', face: '#7d5637', hat: ['helm', '#2c3e50', '#f1c40f'], cloth: ['#2c3e50', '#c0392b'], beard: ['full', '#111111'], weapon: 'axes', brow: 'angry', mouth: 'open' }, // 崇黑虎
  HJ: { body: 'armor', hair: ['buns', '#1b1b1b'], cloth: ['#e74c3c', '#f1c40f'], weapon: 'spear', cloud: 1, brow: 'angry', mouth: 'grin' },                             // 哪吒：火尖槍、風火輪
  // ♦ 武成王與歸周諸侯
  D3: { body: 'armor', hat: ['helm', '#7f8c8d', '#f1c40f'], cloth: ['#7f8c8d', '#2c3e50'], beard: ['mustache', '#1b1b1b'], weapon: 'axe', brow: 'thick' },             // 周紀
  D4: { body: 'armor', hat: ['helm', '#d35400', '#f1c40f'], cloth: ['#d35400', '#f1c40f'], beard: ['full', '#1b1b1b'], weapon: 'blade', brow: 'angry' },               // 黃明
  D5: { body: 'robe', old: 1, hat: ['cap', '#1f3f8f', '#f1c40f'], cloth: ['#5d6d7e', '#f1c40f'], beard: ['long', '#9e9e9e'], weapon: 'spear', brow: 'thick' },         // 蘇護
  D6: { body: 'armor', hat: ['helm', '#16a085', '#f1c40f'], cloth: ['#16a085', '#f1c40f'], beard: ['goatee', '#1b1b1b'], weapon: 'dao', brow: 'thick' },               // 洪錦
  D7: { body: 'robe', old: 1, hair: ['bald'], cloth: ['#f5cba7', '#8b4513'], beard: ['long', '#e8e8e8'], weapon: 'staff', halo: 1, brow: 'kind' },                     // 燃燈道人
  D8: { body: 'armor', hat: ['helm', '#2980b9', '#f1c40f'], cloth: ['#2980b9', '#ecf0f1'], weapon: 'spear', mouth: 'smile' },                                            // 姜文煥
  D9: { body: 'armor', old: 1, hat: ['helm', '#a04000', '#f1c40f'], cloth: ['#a04000', '#f1c40f'], beard: ['full', '#bdbdbd'], weapon: 'guandao', brow: 'thick' },     // 鄧九公
  D10: { body: 'armor', hat: ['helm', '#117a65', '#f1c40f'], cloth: ['#117a65', '#f1c40f'], weapon: 'jian', brow: 'kind' },                                             // 殷洪
  DJ: { body: 'armor', hat: ['feather', '#f1c40f', '#e74c3c'], cloth: ['#f1c40f', '#16a085'], weapon: 'blade', halo: 1, cape: '#e74c3c', brow: 'thick' },               // 孔宣：五色神光
  // ♣ 殷商與截教
  C3: { body: 'robe', hat: ['cap', '#4a235a', '#f1c40f'], cloth: ['#7d3c98', '#f1c40f'], beard: ['mustache', '#1b1b1b'], brow: 'angry', mouth: 'grin', eyes: 'narrow' }, // 費仲
  C4: { body: 'robe', fat: 1, hat: ['cap', '#1b1b1b', '#f1c40f'], cloth: ['#2c3e50', '#f1c40f'], beard: ['goatee', '#1b1b1b'], mouth: 'grin', eyes: 'wink' },            // 尤渾
  C5: { body: 'robe', hat: ['daoist', '#1b1b1b', '#f1c40f'], cloth: ['#2c3e50', '#c0392b'], beard: ['goatee', '#1b1b1b'], weapon: 'jian', cape: '#d9a93a', leo: 1, brow: 'angry', eyes: 'narrow' }, // 申公豹：騎黑虎
  C6: { body: 'armor', hat: ['helm', '#1b1b1b', '#c0392b'], cloth: ['#1b1b1b', '#c0392b'], weapon: 'blade', brow: 'angry', mouth: 'frown' },                             // 余化：化血神刀
  C7: { body: 'lady', hair: ['bun', '#1b1b1b'], cloth: ['#8e44ad', '#f8c8dc'], tail: 1, mouth: 'smile', eyes: 'wink' },                                                  // 妲己：狐尾
  C8: { body: 'armor', fat: 1, face: '#5d8aa8', hat: ['helm', '#2c3e50', '#f1c40f'], cloth: ['#2c3e50', '#27ae60'], beard: ['full', '#1b1b1b'], weapon: 'jian', brow: 'angry', mouth: 'open' }, // 魔禮青：青雲劍
  C9: { body: 'armor', hat: ['helm', '#4a235a', '#c0392b'], cloth: ['#4a235a', '#c0392b'], beard: ['full', '#1b1b1b'], weapon: 'dao', stones: 1, brow: 'angry' },      // 張奎
  C10: { body: 'armor', face: '#4a4a4a', hat: ['helm', '#1b1b1b', '#f1c40f'], cloth: ['#1b1b1b', '#f1c40f'], beard: ['full', '#111111'], weapon: 'whips', cape: '#d9a93a', leo: 1, brow: 'angry', mouth: 'open' }, // 趙公明
  CJ: { body: 'armor', old: 1, hat: ['helm', '#2c3e50', '#f1c40f'], cloth: ['#6c3483', '#f1c40f'], beard: ['long', '#e8e8e8'], weapon: 'whips', mark: ['face', '#f1c40f'], brow: 'angry', mouth: 'frown' }, // 聞仲：額生神目、雌雄金鞭
};

/* ---- 介紹文 ---- */
const TEXT = {
  SA: '元始天尊門下，渭水垂釣遇文王，拜為丞相。持打神鞭、杏黃旗，奉命封神。',
  HA: '西伯侯姬昌次子，即周武王。仁德寬厚，興兵伐紂，牧野一戰定天下。',
  DA: '殷商武成王，因紂王無道反出五關投周。騎五色神牛，忠勇冠世。',
  CA: '商朝末代君主。寵信妲己、建鹿台、設炮烙，荒淫無道，終失天下。',
  S2: '懼留孫門徒。身材矮小，善地行之術，日行千里，以捆仙繩擒敵。',
  H2: '文王收養之子。食仙杏生出風雷雙翅，青面獠牙，手持黃金棍。',
  D2: '哼將。鼻中噴出兩道白光，吸人魂魄，敵將應聲落馬。',
  C2: '哈將。口吐黃氣，敵人聞之魂魄自散，與鄭倫並稱〔哼哈二將〕。',
  S3: '西岐樵夫，誤傷人命，得姜子牙指點避禍，拜師後成為周將。',
  S4: '西岐大將，勇猛善戰，輔佐文王、武王東征。',
  S5: '西岐上大夫，足智多謀，為周室重臣。',
  S6: '道行天尊門徒，手持降魔杵，護法降妖。',
  S7: '闡教十二金仙之一，乾元山金光洞主，哪吒之師。',
  S8: '李靖長子，文殊廣法天尊門徒，持遁龍樁。',
  S9: '李靖次子，普賢真人門徒，持吳鉤雙劍。',
  S10: '黃飛虎長子，清虛道德真君門徒，持攢心釘、乘玉麒麟。',
  SJ: '玉鼎真人門徒，額生天眼，通八九玄功、七十二變，持三尖兩刃刀。',
  H3: '鄧九公之女，善發五光石，百發百中，後嫁土行孫。',
  H4: '黃飛虎幼子，少年英武，槍法如神。',
  H5: '西伯侯長子，孝順溫良，善撫琴，為救父入朝歌而遇害。',
  H6: '陳塘關總兵，哪吒之父。燃燈道人授以玲瓏寶塔，人稱〔托塔天王〕。',
  H7: '闡教十二金仙之首，九仙山桃源洞主，持番天印。',
  H8: '紂王太子，廣成子門徒，後化三頭六臂。',
  H9: '昊天上帝之女，持霧露乾坤網，善用法寶，後嫁洪錦。',
  H10: '北伯侯崇侯虎之弟，面如鍋底，持雙板斧，葫蘆中藏神鷹。',
  HJ: '太乙真人門徒，蓮花化身。腳踏風火輪，持火尖槍、乾坤圈、混天綾。',
  D3: '黃飛虎麾下勇將，隨武成王反出五關。',
  D4: '黃飛虎結義兄弟，隨其反出五關投周。',
  D5: '冀州侯，妲己之父，因獻女受辱，後歸順西周。',
  D6: '三山關總兵，善旗門遁術，歸周後娶龍吉公主。',
  D7: '闡教副教主，靈鷲山元覺洞主，持乾坤尺、定海珠。',
  D8: '東伯侯姜桓楚之子，為報父仇起兵反商。',
  D9: '三山關總兵，驍勇善戰，後歸順西周。',
  D10: '紂王次子，赤精子門徒，持陰陽鏡。',
  DJ: '三山關總兵，背生五色神光，萬物皆可收入光中，難逢敵手。',
  C3: '紂王佞臣，善於阿諛奉承，進讒陷害忠良。',
  C4: '與費仲並稱奸佞，貪財好賄，蠱惑紂王。',
  C5: '姜子牙師弟，投截教，騎黑虎四處遊說各路仙人對抗西周。',
  C6: '汜水關大將，善使化血神刀，人稱〔七首將軍〕。',
  C7: '千年狐精附身之絕色美女，迷惑紂王，助紂為虐。',
  C8: '佳夢關魔家四將之首，持青雲劍，揮舞即起黑風。',
  C9: '澠池守將，善地行之術，騎獨角烏煙獸。',
  C10: '截教峨眉山羅浮洞主，騎黑虎，持定海珠、縛龍索，後封財神。',
  CJ: '商朝太師，截教金靈聖母門徒。額生神目，持雌雄金鞭，忠心護商。',
  X1: '姜子牙奉元始天尊之命封神，榜上有名者皆歸天庭。',
  X2: '姜子牙奉元始天尊之命封神，榜上有名者皆歸天庭。',
};

// 武器、陣式沿用三國版的圖（九龍神火罩←火鏞炮、誅仙劍←巨魔劍、乾坤弓←淬毒弓、火龍鏢←迷魂彈、
// 烈焰陣、九曲黃河陣←五行八卦陣、天絕陣←轟雷術）；捆仙繩用水滸連環馬陣的鎖鏈圖；鬼牌畫成封神榜大旗
window.registerCardTheme('fengshen', { fig: FIG, text: TEXT, art: { ogre: () => window.cardBanner(['封', '神', '榜']) }, alias: { SK: 'shuihu:SK' } });
})();
