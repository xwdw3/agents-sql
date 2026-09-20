# 功能：LangGraph 多步编排（Graph）

## 定位
受控流水线 + **多步规划执行**：把复杂问题拆成子问题逐个执行，再合并对比；安全敏感步骤用确定性节点，不能被模型跳过。

## 涉及文件
- `app/graph/state.py` — `AgentState`（TypedDict）
- `app/graph/nodes.py` — 全部节点函数
- `app/graph/build.py` — `StateGraph` 组装 + checkpointer

## 核心逻辑（节点流）
```
auth → guard → resolve → plan → [循环] → answer → memory
循环：step_begin → route → (rule_select→policy | schema_select→sql_generate→sql_validate→sql_execute) → step_collect
```

| 节点 | 职责 |
|---|---|
| `auth` | 身份加载 + 每轮重置瞬态 |
| `guard` | 输入护栏 |
| `resolve` | 指代消解 |
| `plan` | **拆解子问题**（`PlanResult.sub_questions`） |
| `step_begin` | 设置 `current_question`，重置本步瞬态 |
| `route` | 子问题意图+规则类型 |
| `rule_select/policy` | 制度分支 |
| `schema_select/sql_generate/sql_validate/sql_execute` | 数据分支（两阶段选表+SQL+校验+执行） |
| `step_collect` | 汇总子结果，`step_idx++` |
| `answer` | **合并对比子结果** + 规则 + 引用 |
| `memory` | 滑动窗口（内部，不展示） |

## 关键设计点
- **硬约束纠错环**：`sql_validate` 失败 → 结构化回填错误（含可用视图列表）→ 回 `sql_generate` 重生成，最多 3 次；`sql_execute` 失败同样回喂。
- **checkpointer**：`PostgresSaver`（app_rw 连接池 `autocommit=True + dict_row`），失败回退 `MemorySaver`。
- 所有 LLM 节点 `temperature=0`。

## 依赖
- `app/safety`、`app/db`、`app/rules`、`app/llm`、`app/memory`、`app/schemas`、`app/prompts`。
