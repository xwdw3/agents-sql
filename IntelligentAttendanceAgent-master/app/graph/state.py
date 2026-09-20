"""LangGraph 状态定义。"""
from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    messages: list[Any]          # 近端历史消息
    user_input: str              # 本轮原始用户输入
    resolved_question: str       # 指代消解后的完整问题
    current_question: str        # 当前正在执行的子问题（多步）
    steps: list[str]             # 拆解后的子问题列表
    step_idx: int                # 当前子问题下标
    sub_results: list[dict]      # 各子问题结果
    current_user: dict           # {user_id, display_name, role, data_scope, employee_id, is_admin}
    perm_blocked: bool           # 是否越权被阻断
    perm_note: str               # 权限说明（全员类问题时的提示）
    safety: dict                 # 输入护栏结果
    intent: str                  # policy / data / mixed / chat
    rule_types: list[str]        # 命中的规则类型
    selected_rules: str          # 选中的规则内容
    selected_tables: list[str]   # 阶段一选中的相关表（视图）
    policy_answer: str           # 制度问答结果
    sql: str                     # 生成的 SQL
    sql_check: dict              # SQL 校验结果
    sql_retries: int             # SQL 修复重试计数
    last_error: str              # 上次执行/校验错误
    query_result: str            # 查询结果（JSON 字符串）
    final_answer: str            # 最终答案
    slots: dict                  # 实体槽位
