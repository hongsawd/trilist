# 托管同步服务

管理员部署服务，使用者只填个人令牌。每个令牌映射一个独立 `owner`；同一个人多台设备使用同一令牌。数据库只存令牌的 SHA-256 摘要。系统没有开放注册，令牌由管理员发放。

## 部署与迁移

1. 给 Cloudflare Worker 或 Pages 绑定 D1，执行 `schema.sql`。已有数据库只新增 `sync_users`，不删除原表或旧数据。
2. Worker 使用 `src/index.js`；Pages 使用同一文件作为 `_worker.js`。必须先迁移数据库，再切换服务版本。
3. 保留现有 `SYNC_TOKEN` 或 `meta.token_sha256`，旧个人令牌继续访问原有空间。不要把旧个人令牌发给其他人。
4. 托管手机构建：

   ```bash
   python prepare-hosted.py --url https://YOUR-PROJECT.pages.dev/api/sync --output /path/outside/repository
   ```

   输出只包含页面、共享规则、公开服务地址和服务处理器，不包含令牌、个人数据或设备缓存。Android 构建时复制 `index.html` 和 `shared/` 到 `www/`，不要将 `_worker.js` 放进 APK。

## 发放与撤销令牌

```bash
python issue-token.py --private-dir /path/to/private-tokens
```

工具在仓库外生成凭证 JSON 和注册 SQL，不在终端打印令牌。将生成的 SQL 导入 D1，再私下把 JSON 中的令牌交给对应使用者。令牌文件不要上传或放入安装包。需要撤销时，将对应 `sync_users` 行的 `enabled` 设为 0。

维护者的完整顺序是：

1. 运行上面的生成工具，在私有目录得到一对同名的 `.json` 和 `.sql` 文件。
2. 在已经登录 Cloudflare 的环境，把 SQL 登记到实际服务绑定的数据库：`npx wrangler d1 execute YOUR_DATABASE --remote --file /private/path/user-id.sql`。
3. 登记成功后，从 JSON 读取 `token`，通过私下渠道发给这一位使用者。不要把整个私有目录或数据库信息发出去。
4. 使用者只需在安装好的软件里填写令牌，不需要运行上述命令。其第二台设备填同一枚令牌。

仅生成 JSON 而未执行登记 SQL 的令牌尚未开通，会返回 401。若遗失令牌，可以撤销旧记录并重新为同一空间发放新凭证；不要把其他人的令牌当作替代。

不要给所有使用者发同一枚令牌，那会使他们共用同一份清单。

## 同步规则

- 身份只来自服务端验证过的令牌，客户端不能指定 `owner`。
- 记录以 `owner + kind + id` 隔离，较新的 `updatedAt` 覆盖较旧版本；同一时间戳删除优先。
- 删除墓碑保留；显式撤销必须产生更新的版本。
- 客户端仅上传变化记录；未变化的前台轮询请求发送空数组，服务端返回当前空间的完整快照。
- 本地修改后约 0.35 秒发起同步，前台每 2 秒检查。网络失败从 3 秒开始退避，最长 30 秒。
- 首次连接先在本机备份，非破坏性合并两端内容；同编号不同内容改用新编号分别保留。
- 返回格式异常时保留本机数据；同步期间继续编辑会再补一轮。切换令牌会先备份并清空当前显示，再读取新空间。
- 凭证错误、被撤销或未登记返回 401。请求验证失败不写入部分数据。

## 验收

```bash
node test_shared_sync.mjs
python -X utf8 test_cross_device.py
```

在项目根目录执行，使用内存数据库、临时浏览器和测试令牌，不访问真实服务。
