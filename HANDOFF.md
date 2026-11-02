# 三格交接文档 · v1.1

日期：2026-11-02
桌面仓库：`<本地工作区>/triage`
Git tag：`v1.0`（原始版重建归档）、`v1.1`（当前版）
手机源码：`mobile/index.html`（仓库内）/ `<LOCAL_APP>\sange-mobile-preview.html`（工作副本）
安卓壳：`<LOCAL_APP>\sange-app`
APK：`<LOCAL_APP>\三格-v1.1-debug.apk`
PWA：https://YOUR-PROJECT.pages.dev/
Cloudflare Pages：项目 `sange`，生产分支 `main`
GitHub：`YOUR-GITHUB/trilist`（私有仓库，v1.1 首次推送；2026-11-02 已创建并认证）

> 推送规则：**只有明确说“上传”时才 `git push`**，平时每次修改都不自动推。推送前先按第 8 条洗数据。

## 1. 当前状态

### 桌面端
- Electron 壳 + 单文件 `index.html`；`desktop/` 是 Electron 主进程、托盘、提醒。
- 看板：待办 / 日程 / 念头；日历 / 课表两个面板。
- v1.1 起日程支持 `endDate`、`endTime`；看板显示日期范围，进行中的标「进行中」。
- 日历只显示日程，不再显示课程；课程在课表面板。
- 桌面标题旁显示 `v1.1`；`desktop/package.json` 1.1.0。
- 启动：桌面「三格」快捷方式或 `启动三格.vbs`。

### 手机端
- `sange-mobile-preview.html` 是单文件 Web App；`sange-app` 是 Capacitor 安卓壳。
- 首页：顶部日期、日历、左待办、右日程、底部快捷条。
- 第二页：念头浮签 + 周课表。
- 日历：日程条形、多天连续、当天面板、超出 `+N`；课程不进日历。
- 底部快捷条：`随手记 / 念头 / 待办 / 日程 / ＋`，每个入口打开对应类型。
- 版本 `v1.1`；APK `versionName 1.1`、`versionCode 2`。
- 数据：`localStorage["sange.mobile.v1"]`。
- 小组件：Android 原生 `SangeWidgetProvider`，读 Preferences 的 `sange.widget`，显示今天课程 + 前 3 条待办；Web 端通过 `sange-app` 的 Preferences 插件写入，`WidgetRefresh` 插件触发刷新。真机 launcher 尚未验证。

## 2. 数据模型

### 手机 store
```js
{
  todos:   [{ id, text, meta, tag, tone, done }],
  events:  [{ id, date, time, endDate, endTime, text, place, kind, tone }],
  courses: [{ id, day, start, end, weeks:[5,6,...], name, place, teacher, classNo, color }],
  thoughts:[ "..." ]
}
```
- `day`：周一=1 … 周日=7。
- `start/end`：节次，1–14。
- `weeks`：显式周数组，由 `5-18周`、`5周`、`8周,14周` 等解析。
- 日历按 `date <= 某天 <= endDate` 显示多天日程。

### 桌面 store
- `localStorage["triage.v2"]`：`todo`、`dated`、`ideas`、`done`。
- `dated` 新增可选 `endDate`、`endTime`；旧数据不带这两个字段，兼容。
- 桌面与手机是两套独立本地数据，目前不互通。

## 3. 周数

- 课表锚点：第 9 周周一 = `2026-10-26`；第 10 周 = `2026-11-02` 那周。
- 当前周由 `weekNoForDate()` 计算；课表按 `weeks.includes(weekNo)` 过滤。
- 新学期需要改锚点，或改成可配置的“第 1 周开始日期”。

## 4. 课表导入

- 入口：手机课表页「导入 HTML」。
- 来源：校园教务系统课表页另存为 HTML。
- 表格：`table.wut_table`；8 列（星期日在前），9 行（1-2 … 13-14 节）。
- 单元格文本：`课程名[班级] 教师 周次,星期N,节次,地点`。
- 周次支持：`5-18周`、`5周`、`8周,14周`、`1-16周(单)`、`1-16周(双)`。
- 解析后按 `name|day|start|end|weeks|place|teacher` 去重。
- 导入会覆盖当前课表，会先弹确认。
- 解析在本地浏览器完成，文件不上传。

## 5. 构建与发布

### 桌面
- 无构建；改 `index.html` 后重启 Electron（或刷新）。
- 测试：
  ```powershell
  python -X utf8 test_web_smoke.py
  python -X utf8 test_web_interactions.py
  ```
- Git：
  ```bash
  git -C "<本地工作区>/triage" log --oneline --decorate
  ```

### 手机 PWA
```bash
cd <LOCAL_APP>
cp sange-mobile-preview.html deploy/sange/index.html
npx --yes wrangler@latest pages deploy deploy/sange --project-name sange --branch main
```
- Cloudflare OAuth 登录账号：见本地密码库，不写进仓库。
- 生产地址：https://YOUR-PROJECT.pages.dev/

