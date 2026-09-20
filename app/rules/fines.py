"""确定性罚款规则模块（单一事实源，与规则库'裁定'条目一致）。

金额不交给 LLM 计算，SQL 只取事实（分钟数/次数/小时数），此处集中推导。
"""


def late_or_early_fine(minutes: int) -> str:
    """迟到/早退罚款分档（0≤m<10→5元；[10,20)→10元；[20,30)→20元；≥30→旷工）。"""
    if minutes < 0:
        return "0 元"
    if minutes < 10:
        return "罚 5 元"
    if minutes < 20:
        return "罚 10 元"
    if minutes < 30:
        return "罚 20 元"
    return "按旷工处理"


def overtime_pay(overtime_type: str, hours: float) -> str:
    """加班补偿：周末/周日 1:1 调休优先（无法调休 200%）；法定 300% 不调休；工作日按调休。"""
    if overtime_type == "法定节假日":
        return f"{hours} 小时 × 300% 加班费，不安排调休"
    if overtime_type == "周末":
        return f"{hours} 小时，优先调休 1:1，无法调休按 200% 支付"
    return f"{hours} 小时，按工作日加班（调休）"


def makeup_fine(overdue: bool) -> str:
    return "罚 50 元" if overdue else "0 元"
