# 三格 · 交接（v1.10）

## 三行摘要
- 桌面 Electron + 手机 PWA/APK，同一套「待办 / 日程 / 念头 / 课表」；桌面 v1.2，手机 v1.10。
- 手机在改动后自动同步，桌面支持手动同步；双端真实数据往返仍需一次完整验收。
- 下一步先修同步字段转换、首次同步覆盖保护和自动化测试。GitHub 只在宏明确说“上传”时才推。

## 路径与版本

| 项 | 值 |
|---|---|
| 桌面仓库 | `~/Documents/deepseek-harness/default-workspace/triage` |
| Git tag | `v1.0`（原版重建归档）、`v1.1`（桌面基线）、`v1.10`（手机导航、列表与同步页收尾） |
| GitHub | `YOUR-GITHUB/trilist`（private，已建；本地 commits 未推送） |
| 手机源码 | `mobile/index.html`（仓库内，v1.10）/ `<LOCAL_APP>\sange-mobile-preview.html`（工作副本） |
| 安卓壳 | `<LOCAL_APP>\sange-app`（versionCode 12 / 1.10） |
| APK | `<LOCAL_APP>\三格-v1.10-debug.apk` |
| PWA | https://YOUR-PROJECT.pages.dev/ |
| Cloudflare Pages | 项目 `sange`，生产分支 `main` |

> 推送规则：**只有宏明确说“上传”时才 `git push`**。平时本地提交可以，远端不动。

## 怎么跑

- 桌面：双击桌面「三格」或 `启动三格.vbs`；改 `index.html` 后重启 Electron。
- 手机预览：浏览器打开 `<LOCAL_APP>\sange-mobile-preview.html`。
- PWA：直接开 https://YOUR-PROJECT.pages.dev/。
- APK：覆盖安装，不要卸载（卸载会清 WebView 本地数据）。

## 结构

| 文件 | 作用 |
|---|---|
| `index.html` | 桌面主界面、看板、日历、课表、输入 |
| `desktop/` | Electron 主进程、托盘、提醒、`seed-data.json`（不入库） |
| `mobile/index.html` | 手机端单文件 Web App |
| `sange-app` | Capacitor 安卓壳 + 原生小组件 |
| `HANDOFF.md` / `CHANGELOG.md` | 交接、版本记录 |
| `test_web_smoke.py` / `test_web_interactions.py` | 桌面验收 |

## 数据

手机 `localStorage["sange.mobile.v1"]`：
```js
{
  todos:   [{ id, text, meta, tag, tone, done }],
  events:  [{ id, date, time, endDate, endTime, text, place, kind, tone }],
  courses: [{ id, day, start, end, weeks:[5,6...], name, place, teacher, classNo, color }],
  thoughts:[{ id, text }],
  deleted: [{ kind, id, updatedAt }],          // 待同步的删除墓碑
  sync:    { url, token, lastSync }
}
```
- 所有条目都有 `updatedAt`（毫秒时间戳），同步按它做 LWW。
- `day` 周一=1…周日=7；`start/end` 1–14 节；`weeks` 是显式周数组。
- 日历按 `date <= 某天 <= endDate` 显示多天日程。

桌面 `localStorage["triage.v2"]`：`todo`、`dated`、`ideas`、`done`；`dated` 可选 `endDate` / `endTime`。

## 课表导入

- 手机「课表」页 → 「导入 HTML」→ 选教务系统另存的 HTML。
- 表格：`table.wut_table`；8 列（星期日在前），9 行（1-2 … 13-14 节）。
- 单元格：`课程名[班级] 教师 周次,星期N,节次,地点`。
- 周次：`5-18周`、`5周`、`8周,14周`、`1-16周(单)`、`1-16周(双)`。
- 去重键：`name|day|start|end|weeks|place|teacher`；导入前会确认覆盖。
- 解析在浏览器本地完成，文件不上传。

## 构建与发布

### 桌面测试
```bash
python -X utf8 test_web_smoke.py
python -X utf8 test_web_interactions.py
```

### PWA
```bash
cd <LOCAL_APP>
cp sange-mobile-preview.html deploy/sange/index.html
npx --yes wrangler@latest pages deploy deploy/sange --project-name sange --branch main
```

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
产物 `android/app/build/outputs/apk/debug/app-debug.apk`；版本在 `android/app/build.gradle`。

### 小组件
- `SangeWidgetProvider` 读 `CapacitorStorage` / `sange.widget`。
- Web 端 `saveWidget()` 写快照；`WidgetRefreshPlugin` 触发刷新；30 分钟兜底。
- 真机：长按桌面 → 小组件 → 三格。

