"""LangGraph 节点实现：受控流水线 + 多步规划执行 + 硬约束纠错。"""
import json
from datetime import date, timedelta
from typing import Any

from .state import AgentState
from ..db import executor
from ..db.schema_provider import TABLE_NAMES, schema_provider
from ..llm import invoke_structured, invoke_text
from ..memory import format_history, update_memory
from ..prompts import (
    ANSWER_PROMPT,
    PERM_CHECK_PROMPT,
    PLAN_PROMPT,
    POLICY_SYSTEM,
    RESOLVE_PROMPT,
    ROUTE_PROMPT,
    SQL_CHECK_PROMPT,
    SQL_GEN_PROMPT,
    TABLE_SELECT_PROMPT,
)
from ..rules import rule_store
from ..safety import input_guard
from ..safety.sql_validator import ALLOWED_VIEWS, SqlValidationError, validate as validate_sql
from ..schemas import GuardResult, PermCheckResult, PlanResult, ResolveResult, RouteResult, SqlCheckResult, TableSelectResult

REJECT_MSG = "抱歉，这个问题我无法处理。请围绕公司考勤制度或考勤数据提问。"


def _date_context() -> dict:
    today = date.today()
    month_start = today.replace(day=1)
    month_end = date(today.year, 12, 31) if today.month == 12 else date(today.year, today.month + 1, 1) - timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    return {
        "today": today.isoformat(),
        "month_start": month_start.isoformat(),
        "month_end": month_end.isoformat(),
        "week_start": week_start.isoformat(),
    }


def _q(state: AgentState) -> str:
    """当前问题：多步执行时用 current_question，否则用 resolved_question/user_input。"""
    return state.get("current_question") or state.get("resolved_question") or state["user_input"]


def auth_node(state: AgentState) -> dict[str, Any]:
    """身份加载（RBAC 锚点）+ 每轮重置瞬态字段。"""
    if not state.get("current_user"):
        return {"final_answer": "未登录或会话已失效，请重新登录。"}
    return {
        "resolved_question": "",
        "current_question": "",
        "steps": [],
        "step_idx": 0,
        "sub_results": [],
        "perm_blocked": False,
        "perm_note": "",
        "policy_answer": "",
        "selected_tables": [],
        "rule_types": [],
        "sql": "",
        "sql_check": {},
        "query_result": "",
        "last_error": "",
        "sql_retries": 0,
        "final_answer": "",
    }


def guard_node(state: AgentState) -> dict[str, Any]:
    user_input = state["user_input"]
    result: GuardResult = input_guard.check_input(user_input)
    safety = {"is_safe": result.is_safe, "category": result.category, "reason": result.reason}
    out: dict[str, Any] = {"safety": safety}
    if not result.is_safe:
        out["final_answer"] = REJECT_MSG
    return out


def resolve_node(state: AgentState) -> dict[str, Any]:
    """指代消解：结合历史把'他/上周'等替换为具体对象。无历史时原样返回。"""
    user_input = state["user_input"]
    history = state.get("messages", [])
    if not history:
        return {"resolved_question": user_input}
    result: ResolveResult = invoke_structured(
        RESOLVE_PROMPT.format(history=format_history(history), user_input=user_input), ResolveResult
    )
    return {"resolved_question": result.resolved_question.strip() or user_input}


def perm_check_node(state: AgentState) -> dict[str, Any]:
    """越权早判：普通员工问他人/全员 → 阻断或标记权限说明（管理员跳过）。"""
    user = state.get("current_user", {})
    if user.get("data_scope") != "self":
        return {"perm_blocked": False, "perm_note": ""}
    question = state.get("resolved_question") or state["user_input"]
    result: PermCheckResult = invoke_structured(
        PERM_CHECK_PROMPT.format(
            self_name=user.get("display_name", ""),
            employee_id=user.get("employee_id"),
            question=question,
        ),
        PermCheckResult,
    )
    if result.is_cross_scope:
        if result.kind == "explicit_other":
            return {
                "perm_blocked": True,
                "final_answer": "抱歉，你是普通员工，只能查看本人的数据，无权查询他人的信息。",
            }
        # all_employees：不阻断，但答案需明示权限边界
        return {
            "perm_blocked": False,
            "perm_note": "（注意：你是普通员工，以下仅为你本人的数据，无权查看全员/他人。）",
        }
    return {"perm_blocked": False, "perm_note": ""}


