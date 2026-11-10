'use strict';
// 水滸傳主題：人物特徵、介紹文與特別卡圖（於 cards.js 之後載入）
(() => {

/* ---- 人物特徵（鍵同 cards.js 之 FIG；未列出者沿用三國版） ---- */
const FIG = {
  // 宋江：黑三郎，面黑身短，官帽官袍，手執文筆
  SA: { body: 'robe', face: '#c98f62', hat: ['cap', '#1f2d5a', '#f2c200'], cloth: ['#2f3e73', '#f2c200'], beard: ['goatee', '#1b1b1b'], weapon: 'brush', brow: 'kind', mouth: 'smile' },
  // 盧俊義：玉麒麟，身長貌美，白玉細甲，長槍
  HA: { body: 'armor', hat: ['helm', '#f3efe0', '#f1c40f'], cloth: ['#f5f0e1', '#2b5fc1'], beard: ['goatee', '#1b1b1b'], weapon: 'spear', cape: '#dceaff', brow: 'kind', mouth: 'smile' },
  // 晁蓋：托塔天王，魁偉保正，掌托寶塔
  DA: { body: 'armor', fat: 1, hat: ['band', '#8b1a1a'], cloth: ['#8d4a16', '#f1c40f'], beard: ['full', '#2b1a10'], weapon: 'pagoda', brow: 'thick', mouth: 'open' },
  // 方臘：僭稱聖公，龍袍冕冠，倨傲
  CA: { body: 'robe', fat: 1, hat: ['crown', '#311b4a', '#f2c200'], cloth: ['#f1c40f', '#8e2b20'], beard: ['full', '#1b1b1b'], fold: 1, brow: 'angry', mouth: 'frown' },
  // 高廉：高唐州知府，官帽官袍，仗劍作法，飛沙走石
  S2: { body: 'robe', hat: ['cap', '#1f2d5a', '#f2c200'], cloth: ['#2b3a67', '#c0392b'], beard: ['mustache', '#1b1b1b'], weapon: 'jian', charm: 1, brow: 'angry', mouth: 'frown' },
  // 公孫勝：入雲龍，道冠道袍，松紋古定劍，腳踏祥雲
  H2: { body: 'robe', hat: ['daoist', '#2b5fc1', '#f1c40f'], cloth: ['#2e5fa3', '#f5f0e1'], beard: ['long', '#2b2b2b'], weapon: 'jian', cloud: 1, brow: 'kind' },
  // 喬道清：幻魔君，紫袍道冠，持杖，頭後光輪
  D2: { body: 'robe', hat: ['daoist', '#5b2c6f', '#f1c40f'], cloth: ['#8e44ad', '#f5f0e1'], beard: ['long', '#2b2b2b'], weapon: 'staff', halo: 1, brow: 'kind' },
  // 包道乙：方臘國師，老道，飛劍玄天混元劍
  C2: { body: 'robe', old: 1, hat: ['daoist', '#3b0f0f', '#f2c200'], cloth: ['#7b1f1f', '#f1c40f'], beard: ['long', '#9e9e9e'], weapon: 'jian', charm: 1, brow: 'angry' },
  // 關勝：大刀關勝，面如重棗，綠袍綠盔，青龍偃月刀
  SJ: { body: 'armor', face: '#d8433a', hat: ['helm', '#27ae60', '#f1c40f'], cloth: ['#27ae60', '#f1c40f'], beard: ['long', '#111111'], weapon: 'guandao', brow: 'thick', eyes: 'narrow' },
  // 林沖：豹子頭，環眼怒目，豹紋披風，丈八蛇矛
  HJ: { body: 'armor', hat: ['helm', '#3a4152', '#cfd8dc'], cloth: ['#424d66', '#c0392b'], beard: ['full', '#1b1b1b'], weapon: 'snake', cape: '#d9a93a', leo: 1, brow: 'angry', mouth: 'frown' },
  // 魯智深：花和尚，肥胖光頭，赤膊花繡，水磨禪杖
  DJ: { body: 'robe', fat: 1, hair: ['bald'], cloth: ['#5d4435', '#c9a227'], weapon: 'monkstaff', bare: 1, tattoo: 1, hip: 0, brow: 'thick', mouth: 'open' },
  // 武松：行者，鐵箍頭巾，雙戒刀
  CJ: { body: 'robe', hat: ['band', '#aab7c0'], cloth: ['#4a5a6a', '#8b1a1a'], weapon: 'twindao', hip: 0, brow: 'angry', mouth: 'frown' },
  // 呼延灼：雙鞭，黑甲黑盔，兩條水磨鋼鞭
  S10: { body: 'armor', hat: ['helm', '#2f3640', '#90a4ae'], cloth: ['#2f3640', '#5d6d7e'], beard: ['full', '#111111'], weapon: 'whips', brow: 'angry', mouth: 'frown' },
  // 秦明：霹靂火，黑面暴躁，狼牙棒
  H10: { body: 'armor', face: '#b86048', hat: ['helm', '#c0392b', '#f1c40f'], cloth: ['#c0392b', '#2c3e50'], beard: ['full', '#111111'], weapon: 'club', brow: 'angry', mouth: 'open' },
  // 董平：雙槍將，年少俊秀，雙槍並舉
  D10: { body: 'armor', hat: ['helm', '#2b5fc1', '#f1c40f'], cloth: ['#2b5fc1', '#f1c40f'], weapon: 'twinspear', mouth: 'smile', brow: 'kind' },
  // 石寶：方臘上將，流星錘並佩劈風刀
  C10: { body: 'armor', hat: ['helm', '#5b2c6f', '#f1c40f'], cloth: ['#5b2c6f', '#f1c40f'], beard: ['mustache', '#1b1b1b'], weapon: 'mace', sidearm: 1, brow: 'angry' },
  // 張清：沒羽箭，輕甲，飛石打將
  S9: { body: 'armor', hat: ['band', '#2b5fc1'], cloth: ['#2b5fc1', '#e8e2d0'], weapon: 'sling', stones: 1, mouth: 'grin', brow: 'kind' },
  // 花榮：小李廣，神箭手
  H9: { body: 'armor', hat: ['helm', '#e74c3c', '#f1c40f'], cloth: ['#e74c3c', '#f5f0e1'], weapon: 'bow', mouth: 'smile', brow: 'kind' },
  // 鄧元覺：寶光如來，肥大光頭僧，渾鐵禪杖
  D9: { body: 'robe', fat: 1, hair: ['bald'], face: '#eab98e', cloth: ['#b5651d', '#f1c40f'], weapon: 'monkstaff', halo: 1, hip: 0, brow: 'angry', mouth: 'open' },
  // 方杰：少年驍將，方天戟
  C9: { body: 'armor', hat: ['helm', '#8e44ad', '#f1c40f'], cloth: ['#8e44ad', '#f1c40f'], weapon: 'halberd', brow: 'angry', mouth: 'grin' },
  // 楊志：青面獸，面有青色胎記，寶刀
  S8: { body: 'armor', hat: ['round', '#3b4a5a', '#f1c40f'], cloth: ['#46606b', '#f1c40f'], beard: ['mustache', '#1b1b1b'], weapon: 'dao', mark: ['face', '#4e9a86'], brow: 'angry' },
  // 李逵：黑旋風，膚黑亂髮，赤膊雙板斧
  H8: { body: 'robe', face: '#7d5637', hair: ['wild', '#141414'], beard: ['full', '#111111'], cloth: ['#3b2f2a', '#8b1a1a'], weapon: 'axes', bare: 1, brow: 'angry', mouth: 'open' },
  // 索超：急先鋒，金釘棗陽槊
  D8: { body: 'armor', hat: ['horn', '#c0392b', '#ffffff'], cloth: ['#c0392b', '#2c3e50'], weapon: 'shuo', brow: 'angry', mouth: 'open' },
  // 厲天閏：方臘宿將，長槍
  C8: { body: 'armor', hat: ['helm', '#2c3e50', '#95a5a6'], cloth: ['#34495e', '#c0392b'], beard: ['full', '#2b2b2b'], weapon: 'spear', brow: 'angry', mouth: 'frown' },
  // 吳用：智多星，儒巾文袍，羽扇
  S7: { body: 'robe', hat: ['scholar', '#2c3e50', '#f1c40f'], cloth: ['#1f3f8f', '#f5f0e1'], beard: ['goatee', '#1b1b1b'], weapon: 'fan', brow: 'kind', mouth: 'smile' },
  // 朱武：神機軍師，高冠綠袍，佩劍布陣
  H7: { body: 'robe', hat: ['tall', '#1e5631', '#f1c40f'], cloth: ['#2e7d32', '#e8d9a8'], beard: ['mustache', '#1b1b1b'], weapon: 'jian', brow: 'thick', eyes: 'narrow' },
  // 柴進：小旋風，皇族後裔，錦衣無兵
  D7: { body: 'robe', hat: ['cap', '#8e44ad', '#f1c40f'], cloth: ['#c39bd3', '#f5f0e1'], beard: ['goatee', '#1b1b1b'], fold: 1, brow: 'kind', mouth: 'smile' },
  // 王進：禁軍教頭，老成嚴謹，長槍
  C7: { body: 'armor', hat: ['band', '#6d4c2f'], cloth: ['#6d4c2f', '#2c3e50'], beard: ['long', '#e8e8e8'], old: 1, weapon: 'spear', brow: 'thick' },
  // 史進：九紋龍，身刺青龍，三尖兩刃刀
  S6: { body: 'robe', hair: ['topknot', '#1b1b1b'], cloth: ['#1f6f8b', '#f1c40f'], weapon: 'sanjian', bare: 1, tattoo: 1, brow: 'thick', mouth: 'grin' },
  // 朱仝：美髯公，長鬚及胸，朴刀
  H6: { body: 'armor', hat: ['helm', '#1f3f8f', '#f1c40f'], cloth: ['#1f3f8f', '#f1c40f'], beard: ['long', '#1b1b1b'], weapon: 'blade', brow: 'kind', mouth: 'smile' },
  // 楊雄：病關索，面色蠟黃，劊子手，朴刀
  D6: { body: 'armor', face: '#eee2c8', hat: ['band', '#2c3e50'], cloth: ['#2c3e50', '#95a5a6'], beard: ['mustache', '#1b1b1b'], weapon: 'blade', brow: 'thick', mouth: 'frown' },
  // 王寅：南離大將軍，長槍
  C6: { body: 'armor', hat: ['horn', '#16a085', '#f1c40f'], cloth: ['#148f77', '#f1c40f'], beard: ['mustache', '#1b1b1b'], weapon: 'spear', brow: 'angry' },
  // 戴宗：神行太保，輕裝，腿綁甲馬
  S5: { body: 'robe', hat: ['band', '#e67e22'], cloth: ['#f0e6d2', '#e67e22'], charm: 1, mouth: 'grin', brow: 'kind' },
  // 燕青：浪子，俊秀刺青，川弩
  H5: { body: 'robe', hat: ['cap', '#2980b9', '#f1c40f'], cloth: ['#2e86de', '#f1c40f'], weapon: 'crossbow', bare: 1, tattoo: 1, brow: 'kind', mouth: 'smile' },
  // 李俊：混江龍，水軍頭領，赤臂持篙
  D5: { body: 'robe', face: '#dcae82', hat: ['band', '#2e86de'], cloth: ['#2e86de', '#f5f0e1'], weapon: 'oar', bare: 1, wave: 1, hip: 0, brow: 'thick', mouth: 'grin' },
  // 童貫：樞密使，肥白文弱
  C5: { body: 'robe', fat: 1, hat: ['tall', '#2c3e50', '#f1c40f'], cloth: ['#6c3483', '#f1c40f'], beard: ['mustache', '#2b2b2b'], old: 1, fold: 1, brow: 'angry', mouth: 'frown' },
  // 聞達：大名府都監，長刀
  S4: { body: 'armor', hat: ['helm', '#7f8c8d', '#f1c40f'], cloth: ['#5d6d7e', '#f1c40f'], beard: ['full', '#2b2b2b'], weapon: 'blade', brow: 'thick' },
  // 徐寧：金槍手，雁翎甲，鉤鎌槍
  H4: { body: 'armor', hat: ['helm', '#f1c40f', '#ffffff'], cloth: ['#d4ac0d', '#2b5fc1'], weapon: 'hookspear', brow: 'kind', mouth: 'smile' },
  // 劉唐：赤髮鬼，紅髮，鬢有硃砂記，朴刀
  D4: { body: 'robe', hair: ['wild', '#c0392b'], beard: ['mustache', '#8b2500'], cloth: ['#7b241c', '#f1c40f'], weapon: 'blade', mark: ['temple', '#c0392b'], brow: 'angry', mouth: 'open' },
  // 龐萬春：小養由基，毒箭神射
  C4: { body: 'armor', hat: ['band', '#1e8449'], cloth: ['#1e8449', '#f1c40f'], weapon: 'bow', eyes: 'narrow', brow: 'angry' },
  // 李成：大名府都監，佩劍
  S3: { body: 'armor', hat: ['round', '#6d4c2f', '#f1c40f'], cloth: ['#8a5a1a', '#f1c40f'], beard: ['goatee', '#2b2b2b'], weapon: 'jian', brow: 'thick' },
  // 解珍：兩頭蛇，獵戶，鋼叉
  H3: { body: 'robe', hat: ['band', '#8d6e63'], cloth: ['#6e4b2a', '#a0522d'], beard: ['mustache', '#2b1a10'], weapon: 'fork', cape: '#9c6b4a', brow: 'thick', mouth: 'open' },
  // 阮小二：立地太歲，漁人赤膊，魚叉
  D3: { body: 'robe', face: '#c88f5e', hat: ['band', '#27ae60'], cloth: ['#1e8449', '#f5f0e1'], beard: ['mustache', '#1b1b1b'], weapon: 'fork', bare: 1, wave: 1, hip: 0, brow: 'angry', mouth: 'open' },
  // 高俅：太尉，蹴鞠倖進，奸相
  C3: { body: 'robe', hat: ['tall', '#8b1a1a', '#f1c40f'], cloth: ['#b03a2e', '#f1c40f'], beard: ['mustache', '#1b1b1b'], weapon: 'ball', eyes: 'wink', mouth: 'grin', brow: 'angry' },
};

/* ---- 介紹文 ---- */
const TEXT = {
  S2: '高唐州知府，高俅之堂弟。善使妖法，能飛沙走石、召喚神兵，曾大敗梁山人馬。',
  H2: '綽號〔入雲龍〕，道號一清。羅真人門徒，能呼風喚雨、駕霧騰雲，善五雷天罡正法。',
  D2: '田虎麾下護國靈感真人，人稱〔幻魔君〕。精通幻術，後拜羅真人為師。',
  C2: '方臘國師，人稱〔靈應天師〕。善使妖法，飛劍〔玄天混元劍〕能取人首級。',
  SA: '綽號〔黑三郎〕，面黑身短。鄆城押司出身，仗義疏財，為梁山泊之主，豎〔替天行道〕杏黃旗。',
  HA: '北京大名府員外，綽號〔玉麒麟〕。相貌堂堂，棍棒天下無對，為梁山馬軍副總兵。',
  DA: '綽號〔托塔天王〕，東溪村保正。能托石塔，劫取生辰綱後上山，為梁山第一任寨主。',
  CA: '江南反賊之首，僭稱〔聖公〕，建元永樂，據八州二十五縣，為梁山征討之大敵。',
  SJ: '關羽之後，綽號〔大刀關勝〕。面如重棗，鬚長過腹，一口青龍偃月刀威風凜凜。',
  HJ: '綽號〔豹子頭〕，環眼虎鬚。原東京八十萬禁軍教頭，使丈八蛇矛，風雪山神廟後投梁山。',
  DJ: '綽號〔花和尚〕，滿背花繡。拳打鎮關西、倒拔垂楊柳，一條水磨禪杖重六十二斤。',
  CJ: '綽號〔行者〕。景陽岡上赤手打死猛虎，雙戒刀快似疾風，血濺鴛鴦樓名動天下。',
  S10: '綽號〔雙鞭〕，開國功臣呼延讚之後。鐵甲黑馬，兩條水磨鋼鞭，曾以連環馬大破梁山。',
  H10: '綽號〔霹靂火〕，青州兵馬總管。性如烈火，聲若雷霆，一條狼牙棒無人敢近。',
  D10: '綽號〔雙槍將〕，東平府兵馬都監。眉清目秀，雙槍並舉，軍中稱〔風流萬戶侯〕。',
  C10: '方臘軍中第一員大將。劈風刀鋒利無比，流星錘百發百中，連傷梁山數員頭領。',
  S9: '綽號〔沒羽箭〕，虎騎出身。袋中石子飛打百發百中，曾連打梁山一十五員頭領。',
  H9: '綽號〔小李廣〕，清風寨知寨。梁山第一神箭手，姿容俊秀，箭不虛發。',
  D9: '方臘國師，綽號〔寶光如來〕。肥壯光頭，渾鐵禪杖五十餘斤，與魯智深鬥得旗鼓相當。',
  C9: '方臘之姪孫，年少驍勇。一條方天戟橫衝直撞，為江南軍中後起之秀。',
  S8: '綽號〔青面獸〕，面有青色胎記。三代將門之後，押送生辰綱失陷黃泥岡而落草。',
  H8: '綽號〔黑旋風〕，膚黑如鐵，鬚髮亂蓬。赤膊使兩把板斧，忠於宋江勝過自家性命。',
  D8: '大名府正牌軍，綽號〔急先鋒〕。使一條金釘棗陽槊，臨陣爭先，與楊志鬥得難分勝負。',
  C8: '方臘之歙州守將，槍法老練。於獨松關連傷梁山數員頭領，為江南第一勁敵。',
  S7: '綽號〔智多星〕，道號加亮先生。羽扇輕搖計謀百出，智取生辰綱，為梁山軍師。',
  H7: '少華山寨主，人稱〔神機軍師〕。精通陣法、廣有謀略，後為梁山副軍師。',
  D7: '後周皇族之後，綽號〔小旋風〕。滄州大官人，持丹書鐵券，仗義疏財廣納天下好漢。',
  C7: '東京八十萬禁軍教頭，史進之師。棍棒精熟，因避高俅之害而出走延安。',
  S6: '綽號〔九紋龍〕，身上刺九條青龍。少華山首領，使三尖兩刃刀，年少氣盛。',
  H6: '綽號〔美髯公〕，鄆城馬兵都頭。身長八尺，鬍鬚美如關雲長，義氣過人屢放罪囚。',
  D6: '綽號〔病關索〕，薊州押獄兼行刑劊子。面色蠟黃卻武藝精熟，一條朴刀無人能擋。',
  C6: '方臘之南離大將軍，石匠出身。坐下寶馬〔轉山飛〕，槍法通神，威震歙州。',
  S5: '綽號〔神行太保〕，江州兩院押牢節級。腿綁甲馬神符，日行八百里，專遞梁山軍情。',
  H5: '綽號〔浪子〕，盧俊義心腹小乙哥。一身雪練似的花繡，相撲天下無敵，川弩百步穿楊。',
  D5: '綽號〔混江龍〕，揭陽嶺水軍頭領。精熟水性，能水底伏七日七夜，後為暹羅國之主。',
  C5: '當朝樞密使。統十萬大軍征剿梁山而全軍潰敗，弄權誤國之奸臣。',
  S4: '大名府兵馬都監，軍中號為〔天王〕。刀法純熟，久鎮北京，為梁山攻城時之勁敵。',
  H4: '綽號〔金槍手〕，金槍班教師。鉤鎌槍法與雁翎鎖子甲天下獨步，破連環馬之功臣。',
  D4: '綽號〔赤髮鬼〕，紅髮赤鬚，鬢邊一搭硃砂記。一條朴刀兇猛，報生辰綱消息之人。',
  C4: '方臘軍中神箭將，綽號〔小養由基〕。箭上淬毒，百步取人，曾射殺梁山數員頭領。',
  S3: '大名府兵馬都監，與聞達並稱兩員虎將。使一口好劍，久經戰陣，老於用兵。',
  H3: '綽號〔兩頭蛇〕，登州獵戶。一把鋼叉慣上山打虎，與弟解寶形影不離。',
  D3: '綽號〔立地太歲〕，石碣村漁人。赤膊搖船，水裡來去如龍，阮氏三雄之長。',
  C3: '當朝太尉。因踢得好蹴鞠而得寵倖進，陷害王進、林沖，為朝中奸佞之首。',
  SQ: '轟天雷凌振所造之火砲。風火砲、金輪砲皆出其手，發時聲如天雷，石破城摧。',
  HQ: '楊志家傳之祖上寶刀。吹毛可斷、殺人刀口不沾血，削銅剁鐵如切豆腐。',
  DQ: '箭鏃淬以毒藥之弩，中人立倒。龐萬春用之連傷數將，軍中聞之膽寒。',
  CQ: '江湖上的藥酒。和入酒中味不可辨，飲者頃刻昏倒，孟州道十字坡最是有名。',
  SK: '呼延灼之陣法。三十匹馬為一連，馬帶甲、人披鎧，鐵環相鎖齊頭並進，不破不散。',
  HK: '公孫勝之道法。遇火而反其風，將敵人烈焰盡數捲回，破高唐州神兵即用此法。',
  DK: '梁山泊之大陣。九隊為宮、八門應卦，中軍居中策應，童貫十萬大軍困死其中。',
  CK: '羅真人所授之道術。仗劍書符，召五雷天罡，風雷俱發，妖法邪術盡破。',
  X1: '梁山泊杏黃旗上四字，聚義替天行道。本卡使用時，可將敵軍將領、士兵、武器、陣勢卡及領地占為己有。',
  X2: '梁山泊杏黃旗上四字，聚義替天行道。本卡使用時，可將敵軍將領、士兵、武器、陣勢卡及領地占為己有。',
};

/* ---- 繪圖小工具（與 cards.js 同風格，獨立一份以免動到原檔） ---- */
const OL = '#2a1a10';
const st = (w = 2.4) => `stroke="${OL}" stroke-width="${w}" stroke-linejoin="round" stroke-linecap="round"`;
const shp = (d, fill, sh = 'cgSh', w) => `<path d="${d}" fill="${fill}" ${st(w)}/>` + (sh ? `<path d="${d}" fill="url(#${sh})"/>` : '');
const fl = (d, fill, op) => `<path d="${d}" fill="${fill}"${op != null ? ` fill-opacity="${op}"` : ''}/>`;
const elp = (cx, cy, rx, ry) => `M${cx - rx},${cy} a${rx},${ry} 0 1,0 ${2 * rx},0 a${rx},${ry} 0 1,0 ${-2 * rx},0z`;
const E = (cx, cy, rx, ry, fill, sh = 'cgSh', w) => shp(elp(cx, cy, rx, ry), fill, sh, w);
const EF = (cx, cy, rx, ry, fill, op) => fl(elp(cx, cy, rx, ry), fill, op);
const line = (x1, y1, x2, y2, c = OL, w = 2.4) => `<path d="M${x1},${y1} L${x2},${y2}" stroke="${c}" stroke-width="${w}" stroke-linecap="round" fill="none"/>`;
const curve = (d, c = OL, w = 2.4, op) => `<path d="${d}" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" fill="none"${op != null ? ` stroke-opacity="${op}"` : ''}/>`;
const mir = (svg, ax = 125) => `<g transform="matrix(-1,0,0,1,${2 * ax},0)">${svg}</g>`;
const both = (svg, ax = 125) => svg + mir(svg, ax);
const shaft = (x0, y0, x1, y1, wd = 6, col = '#8a5a2b', hi = '#c48a4f', rings = '#c9a227') => `<path d="M${x0},${y0} L${x1},${y1}" stroke="${OL}" stroke-width="${wd + 3}" stroke-linecap="round"/><path d="M${x0},${y0} L${x1},${y1}" stroke="${col}" stroke-width="${wd}" stroke-linecap="round"/><path d="M${x0 - wd / 4},${y0} L${x1 - wd / 4},${y1}" stroke="${hi}" stroke-width="${wd / 3}" stroke-linecap="round"/>`
  + (rings ? [0.2, 0.45, 0.7].map(t => `<path d="M${x0 + (x1 - x0) * t - wd / 2 - 1},${y0 + (y1 - y0) * t} h${wd + 2}" stroke="${OL}" stroke-width="4.2"/><path d="M${x0 + (x1 - x0) * t - wd / 2 - .5},${y0 + (y1 - y0) * t} h${wd + 1}" stroke="${rings}" stroke-width="2.6"/>`).join('') : '');
const tassel = (cx, cy, c, len = 26) => [-6, -3, 0, 3, 6].map(dx => curve(`M${cx + dx * .6},${cy} q${dx * 1.2},${len * .5} ${dx * .4},${len + Math.abs(dx) * -.6}`, c, 2.6)).join('')
  + E(cx, cy, 7, 4, 'url(#cgGold)', null, 1.4) + E(cx, cy - 4, 3, 3, c, null, 1.2);
const star4 = (cx, cy, r, c = '#fff') => fl(`M${cx},${cy - r} Q${cx + r * .18},${cy - r * .18} ${cx + r},${cy} Q${cx + r * .18},${cy + r * .18} ${cx},${cy + r} Q${cx - r * .18},${cy + r * .18} ${cx - r},${cy} Q${cx - r * .18},${cy - r * .18} ${cx},${cy - r}z`, c);
const txt = (x, y, s, size, fill, w = 1.6) => `<text x="${x}" y="${y}" font-size="${size}" font-weight="900" text-anchor="middle" fill="${fill}" stroke="${OL}" stroke-width="${w}" paint-order="stroke">${s}</text>`;

/* ---- 特別卡圖 ---- */

// 青鋼寶刀：楊志祖傳寶刀，柳葉刀身、金吞口、環首紅纓
const HQ = () => EF(125, 180, 112, 112, 'url(#cgAura)')
  + `<g transform="rotate(18 125 196)">`
  + shp('M114,244 C112,170 122,98 140,40 L154,58 C154,118 148,186 136,244z', 'url(#cgBlade)', null, 2.6)
  + fl('M114,244 C112,170 122,98 140,40 L154,58 C154,118 148,186 136,244z', '#3aa0a8', .2)
  + curve('M122,238 C122,172 130,112 142,58', '#8fa6b4', 1.8)
  + curve('M118,226 C118,166 126,114 137,64', '#ffffff', 1.6, .85)
  + shp('M140,72 l9,-10 l2,12z', '#ffffff', null, 0)
  + shp('M104,246 q21,-11 42,0 q-4,10 -9,12 q-12,-6 -24,0 q-5,-2 -9,-12z', 'url(#cgGold)', null, 2.2)
  + E(125, 250, 6, 4, '#8b1a1a', 'cgSh', 1.4)
  + shp('M115,256 h18 v44 h-18z', '#4e342e', null, 2) + Array.from({ length: 6 }, (_, k) => curve(`M115,${260 + k * 7} l18,5`, '#c9a227', 1.6)).join('')
  + `<circle cx="124" cy="310" r="11" fill="none" stroke="${OL}" stroke-width="4.4"/><circle cx="124" cy="310" r="11" fill="none" stroke="url(#cgGold)" stroke-width="2.8"/>`
  + curve('M132,318 q14,12 8,30 M138,316 q8,14 4,28', '#e53935', 3) + '</g>'
  + star4(72, 104, 11, '#fff59d') + star4(58, 86, 6, '#ffeb3b') + star4(196, 250, 9, '#fff59d') + star4(206, 148, 6, '#fff')
  + curve('M58, 150 q-8,-18 4,-30', '#7fe3ff', 3.4, .8);

// 毒藥弩：淬毒之川弩，綠毒滴落、藥瓶骷髏
const DQ = () => EF(125, 184, 104, 104, 'url(#cgPoison)')
  + `<g transform="rotate(-22 125 196)">`
  + shp('M34,186 h150 l-7,22 h-136 a9,9 0 0 1 -7,-22z', 'url(#cgWood)', 'cgShV', 2.4) + fl('M38,189 h142 l-5,16 h-130z', 'url(#cgGrain)')
  + curve('M170,128 q30,68 0,136', OL, 11) + curve('M170,128 q30,68 0,136', '#6d4c41', 7) + curve('M172,136 q24,60 0,120', '#a1887f', 2)
  + line(170, 128, 170, 264, '#eee', 1.8) + E(170, 128, 5, 5, 'url(#cgGold)', null, 1.4) + E(170, 264, 5, 5, 'url(#cgGold)', null, 1.4)
  + shp('M70,190 h104 l20,7 l-20,7 h-104z', '#a0682c', null, 1.8) + curve('M74,197 h98', '#d9a066', 1.4)
  + shp('M192,192 l26,5 l-26,5z', '#76ff03', 'cgSh', 1.8)
  + shp('M44,208 q6,22 -10,28 q-4,-14 -2,-28z', '#5d4037', null, 2) + shp('M28,180 h20 v10 h-20z', 'url(#cgMetal)', null, 1.6)
  + E(60, 184, 7, 7, 'url(#cgGold)', null, 1.6) + '</g>'
  + [[196, 150, 6], [186, 168, 4.6], [204, 174, 4], [176, 190, 3.4]].map(([x, y, r]) => shp(`M${x},${y - r * 2} q${r},${r * 1.6} ${r},${r * 2.6} a${r},${r} 0 1,1 ${-2 * r},0 q0,${-r} ${r},${-r * 2.6}z`, '#76ff03', 'cgSh', 1.2)).join('')
  + `<g transform="translate(66 282)">` + shp('M-14,-26 h28 v12 l10,20 q2,24 -24,24 q-26,0 -24,-24 l10,-20z', '#2e7d32', 'cgShV', 2.4)
  + fl('M-18,2 q18,-8 36,0 q2,18 -18,18 q-20,0 -18,-18z', '#76ff03') + shp('M-10,-34 h20 v10 h-20z', '#5d4037', null, 1.8)
  + EF(-8, 6, 5, 3, '#fff', .6) + '</g>'
  + `<g transform="translate(176 262) scale(.8)">` + E(0, 0, 20, 18, '#f5f5f5', 'cgSh', 2) + shp('M-10,14 h20 v10 h-20z', '#f5f5f5', null, 1.8)
  + E(-7, -2, 5.5, 6, '#111', null, 0) + E(7, -2, 5.5, 6, '#111', null, 0) + EF(-6, -2, 2, 2, '#76ff03') + EF(8, -2, 2, 2, '#76ff03')
  + fl('M0,4 l-3,6 h6z', '#111') + [-6, -2, 2, 6].map(x => line(x, 15, x, 23, '#555', 1)).join('') + '</g>'
  + curve('M96,286 q28,22 54,2', '#2e7d32', 3, .55);

// 蒙汗藥：下了藥的酒碗、葫蘆與藥包，綠霧氤氳
const CQ = () => EF(118, 186, 108, 110, 'url(#wmSmoke)')
  // 葫蘆
  + `<g transform="rotate(12 196 176)">` + E(196, 196, 30, 32, '#c8821f', 'cgSh', 2.4) + E(196, 152, 19, 20, '#d89a2c', 'cgSh', 2.2)
  + shp('M186,166 q10,8 20,0 q-2,10 -10,12 q-8,-2 -10,-12z', '#b06c14', null, 1.6)
  + shp('M190,124 h12 v12 h-12z', '#6d4c2f', null, 1.8) + curve('M186,138 q10,6 20,0', '#8b1a1a', 3)
  + EF(186, 186, 9, 12, '#fff', .3) + EF(190, 146, 5, 6, '#fff', .35) + '</g>'
  // 綠霧
  + [[94, 0], [118, 10], [142, 4]].map(([x, d]) => curve(`M${x},${242 - d} q-20,-28 6,-48 q24,-18 4,-44 q-18,-22 6,-40`, '#8fc34a', 5.6, .8)
    + curve(`M${x + 3},${240 - d} q-16,-26 7,-44 q21,-16 3,-40`, '#dcedc8', 2.4, .75)).join('')
  + EF(102, 118, 26, 20, 'url(#wmSmoke)') + EF(146, 96, 20, 16, 'url(#wmSmoke)') + EF(120, 76, 16, 13, 'url(#wmSmoke)')
  // 酒碗
  + EF(118, 316, 76, 11, 'url(#cgGround)')
  + shp('M50,244 q8,60 68,60 q60,0 68,-60z', '#f3ead3', 'cgShV', 2.6) + fl('M50,244 q8,60 68,60 q60,0 68,-60z', 'url(#cgBrocade)')
  + curve('M62,262 q56,22 112,0', '#2b5fc1', 2.6) + curve('M70,276 q48,18 96,0', '#2b5fc1', 1.6)
  + shp('M94,302 h48 v10 q-24,8 -48,0z', '#e3d7b8', 'cgShV', 2)
  + E(118, 244, 70, 18, '#f7f1e0', null, 2.6) + E(118, 245, 59, 13, 'url(#wmWine)', null, 1.8)
  + EF(98, 241, 16, 5, '#fff', .35) + EF(140, 248, 9, 3, '#dcedc8', .5)
  + [[92, 246, 7], [136, 250, 5], [116, 240, 4]].map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r}" fill="none" stroke="#dcedc8" stroke-width="1.6" stroke-opacity=".8"/>`).join('')
  // 藥包
  + `<g transform="rotate(-8 56 300)">` + shp('M28,286 l26,-12 l28,10 l-6,32 h-44z', '#f7efd8', 'cgShV', 2.4) + fl('M28,286 l26,-12 l28,10 l-6,32 h-44z', 'url(#cgGrain)')
  + curve('M30,290 q26,10 50,-4', '#c0392b', 2.4) + txt(55, 308, '藥', 20, '#8b1a1a', 1.2) + '</g>'
  + [[92, 320], [102, 326], [84, 328], [110, 318]].map(([x, y]) => E(x, y, 4, 3, '#ffffff', null, 1.2)).join('')
  + star4(166, 136, 7, '#dcedc8') + star4(74, 150, 5, '#dcedc8');

// 連環馬陣：披甲戰馬（正面特寫）以鐵環相鎖
const hhead = (cx, cy, sc, barb, trim) => {
  const head = 'M0,-70 C-26,-66 -34,-36 -30,2 C-26,38 -14,64 0,64 C14,64 26,38 30,2 C34,-36 26,-66 0,-70z';
  const mask = 'M0,-62 C-13,-60 -17,-34 -15,-4 C-13,22 -6,44 0,44 C6,44 13,22 15,-4 C17,-34 13,-60 0,-62z';
  const chest = 'M-40,56 q40,18 80,0 l18,72 q-58,22 -116,0z';
  const cheek = 'M-27,-22 L-41,-8 L-38,28 L-24,40z';
  return `<g transform="translate(${cx} ${cy}) scale(${sc})">`
    + shp(chest, barb, 'cgSh', 2.8) + fl(chest, 'url(#cgLam)')
    + shp('M-44,74 q44,20 88,0 l3,14 q-46,21 -94,0z', trim, 'cgShV', 2.2) + curve('M-40,82 q40,18 80,0', '#f1c40f', 2)
    + shp('M-24,-64 l-9,-36 l25,26z', '#5d4037', 'cgSh', 2.2) + shp('M24,-64 l9,-36 l-25,26z', '#5d4037', 'cgSh', 2.2)
    + fl('M-22,-68 l-5,-20 l13,14z', '#f6c7a8') + fl('M22,-68 l5,-20 l-13,14z', '#f6c7a8')
    + shp(head, '#6d4c37', 'cgSh', 2.8)
    + both(curve('M-18,-62 q-6,-14 -2,-24', '#3e2723', 3.4), 0)
    + shp(cheek, barb, 'cgSh', 2.2) + fl(cheek, 'url(#cgLam)') + mir(shp(cheek, barb, 'cgSh', 2.2) + fl(cheek, 'url(#cgLam)'), 0)
    + shp(mask, 'url(#cgGold)', 'cgSh', 2.4) + curve('M0,-54 v92', '#b07a16', 2)
    + [-30, -6, 18].map(y => curve(`M-13,${y} q13,5 26,0`, '#b07a16', 1.6)).join('')
    + shp('M0,-98 q14,22 10,38 q-10,6 -20,0 q-4,-16 10,-38z', '#c0392b', 'cgSh', 2.2) + fl('M0,-90 q7,16 5,26 q-5,3 -10,0 q-2,-10 5,-26z', '#ffeb3b')
    + E(-23, -14, 8, 9, '#ffffff', null, 2.2) + E(-23, -12, 4.4, 5, '#1b1b1b', null, 0) + EF(-21, -16, 1.8, 1.8, '#fff')
    + E(23, -14, 8, 9, '#ffffff', null, 2.2) + E(23, -12, 4.4, 5, '#1b1b1b', null, 0) + EF(25, -16, 1.8, 1.8, '#fff')
    + E(-8, 44, 4.4, 5.4, '#3e2723', null, 1.6) + E(8, 44, 4.4, 5.4, '#3e2723', null, 1.6)
    + curve('M-9,58 q9,6 18,0', '#3e2723', 2.4)
    + '</g>';
};
const chain = (p0, p1, p2, n, sc = 1) => Array.from({ length: n }, (_, k) => {
  const t = k / (n - 1), u = 1 - t;
  const x = (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]).toFixed(1), y = (u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]).toFixed(1);
  const a = k % 2, rx = (a ? 11 : 6.5) * sc, ry = (a ? 6.5 : 11) * sc;
  return `<ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" fill="none" stroke="${OL}" stroke-width="${6 * sc}"/><ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" fill="none" stroke="url(#cgMetal)" stroke-width="${3.6 * sc}"/>`;
}).join('');
const SK = () => EF(125, 190, 122, 108, 'url(#cgHalo)')
  + [[62, 58], [40, 84], [84, 72]].map(([x, y]) => shaft(x - 14, y + 170, x, y, 5, '#5d3a1a', '#8d6e63', null)
    + shp(`M${x},${y} q7,-17 8,-30 q4,13 8,30 q-8,6 -16,0z`, 'url(#cgBlade)', null, 1.8)).join('')
  + EF(125, 330, 112, 13, 'url(#cgGround)')
  + hhead(188, 170, .6, '#6b7b88', '#8e2b20')
  + hhead(102, 176, .92, '#8a5a32', '#2b5fc1')
  + chain([4, 268], [120, 318], [246, 250], 13)
  + chain([146, 214], [184, 236], [224, 206], 8, .62)
  + [[36, 300], [224, 288]].map(([x, y]) => EF(x, y, 26, 13, '#e8dcc0', .5) + EF(x + 16, y + 12, 18, 9, '#e8dcc0', .32)).join('')
  + star4(34, 160, 7, '#fff59d') + star4(228, 220, 6, '#fff59d');

