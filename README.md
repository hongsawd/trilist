# 三格

一个把待办、日程和念头放在同一屏的个人工作台。桌面端是 Electron 侧栏，手机端是可直接安装的 Web App / Android APK。

![桌面看板](docs/screenshots/desktop-board.png)

| 平台 | 形态 | 主要入口 |
|---|---|---|
| Windows / Electron | 侧栏、托盘、全局快捷键、到点提醒 | `启动三格.vbs` |
| 手机 | PWA / Capacitor Android | `mobile/index.html` |

## 安装和开始使用

**Windows 安装包**

1. 拿到 `三格-Windows-v1.6.zip` 后，先完整解压到一个固定文件夹。
2. 在解压后的「三格」文件夹中，双击 `启动三格.vbs`。不要在压缩包里直接运行。
3. 安装包已带运行环境，无需安装 Node.js、Python 或 Electron，也不用执行命令。
4. 第一次打开是空白清单。关闭窗口后程序留在托盘；按 `Ctrl+Alt+Space` 可再次唤起。

桌面右上角的齿轮打开提醒设置：提前 30 分钟、自定义，或不提醒；自定义填 `0` 表示到点提醒。

**Android 安装包**

打开作者提供的 APK，按手机提示安装。更新时直接覆盖安装，保留原有数据。普通使用者不需要 Android 开发环境，也不需要自己构建。

**要开启同步**

向提供安装包的维护者索取一枚已经开通的个人令牌，在应用的“同步”页粘贴后点“立即同步”。电脑和手机使用同一枚令牌，就会连接到同一份清单。没有令牌时仍可离线使用。

当前没有自助注册，GitHub 中也没有可直接复制的公共令牌。自己随便生成一段文字不能直接使用，必须先由维护者登记开通；不同的人分别领取自己的令牌。

演示图展示的是样例内容，正式软件不会预先填入这些事项。

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
- 桌面端支持全局快捷键、托盘、近期安排小窗；齿轮设置中可选择提前 30 分钟、自定义分钟数或不提醒。
- 可选双设备同步：本地修改后约 0.35 秒发起上传，前台每 2 秒检查，窗口重新聚焦时立即同步；实际延迟取决于网络。
- 首次连接自动备份并合并两端数据；同名冲突分别保留，删除墓碑防止离线数据复活。

## 开发者：从源码运行

普通使用者请按上面的安装包步骤操作。下面只用于修改代码或自行构建。

<details>
<summary>展开桌面源码运行步骤</summary>

需要 Node.js/Electron 运行环境。

```bash
cd desktop
npm install
npm start
```

在 Windows 上也可以运行根目录的 `启动三格.vbs /autostart` 作为后台常驻程序。

</details>

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

<details>
<summary>展开手机源码预览与构建步骤</summary>

直接用浏览器打开 `mobile/index.html` 即可。Android 壳位于独立的 Capacitor 工程中：

```bash
npx cap copy android
cd android
./gradlew.bat assembleDebug
```

安装 APK 时建议覆盖安装，不要先卸载，否则 WebView 本地数据会被清除。

</details>

## 双端同步

托管版已内置服务地址，使用者只需填写管理员提供的个人令牌；同一个人多台设备使用同一令牌，不同人的令牌对应独立数据空间。令牌就是访问凭证，请勿共用或公开。

自行部署的源码版仍可填写两项：

1. **服务地址**：例如 `https://YOUR-PROJECT.pages.dev/api/sync`
2. **同步令牌**：由服务端生成的随机字符串

地址和令牌只保存在本机 `localStorage`，不应写进仓库。服务端部署方法见 [sync-worker/README.md](sync-worker/README.md)。

同步模型：

- 每条记录以 `kind + id` 标识，携带 `updatedAt`。
- 同一记录以较新的修改为准。
- 删除使用墓碑，防止另一台离线设备把数据复活。
- 服务端通过个人令牌查找独立数据空间，不接受客户端指定其他人的空间。旧个人令牌仍读取原有数据。

<details>
<summary>维护者：自行部署服务</summary>

```bash
cd sync-worker
cp wrangler.example.toml wrangler.toml
npx wrangler d1 create sange-sync
npx wrangler d1 execute sange-sync --file=schema.sql
npx wrangler secret put SYNC_TOKEN
npx wrangler deploy
```

把 `wrangler.toml` 中生成的 D1 ID 填好，然后将部署后的 `/sync` 地址和同一令牌填入三格。

多人托管服务的令牌生成、登记与撤销见 [维护者说明](sync-worker/README.md#发放与撤销令牌)。不要把单用户部署的同一令牌发给所有人。

</details>

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
python -X utf8 test_cross_device.py
node test_shared_sync.mjs
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
- 多人服务升级需要先执行数据库迁移，再部署新版服务；仅更新 APK 不会升级线上服务。

### 排序和滑动

两端待办使用同一规则：未完成优先、紧急程度优先、同级按截止日期，最后按记录编号稳定排序。日程按日期排列，同日事件先于默认课程，已结束课程沉底。手机左右页面保持跟手平移，待办与日程各自原生纵向滚动；同步未产生内容变化时不重绘列表。

首次打开默认空白。需要演示数据时使用 `?demo=1`，不要用演示环境连接个人同步空间。
