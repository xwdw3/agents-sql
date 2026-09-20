// 纯 HTML 前端：登录 + SSE 流式聊天 + 动态思考链路 + 历史会话（原生 JS）
const state = {
  token: null,
  user: null,
  threadId: null,
  streaming: false,
};

const $ = (id) => document.getElementById(id);

// ---------- 安全 markdown 渲染（先转义 HTML，再轻量格式化）----------
function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function renderMarkdown(text) {
  let s = escapeHtml(text);
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>'); // 加粗
  s = s.replace(/^\s*[-•]\s+/gm, '• ');                       // 列表项
  s = s.replace(/\n/g, '<br>');                               // 换行
  return s;
}

// ---------- 登录 ----------
async function doLogin(username, password) {
  const res = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    $('loginError').textContent = '用户名或密码错误';
    return;
  }
  const user = await res.json();
  state.token = user.token;
  state.user = user;
  state.threadId = null;
  $('loginView').hidden = true;
  $('chatView').hidden = false;
  const scope = user.data_scope === 'all' ? '全局' : '仅本人';
  $('identity').textContent = `${user.display_name} [${user.role_name || '用户'}·${scope}]`;
  $('loginError').textContent = '';
  $('messages').innerHTML = '';
  $('steps').innerHTML = '';
  appendMsg('ai', `你好，${user.display_name}。请问有什么可以帮你？`);
  loadSessions();
}

$('loginBtn').addEventListener('click', () => doLogin($('username').value.trim(), $('password').value));
$('password').addEventListener('keydown', (e) => { if (e.key === 'Enter') doLogin($('username').value.trim(), $('password').value); });
document.querySelectorAll('.quick button').forEach((b) => {
  b.addEventListener('click', () => doLogin(b.dataset.u, b.dataset.p));
});
$('logoutBtn').addEventListener('click', () => {
  state.token = null; state.user = null; state.threadId = null;
  $('chatView').hidden = true; $('loginView').hidden = false;
});

// ---------- 会话列表 ----------
async function loadSessions() {
  const res = await fetch('/api/sessions', { headers: { 'Authorization': 'Bearer ' + state.token } });
  if (!res.ok) return;
  const data = await res.json();
  const list = $('sessionList');
  list.innerHTML = '';
  (data.sessions || []).forEach((s) => {
    const li = document.createElement('li');
    li.className = s.thread_id === state.threadId ? 'active' : '';

    const title = document.createElement('span');
    title.className = 'sess-title';
    const raw = s.title || ('会话 ' + (s.thread_id || '').slice(0, 8));
    title.textContent = raw.length > 8 ? raw.slice(0, 8) + '…' : raw;
    title.addEventListener('click', () => openSession(s.thread_id));

    const del = document.createElement('button');
    del.className = 'sess-del';
    del.textContent = '×';
    del.title = '删除会话';
    del.addEventListener('click', (e) => { e.stopPropagation(); deleteSession(s.thread_id); });

    li.appendChild(title);
    li.appendChild(del);
    list.appendChild(li);
  });
}

async function deleteSession(threadId) {
  if (!confirm('确定删除该会话及其所有记录？')) return;
  const res = await fetch('/api/sessions/' + encodeURIComponent(threadId), {
    method: 'DELETE',
    headers: { 'Authorization': 'Bearer ' + state.token },
  });
  if (!res.ok) return;
  if (state.threadId === threadId) {
    state.threadId = null;
    $('messages').innerHTML = '';
    $('steps').innerHTML = '';
  }
  loadSessions();
}

async function openSession(threadId) {
  state.threadId = threadId;
  const res = await fetch('/api/sessions/' + encodeURIComponent(threadId), {
    headers: { 'Authorization': 'Bearer ' + state.token },
  });
  if (!res.ok) return;
  const data = await res.json();
  $('messages').innerHTML = '';
  $('steps').innerHTML = '';
  (data.history || []).forEach((m) => {
    if (m.role === 'user') appendMsg('user', m.content || '');
    else if (m.role === 'assistant') appendMsg('ai', m.content || '');
  });
  loadSessions();
}
$('newChatBtn').addEventListener('click', () => { state.threadId = null; $('messages').innerHTML = ''; $('steps').innerHTML = ''; loadSessions(); });

// ---------- 消息渲染 ----------
function appendMsg(role, text) {
  const wrap = document.createElement('div');
  wrap.className = 'msg ' + role;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = renderMarkdown(text);
  wrap.appendChild(bubble);
  $('messages').appendChild(wrap);
  $('messages').scrollTop = $('messages').scrollHeight;
  return bubble;
}

// ---------- 动态思考链路（实际调度链路：status 事件按节点推进）----------
function renderSteps(steps, done) {
  const html = steps.map((s, i) => {
    if (done) return `<span class="step-done">✓ ${s}</span>`;
    return i === steps.length - 1
      ? `<span class="step-cur">⏳ ${s}</span>`
      : `<span class="step-done">✓ ${s}</span>`;
  }).join('<span class="step-arrow"> → </span>');
  const tail = done ? ' <span class="step-arrow">→</span> <span class="step-done">✓ 回答完毕</span>' : '';
  $('steps').innerHTML = '<span class="step-title">思考链路</span> ' + html + tail;
}

// ---------- SSE 流式 ----------
async function send() {
  if (state.streaming) return;
  const input = $('input');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  state.streaming = true;
  $('sendBtn').disabled = true;
  const stepLog = [];
  $('steps').textContent = '思考链路：准备中…';
  appendMsg('user', text);
  const aiBubble = appendMsg('ai', '');

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + state.token },
      body: JSON.stringify({ message: text, thread_id: state.threadId }),
    });
    if (!res.ok) { throw new Error('请求失败 ' + res.status); }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      buf = buf.replace(/\r\n/g, '\n');
      let idx;
      while ((idx = buf.indexOf('\n\n')) >= 0) {
        const block = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const { event, data } = parseEvent(block);
        if (event === 'status' && data) {
          stepLog.push(data.label);
          renderSteps(stepLog, false);
        } else if (event === 'session' && data) {
          state.threadId = data.thread_id;
        } else if (event === 'token' && data) {
          aiBubble.textContent += data.delta;
          scroll();
        } else if (event === 'result' && data) {
          aiBubble.innerHTML = renderMarkdown(data.final_answer || '');
          renderSteps(stepLog, true);
          scroll();
        } else if (event === 'error' && data) {
          aiBubble.textContent = '出错了：' + (data.message || '未知错误');
        }
      }
    }
  } catch (e) {
    aiBubble.textContent = '出错了：' + e.message;
  } finally {
    state.streaming = false;
    $('sendBtn').disabled = false;
    loadSessions();
  }
}

function parseEvent(block) {
  let event = 'message';
  let data = null;
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) {
      const raw = line.slice(5).trim();
      try { data = JSON.parse(raw); } catch { data = raw; }
    }
  }
  return { event, data };
}

function scroll() { $('messages').scrollTop = $('messages').scrollHeight; }

$('sendBtn').addEventListener('click', send);
$('input').addEventListener('keydown', (e) => { if (e.key === 'Enter') send(); });
