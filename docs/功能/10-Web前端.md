# 功能：Web 前端（纯 HTML）

## 定位
纯 HTML/CSS/原生 JS 的单页对话界面（无框架、无构建），与后端同目录，由 FastAPI 静态托管。

## 涉及文件
- `web/index.html` / `web/style.css` / `web/main.js`
- `main.py` — `StaticFiles` 托管 + `/api/login`、`/api/chat`(SSE)、`/api/sessions`

## 核心逻辑
1. **登录**：`POST /api/login` → 存 `localStorage`，切到聊天视图（`hidden` 属性切换，CSS 已加 `[hidden]{display:none!important}`）。
2. **流式聊天**：`fetch` POST `/api/chat` + `ReadableStream` 手动解析 SSE（`\r\n` 规范化为 `\n` 后按 `\n\n` 切事件）。
3. **思考链路**：`status` 事件累积渲染成链路（当前 `⏳`、完成 `✓`），结束显示 `✓ 回答完毕`；内部节点（memory）不展示。
4. **历史会话**：点击会话项 → `GET /api/sessions/{id}` 回放历史。
5. **美化输出**：安全 markdown 渲染（先 HTML 转义，再 `**加粗**`/`- 列表`/换行），流式中纯文本、结束时转富文本。

## 关键设计点
- **防 XSS**：动态内容一律 `textContent` 或先转义再渲染，禁 `innerHTML` 拼未转义内容。
- **缓存版本号**：`style.css?v=N`、`main.js?v=N` 强制刷新。
- 切换会话/新建对话时**清空思考链路**。

## 依赖
- `main.py`（SSE 事件：session/status/token/result/error）。