def plan_node(state: AgentState) -> dict[str, Any]:
    """规划器：把问题拆解为可独立执行的子问题（简单问题就一个）。"""
    question = state.get("resolved_question") or state["user_input"]
    plan: PlanResult = invoke_structured(PLAN_PROMPT.format(user_input=question), PlanResult)
    steps = [s.strip() for s in plan.sub_questions if s.strip()] or [question]
    return {"steps": steps, "step_idx": 0, "sub_results": []}


def step_begin_node(state: AgentState) -> dict[str, Any]:
    """进入下一个子问题：设置 current_question + 重置本步瞬态。"""
    steps = state.get("steps", [])
    idx = state.get("step_idx", 0)
    q = steps[idx] if idx < len(steps) else state["user_input"]
    return {
        "current_question": q,
        "policy_answer": "",
        "selected_tables": [],
        "sql": "",
        "sql_check": {},
        "query_result": "",
        "last_error": "",
        "sql_retries": 0,
        "final_answer": "",
    }


def route_node(state: AgentState) -> dict[str, Any]:
    user_input = _q(state)
    result: RouteResult = invoke_structured(
        ROUTE_PROMPT.format(rule_type_list=" / ".join(rule_store.RULE_TYPE_LIST), user_input=user_input),
        RouteResult,
    )
    kw_types = rule_store.select_by_keywords(user_input)
    rule_types = sorted(set(result.rule_types) | set(kw_types))
    return {"intent": result.intent, "rule_types": rule_types}


def rule_select_node(state: AgentState) -> dict[str, Any]:
    return {"selected_rules": rule_store.get_rules(state.get("rule_types", []))}


def policy_node(state: AgentState) -> dict[str, Any]:
    user_input = _q(state)
    prompt = POLICY_SYSTEM.format(selected_rules=state.get("selected_rules", "")) + f"\n用户问题：{user_input}\n回答："
    return {"policy_answer": invoke_text(prompt)}


def _scope_hint(user: dict) -> str:
    if user.get("data_scope") == "self" and user.get("employee_id"):
        return f"你只能查询本人数据，强制附加 employee_id = {user['employee_id']} 条件，禁止查他人。"
    return "你是管理员，可查询全局数据。"


def schema_select_node(state: AgentState) -> dict[str, Any]:
    """阶段一选表：结果硬约束——只保留白名单内的视图名。"""
    user_input = _q(state)
    sel: TableSelectResult = invoke_structured(
        TABLE_SELECT_PROMPT.format(table_overview=schema_provider.get_simple_schema(), user_input=user_input),
        TableSelectResult,
    )
    tables = [t for t in sel.tables if t in TABLE_NAMES]
    return {"selected_tables": tables}


def sql_generate_node(state: AgentState) -> dict[str, Any]:
    user = state.get("current_user", {})
    ctx = _date_context()
    user_input = _q(state)
    if state.get("last_error"):
        user_input = f"{user_input}\n【上次错误，必须修正】{state['last_error']}"

    prompt = SQL_GEN_PROMPT.format(
        data_scope=user.get("data_scope", "self"),
        employee_id=user.get("employee_id", "NULL"),
        scope_hint=_scope_hint(user),
        today=ctx["today"],
        month_start=ctx["month_start"],
        month_end=ctx["month_end"],
        week_start=ctx["week_start"],
        schema=schema_provider.get_detail_schema(state.get("selected_tables", [])),
        user_input=user_input,
    )
    sql = invoke_text(prompt).strip().strip("`")
    if sql.lower().startswith("sql"):
        sql = sql[3:].strip()
    return {"sql": sql, "last_error": ""}


