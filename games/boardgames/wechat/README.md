# 英雄擲天下: WeChat mini game (微信小遊戲)

## Listing text

- **Name:** 英雄掷天下 (Traditional: 英雄擲天下). Check that it's free with 名称检测 when registering.
- **Description (小游戏介绍, 4–120 characters):** 以三国、水浒、封神、西游、楚汉为题材的回合制策略棋盘游戏。掷骰行军，购置领地、建设城池，招募武将单挑攻城，善用锦囊妙计扭转战局。支持2至4人同机对战或挑战电脑，率先占领二十处领地者一统天下。
- **Tagline / share title:** 掷骰行军，攻城略地——古今英雄任你调遣。

This folder is a WeChat mini game project. It runs the same rules engine as the web version (`engine.js`, `themes.js`, `texts.js`, `server/form.js`) and draws everything on a canvas, because mini games have no HTML. It is single-device only for now: one player against the computer, or several people passing one phone.

## Phone layout

- **Portrait board.** The board is drawn upright and fitted to the screen width. On a 390-pt-wide phone (iPhone 12–16), city names come out at about 14–20 pt and square labels at 12–15 pt.
- **Phone-only board art** (`tools/make_board_svg.py --mobile`):
  - Labels are enlarged, and long names are shortened: 職業介紹所 → 介紹所, 緊急軍情 → 軍情, 商店街 → 商店.
  - Tiny captions such as 抽牌 and 古戰場 are dropped. Tap any square for its full details.
  - The shop squares have no brand logos.
- **Text sizes** follow Apple's and WeChat's guidance:
  - Body text 16 pt, secondary text at least 13 pt.
  - Every button is at least 44 pt tall.
- **Bottom sheets.** Dialogs slide up from the bottom, so the top of the board stays visible. Long dialogs scroll.
- **Controls:**
  - Choices are full-width rows with radio buttons or checkboxes. Numbers use −/＋ buttons plus 最少 and 最多.
  - Cards in a dialog are 72–84 pt wide. Long-press a card to see its description.
- **Board gestures:** pinch to zoom (up to 3.2×), drag to pan, double-tap to zoom in or reset, tap a square for its details. When zoomed in, the board follows the current player.
- **Computer turns, step by step.** Computer flags move one square at a time. Each computer action appears on a card over the board, with the two before it, and the game pauses on it: 5 seconds at 慢, 3 seconds at 中 and 2 seconds at 快. The card stays on the half of the board away from the moving flag. Tap it to skip ahead. If a computer's action involves you (an attack, for example), your dialog appears only after you've read what happened.
- **Small screens.** On small phones such as the iPhone SE, the board shrinks a little so the player panels and action buttons still fit. Pinch-zoom makes up the difference.
- **Screen layout:** the top row (next to WeChat's ⋯ ◎ button) shows the menu and whose turn it is. Below the board are the four player panels and the action row: 擲骰子, 錦囊, 變賣 and 手牌.
- **Health notice.** The setup screen shows 健康遊戲忠告, which WeChat requires.

## Build

From the repository root. Needs Node.js 22 or later, Python 3 and Google Chrome:

```sh
node tools/build_wechat.js
```

The build does the following:
1. Copies the shared engine files into `wechat/js/lib/`.
2. Draws the phone boards and the card sheets as JPGs in headless Chrome, and writes the card descriptions to `wechat/js/data/cardinfo.js`.
3. Writes the browser preview bundle.
4. Puts each theme's board and cards (about 1.6 MB) in its own subpackage, `wechat/themes/<key>/`, listed in `game.json`. The phone downloads a theme's subpackage only when that theme is picked; the start button shows the download progress. The main package keeps only the code and small theme previews, about 0.45 MB against WeChat's 4 MB limit. All five themes together are about 8.3 MB, against the 30 MB total limit.

The generated files are git-ignored, so run the build again after changing the engine, the themes or the art.

## Try it in a browser first

After building, open `tools/wechat-preview/index.html` in Chrome. Turn on DevTools device mode (for example "iPhone 14 Pro") and reload. Add `?notch=1` to simulate a phone with a notch and home bar. The preview fakes the few `wx` APIs the game uses (`tools/wechat-preview/wx-shim.js`).

## Run it in WeChat

1. **Register a mini game account.** Go to <https://mp.weixin.qq.com/>, register a 小程序, and choose **游戏** at registration (this can't be changed later). An individual (个人) account works.
   - Don't pick 牌类 as the category: individuals can't use it, and it has extra rules. 休闲 or 棋类 fit this game.
   - Your AppID is under 开发管理 → 开发设置.
2. **Install WeChat DevTools (微信开发者工具).** Download it from <https://developers.weixin.qq.com/minigame/dev/devtools/download.html>; there's a native Apple Silicon build. Log in by scanning with WeChat.
3. **Import the project.** Choose 导入 and pick this `wechat/` folder. Enter your AppID; it replaces `touristappid` in `project.config.json`.
   - Without an account you can use a 测试号. It can preview on your own phone but can't upload, so friends can't try it that way.
4. **Test on your phone.** Click **预览** and scan the QR code with WeChat.

## Let friends test it (体验版)

1. In DevTools, click **上传**. Enter a version number such as `0.1.0` and a note.
2. On mp.weixin.qq.com, go to **版本管理**, find the upload under 开发版本, and choose **选为体验版**.
3. Go to **成员管理 → 体验成员** and add each friend's WeChat ID.
   - An individual account can have **15 testers**. Company accounts can have 30–90, depending on verification.
4. Send your friends the **体验版 QR code**, also on 版本管理. They scan it in WeChat and the game opens. Only people on the tester list can open it.

The trial version doesn't go through WeChat's review, so it's the right stage for collecting feedback.

## Before formal release

WeChat reviews the game when you submit it. Things to sort out first:

- **Content** (operating rules 2.5.5, 2.5.6 and 2.6.2: trademarks, copyrighted characters, vulgar content): the known issues are fixed. The brand logos are gone, the licensed 2-card characters are replaced, and the suggestive and off-theme card texts are rewritten. Re-check any new names or text you add.
- **Paperwork** for a free game without in-app purchases:
  - **游戏自审自查报告:** filled in online.
  - **适龄提示:** the age-suitability notice.
  - **小游戏备案:** the game filing. The platform takes 1–2 working days, plus 10–20 for the authority.
  - **小程序备案:** the ICP filing.
  - A 游戏版号 (game license) is only needed if you add in-app purchases.
  - Keep English and the word 软件 out of the game name; otherwise a 软著 (software copyright registration) is required.
- **Online play** will need more:
  - An HTTPS server on an ICP-filed domain added to the domain allowlist.
  - Players signed in with `wx.login` and identified server-side with `code2Session` (openid), replacing the per-tab seat code (see the main README).
