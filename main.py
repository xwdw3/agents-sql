"""FastAPI 入口：纯 HTML 静态托管 + /api/login + /api/chat(SSE) + /api/sessions。

支持两种启动方式：
1) PyCharm 直接 Run 本文件（__main__ 中 uvicorn.run(app)，host/port 可调）；
2) 命令行：uvicorn main:app --reload
"""
import asyncio
import json
import threading
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.auth import login, resolve_user
from app.graph.build import graph
from app.session import create_session, delete_session, get_session, list_sessions

# 基于文件绝对路径定位 web 目录（避免 PyCharm 工作目录不一致找不到静态文件）
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="考勤问答 Agent")

_NODE_LABELS = {
    "auth": "校验身份",
    "guard": "安全审查",
    "resolve": "理解上下文",
    "perm_check": "权限校验",
    "plan": "规划任务",
    "step_begin": "执行子问题",
    "route": "理解问题",
    "rule_select": "检索制度规则",
    "schema_select": "选择相关表",
    "policy": "生成制度答案",
    "sql_generate": "生成 SQL",
    "sql_validate": "校验 SQL",
    "sql_execute": "查询数据库",
    "step_collect": "汇总子结果",
    "answer": "生成回答",
    "memory": "更新记忆",
}

# 内部节点：不在思考链路中展示
_SKIP_NODES = {"memory"}


class LoginReq(BaseModel):
    username: str
    password: str


class ChatReq(BaseModel):
    message: str
    thread_id: Optional[str] = None


def _resolve_user(request: Request) -> dict:
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    user = resolve_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或会话已失效")
    return user


@app.post("/api/login")
def api_login(req: LoginReq):
    user = login(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return user


@app.get("/api/sessions")
def api_sessions(request: Request):
    user = _resolve_user(request)
    return {"sessions": list_sessions(user["user_id"])}


@app.get("/api/sessions/{thread_id}")
def api_session_history(thread_id: str, request: Request):
    """返回某会话的历史消息（从 checkpointer 读图状态）。"""
    user = _resolve_user(request)
    if not get_session(user["user_id"], thread_id):
        raise HTTPException(status_code=403, detail="无权访问该会话")
    state = graph.get_state({"configurable": {"thread_id": thread_id}})
    values = state.values or {}
    history = [
        {"role": m.get("role"), "content": m.get("content")}
        for m in values.get("messages", [])
        if isinstance(m, dict) and m.get("role") in ("user", "assistant")
    ]
    return {"history": history}


@app.delete("/api/sessions/{thread_id}")
def api_delete_session(thread_id: str, request: Request):
    """删除会话 + 清空其 LangGraph checkpoint 记录。"""
    user = _resolve_user(request)
    if not delete_session(user["user_id"], thread_id):
        raise HTTPException(status_code=404, detail="会话不存在或无权删除")
    return {"ok": True}


@app.post("/api/chat")
async def api_chat(req: ChatReq, request: Request):
    user = _resolve_user(request)
    if req.thread_id:
        thread_id = req.thread_id
        if not get_session(user["user_id"], thread_id):
            raise HTTPException(status_code=403, detail="无权访问该会话")
    else:
        thread_id = str(uuid.uuid4())
        create_session(user["user_id"], thread_id, title=req.message.strip()[:30] or None)

    config = {"configurable": {"thread_id": thread_id, "user_id": user["user_id"]}}
    inputs = {"user_input": req.message, "current_user": user}
    q: asyncio.Queue = asyncio.Queue()

    def runner() -> None:
        final_answer = ""
        try:
            for event in graph.stream(inputs, config, stream_mode="updates"):
                for node_name, upd in event.items():
                    if node_name in _SKIP_NODES:
                        continue
                    label = _NODE_LABELS.get(node_name, node_name)
                    q.put_nowait({
                        "type": "status",
                        "data": json.dumps({"node": node_name, "label": label}, ensure_ascii=False),
                    })
                    if isinstance(upd, dict) and "final_answer" in upd:
                        final_answer = upd["final_answer"]
        except Exception as e:  # noqa: BLE001
            q.put_nowait({"type": "error", "data": json.dumps({"message": str(e)}, ensure_ascii=False)})
            return
        q.put_nowait({"type": "final", "answer": final_answer})

    threading.Thread(target=runner, daemon=True).start()

    async def event_gen():
        yield {"event": "session", "data": json.dumps({"thread_id": thread_id}, ensure_ascii=False)}
        while True:
            item = await q.get()
            if item["type"] == "status":
                yield {"event": "status", "data": item["data"]}
            elif item["type"] == "error":
                yield {"event": "error", "data": item["data"]}
                break
            elif item["type"] == "final":
                answer = item["answer"] or ""
                for i in range(0, len(answer), 24):
                    yield {
                        "event": "token",
                        "data": json.dumps({"delta": answer[i : i + 24]}, ensure_ascii=False),
                    }
                yield {"event": "result", "data": json.dumps({"final_answer": answer}, ensure_ascii=False)}
                break

    return EventSourceResponse(event_gen())


# 静态托管必须在 API 路由之后挂载（catch-all）
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    # PyCharm 直接 Run 本文件时生效
    uvicorn.run(app, host="0.0.0.0", port=8000)
