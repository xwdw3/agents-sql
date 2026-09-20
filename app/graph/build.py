"""StateGraph 组装：多步规划执行 + 硬约束重试。"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ..config import settings
from .nodes import (
    answer_node,
    auth_node,
    guard_node,
    memory_node,
    perm_check_node,
    plan_node,
    policy_node,
    resolve_node,
    route_node,
    rule_select_node,
    schema_select_node,
    sql_execute_node,
    sql_generate_node,
    sql_validate_node,
    step_begin_node,
    step_collect_node,
)
from .state import AgentState


def _get_checkpointer():
    """优先 PostgresSaver（app_rw 连接池），失败回退内存。"""
    try:
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool
        from langgraph.checkpoint.postgres import PostgresSaver

        pool = ConnectionPool(
            settings.rw_psycopg_dsn,
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
            min_size=1,
            max_size=5,
            open=True,
        )
        saver = PostgresSaver(pool)
        saver.setup()
        return saver
    except Exception:
        return MemorySaver()


def _guard_next(state: AgentState) -> str:
    return END if not state.get("safety", {}).get("is_safe", False) else "resolve"


def _perm_next(state: AgentState) -> str:
    return "answer" if state.get("perm_blocked") else "plan"


def _route_next(state: AgentState) -> str:
    intent = state.get("intent", "chat")
    if intent == "chat":
        return "step_collect"
    if intent in ("policy", "mixed"):
        return "rule_select"
    return "schema_select"  # data


def _policy_next(state: AgentState) -> str:
    return "schema_select" if state.get("intent") == "mixed" else "step_collect"


def _validate_next(state: AgentState) -> str:
    if state.get("sql_check", {}).get("passed"):
        return "sql_execute"
    if state.get("sql_retries", 0) < 3:
        return "sql_generate"
    return "step_collect"


def _execute_next(state: AgentState) -> str:
    if state.get("last_error") and state.get("sql_retries", 0) < 3:
        return "sql_generate"
    return "step_collect"


def _step_next(state: AgentState) -> str:
    idx = state.get("step_idx", 0)
    steps = state.get("steps", [])
    return "step_begin" if idx < len(steps) else "answer"


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("auth", auth_node)
    g.add_node("guard", guard_node)
    g.add_node("resolve", resolve_node)
    g.add_node("perm_check", perm_check_node)
    g.add_node("plan", plan_node)
    g.add_node("step_begin", step_begin_node)
    g.add_node("route", route_node)
    g.add_node("rule_select", rule_select_node)
    g.add_node("policy", policy_node)
    g.add_node("schema_select", schema_select_node)
    g.add_node("sql_generate", sql_generate_node)
    g.add_node("sql_validate", sql_validate_node)
    g.add_node("sql_execute", sql_execute_node)
    g.add_node("step_collect", step_collect_node)
    g.add_node("answer", answer_node)
    g.add_node("memory", memory_node)

    g.add_edge(START, "auth")
    g.add_edge("auth", "guard")
    g.add_conditional_edges("guard", _guard_next, {"resolve": "resolve", END: END})
    g.add_edge("resolve", "perm_check")
    g.add_conditional_edges("perm_check", _perm_next, {"plan": "plan", "answer": "answer"})
    g.add_edge("plan", "step_begin")
    g.add_edge("step_begin", "route")
    g.add_conditional_edges("route", _route_next, {
        "rule_select": "rule_select",
        "schema_select": "schema_select",
        "step_collect": "step_collect",
    })
    g.add_edge("rule_select", "policy")
    g.add_conditional_edges("policy", _policy_next, {"schema_select": "schema_select", "step_collect": "step_collect"})
    g.add_edge("schema_select", "sql_generate")
    g.add_edge("sql_generate", "sql_validate")
    g.add_conditional_edges("sql_validate", _validate_next, {
        "sql_execute": "sql_execute",
        "sql_generate": "sql_generate",
        "step_collect": "step_collect",
    })
    g.add_conditional_edges("sql_execute", _execute_next, {"sql_generate": "sql_generate", "step_collect": "step_collect"})
    g.add_conditional_edges("step_collect", _step_next, {"step_begin": "step_begin", "answer": "answer"})
    g.add_edge("answer", "memory")
    g.add_edge("memory", END)

    return g.compile(checkpointer=_get_checkpointer())


# 模块级单例
graph = build_graph()
