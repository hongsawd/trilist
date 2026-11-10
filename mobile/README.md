# 三格手机端

`index.html` 是手机端 Web App 的源码（v1.15），共享规则位于根目录的 `shared/`。

- 直接双击可在浏览器预览；数据存 `localStorage["sange.mobile.v1"]`。
- PWA 发布：复制到 `deploy/sange/index.html`，用 Wrangler 部署到 Cloudflare Pages 项目 `sange`。
- APK：将页面和根目录的 `shared/` 一起复制到安卓工程 `www/`，执行 `npx cap copy android`，再运行 Gradle `assembleDebug`。
- 正式首次打开为空白；截图可以在独立浏览器环境用 `?demo=1` 加载演示内容。
- 托管版通过 `sync-worker/prepare-hosted.py` 内置公开服务地址，使用者仅填个人令牌。多人隔离需要先升级线上服务，不能共用管理员的个人令牌。
- 预览、构建和测试见 [开发说明](../docs/DEVELOPMENT.md)。
- 课表导入在“课表”页点“导入 HTML”，选择教务系统另存的 HTML；解析在本机完成，不上传。
- 发布前检查页面、共享配置、图片与 APK；不能含真实个人数据或令牌。
