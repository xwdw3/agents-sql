"""端到端冒烟测试：登录 + 数据问答 + 制度问答 + 多轮追问。"""
import json
import urllib.request

BASE = "http://127.0.0.1:8000"


def http(path, payload=None, token=None, timeout=180):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method="POST" if payload is not None else "GET")
    return urllib.request.urlopen(req, timeout=timeout)


def login(u, p):
    return json.loads(http("/api/login", {"username": u, "password": p}).read())


def parse_sse(raw: str):
    raw = raw.replace("\r\n", "\n")  # SSE 用 \r\n 分隔，规范化
    events = []
    for block in raw.split("\n\n"):
        ev, data = "message", None
        for line in block.split("\n"):
            if line.startswith("event:"):
                ev = line[6:].strip()
            elif line.startswith("data:"):
                d = line[5:].strip()
                try:
                    data = json.loads(d)
                except Exception:
                    data = d
        events.append((ev, data))
    return events


def chat(token, message, thread_id=None):
    payload = {"message": message}
    if thread_id:
        payload["thread_id"] = thread_id
    raw = http("/api/chat", payload, token).read().decode("utf-8")
    return parse_sse(raw)


def summarize(tag, events):
    statuses = [d.get("label") for e, d in events if e == "status" and isinstance(d, dict)]
    session = [d.get("thread_id") for e, d in events if e == "session" and isinstance(d, dict)]
    answer = ""
    for e, d in events:
        if e == "result" and isinstance(d, dict):
            answer = d.get("final_answer", "")
        elif e == "error" and isinstance(d, dict):
            answer = "ERROR: " + str(d.get("message", d))
    print(f"\n===== {tag} =====")
    print("thread_id:", session)
    print("节点流程:", " -> ".join(statuses))
    print("回答:", answer)


if __name__ == "__main__":
    # 1) 管理员登录 + 数据问答
    admin = login("admin", "admin123")
    print("登录 OK:", admin["display_name"], "| 角色:", admin["role_name"], "| 范围:", admin["data_scope"])
    summarize("管理员·数据问答：张三这个月迟到了几次", chat(admin["token"], "张三这个月迟到了几次"))

    # 2) 制度问答
    summarize("管理员·制度问答：周日加班怎么算", chat(admin["token"], "周日加班怎么算，能调休吗"))

    # 3) 员工多轮追问（测试会话 + 指代消解 + checkpoint 持久化）
    zs = login("zhangsan", "123456")
    print("\n登录 OK:", zs["display_name"], "| 角色:", zs["role_name"], "| 范围:", zs["data_scope"])
    ev1 = chat(zs["token"], "我这个月迟到了几次")
    summarize("员工·首问：我这个月迟到了几次", ev1)
    tid = [d.get("thread_id") for e, d in ev1 if e == "session"]
    tid = tid[0] if tid else None
    summarize("员工·追问（多轮）：那早退呢", chat(zs["token"], "那早退呢", thread_id=tid))
