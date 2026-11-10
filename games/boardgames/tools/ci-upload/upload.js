#!/usr/bin/env node
'use strict';
/* Upload the board_games WeChat mini game with miniprogram-ci.
 *
 * Usage (from this folder, after `npm install`):
 *   node upload.js [version] [description]
 *   e.g. node upload.js 0.1.0 "first ci upload"
 *
 * The AppID is read from ../../wechat/project.config.json at runtime,
 * so it is not hard-coded here. The private key is NEVER pasted into
 * this file or into chat: download it from mp.weixin.qq.com
 * (Development Management -> Development Settings -> Mini Program
 * Code Upload), save it as private.key in this folder (or point
 * WX_PRIVATE_KEY_PATH at it), and keep it out of git.
 *
 * If IP whitelisting is enabled on that same MP page, add the IP you
 * are uploading from, or the upload will fail with an IP error.
 */
const fs = require('fs');
const path = require('path');
const ci = require('miniprogram-ci');

const ROOT = path.join(__dirname, '..', '..');
const PROJECT_PATH = path.join(ROOT, 'wechat');
const CONFIG_PATH = path.join(PROJECT_PATH, 'project.config.json');

const version = process.argv[2] || '0.1.0';
const desc = process.argv[3] || 'ci upload';

const keyPath =
  process.env.WX_PRIVATE_KEY_PATH ||
  path.join(__dirname, 'private.key');

if (!fs.existsSync(CONFIG_PATH)) {
  console.error('project.config.json not found at', CONFIG_PATH);
  process.exit(1);
}
const { appid } = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
if (!appid || appid === 'touristappid') {
  console.error('No real AppID in project.config.json; set it in DevTools first.');
  process.exit(1);
}
if (!fs.existsSync(keyPath)) {
  console.error('Private key not found at', keyPath);
  console.error('Download it from mp.weixin.qq.com (code upload settings),');
  console.error('save it as private.key in this folder, and do not commit it.');
  process.exit(1);
}

(async () => {
  const project = new ci.Project({
    appid,
    type: 'miniGame',
    projectPath: PROJECT_PATH,
    privateKeyPath: keyPath,
    ignores: ['node_modules/**/*'],
  });
  console.log('Uploading miniGame project', PROJECT_PATH, 'version', version);
  const result = await ci.upload({
    project,
    version,
    desc,
    robot: 1,
    setting: { es6: true, minify: true },
    // The whole package is >5 MB, and ci.upload defaults to the COS
    // async upload path for large packages -- the same COS transfer
    // that stalls in DevTools from this network. Force the direct
    // upload path first; if that fails, try again without this line.
    useCOS: false,
    onProgressUpdate: (task) => console.log('progress:', task),
  });
  console.log('Upload result:', result);
  console.log('Check the uploaded version in mp.weixin.qq.com -> Version Management.');
})().catch((err) => {
  console.error('Upload failed:', err && err.message ? err.message : err);
  process.exit(1);
});
