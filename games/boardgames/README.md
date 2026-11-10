# 英雄擲天下

以三國、水滸、封神、西遊、楚漢為題材的回合制策略棋盤遊戲。擲骰行軍，購置領地、建設城池，招募武將單挑攻城，善用錦囊妙計扭轉戰局。支援2至4人同機對戰或挑戰電腦，率先佔領二十處領地者一統天下。

A property-and-siege board game with a board, rule book, poker cards, event cards and territory deeds, playable in several themes. The repository folder is `board_games`.

## Themes

Every theme uses the same rules, prices, tolls and card strengths. A theme only changes names and pictures: the board, the place names, the characters on the poker cards, the names of some special and strategy cards, and the page title.

| Theme | Key | Setting | Commanders (the four aces) | Event decks |
|---|---|---|---|---|
| 三國風雲 | `sanguo` | Three Kingdoms (*三國演義*) | 曹操、劉備、孫權、董卓 | 緊急軍情 / 錦囊妙計 |
| 水滸群豪 | `shuihu` | Water Margin (*水滸傳*) | 宋江、盧俊義、晁蓋、方臘 | 江湖告急 / 智取妙計 |
| 封神演義 | `fengshen` | Investiture of the Gods (*封神演義*) | 姜子牙、姬發、黃飛虎、紂王 | 天機示警 / 仙家妙計 |
| 西遊歷險 | `xiyou` | Journey to the West (*西遊記*) | 唐三藏、孫悟空、豬八戒、牛魔王 | 妖魔作亂 / 菩薩錦囊 |
| 楚漢爭霸 | `chuhan` | Chu–Han Contention (*楚漢傳奇*) | 劉邦、項羽、韓信、秦二世 | 烽火急報 / 帷幄妙計 |

Pick the theme on the offline setup screen, or as table owner in the online lobby (sit down → owner picks the theme → everyone picks a hero from that theme). In every theme the four 2-cards are figures known for supernatural powers (in Sanguo: 黃承彥、木鹿大王、于吉、張角), the 7s are mostly strategists, and the Jacks are the strongest fighters. The two rest squares, the treasure square and the recruiting square each use a place from that story (for example 鴻門, 阿房宮, 驪山陵 and 築壇拜將 in Chu–Han), and the event cards that mention people or places are reworded for each theme.

### Adding a theme

1. **`themes.js`**: add a `<KEY>_TILES` list (all 55 square names, in the same order as `TILES` in `engine.js`), a cards map, an entry in `THEMES` and the key in `order`. The entry has a `label`, `sub` (subtitle), `board` file name, `tiles`, `cards` (card code → name), `strategy` (strategy-card key → name), `kinds` (e.g. `overlord` → joker-card name) and `emergency` (event-card key → replacement text, title or agent). Anything not listed keeps the Sanguo version.
2. **Board**: run `python3 tools/make_board_svg.py`. It reads every theme in `order` and writes `board-<key>.svg`.
3. **Card art**: write a `theme-<key>-art.js` that calls `registerCardTheme('<key>', { fig, text, art, alias })`, like `theme-fengshen-art.js`, and load it in `index.html` after `theme-shuihu-art.js`. `alias` reuses another theme's special-card picture (for example `{ SK: 'shuihu:SK' }`), and `window.cardBanner([...])` draws a joker banner with your own text. Cards it doesn't cover use the Sanguo art.
4. **Online play and WeChat**: nothing to add. The server and `tools/build_wechat.js` pick up every theme from `themes.js`.

## Files