### APK
```bash
cp <LOCAL_APP>/sange-mobile-preview.html <LOCAL_APP>/sange-app/www/index.html
cd <LOCAL_APP>/sange-app
npx cap copy android
cd android
export JAVA_HOME="<LOCAL_APP>/jdk21/jdk-21.0.13+9"
export ANDROID_HOME="<LOCAL_APP>/android-sdk"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$PATH"
./gradlew.bat assembleDebug --no-daemon
```
- 产物：`android/app/build/outputs/apk/debug/app-debug.apk`
- 版本：`android/app/build.gradle` 的 `versionCode` / `versionName`。
- 当前 APK 复制到 `<LOCAL_APP>\三格-v1.1-debug.apk`。
- 覆盖安装，不要先卸载，否则本地数据会清。

## 6. 小组件

- 原生：`android/app/src/main/java/com/sange/app/SangeWidgetProvider.java`
- 布局：`res/layout/widget_sange.xml`
- 配置：`res/xml/sange_widget_info.xml`
- 数据：Web 端 `saveWidget()` 写 Preferences key `sange.widget`（SharedPreferences 文件 `CapacitorStorage`）。
- 刷新：`WidgetRefreshPlugin` 在数据变化时调用 `AppWidgetManager.updateAppWidget`。
- 周期：`updatePeriodMillis=1800000`（30 分钟）兜底。
- 真机测试：长按桌面 → 小组件 → 三格。

## 7. 已知问题 / 限制

- 没有双端同步；桌面、PWA、APK 各自本地数据。
- 手机待办只能完成/恢复，日程只能新增；编辑/删除待办和日程还没做。
- 课表可以新增/编辑/删除课程。
- 小组件还没在真机 launcher 上验证；立即刷新依赖插件。
- 顶部安全区用 `max(56px, 16px + env(safe-area-inset-top))`；不同机型可能还要微调。
- 周数锚点写死在 2026-10-26；换学期要改。
- 教务系统页面改版会导致 HTML 导入解析失败。
- 桌面 v1.0 是反向还原归档，不是原始字节副本；见 `CHANGELOG.md`。

## 8. 安全与规矩

- 上传/部署/发链接前先洗数据：真实待办、念头、健康、课程地点、姓名、账号一律换成中性示例；上线前搜原文和线上页面。
- 仓库 `.gitignore` 已排除 `triage.json`、`desktop/seed-data.json`、`reminder-state.json`、`desktop/profile/`、截图。
- 界面上看起来能点的东西必须真的能点。
- 改没有版本控制的项目前先 `git init` 或备份。

## 9. 下一步：双端同步

目标：桌面端和手机端共享同一份待办/日程/念头/课表，离线和冲突都能处理。

### 方案 A：Cloudflare Worker + D1/KV（推荐）
- 一个极小的同步 API：`GET /snapshot`、`POST /snapshot`，用共享 token 鉴权。
- 每条记录带 `updatedAt` 和 `deleted` 墓碑；合并规则：按条目 last-write-wins，删除优先。
- 手机和桌面各自在本地先写，再后台推送；失败不影响本地。
- 初版可以只做“打开时拉、改动后推”，不做实时。
- 数据量很小（个人待办/日程/课程），D1/KV 免费额度足够。
- 需要把桌面的 `index.html` 也接上同步客户端。

### 方案 B：WebDAV / 网盘文件同步
- 同步一个 JSON 文件（坚果云等）；改动后上传，打开时下载。
- 没有服务器代码，但冲突会产生副本，手机后台不稳定。

### 方案 C：CRDT（Automerge/Yjs）
- 真正无冲突合并，但引入依赖和复杂度；当前数据量不值得。

### 建议
先做 A 的最小版：单用户共享 token、整份 snapshot、按条目 LWW + 墓碑；先手动“同步”按钮，再自动。需要先定：
1. 用 Cloudflare Worker + D1 还是 KV；
2. token 放哪、怎么在两端配置；
3. 冲突时以哪端为准（默认最近修改）；
4. 桌面端 localStorage 如何迁移到同步层。

## 10. 文件索引

- 桌面主界面：`triage/index.html`
- 桌面 Electron：`triage/desktop/`
- 手机 Web：`<LOCAL_APP>\sange-mobile-preview.html`
- 安卓壳：`<LOCAL_APP>\sange-app`
- 部署目录：`<LOCAL_APP>\deploy\sange`
- 版本记录：`triage/CHANGELOG.md`
- 测试：`triage/test_web_smoke.py`、`triage/test_web_interactions.py`
- APK：`<LOCAL_APP>\三格-v1.1-debug.apk`
