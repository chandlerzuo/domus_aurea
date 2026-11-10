# WeChat mini game upload via miniprogram-ci

Alternative to the DevTools Upload button, which times out on the
Tencent Cloud COS transfer from this network. This path uploads
with a private key from the MP platform instead.

## 1. Get the private key (once, by hand)

1. Go to mp.weixin.qq.com, open the mini game account.
2. Development Management -> Development Settings -> Mini Program
   Code Upload (小程序代码上传).
3. Generate/download the key file.
4. Save it as `private.key` in this folder.
5. Configure the IP whitelist on that page and add the IP you are
   uploading from. miniprogram-ci will not work without a
   whitelisted IP.

Never commit `private.key`, never paste its contents into chat.
Add `tools/ci-upload/private.key` and `tools/ci-upload/node_modules/`
to .gitignore if they are not already ignored.

## 2. Install and upload

```sh
cd ~/Documents/GitHub/board_games/tools/ci-upload
npm install
node upload.js 0.1.0 "first ci upload"
```

Bump the version number if WeChat reports that version already exists.
The AppID is read from `wechat/project.config.json` at runtime.

## 3. Verify

mp.weixin.qq.com -> Version Management -> Development Version
should list the new version. From there it can be set as a trial
version (体验版) for testers.