| File | Purpose |
|---|---|
| `index.html` | Page markup and styles |
| `engine.js` | Rules engine (no UI). Runs in the browser for offline play and in Node for online play |
| `client.js` | Board, side panel, dialogs and hover tips; the offline and online adapters |
| `texts.js` | Rules book and square descriptions, shared by the web version and the WeChat mini game |
| `cards.js` | SVG artwork for the 54 poker cards |
| `themes.js` | Theme data: square names, character names and card names for each theme |
| `theme-<key>-art.js` | Card portraits, descriptions and special-card art for each theme other than Sanguo (Sanguo's are in `cards.js`) |
| `board-<key>.svg` | One board per theme |
| `tools/make_board_svg.py` | Generates the board files from the names in `themes.js` (`--mobile` writes the portrait phone boards) |
| `wechat/` | WeChat mini game version (see [`wechat/README.md`](wechat/README.md)) |
| `tools/build_wechat.js`, `tools/wechat-preview/` | Builds the mini game's images and shared files; previews it in a browser |
| `server/server.js` | Online game server (Node.js, no dependencies) |
| `server/form.js` | Lets the server read answers to dialogs that contain form fields |

## Play offline (one computer)

Open `index.html` directly in a browser. Each seat can be a human or the computer; several humans can share one screen (the game asks you to pass the device before showing private cards). Pick the theme on the setup screen, or open `index.html?theme=shuihu` to start with Water Margin selected. `index.html?demo` runs a computer-only game; add `&theme=shuihu` for Water Margin.

## Play on WeChat (mini game)

`wechat/` is a WeChat mini game version with a portrait, phone-sized layout. Build it with `node tools/build_wechat.js`, then open the `wechat/` folder in WeChat DevTools. [`wechat/README.md`](wechat/README.md) covers the layout, how to let up to 15 friends test it as a 體驗版 (trial version), and what to fix before formal release.

## Play online (local test)

```sh
node server/server.js          # or SANGUO_PORT=9000 node server/server.js
```

Open <http://127.0.0.1:8765/> in several browser tabs or windows. Each tab is a separate player (the seat is remembered per tab, so reloading keeps your seat).

**Four tables.** The first page lists 4 tables with who is sitting where. Pick one to sit down, or watch a game that is already running (a spectator never sees anyone's hand).
- **Before the game:** ① sit at an open seat; the first player to sit is the table owner (房主). ② Only the owner picks the theme, by clicking one of five book covers; everyone else sees which one is chosen, and the table list shows it too. ③ Once the theme is chosen, each seated player picks a commander (主帥) from that theme; changing the theme makes everyone pick again. The owner can wait for friends, or turn empty seats into computer players (one by one, or with 空位全部設為電腦), set the speed, and start. Each table has its own theme.
- **During the game:** any player can stand up (離座). A computer takes over that seat and plays on. If the player stands up while a question is waiting, the game answers it with its default (usually the highlighted button).
- **When everyone has stood up:** when the last human leaves, the game ends and the table opens again for new players. A player whose browser stays disconnected for 90 seconds is stood up automatically (`SANGUO_GRACE_MS` changes that), so a closed tab can't keep a table stuck.
- **After a game:** any seated player can start a new one at the same table, with the same seats.
- **Under the hood:** each running game lives in its own worker thread (`server/game_worker.js`) with its own copy of the rules engine, because the engine keeps one game's state in module variables.

The game engine runs on the server, and each browser receives only that player's own view: your own hand, the public parts of the board, and cards you remember from public captures. Opponents' hands never reach your browser.

### Why it only runs on 127.0.0.1

This version has no login. The per-tab seat code only links a browser tab to a seat; it does not prove who someone is. The server therefore refuses to listen on anything other than `127.0.0.1` / `::1` / `localhost` (setting `SANGUO_HOST=0.0.0.0` makes it exit with an error).

> **In the Xanadu repo** the board game is deployed together with Guandan by the top-level `deploy/setup.sh`: one HTTPS address and one login, with this game under `/boardgames/`. The section below describes deploying this game by itself.

### Host it next to guandan on a Tencent Cloud server

`deploy/` adds this game to a Lighthouse machine that already runs [guandan](../guandan) with its HTTPS + shared-password nginx (`setup_lighthouse.sh --public`). It reuses that nginx certificate and login, so one password protects both games, and it never makes a password of its own: if guandan's login isn't set up, it stops.

```sh
deploy/make_bundle.sh                        # on your computer, from a committed checkout → dist/board_games-<rev>.tar.gz
scp dist/board_games-<rev>.tar.gz ubuntu@<server-ip>:~
# on the server
tar xzf board_games-<rev>.tar.gz && sudo bash board_games-<rev>/deploy/setup_tencent.sh
```

- **What it sets up:** Node.js 18+ if missing; the game in `/opt/board_games`, read-only to the service; a hardened systemd service `boardgames`, running as its own user and listening on `127.0.0.1:8765` only; and one extra nginx HTTPS port (default `8443`, `--port` to change) in front of it, with the login in place before the game starts.
- **What it checks before it says "done":** the game listens on loopback only, and anonymous requests to the page and the API get `401` with a login prompt. If anything fails it closes the public port again and stops.
- **By hand, in the Lighthouse firewall:** allow TCP `8443` (from anywhere, or only your friends' CIDR ranges such as `203.0.113.0/24`). Never open `8765`. Keep SSH limited to your IP.
- **Upgrade:** build a new bundle, copy it over, and run the script again. **Remove:** `sudo bash .../deploy/setup_tencent.sh --remove`, then delete the firewall rule.
- **Limits:** the login is guandan's one shared password, not a per-person account. Anyone who has it can sit at any open seat and run a table's lobby, so share it only with people you want at the tables. There are 4 tables, so up to 4 games run at once (about 50 MB each; the service is capped at 700 MB). A mainland-China server may need an ICP filing for public access (see guandan's `docs/DEPLOY.md`). The browser shows a certificate warning once for this port.
- **Not tried on a real server yet:** `deploy/setup_tencent.sh` has been syntax-checked, and the bundle has been unpacked and served locally, but the script itself has not been run on a Lighthouse machine.

### Before friends on other computers can join (without that server)

1. **Host it on a personal account, not a corporate machine.** For example a personal cloud account or a hosting service that runs Node.js. Do not expose it from a work laptop or Cloud Desktop.
2. **Add a real sign-in** from the hosting platform or an identity provider (for example "Sign in with Google"), so each seat is tied to a verified account. Do not use home-made passwords or shared room codes.
3. **Serve it over HTTPS only.**
4. **Map signed-in accounts to seats** in `server/server.js` (`/api/join` and `seatByToken`) instead of the per-tab code, and only then allow a non-loopback listen address.