def sql_validate_node(state: AgentState) -> dict[str, Any]:
    sql = state.get("sql", "")
    from ..config import settings

    try:
        final_sql, static_report = validate_sql(sql, settings.max_rows)
        static_result = "通过：" + json.dumps(static_report, ensure_ascii=False)
    except SqlValidationError as e:
        msg = str(e)
        if "表不在白名单" in msg:
            msg += f"；可用视图仅限：{', '.join(sorted(ALLOWED_VIEWS))}"
        return {
            "sql_check": {"passed": False, "reason": msg},
            "last_error": msg,
            "sql_retries": state.get("sql_retries", 0) + 1,
        }

    check: SqlCheckResult = invoke_structured(
        SQL_CHECK_PROMPT.format(static_result=static_result, sql=final_sql), SqlCheckResult
    )
    if not check.is_read_only:
        return {
            "sql_check": {"passed": False, "reason": check.reason},
            "last_error": f"语义校验未通过：{check.reason}",
            "sql_retries": state.get("sql_retries", 0) + 1,
        }
    return {"sql": final_sql, "sql_check": {"passed": True, "reason": check.reason}}


def sql_execute_node(state: AgentState) -> dict[str, Any]:
    sql = state.get("sql", "")
    print(f"[SQL执行] {sql}", flush=True)
    try:
        result = executor.execute(sql)
        return {"query_result": json.dumps(result, ensure_ascii=False, default=str)}
    except Exception as e:
        return {
            "query_result": "",
            "last_error": f"执行失败：{e}",
            "sql_retries": state.get("sql_retries", 0) + 1,
        }


def step_collect_node(state: AgentState) -> dict[str, Any]:
    """收集当前子问题结果，步进。"""
    sub = {
        "question": state.get("current_question", ""),
        "query_result": state.get("query_result", ""),
        "policy_answer": state.get("policy_answer", ""),
    }
    sub_results = list(state.get("sub_results", [])) + [sub]
    return {"sub_results": sub_results, "step_idx": state.get("step_idx", 0) + 1}


def answer_node(state: AgentState) -> dict[str, Any]:
    # 越权阻断：直接返回预设话术
    if state.get("perm_blocked"):
        return {"final_answer": state.get("final_answer") or "抱歉，你无权查询该信息。"}

    user_input = state.get("resolved_question") or state["user_input"]
    sub_results = state.get("sub_results", [])
    selected_rules = state.get("selected_rules") or rule_store.get_rules([], include_verdicts=True)

    if state.get("intent") == "chat":
        return {"final_answer": invoke_text(f"请礼貌简短回应用户的闲聊：{user_input}")}

    # 校验/执行失败且重试耗尽 → 如实告知
    if state.get("last_error") and not any(s.get("query_result") for s in sub_results) and state.get("sql_retries", 0) >= 2:
        err = state["last_error"]
        hint = "（SQL 引用了不存在的表，请换一种问法）" if "表不在白名单" in err else "（请换一种更明确的问法）"
        return {"final_answer": f"抱歉，本次查询未成功：{err}{hint}"}

    # 合并多步子结果
    parts = []
    for sub in sub_results:
        seg = []
        if sub.get("policy_answer"):
            seg.append(f"【{sub['question']} 规则】{sub['policy_answer']}")
        if sub.get("query_result"):
            seg.append(f"【{sub['question']} 查询结果】{sub['query_result']}")
        if seg:
            parts.append("\n".join(seg))
    combined = "\n\n".join(parts) if parts else "（本次未查询数据库）"

    prompt = ANSWER_PROMPT.format(
        selected_rules=selected_rules or "（无）",
        query_result=combined,
        user_input=user_input,
    )
    final = invoke_text(prompt)
    perm_note = state.get("perm_note", "")
    if perm_note:
        final = perm_note + "\n\n" + final
    return {"final_answer": final}


def memory_node(state: AgentState) -> dict[str, Any]:
    messages = list(state.get("messages", []))
    messages.append({"role": "user", "content": state["user_input"]})
    messages.append({"role": "assistant", "content": state.get("final_answer", "")})
    state["messages"] = messages
    return update_memory(state)
