# 三格手机端

`index.html` 是手机端单文件 Web App 的源码（v1.9，含同步）。

- 直接双击可在浏览器预览；数据存 `localStorage["sange.mobile.v1"]`。
- PWA 发布：复制到 `deploy/sange/index.html`，用 Wrangler 部署到 Cloudflare Pages 项目 `sange`。
- APK：复制到 `sange-app/www/index.html`（安卓壳目录），`npx cap copy android`，再运行 Gradle `assembleDebug`。
- 详细路径、构建命令、数据模型和已知限制见仓库根目录的 `HANDOFF.md`。
- 课表导入在“课表”页点“导入 HTML”，选择教务系统另存的 HTML；解析在本机完成，不上传。
- 本文件不含真实个人数据；发布前仍需按 `HANDOFF.md` 第 8 条检查。