## 已知限制

- 桌面已接同步：普通同步双向 LWW；首次同步默认「课程跟云端，其余跟电脑」。
- 手机已在 v1.8 适配桌面 `cat/note/where` 字段；仍需真机完成一次双向同步复测。
- 首次同步缺少本地时间强制抬升，历史示例 ID 碰撞时可能覆盖真实条目。
- 暂无覆盖同步合并、首次同步和墓碑回放的自动化测试。
- 桌面课表已进 store，但还没有 HTML 导入；真课表靠首次同步从云端拉。
- 手机待办只能完成/恢复，日程只能新增；编辑/删除待办、日程未做。
- 小组件未真机验证；立即刷新依赖插件。
- 顶部安全区使用 `max(16px, env(safe-area-inset-top))`，量产前仍需在刘海屏和曲面屏真机复核。
- 周数锚点写死 `2026-10-26`（第 9 周周一）；换学期要改。
- 教务系统页面改版会导致导入失败。
- v1.0 是按编辑记录反向还原的归档，不是原始字节副本；见 `CHANGELOG.md`。

## 同步现状与待修

最小契约：
- `GET /snapshot`、`POST /snapshot`；单用户 token 鉴权。
- 每条记录带 `updatedAt` 和 `deleted` 墓碑；按条目 last-write-wins，删除优先。
- 客户端：本地先写；打开时拉，改动后推；先做手动「同步」按钮，再自动。
- D1 表：`items(owner, kind, id, payload, updated_at, deleted)`，按 `owner+kind+id` 唯一。
- 迁移：给手机 store 的 todos/events/courses/thoughts 和桌面 store 的 todo/dated/ideas/done 补 `updatedAt`/`deleted`；桌面加读写包装。
- 验收：两台设备、离线改、删除/恢复、同一条冲突、初次全量。

### 后端已部署（2026-11-02）

- Pages Function（当前）：`deploy/sange/_worker.js`，地址 https://YOUR-PROJECT.pages.dev/api/sync
- Worker（备用）：`sange-sync`，地址 https://YOUR-WORKER.workers.dev
- D1：`sange-sync`（APAC），表 `items(owner, kind, id, payload, updated_at, deleted)`
- 源码：`sync-worker/`（`wrangler.toml`、`src/index.js`、`schema.sql`）
- token：本地 `<LOCAL_APP>/deploy/sync-worker/.sync-token.txt`，**不进仓库**。
  - Pages 端只存 SHA-256 到 D1 `meta.token_sha256`；Worker 端仍是 `SYNC_TOKEN` secret。
- 接口：`POST /sync`，`Authorization: Bearer <token>`，body `{items:[{kind,id,updatedAt,deleted,payload}]}`，返回合并后全量
- 合并规则：`ON CONFLICT ... WHERE excluded.updated_at > items.updated_at`，即按条 LWW
- **已验证**：health、401、LWW、墓碑（curl 走 Clash `127.0.0.1:7897`，需加 `--ssl-no-revoke`）
- 注意：访问 workers.dev 需要代理；浏览器走系统代理，终端 curl 要手动设 `https_proxy`

### 手机端已接（v1.1+sync）

- 入口：顶部「设置」页 → 只填令牌 → 立即同步；请求 12 秒超时。
- 接口内置为 `https://YOUR-PROJECT.pages.dev/api/sync`，与 PWA 同域名；workers.dev 版本保留作备用。
- 每条记录带 `updatedAt`；删除写进 `store.deleted` 墓碑，同步成功后清空。
- 改动后 4 秒防抖自动推；打开页面自动拉；同步期间若本地又改，放弃本次回写，等下一次。
- `thoughts` 从字符串数组迁移为 `{id, text, updatedAt}`，`loadStore()` 里自动转换。
- 令牌存在 `localStorage`，明文；单机个人使用可接受。
- 已测：模拟接口的推/拉/墓碑/防抖；真实接口只测了 health 和 curl，浏览器带真 token 的往返还没跑。

待定：
1. ~~token 放哪~~ → 已定：本地文件 + 首启输入，不进仓库；
2. 同步范围（只三格数据，不含课表导入原文件）；
3. 自动同步触发频率。

## 规矩

- 上传/部署/发链接前先洗数据；线上和仓库里不能有真实待办、念头、健康、课程地点、姓名、账号。
- 看起来能点的东西必须真的能点。
- 改没有版本控制的项目前先 `git init` 或备份。
- GitHub 只在宏说“上传”时推。
