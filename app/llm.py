"""DeepSeek 模型工厂与结构化输出封装（含回退）。"""
import json
import re
from functools import lru_cache
from typing import Type, TypeVar

from langchain_deepseek import ChatDeepSeek
from pydantic import BaseModel

from .config import settings

T = TypeVar("T", bound=BaseModel)


@lru_cache(maxsize=1)
def get_llm(temperature: float = 0.0) -> ChatDeepSeek:
    """DeepSeek Chat 实例，temperature=0 保证可复现。"""
    return ChatDeepSeek(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        api_base=settings.deepseek_base_url,
        temperature=temperature,
        timeout=60,
        max_retries=2,
    )


def invoke_text(prompt: str) -> str:
    """普通文本调用。"""
    resp = get_llm().invoke(prompt)
    return resp.content if isinstance(resp.content, str) else str(resp.content)


def invoke_structured(prompt: str, model_cls: Type[T]) -> T:
    """结构化输出；优先 function-calling，失败回退到 JSON 解析。"""
    try:
        return get_llm().with_structured_output(model_cls).invoke(prompt)
    except Exception:
        raw = invoke_text(prompt + "\n\n【严格要求】只输出一个 JSON 对象，不要任何解释。")
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            raise ValueError(f"结构化输出解析失败: {raw[:200]}")
        return model_cls.model_validate(json.loads(m.group(0)))