// 替天行道：梁山杏黃大旗、交叉兵器、群山與一百零八星；旗上文字可換（其他主題的鬼牌也用這面旗，見 window.cardBanner）
const banner = (chars = ['替', '天', '行', '道']) => EF(125, 180, 124, 150, 'url(#cgHalo)')
  + Array.from({ length: 12 }, (_, k) => { const a = (k * 30 - 90) * Math.PI / 180, r0 = 46, r1 = 168;
    return fl(`M${125 + r0 * Math.cos(a)},${180 + r0 * Math.sin(a)} L${125 + r1 * Math.cos(a - .06)},${180 + r1 * Math.sin(a - .06)} L${125 + r1 * Math.cos(a + .06)},${180 + r1 * Math.sin(a + .06)}z`, '#ffe9a8', .4); }).join('')
  // 梁山群峰
  + shp('M-6,336 l40,-70 l26,26 l34,-66 l32,56 l28,-38 l48,92z', '#2f4858', 'cgShV', 2.4)
  + curve('M34,266 l12,20 M94,226 l16,26 M160,244 l14,18', '#17222b', 2)
  + fl('M94,230 l14,-26 l6,12z M34,272 l10,-14 l6,10z M202,284 l10,-14 l8,14z', '#dff1ff', .45)
  + shp('M-6,336 q62,-16 130,-6 q64,10 132,2 v16 h-262z', 'url(#wmWater)', 'cgShV', 2.2)
  + curve('M14,332 q30,-9 60,0 M150,330 q30,-9 60,0', '#fff', 2.2, .65)
  // 交叉兵器（旗後交叉）
  + shaft(214, 332, 40, 76, 7, '#5d3a1a', '#8d6e63', '#c9a227')
  + `<g transform="rotate(-34 40 76)">` + shp('M40,78 q-40,-18 -24,-64 q4,7 11,9 q-2,-7 4,-15 q15,28 15,70z', 'url(#cgBlade)', null, 2.2)
  + curve('M27,22 q-6,24 11,48', '#8d9ba5', 1.6) + shp('M33,70 h14 l-2,7 h-10z', 'url(#cgGold)', null, 1.6) + '</g>'
  + shaft(36, 332, 210, 76, 7, '#5d3a1a', '#8d6e63', '#c9a227')
  + `<g transform="rotate(34 210 76)">` + shp('M210,34 q8,20 9,36 q-5,6 -9,8 q-5,-2 -9,-8 q1,-16 9,-36z', 'url(#cgBlade)', null, 2.2)
  + curve('M210,42 v30', '#8d9ba5', 1.4) + shp('M203,76 h14 l-2,8 h-10z', 'url(#cgGold)', null, 1.6) + '</g>'
  // 旗桿與橫桁
  + shaft(125, 342, 125, 24, 9, '#6d4c2f', '#a1763f', null)
  + shp('M125,10 q8,14 7,26 h-14 q-1,-12 7,-26z', 'url(#cgGold)', null, 2)
  + shp('M74,44 h102 v12 h-102z', '#8b1a1a', 'cgShV', 2.2) + E(74, 50, 6.5, 7.5, 'url(#cgGold)', null, 1.8) + E(176, 50, 6.5, 7.5, 'url(#cgGold)', null, 1.8)
  // 旗面
  + shp('M79,56 h92 v246 L125,282 L79,302z', 'url(#wmBanner)', 'cgSh', 2.8)
  + fl('M79,56 h92 v246 L125,282 L79,302z', 'url(#cgBrocade)')
  + shp('M79,56 h12 v242 l-12,4z', '#8b1a1a', 'cgShV', 1.8) + shp('M159,56 h12 v246 l-12,-16z', '#8b1a1a', 'cgShV', 1.8)
  + [0, 1, 2, 3, 4, 5].map(k => E(85, 78 + k * 42, 2.8, 2.8, 'url(#cgGold)', null, .9) + E(165, 78 + k * 42, 2.8, 2.8, 'url(#cgGold)', null, .9)).join('')
  + curve('M96,62 v234 M154,62 v232', '#b07a16', 1.4, .5)
  + chars.map((ch, k) => txt(125, 198 - (chars.length - 1) * 28 + k * 56, ch, 50, '#8b1a1a', 2.2)).join('')
  // 一百零八星
  + [[44, 70], [62, 112], [34, 148], [206, 72], [192, 116], [218, 152], [72, 44], [180, 42]].map(([x, y], k) => star4(x, y, k % 2 ? 9 : 6, '#fff8c4')).join('')
  + star4(125, 20, 7, '#fff8c4');

const ogre = () => banner();
window.cardBanner = banner;
window.registerCardTheme('shuihu', { fig: FIG, text: TEXT, art: { HQ, DQ, CQ, SK, ogre } });
})();
