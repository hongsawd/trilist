# 三格同步服务模板

同步服务是可选组件。三格在本地不联网也能使用；需要多设备同步时，再部署这一套。

## 方案 A：Cloudflare Worker + D1

1. 在 Cloudflare 创建 D1 数据库，并执行 `schema.sql`。
2. 复制模板配置：

   ```bash
   cp wrangler.example.toml wrangler.toml
   ```

3. 把 `wrangler.toml` 里的 `database_id` 换成自己的 D1 ID。
4. 生成一段长随机令牌：

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

5. 写入 Worker secret：

   ```bash
   npx wrangler secret put SYNC_TOKEN
   ```

6. 部署：

   ```bash
   npx wrangler deploy
   ```

7. 在三格的“云端同步”里填写服务地址和同一个令牌。

## 方案 B：Cloudflare Pages Functions

把 [`pages-worker.example.js`](pages-worker.example.js) 复制为 Pages 输出目录里的 `_worker.js`，在 Pages 项目中配置 `DB` 绑定和 `SYNC_TOKEN` secret。服务地址形如：

```text
https://YOUR-PROJECT.pages.dev/api/sync
```

`wrangler.toml`、`.dev.vars` 和 `.sync-token.txt` 都已加入忽略规则，真实数据库 ID 与令牌不会进入仓库。

## 数据规则

- 每种条目使用 `kind + id` 标识。
- `updatedAt` 较新的版本覆盖旧版本。
- 删除会写墓碑，避免另一台离线设备把条目恢复。
- 默认只有一个 `SYNC_OWNER=default` 数据空间；多用户隔离尚未实现。
