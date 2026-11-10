# 开发与测试

## 项目结构

```text
index.html          Windows 界面
desktop/            Electron 桌面进程、托盘和提醒
mobile/             手机界面
shared/             两端共用的排序与同步规则
sync-worker/        同步服务和数据库结构
docs/screenshots/   演示截图
test_*              自动化检查
```

## Windows 源码运行

需要 Node.js，在 `desktop` 目录执行：

```bash
npm install
npm start
```

修改界面后重新加载窗口；修改桌面进程后重启应用。

## 手机预览与构建

在浏览器打开 `mobile/index.html` 可以预览。页面依赖上一级的 `shared/`，请保留目录结构。

Android 使用独立的 Capacitor 工程。将手机页面复制为工程中的 `www/index.html`，同时将 `shared/` 复制为 `www/shared/`，再运行 `npx cap copy android` 和 Gradle `assembleDebug`。当前仓库未包含完整 Android 壳工程。

托管版通过 `sync-worker/prepare-hosted.py` 写入公开服务地址。令牌由用户在软件中填写。

## 数据与分发

- 正式首次打开使用空白数据。演示截图应使用独立配置，通过 `?demo=1` 或人工构造样例展示。
- Windows 本地数据在 `desktop/profile/`；手机数据在 WebView 的本地存储中。
- 交接记录、个人配置、令牌、设备缓存和真实事项不进入仓库或发布包。
- Windows 分发包包含 Electron 运行时；普通使用者无需安装开发环境。

## 自动化检查

浏览器检查需要 Windows 上的 Microsoft Edge，以及 Python 的 `websocket-client`。

```bash
python -X utf8 test_web_interactions.py
python -X utf8 test_desktop_static.py
python -X utf8 test_mobile_edit_delete.py
python -X utf8 test_mobile_gestures.py
python -X utf8 test_sync_safety.py
python -X utf8 test_mobile_sync_retry.py
python -X utf8 test_cross_device.py
python -X utf8 test_reminder_settings.py
node test_shared_sync.mjs
node test_reminder_rules.cjs
```

同步测试使用本地服务和测试数据，不依赖个人令牌。

## 当前限制

- 课程周数使用固定的学期锚点，尚未提供换学期设置。
- Android 小组件仍需进一步真机验证。
- 同步采用较新的整条记录，尚未提供冲突选择界面。
- 独立笔记页仍在计划中。
