"""用户输入安全护栏：规则快筛 + LLM 结构化精判。"""
import re

from ..llm import invoke_structured
from ..prompts import GUARD_PROMPT
from ..schemas import GuardResult

# 规则黑名单（确定性，零成本）
BLACKLIST_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"忽略(以上|之前)?(所有)?指令",
    r"你现在是|你扮演|你是系统|系统提示",
    r"system\s*prompt",
    r"\b(drop|truncate|delete|insert|update)\s+(table|from|into)",
    r"show\s+tables|information_schema",
    r"身份证|银行卡|工资条|他人密码|password",
]
MAX_LEN = 1000


def check_input(user_input: str) -> GuardResult:
    """返回 GuardResult；is_safe=False 表示拒绝进入模型。"""
    text = user_input.strip()
    if not text:
        return GuardResult(is_safe=False, category="off_topic", reason="空输入")
    if len(text) > MAX_LEN:
        return GuardResult(is_safe=False, category="harmful", reason="输入过长")

    for pattern in BLACKLIST_PATTERNS:
        if re.search(pattern, text, re.I):
            return GuardResult(is_safe=False, category="prompt_injection", reason=f"命中规则黑名单: {pattern}")

    # LLM 精判（结构化输出）
    return invoke_structured(GUARD_PROMPT.format(user_input=text), GuardResult)
