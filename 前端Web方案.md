# 前端 Web 专项方案（纯 HTML，demo 阶段）

> 关联文档：《技术方案.md》第十一节。
> **定位**：demo 阶段**不单独开发前端**——纯 HTML/CSS/原生 JS，无框架、无 npm、无构建；静态文件与后端代码**同目录**（`web/`），由 FastAPI 静态托管。
> 范围：登录 + 聊天 + SSE 流式 + 进度 + 引用 + 身份标签，最小可用即可。

---

## 一、原则与范围

| 项 | 决策 |
|---|---|
| 技术栈 | 纯 HTML5 + CSS3 + 原生 JS（ES6），**无框架、无构建** |
| 位置 | 与后端代码同目录：`web/`（`index.html` + `style.css` + `main.js`） |
| 后端 | FastAPI 托管静态 + `/api/login` + `/api/chat`(SSE) + `/api/sessions` |
| 流式 | `fetch` POST + `ReadableStream` 手动解析 SSE |
| 范围 | 登录、聊天、流式渲染、进度步骤、引用卡片、身份标签、会话切换 |

**demo 阶段明确不做**：独立前端工程/路由/组件库、图表可视化、多主题、复杂鉴权（OAuth）、国际化。

---

## 二、目录结构（与代码同目录）

```
E:\pycharm_python_project\InterviewAgentSql\
├── app/                  # 后端（LangGraph、safety、db、rules…）
│   └── ...
├── web/                  # 纯 HTML 前端（同目录，无独立工程）
│   ├── index.html        # 单页：登录视图 + 聊天视图
│   ├── style.css         # 样式
│   └── main.js           # 原生 JS：登录 / SSE 流式 / DOM 渲染
├── main.py               # FastAPI 入口：静态托管 + API + SSE
├── requirements.txt
└── .env
```

> 无 `frontend/` 独立目录、无 `package.json`、无构建产物。

---

## 三、总体架构

```
浏览器(纯HTML/JS) ──HTTP/SSE──▶ FastAPI(main.py) ──astream──▶ LangGraph ──▶ PostgreSQL
```

- 前端只调 FastAPI，不直连数据库、不接触 `DEEPSEEK_API_KEY`。
- FastAPI 用 `StaticFiles(directory="web", html=True)` 托管静态文件，`/api/*` 走接口。

---

## 四、页面设计（单页 index.html，两个视图切换）

### 4.1 登录视图
- 用户名 + 密码输入框；快捷登录按钮（zhangsan / lisi / wangwu / admin）。
- 调 `POST /api/login` → 成功存 `localStorage`（user_id/token/role/data_scope/display_name）→ 切到聊天视图。
- 失败提示"用户名或密码错误"。

### 4.2 聊天视图
```
┌────────────────────────────────────────────────────────────┐
│ 顶栏  张三 [普通员工·仅本人]          [退出登录]              │
├──────────────┬─────────────────────────────────────────────┤
│ 会话列表      │  消息区（流式渲染）                           │
│ [新建对话]    │  用户：我这个月迟到了几次？                    │
│  会话1       │  AI：[生成SQL… 查询数据库…]                   │
│  会话2       │     你本月迟到 3 次：…                        │
│              │     ▸引用：迟到罚款分档 · 数据来源             │
│              │  [输入框...................] [发送]           │
└──────────────┴─────────────────────────────────────────────┘
```

交互要点：
- **流式文本**：`token` 事件逐块 `textContent += delta` 追加（**禁用 innerHTML** 防 XSS）。
- **进度步骤**：`status` 事件切换步骤条（理解问题→检索规则→生成SQL→查询数据库→生成回答）。
- **引用卡片**：`citation` 事件渲染可折叠引用（条款 title+序号 / 表+结果摘要）。
- **身份标签**：`data_scope=self` 显示"仅本人"，`all` 显示"全局"。
- **会话切换**：`GET /api/sessions` 拉列表，点击切换 thread_id 加载历史。
- **停止生成**：`AbortController` 中断当前 fetch。

---

## 五、接口协议

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/login` | POST | `{username, password}` → `{user_id, display_name, role, data_scope, employee_id, token}` |
| `/api/chat` | POST（SSE） | `{message, thread_id?}` + `Authorization: Bearer <token>` → SSE 流 |
| `/api/sessions` | GET | 当前 user_id 的会话列表 |
| `/api/sessions/{thread_id}` | GET | 会话历史（回放） |

### SSE 事件类型（`data:` 行 JSON）

| event | payload | 前端动作 |
|---|---|---|
| `status` | `{node, label}` | 进度步骤 |
| `token` | `{delta}` | 增量文本追加 |
| `citation` | `{type: "rule"/"data", items}` | 引用卡片 |
| `result` | `{final_answer, citations, query_result_summary}` | 结束落盘 |
| `error` | `{message, boundary?}` | 错误/边界话术（按 boundary 换样式） |

---

## 六、SSE 流式解析（原生 JS，POST + ReadableStream）

原生 `EventSource` 只支持 GET、无法带 `Authorization` 头，故用 `fetch` POST + 流式读取，手动按空行切分 `data:`：

```
const res = await fetch('/api/chat', { method:'POST', headers, body, signal });
const reader = res.body.getReader();
const decoder = new TextDecoder();
let buf = '';
while (true) {
  const {done, value} = await reader.read();
  if (done) break;
  buf += decoder.decode(value, {stream:true});
  // 按 "\n\n" 切事件，解析每个 data: 行的 JSON，分发给 status/token/citation/result/error 处理器
}
```

> 后端用 `sse-starlette` 的 `EventSourceResponse` 产出标准 SSE，前端做最小解析器即可（约 20 行）。

---

## 七、关键实现要点（原生 JS）

1. **登录态**：`localStorage.setItem('auth', JSON.stringify({...}))`；每次请求带 `Authorization` 头。
2. **防 XSS**：所有动态内容（AI 文本、引用、错误）用 `textContent` / `createElement` 渲染，**永不 innerHTML 拼接用户/模型内容**。
3. **状态**：一个全局 `state` 对象（当前 user、thread_id、messages、streaming），不引框架。
4. **渲染**：消息列表为 DOM 容器，新增消息 `createElement` 追加；流式只改最后一个 AI 气泡的 `textContent`。
5. **错误处理**：`fetch` 失败/断流 → 提示重试；`error` 事件按 `boundary` 字段换样式（工资/缺席/越权）。

---

## 八、安全

- 密码哈希校验在后端（演示 sha256 / 生产 bcrypt），前端只提交明文一次。
- `password_hash` 等敏感列服务端不返回。
- 越权拦截在**服务端**（校验器 + 只读角色 + RLS），前端只做展示，不做信任。
- 流式内容纯文本渲染防 XSS；生产上 HTTPS。

---

## 九、运行与部署

| 环境 | 方式 |
|---|---|
| 本地 | `uvicorn main:app --reload` → 打开 `http://127.0.0.1:8000` |
| 演示 | 同上（静态由 FastAPI 托管，零构建） |
| 生产（可选） | Nginx 反代 `/api` + 托管静态，或直接 FastAPI + HTTPS |

---

## 十、范围声明（demo 阶段）

- 前端为**最小可用单页**，不单独成立前端工程、不引入构建链与组件库。
- 若后续要正式产品化，再评估 Vue3/React + 独立工程（见历史版本方案），当前 demo 保持"纯 HTML、同目录、零构建"。
