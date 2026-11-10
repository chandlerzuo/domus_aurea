'use strict';
// 西遊記主題：人物特徵、介紹文與特別卡圖（於 cards.js、theme-shuihu-art.js 之後載入）
(() => {

/* ---- 人物特徵（鍵同 cards.js 之 FIG） ---- */
const FIG = {
  // 主帥
  SA: { body: 'robe', hair: ['bald'], cloth: ['#c0392b', '#f1c40f'], weapon: 'monkstaff', halo: 1, brow: 'kind', mouth: 'smile' },                                       // 唐三藏：袈裟錫杖
  HA: { body: 'armor', animal: 'monkey', face: '#b5743a', hat: ['band', '#f1c40f'], cloth: ['#f1c40f', '#c0392b'], weapon: 'staff', cloud: 1, brow: 'angry', mouth: 'grin' },              // 孫悟空：金箍、筋斗雲
  DA: { body: 'robe', fat: 1, animal: 'pig', face: '#f8c6d2', hat: ['cap', '#1b1b1b', '#f1c40f'], cloth: ['#2c3e50', '#f1c40f'], weapon: 'fork', eyes: 'narrow', mouth: 'laugh' },     // 豬八戒：九齒釘耙
  CA: { body: 'armor', fat: 1, face: '#7d5637', hat: ['horn', '#1b1b1b', '#f5f0e1'], cloth: ['#1b1b1b', '#f1c40f'], beard: ['full', '#111111'], weapon: 'club', brow: 'angry', mouth: 'frown' }, // 牛魔王
  // 2 點：身懷異術者
  S2: { body: 'robe', old: 1, hat: ['cap', '#6d4c2f', '#f1c40f'], cloth: ['#a1763f', '#f5f0e1'], beard: ['long', '#e8e8e8'], weapon: 'staff', stones: 1, brow: 'kind', mouth: 'smile' }, // 土地公
  H2: { body: 'robe', old: 1, hair: ['topknot', '#e8e8e8'], cloth: ['#e8e2d0', '#c0392b'], beard: ['long', '#e8e8e8'], weapon: 'fan', cloud: 1, brow: 'kind', mouth: 'laugh' }, // 赤腳大仙
  D2: { body: 'armor', face: '#5d8aa8', hat: ['helm', '#2c3e50', '#f1c40f'], cloth: ['#2c3e50', '#f1c40f'], weapon: 'spear', mark: ['face', '#f1c40f'], eyes: 'narrow' }, // 千里眼
  C2: { body: 'armor', face: '#a9cce3', hat: ['helm', '#16a085', '#f1c40f'], cloth: ['#16a085', '#f1c40f'], weapon: 'fork', charm: 1, mouth: 'open' },                    // 順風耳
  // ♠ 佛門與取經
  S3: { body: 'armor', hat: ['helm', '#ecf0f1', '#f1c40f'], cloth: ['#ecf0f1', '#5dade2'], weapon: 'spear', wave: 1, brow: 'kind' },                                       // 白龍馬
  S4: { body: 'robe', face: '#a0785a', hair: ['wild', '#c0392b'], cloth: ['#5d6d7e', '#f1c40f'], beard: ['full', '#c0392b'], weapon: 'monkstaff', brow: 'thick' },       // 沙悟淨：降妖寶杖
  S5: { body: 'robe', old: 1, hat: ['daoist', '#1f3f8f', '#f1c40f'], cloth: ['#f5f0e1', '#1f3f8f'], beard: ['long', '#e8e8e8'], weapon: 'brush', halo: 1, brow: 'kind' }, // 菩提祖師
  S6: { body: 'armor', fat: 1, face: '#3b2f2a', hat: ['bear', '#1b1b1b', '#f1c40f'], cloth: ['#1b1b1b', '#c0392b'], weapon: 'spear', brow: 'angry', mouth: 'open' },     // 黑熊精
  S7: { body: 'lady', hair: ['bun', '#1b1b1b'], cloth: ['#f5f5f5', '#5dade2'], halo: 1, cloud: 1, brow: 'kind', mouth: 'smile' },                                         // 觀音菩薩
  S8: { body: 'robe', hair: ['bun', '#1b1b1b'], cloth: ['#f1c40f', '#2b5fc1'], weapon: 'jian', halo: 1, brow: 'kind' },                                                   // 文殊菩薩：智慧劍
  S9: { body: 'robe', hair: ['bun', '#1b1b1b'], cloth: ['#ecf0f1', '#e67e22'], weapon: 'staff', halo: 1, brow: 'kind', mouth: 'smile' },                                 // 普賢菩薩
  S10: { body: 'robe', fat: 1, hair: ['bald'], cloth: ['#f39c12', '#c0392b'], halo: 1, fold: 1, eyes: 'closed', mouth: 'laugh' },                                        // 彌勒佛
  SJ: { body: 'robe', hair: ['bald'], face: '#f5c26b', cloth: ['#f1c40f', '#c0392b'], halo: 1, cloud: 1, fold: 1, eyes: 'closed', mouth: 'smile' },                       // 如來佛祖
  // ♥ 天庭
  H3: { body: 'lady', hair: ['buns', '#1b1b1b'], cloth: ['#f8c8dc', '#f5f0e1'], cloud: 1, brow: 'kind', mouth: 'smile' },                                                 // 嫦娥
  H4: { body: 'armor', fat: 1, face: '#c0392b', hat: ['helm', '#8e44ad', '#f1c40f'], cloth: ['#8e44ad', '#f1c40f'], beard: ['full', '#1b1b1b'], weapon: 'axes', brow: 'angry', mouth: 'open' }, // 巨靈神：宣花板斧
  H5: { body: 'robe', old: 1, hat: ['daoist', '#f1c40f', '#8b1a1a'], cloth: ['#ecf0f1', '#f1c40f'], beard: ['long', '#ffffff'], weapon: 'fan', cloud: 1, brow: 'kind' },  // 太上老君
  H6: { body: 'armor', hat: ['crown', '#8e44ad', '#f2c200'], cloth: ['#8e44ad', '#f1c40f'], beard: ['long', '#1b1b1b'], weapon: 'pagoda', brow: 'thick' },               // 托塔天王
  H7: { body: 'robe', old: 1, hat: ['daoist', '#ecf0f1', '#f1c40f'], cloth: ['#ecf0f1', '#5dade2'], beard: ['long', '#ffffff'], weapon: 'staff', brow: 'kind', mouth: 'smile' }, // 太白金星
  H8: { body: 'armor', face: '#5dade2', hair: ['wild', '#1b1b1b'], cloth: ['#2b5fc1', '#f1c40f'], weapon: 'mace', charm: 1, brow: 'angry', mouth: 'open' },               // 雷公
  H9: { body: 'armor', hair: ['buns', '#1b1b1b'], cloth: ['#e74c3c', '#f1c40f'], weapon: 'spear', cloud: 1, brow: 'angry', mouth: 'grin' },                               // 哪吒
  H10: { body: 'armor', fat: 1, hat: ['crown', '#2c3e50', '#f2c200'], cloth: ['#2c3e50', '#27ae60'], beard: ['full', '#1b1b1b'], weapon: 'jian', brow: 'angry' },        // 增長天王
  HJ: { body: 'armor', hat: ['helm', '#dfe6e9', '#f1c40f'], cloth: ['#ecf0f1', '#2b5fc1'], weapon: 'sanjian', mark: ['face', '#c0392b'], cape: '#c0392b', brow: 'thick' }, // 二郎神
  // ♦ 龍宮、地府與山中妖王
  D3: { body: 'robe', fat: 1, face: '#5d4037', hat: ['crown', '#1b1b1b', '#f2c200'], cloth: ['#1b1b1b', '#c0392b'], beard: ['full', '#1b1b1b'], weapon: 'brush', brow: 'angry', mouth: 'frown' }, // 閻羅王：生死簿
  D4: { body: 'robe', hat: ['crown', '#2980b9', '#f2c200'], cloth: ['#2980b9', '#f1c40f'], beard: ['long', '#f1c40f'], fold: 1, wave: 1, brow: 'thick' },                 // 東海龍王
  D5: { body: 'robe', hat: ['daoist', '#5d4037', '#f1c40f'], cloth: ['#f5e6c8', '#5d4037'], beard: ['long', '#1b1b1b'], weapon: 'jian', cloud: 1, brow: 'kind' },          // 鎮元大仙
  D6: { body: 'armor', face: '#7cb342', hat: ['helm', '#f1c40f', '#c0392b'], cloth: ['#f1c40f', '#8b1a1a'], beard: ['full', '#1b1b1b'], weapon: 'blade', brow: 'angry', mouth: 'open' }, // 黃袍怪
  D7: { body: 'robe', hair: ['bald'], cloth: ['#8b1a1a', '#f1c40f'], weapon: 'monkstaff', halo: 1, brow: 'kind' },                                                        // 地藏王菩薩
  D8: { body: 'armor', face: '#8e44ad', hat: ['feather', '#5b2c6f', '#f1c40f'], cloth: ['#5b2c6f', '#f1c40f'], weapon: 'halberd', brow: 'angry', mouth: 'open' },         // 九頭蟲
  D9: { body: 'armor', fat: 1, face: '#7d5637', hair: ['wild', '#27ae60'], cloth: ['#27ae60', '#f1c40f'], weapon: 'blade', brow: 'angry', mouth: 'open' },              // 獅駝王
  D10: { body: 'armor', fat: 1, face: '#5d6d7e', hat: ['horn', '#2c3e50', '#ecf0f1'], cloth: ['#2c3e50', '#5dade2'], weapon: 'spear', brow: 'angry' },                   // 青牛精
  DJ: { body: 'armor', animal: 'monkey', face: '#7f6a4f', hat: ['band', '#7f8c8d'], cloth: ['#7f8c8d', '#c0392b'], weapon: 'staff', brow: 'angry', mouth: 'grin' },                        // 六耳獼猴
  // ♣ 妖魔
  C3: { body: 'lady', hat: ['mouse', '#ffffff', '#f8c8dc'], cloth: ['#f8c8dc', '#ffffff'], mouth: 'smile', brow: 'kind' },                                                // 玉兔精
  C4: { body: 'lady', hair: ['bun', '#1b1b1b'], cloth: ['#5b2c6f', '#c39bd3'], eyes: 'wink', mouth: 'smile' },                                                            // 蜘蛛精
  C5: { body: 'lady', face: '#f2f2f2', hair: ['ponytail', '#ecf0f1'], cloth: ['#ecf0f1', '#7f8c8d'], eyes: 'narrow' },                                                    // 白骨精
  C6: { body: 'armor', face: '#d4ac0d', hair: ['wild', '#b7950b'], cloth: ['#b7950b', '#784212'], weapon: 'fork', charm: 1, brow: 'angry', mouth: 'open' },              // 黃風怪
  C7: { body: 'lady', hair: ['buns', '#1b1b1b'], cloth: ['#c0392b', '#f1c40f'], charm: 1, brow: 'angry' },                                                                // 鐵扇公主
  C8: { body: 'armor', hat: ['horn', '#f1c40f', '#ffffff'], cloth: ['#f1c40f', '#8b4513'], beard: ['full', '#1b1b1b'], weapon: 'jian', brow: 'angry', mouth: 'grin' },   // 金角大王
  C9: { body: 'armor', hat: ['horn', '#bdc3c7', '#ffffff'], cloth: ['#bdc3c7', '#2c3e50'], beard: ['full', '#1b1b1b'], weapon: 'jian', brow: 'angry', mouth: 'grin' },   // 銀角大王
  C10: { body: 'robe', face: '#f5b7b1', hair: ['buns', '#1b1b1b'], cloth: ['#e74c3c', '#f1c40f'], weapon: 'spear', charm: 1, bare: 1, brow: 'angry', mouth: 'grin' },    // 紅孩兒：火尖槍、三昧真火
  CJ: { body: 'armor', face: '#f0b27a', hat: ['feather', '#f1c40f', '#c0392b'], cloth: ['#f1c40f', '#c0392b'], weapon: 'halberd', cape: '#f39c12', brow: 'angry', eyes: 'narrow' }, // 金翅大鵬
};

/* ---- 介紹文 ---- */
const TEXT = {
  SA: '大唐高僧，奉唐太宗之命前往西天取經，收悟空、八戒、悟淨為徒。',
  HA: '花果山石猴，自封〔齊天大聖〕。持如意金箍棒，會七十二變，一個筋斗十萬八千里。',
  DA: '原為天蓬元帥，因醉戲嫦娥被貶下凡，誤投豬胎。持九齒釘耙，好吃懶做。',
  CA: '平天大聖，孫悟空結義兄長，鐵扇公主之夫，持混鐵棍，力大無窮。',
  S2: '一方土地神，熟知當地山川妖怪底細，常為取經人指點迷津。',
  H2: '天庭散仙，赤足行走，被悟空騙往通明殿，誤了蟠桃大會。',
  D2: '天庭神將，目運兩道金光，能看清千里之外。',
  C2: '天庭神將，耳聽八方，千里之外的聲音也聽得一清二楚。',
  S3: '西海龍王三太子，因縱火燒毀明珠被貶，化為白馬馱唐僧西行。',
  S4: '原為捲簾大將，被貶流沙河為妖，皈依後持降妖寶杖保唐僧取經。',
  S5: '靈台方寸山斜月三星洞主，孫悟空之師，傳授七十二變與筋斗雲。',
  S6: '黑風山妖王，盜走唐僧袈裟，後被觀音收為落伽山守山大神。',
  S7: '南海落伽山大慈大悲觀世音菩薩，賜悟空緊箍兒，處處救取經人於危難。',
  S8: '四大菩薩之一，騎青毛獅子，持智慧劍。',
  S9: '四大菩薩之一，騎六牙白象，以大行願著稱。',
  S10: '未來佛，袒胸露腹，笑口常開，持人種袋收服妖魔。',
  SJ: '西天靈山大雷音寺佛祖，以五指山壓住大鬧天宮的孫悟空。',
  H3: '月宮仙子，與玉兔相伴，容貌絕美。',
  H4: '托塔天王麾下先鋒，力大無窮，持宣花板斧，曾與悟空交戰。',
  H5: '兜率宮道祖，以八卦爐煉丹，金剛琢能套取兵器。',
  H6: '天庭降魔大元帥，掌玲瓏寶塔，哪吒之父，率天兵圍剿花果山。',
  H7: '天庭老神仙，兩度奉旨招安孫悟空，常為取經人通風報信。',
  H8: '天庭司雷之神，手持雷錘，與電母同掌雷電。',
  H9: '托塔天王三太子，三頭六臂，腳踏風火輪，持火尖槍。',
  H10: '四大天王之一，鎮守南方，持寶劍守護天門。',
  HJ: '玉帝外甥，額生天眼，會七十二變，持三尖兩刃刀，曾擒住孫悟空。',
  D3: '陰司冥府之主，掌生死簿，曾被悟空勾去花果山猴類的名字。',
  D4: '東海龍王敖廣，悟空在其龍宮中取得定海神針，即如意金箍棒。',
  D5: '萬壽山五莊觀觀主，地仙之祖，以袖裡乾坤困住唐僧師徒。',
  D6: '碗子山波月洞妖王，本為天上奎木狼星，下凡化為黃袍郎君。',
  D7: '幽冥教主，坐騎諦聽能辨真假悟空。',
  D8: '碧波潭萬聖龍王之婿，九頭九口，盜走祭賽國佛寶舍利。',
  D9: '獅駝嶺三魔之首，青毛獅子精，張口能吞十萬天兵。',
  D10: '金兜山獨角兕大王，本為太上老君坐騎，以金剛琢套走眾神兵器。',
  DJ: '與孫悟空一模一樣的獼猴，善聆音，能察理，假冒悟空難辨真假。',
  C3: '月宮搗藥玉兔，私下凡間假冒天竺國公主，欲招唐僧為駙馬。',
  C4: '盤絲洞七位女妖，肚臍吐絲結網，困住唐僧。',
  C5: '白虎嶺屍魔，三次變化欺騙唐僧，終被悟空打死。',
  C6: '黃風嶺妖王，吹起三昧神風，飛沙走石，吹得悟空睜不開眼。',
  C7: '翠雲山芭蕉洞主，牛魔王之妻，持芭蕉扇，一扇能熄滅火焰山。',
  C8: '平頂山蓮花洞大王，本為太上老君看金爐的童子，持紫金紅葫蘆。',
  C9: '金角大王之弟，持羊脂玉淨瓶與七星寶劍，喚人名字即可收入寶中。',
  C10: '牛魔王之子，號聖嬰大王，口吐三昧真火，持火尖槍。',
  CJ: '獅駝國大鵬金翅鵰，振翅九萬里，兩翅一搧便追上悟空的筋斗雲。',
  X1: '孫悟空大鬧天宮，十萬天兵天將也擋不住，所向披靡。',
  X2: '孫悟空大鬧天宮，十萬天兵天將也擋不住，所向披靡。',
};

// 武器、陣式沿用三國版的圖（三昧真火←火鏞炮、七星寶劍←巨魔劍、倒馬毒樁←淬毒弓、八卦爐←烈焰陣、
// 天羅地網←五行八卦陣、緊箍咒←轟雷術）；幌金繩、紫金紅葫蘆用水滸的鎖鏈圖與葫蘆圖；鬼牌畫成大鬧天宮大旗
window.registerCardTheme('xiyou', { fig: FIG, text: TEXT, art: { ogre: () => window.cardBanner(['大', '鬧', '天', '宮']) }, alias: { SK: 'shuihu:SK', CQ: 'shuihu:CQ' } });
})();
