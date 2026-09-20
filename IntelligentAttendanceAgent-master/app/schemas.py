"""LLM 结构化输出的 Pydantic 模型。"""
from pydantic import BaseModel, Field


class GuardResult(BaseModel):
    is_safe: bool = Field(description="输入是否安全")
    category: str = Field(description="normal / prompt_injection / harmful / off_topic / sensitive_request")
    reason: str = Field(description="判定理由")


class RouteResult(BaseModel):
    intent: str = Field(description="policy / data / mixed / chat")
    rule_types: list[str] = Field(default_factory=list, description="命中的制度规则类型（仅制度/混合需要）")


class SqlCheckResult(BaseModel):
    is_read_only: bool = Field(description="SQL 是否只读且安全")
    risk_level: str = Field(description="low / medium / high")
    reason: str = Field(description="判定理由")


class TableSelectResult(BaseModel):
    tables: list[str] = Field(description="与用户问题相关的视图名称列表")


class ResolveResult(BaseModel):
    resolved_question: str = Field(description="结合历史完成指代消解后的完整问题（如'他'→具体姓名、'上周'→具体时间）")


class PlanResult(BaseModel):
    sub_questions: list[str] = Field(description="拆解后的子问题列表；简单问题只含一个元素（等于原问题）")


class PermCheckResult(BaseModel):
    is_cross_scope: bool = Field(description="是否越权（查他人/查全员，而非仅本人）")
    kind: str = Field(description="explicit_other / all_employees / self")
    reason: str = Field(description="判定说明")

