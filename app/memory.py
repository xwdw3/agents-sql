"""记忆：滑动窗口截断。

多轮指代消解（"他呢" → "张三早退几次"）由 `resolve_node` 用 LLM 结构化输出完成，
不在此处做硬编码姓名/时间词的子串匹配——硬编码会与库脱节、无法处理代词、且易误匹配。
"""
from typing import Any

MAX_HISTORY = 8


def update_memory(state: dict[str, Any]) -> dict[str, Any]:
    """截断近端消息，保留最近 MAX_HISTORY 条。"""
    messages = state.get("messages", [])
    return {"messages": messages[-MAX_HISTORY:]}


def format_history(messages: list[Any], limit: int = 6) -> str:
    """把最近 N 条消息格式化为文本，供指代消解提示使用。"""
    lines = []
    for m in messages[-limit:]:
        if isinstance(m, dict):
            role = m.get("role", "")
            content = m.get("content", "")
        else:
            role, content = "", str(m)
        lines.append(f"{role}: {content}")
    return "\n".join(lines) or "（无历史）"
