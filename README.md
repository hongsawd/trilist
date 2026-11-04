# 三格

一个把待办、日程和念头放在同一屏的个人工作台。桌面端是 Electron 侧栏，手机端是可直接安装的 Web App / Android APK。

![桌面看板](docs/screenshots/desktop-board.png)

| 平台 | 形态 | 主要入口 |
|---|---|---|
| Windows / Electron | 侧栏、托盘、全局快捷键、到点提醒 | `启动三格.vbs` |
| 手机 | PWA / Capacitor Android | `mobile/index.html` |

## 为什么是三格

| 分区 | 判断方式 | 行为 |
|---|---|---|
| 待办 | 现在能开始动手 | 可带截止日期；勾掉后进入已完成，可撤销 |
| 日程 | 有日期或时间，到点才发生 | 进入日历；完成后从“接下来”消失 |
| 念头 | 暂时没有明确动作，或需要等条件 | 随机浮现，可转待办、搁下或直接编辑 |

手机首页保持单屏可读：上方看板/日期，下面是待办和日程两列；日历、课表和设置通过点击或左右滑动切换。

<p>
  <img src="docs/screenshots/mobile-home.png" alt="手机首页" width="32%">
  <img src="docs/screenshots/mobile-thoughts.png" alt="念头与课表" width="32%">
  <img src="docs/screenshots/sync-settings.png" alt="同步设置" width="32%">
</p>

## 功能

- 待办、日程、念头和课程都有编辑/删除；删除后底部可撤销。
- 日期、时间、地点支持键盘、滚轮和触控操作。
- 课表可导入教务系统 HTML，也可手工编辑。
- 已结束课程自动变灰、划线并沉到列表底部。
- 桌面端支持全局快捷键、托盘、近期安排小窗和提前 30 分钟提醒。
- 可选双设备同步：本地修改约 1.5 秒后上传，前台约 10–12 秒拉取，窗口重新聚焦时立即同步。
- 首次同步自动备份，并用时间戳和删除墓碑避免离线数据被误恢复。

## 运行桌面版

需要 Node.js/Electron 运行环境。

```bash
cd desktop
npm install
npm start
```

在 Windows 上也可以运行根目录的 `启动三格.vbs /autostart` 作为后台常驻程序。

快捷键：

| 按键 | 作用 |
|---|---|
| `Ctrl+Alt+Space` | 打开 / 收起完整侧栏 |
| `Ctrl+Alt+Q` | 打开近期安排小窗 |
| `I` | 进入输入模式 |
| `X / C` | 切换上一个 / 下一个面板 |
| `S` | 打开近期安排 |
| `H` 或 `?` | 打开键盘说明 |
| `Esc` | 返回普通模式或关闭弹层 |

## 运行手机版

直接用浏览器打开 `mobile/index.html` 即可。Android 壳位于独立的 Capacitor 工程中：

```bash
npx cap copy android
cd android
./gradlew.bat assembleDebug
```

安装 APK 时建议覆盖安装，不要先卸载，否则 WebView 本地数据会被清除。

## 双端同步

同步是可选功能，默认关闭。应用设置页只要求两项：

1. **服务地址**：例如 `https://YOUR-PROJECT.pages.dev/api/sync`
2. **同步令牌**：由服务端生成的随机字符串

地址和令牌只保存在本机 `localStorage`，不应写进仓库。服务端部署方法见 [sync-worker/README.md](sync-worker/README.md)。

同步模型：

- 每条记录以 `kind + id` 标识，携带 `updatedAt`。
- 同一记录以较新的修改为准。
- 删除使用墓碑，防止另一台离线设备把数据复活。
- 当前是单用户数据空间，多用户隔离尚未实现。

### 部署同步服务

```bash
cd sync-worker
cp wrangler.example.toml wrangler.toml
npx wrangler d1 create sange-sync
npx wrangler d1 execute sange-sync --file=schema.sql
npx wrangler secret put SYNC_TOKEN
npx wrangler deploy
```

把 `wrangler.toml` 中生成的 D1 ID 填好，然后将部署后的 `/sync` 地址和同一令牌填入三格。

## 数据与隐私

- 桌面数据：Electron profile 内的 `localStorage["triage.v2"]`。
- 手机数据：`localStorage["sange.mobile.v1"]`。
- 仓库默认只包含中性示例数据，不包含真实待办、健康信息、课程地点或同步令牌。
- 同步服务只接收启用同步后的业务数据；不接收课表 HTML 原文件。
- `wrangler.toml`、`.dev.vars`、`.sync-token.txt` 和本地 profile 已加入忽略规则。

## 测试

```bash
python -X utf8 test_e2e.py
python -X utf8 test_desktop_static.py
python -X utf8 test_web_interactions.py
python -X utf8 test_reminder_daemon.py
python -X utf8 test_sync_safety.py
python -X utf8 test_mobile_edit_delete.py
python -X utf8 test_mobile_sync_retry.py
```

浏览器测试需要本机 Edge 和 `websocket-client`。

## 目录

```text
desktop/        Electron 主进程、托盘、提醒、近期窗口
mobile/         手机 Web App
sync-worker/    可选同步服务和部署模板
docs/           README 截图
index.html      桌面渲染页面
test_*.py       本地验收
```

## 已知限制

- 课程表当前以 2026-10-26（第 9 周）为周数锚点，换学期需要修改。
- Android 桌面小组件尚未在所有机型完成验证。
- 同步冲突采用“较新的修改覆盖”，没有手工选择冲突版本的界面。
- 当前仅支持单用户同步空间。
