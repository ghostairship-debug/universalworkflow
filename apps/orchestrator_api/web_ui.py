from __future__ import annotations

import html
import json
from typing import Any


def _escape(value: Any) -> str:
    return html.escape("" if value is None else str(value))


DISPLAY_LABELS = {
    "pending": "待处理",
    "prepared": "已准备",
    "running": "运行中",
    "awaiting_review": "等待审查",
    "completed": "已完成",
    "failed": "失败",
    "cancelled": "已取消",
    "open": "打开",
    "clarifying": "待澄清",
    "planning": "规划中",
    "ready_to_launch": "可启动",
    "launched": "已启动",
    "human_pending": "人工待审",
    "human_approved": "人工通过",
    "human_rejected": "人工拒绝",
    "user": "用户",
    "assistant": "助手",
    "system": "系统",
    "tool": "工具",
    "text": "文本",
    "workflow_event": "工作流事件",
    "confirmation_required": "需要确认",
    "confirmation_result": "确认结果",
    "error": "错误",
    "posted": "已发布",
    "pending_confirmation": "等待确认",
    "confirmed": "已确认",
    "blocked": "已阻塞",
    "plan_preview": "计划预览",
    "launch_prepare": "启动准备",
    "launch_execute": "启动并执行",
    "resume_run": "继续运行",
    "approve_run": "通过审查",
    "reject_run": "拒绝审查",
    "cancel_run": "取消运行",
    "summarize_run": "运行摘要",
    "pr_ready_summary": "PR 摘要",
    "diagnose_failure": "排查失败",
    "create_followup": "创建后续事项",
    "chat_guidance": "聊天引导",
    "message": "消息",
    "ready": "就绪",
    "session ready": "会话就绪",
    "monitor_run": "监控运行",
    "wait_for_run_checkpoint": "等待运行检查点",
    "review_then_continue": "审查后继续",
    "review_then_replan": "审查后重规划",
    "replan_session": "重规划会话",
    "auto": "自动",
    "single-path preset": "单路径预设",
    "low": "低",
    "medium": "中",
    "high": "高",
    "True": "是",
    "False": "否",
    "true": "是",
    "false": "否",
}


def _display(value: Any) -> str:
    raw = "" if value is None else str(value)
    return DISPLAY_LABELS.get(raw, raw)


def _json_block(payload: Any) -> str:
    return f"<pre>{_escape(json.dumps(payload, ensure_ascii=False, indent=2))}</pre>"


def _pill(value: str, tone: str = "neutral") -> str:
    return f'<span class="pill pill-{tone}">{_escape(_display(value))}</span>'


def _cluster_status_banner(cluster: dict[str, Any] | None) -> str:
    payload = cluster or {}
    if payload.get("enabled", True):
        return ""
    return (
        '<div class="notice" style="margin-bottom:12px;">'
        "调度权威集群已关闭，当前为本地单机模式。"
        "</div>"
    )


def _nav() -> str:
    links = [
        ('/ui', '总览'),
        ('/ui/runs', '运行'),
        ('/ui/workbench', '聊天工作台'),
        ('/ui/reviews', '审查'),
        ('/ui/governance', '治理'),
        ('/ui/config', '配置'),
    ]
    items = "".join(
        f'<a class="nav-link" href="{href}">{_escape(label)}</a>'
        for href, label in links
    )
    return f'<nav class="nav">{items}</nav>'


def _layout(title: str, body: str, *, notice: str | None = None) -> str:
    notice_block = f'<div class="notice">{_escape(notice)}</div>' if notice else ""
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(title)}</title>
  <style>
    :root {{
      --bg: #f4f1ea;
      --panel: #fffdf7;
      --line: #d7ccbf;
      --ink: #1f2421;
      --muted: #5b625c;
      --accent: #1f6f61;
      --warm: #a8612d;
      --danger: #9f2a1d;
      --shadow: 0 12px 28px rgba(31, 36, 33, 0.08);
      --radius: 18px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, rgba(31, 111, 97, 0.12), transparent 24%),
        linear-gradient(180deg, #f8f6f0 0%, var(--bg) 100%);
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .shell {{ max-width: 1320px; margin: 0 auto; padding: 28px 22px 48px; }}
    .hero {{
      background: linear-gradient(135deg, rgba(31, 111, 97, 0.96), rgba(168, 97, 45, 0.92));
      color: white;
      border-radius: 28px;
      padding: 24px 28px;
      box-shadow: var(--shadow);
      margin-bottom: 18px;
    }}
    .hero h1 {{ margin: 0 0 8px; font-size: 32px; }}
    .hero p {{ margin: 0; max-width: 860px; line-height: 1.5; opacity: 0.92; }}
    .nav {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin: 18px 0 22px;
    }}
    .nav-link {{
      display: inline-flex;
      align-items: center;
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(31, 36, 33, 0.08);
      box-shadow: 0 4px 12px rgba(31, 36, 33, 0.05);
    }}
    .notice {{
      background: #fff2da;
      border: 1px solid #e4b974;
      color: #6d491f;
      border-radius: 16px;
      padding: 12px 14px;
      margin-bottom: 18px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
      margin-bottom: 18px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid rgba(31, 36, 33, 0.08);
      border-radius: var(--radius);
      padding: 18px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }}
    .panel h2, .panel h3 {{ margin-top: 0; }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .stat {{
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(31, 36, 33, 0.08);
      border-radius: 16px;
      padding: 14px;
    }}
    .stat-label {{ color: var(--muted); font-size: 13px; text-transform: uppercase; letter-spacing: .06em; }}
    .stat-value {{ font-size: 26px; font-weight: 700; margin-top: 6px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      padding: 10px 8px;
      border-bottom: 1px solid rgba(31, 36, 33, 0.08);
      text-align: left;
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }}
    .pill {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 5px 10px;
      font-size: 12px;
      font-weight: 600;
      margin-right: 6px;
      background: #ece8e0;
      color: #544c44;
    }}
    .pill-ok {{ background: #d8f0e9; color: #185546; }}
    .pill-warn {{ background: #fff0d9; color: #8a5713; }}
    .pill-danger {{ background: #f7ddd9; color: #7d271f; }}
    .pill-info {{ background: #dbeceb; color: #1f5751; }}
    .kv {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }}
    .kv-item {{
      padding: 12px;
      border-radius: 14px;
      background: rgba(31, 111, 97, 0.05);
      border: 1px solid rgba(31, 111, 97, 0.10);
    }}
    .kv-item strong {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .05em;
      margin-bottom: 6px;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 18px;
    }}
    form.inline {{ display: inline-flex; gap: 8px; align-items: center; margin: 0; }}
    button, .button {{
      appearance: none;
      border: none;
      border-radius: 999px;
      padding: 10px 14px;
      background: var(--accent);
      color: white;
      cursor: pointer;
      font-weight: 600;
      box-shadow: 0 6px 14px rgba(31, 111, 97, 0.18);
    }}
    button.secondary, .button.secondary {{ background: #7c857f; }}
    button.warn, .button.warn {{ background: var(--warm); }}
    button.danger, .button.danger {{ background: var(--danger); }}
    input, select, textarea {{
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.88);
      min-width: 120px;
    }}
    pre {{
      overflow-x: auto;
      background: #1e221f;
      color: #edf4f0;
      border-radius: 16px;
      padding: 14px;
      font-size: 12px;
      line-height: 1.45;
    }}
    .split {{
      display: grid;
      grid-template-columns: 1.1fr .9fr;
      gap: 16px;
    }}
    .timeline {{
      list-style: none;
      padding: 0;
      margin: 0;
    }}
    .timeline li {{
      padding: 10px 0;
      border-bottom: 1px solid rgba(31, 36, 33, 0.08);
    }}
    .chat-shell {{
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(260px, .65fr);
      gap: 16px;
    }}
    .chat-transcript {{
      min-height: 360px;
      max-height: 620px;
      overflow-y: auto;
      padding: 14px;
      border-radius: 18px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.72), rgba(255,253,247,0.92)),
        radial-gradient(circle at top left, rgba(31,111,97,0.10), transparent 32%);
      border: 1px solid rgba(31, 36, 33, 0.08);
    }}
    .chat-message {{
      width: min(92%, 820px);
      margin: 0 0 12px;
      padding: 12px 14px;
      border-radius: 18px;
      background: rgba(255,255,255,0.88);
      border: 1px solid rgba(31, 36, 33, 0.08);
      box-shadow: 0 8px 18px rgba(31, 36, 33, 0.05);
    }}
    .chat-user {{
      margin-left: auto;
      background: rgba(31,111,97,0.12);
      border-color: rgba(31,111,97,0.22);
    }}
    .chat-assistant {{ margin-right: auto; }}
    .chat-system {{ background: rgba(168,97,45,0.10); }}
    .chat-meta {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
    }}
    .chat-content {{ white-space: pre-wrap; line-height: 1.52; }}
    .confirmation-card {{
      margin-top: 10px;
      padding: 12px;
      border-radius: 14px;
      background: #fff2da;
      border: 1px solid #e4b974;
    }}
    .stream-event {{
      margin: 8px 0 0;
      padding: 9px 11px;
      border-radius: 14px;
      background: rgba(31, 111, 97, 0.08);
      color: var(--muted);
      font-size: 13px;
    }}
    .muted {{ color: var(--muted); }}
    @media (max-width: 900px) {{
      .split {{ grid-template-columns: 1fr; }}
      .chat-shell {{ grid-template-columns: 1fr; }}
      .hero h1 {{ font-size: 26px; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>{_escape(title)}</h1>
      <p>Universal Agentic Workflow OS 本地操作台</p>
    </section>
    {_nav()}
    {notice_block}
    {body}
  </div>
</body>
</html>"""


def _run_table(rows: list[dict[str, Any]]) -> str:
    def _as_run_row(row: dict[str, Any]) -> dict[str, Any]:
        if "run" in row:
            return row
        return {
            "run": {
                "run_id": row["run_id"],
                "preset_id": row["preset_id"],
                "status": row["status"],
                "goal": row["goal"],
            },
            "effective_review_state": row.get("effective_review_state"),
            "next_action": row.get("next_action"),
        }

    body = "".join(
        f"""
        <tr>
          <td><a href="/ui/runs/{_escape(normalized['run']['run_id'])}">{_escape(normalized['run']['run_id'])}</a></td>
          <td>{_escape(normalized['run']['preset_id'])}</td>
          <td>{_pill(str(normalized['run']['status']), _status_tone(str(normalized['run']['status'])))}</td>
          <td>{_pill(str(normalized['effective_review_state']), _review_tone(str(normalized['effective_review_state'])))}</td>
          <td>{_escape(_display(normalized['next_action']))}</td>
          <td>{_escape(normalized['run']['goal'])}</td>
        </tr>
        """
        for normalized in (_as_run_row(row) for row in rows)
    )
    if not body:
        body = '<tr><td colspan="6" class="muted">暂无运行记录。</td></tr>'
    return f"""
    <table>
      <thead>
        <tr>
          <th>运行 ID</th>
          <th>预设</th>
          <th>状态</th>
          <th>审查</th>
          <th>下一步</th>
          <th>目标</th>
        </tr>
      </thead>
      <tbody>{body}</tbody>
    </table>
    """


def _status_tone(status: str) -> str:
    mapping = {
        "completed": "ok",
        "failed": "danger",
        "cancelled": "danger",
        "awaiting_review": "warn",
        "running": "info",
        "prepared": "info",
    }
    return mapping.get(status, "neutral")


def _review_tone(state: str) -> str:
    if state in {"human_approved"}:
        return "ok"
    if state in {"human_pending"}:
        return "warn"
    if state in {"human_rejected"}:
        return "danger"
    return "neutral"


def _session_table(rows: list[dict[str, Any]]) -> str:
    body = "".join(
        f"""
        <tr>
          <td><a href="/ui/workbench?session_id={_escape(row['session_id'])}">{_escape(row['session_id'])}</a></td>
          <td>{_pill(str(row.get('status', '-')), _status_tone(str(row.get('status', '-'))))}</td>
          <td>{_escape(_display(row.get('intent_packet', {}).get('preferred_preset_id') or 'auto'))}</td>
          <td>{_escape(row.get('active_run_id') or '-')}</td>
          <td>{_escape(row.get('intent_packet', {}).get('goal') or '-')}</td>
        </tr>
        """
        for row in rows
    )
    if not body:
        body = '<tr><td colspan="5" class="muted">暂无最近会话。</td></tr>'
    return f"""
    <table>
      <thead>
        <tr>
          <th>会话</th>
          <th>状态</th>
          <th>预设</th>
          <th>当前运行</th>
          <th>目标</th>
        </tr>
      </thead>
      <tbody>{body}</tbody>
    </table>
    """


def _chat_message_block(message: dict[str, Any]) -> str:
    role = str(message.get("role") or "assistant")
    message_type = str(message.get("message_type") or "text")
    status = str(message.get("status") or "posted")
    action_type = str(message.get("action_type") or "")
    payload = message.get("payload_json") if isinstance(message.get("payload_json"), dict) else {}
    confirmation = payload.get("confirmation") if isinstance(payload, dict) else None
    pr_ready_summary = payload.get("pr_ready_summary") if isinstance(payload, dict) else None
    confirmation_block = ""
    if (
        message_type == "confirmation_required"
        and status == "pending_confirmation"
        and isinstance(confirmation, dict)
    ):
        confirmation_block = f"""
        <div class="confirmation-card">
          <strong>需要确认</strong>
          <p class="muted">动作={_escape(_display(confirmation.get('action_type')))} 运行={_escape(confirmation.get('run_id') or '-')}</p>
          <form method="post" action="/ui/workbench/chat/actions/{_escape(message.get('message_id'))}/confirm">
            <textarea name="rationale" rows="2" style="width:100%;" placeholder="可选：确认理由"></textarea>
            <div class="actions" style="margin:10px 0 0;"><button class="warn" type="submit">确认执行</button></div>
          </form>
        </div>
        """
    pr_block = ""
    if isinstance(pr_ready_summary, dict):
        pr_block = f"""
        <details style="margin-top:10px;">
          <summary>查看 PR 摘要</summary>
          {_json_block(pr_ready_summary)}
        </details>
        """
    return f"""
    <div class="chat-message chat-{_escape(role)}" data-message-id="{_escape(message.get('message_id') or '')}">
      <div class="chat-meta">
        {_pill(role, "info" if role == "user" else "neutral")}
        {_pill(message_type, "warn" if message_type == "confirmation_required" else "neutral")}
        {_pill(status, _status_tone(status))}
        <span>{_escape(_display(action_type or "message"))}</span>
      </div>
      <div class="chat-content">{_escape(message.get('content') or '')}</div>
      {confirmation_block}
      {pr_block}
    </div>
    """


def _workbench_chat_panel(session_payload: dict[str, Any] | None) -> str:
    if session_payload is None:
        return """
        <section class="panel">
          <h2>流式聊天工作台</h2>
          <p class="muted">把目标直接写进聊天框；第一版流式展示工作流事件，而不是大模型 token 级输出。</p>
          <div class="chat-shell">
            <div>
              <div class="chat-transcript">
                <div class="chat-message chat-assistant">
                  <div class="chat-meta"><span class="pill pill-info">助手</span><span>就绪</span></div>
                  <div class="chat-content">说出你想完成的任务，我会创建意图会话、给出计划预览，并把后续启动、继续、审查、测试证据和 PR 摘要都投到这个窗口里。</div>
                </div>
              </div>
              <form method="post" action="/ui/workbench/chat" style="margin-top:14px;">
                <textarea name="message" rows="4" style="width:100%;" placeholder="例如：为当前项目做 M39 流式聊天工作台的计划预览"></textarea>
                <div class="actions" style="margin-top:10px;"><button type="submit">发送并创建会话</button></div>
              </form>
            </div>
            <aside class="kv">
              <div class="kv-item"><strong>主入口</strong>/ui/workbench</div>
              <div class="kv-item"><strong>流式源</strong>SSE 工作流事件</div>
              <div class="kv-item"><strong>安全规则</strong>继续 / 通过 / 拒绝 / 取消需要确认</div>
            </aside>
          </div>
        </section>
        """

    session = session_payload["session"]
    session_id = session["session_id"]
    messages = session_payload.get("chat_messages") or []
    transcript = "".join(_chat_message_block(message) for message in messages)
    if not transcript:
        transcript = """
        <div class="chat-message chat-assistant">
          <div class="chat-meta"><span class="pill pill-info">助手</span><span>会话就绪</span></div>
          <div class="chat-content">这个会话还没有聊天记录。你可以输入“预览计划”“启动”“继续”“总结”或“PR 摘要”。</div>
        </div>
        """
    active_run_id = session.get("active_run_id") or "-"
    status = session.get("status") or "-"
    stream_url = f"/interaction/sessions/{session_id}/stream"
    return f"""
    <section class="panel">
      <h2>流式聊天工作台</h2>
      <p class="muted">当前窗口会接收 LLM delta 流式回复；workflow 状态只更新右侧状态卡，不再刷进聊天气泡。</p>
      <div class="chat-shell">
        <div>
          <div id="chat-stream" class="chat-transcript" data-session-id="{_escape(session_id)}">
            {transcript}
          </div>
          <form id="chat-form" method="post" action="/ui/workbench/chat" style="margin-top:14px;">
            <input type="hidden" name="session_id" value="{_escape(session_id)}">
            <textarea name="message" rows="4" style="width:100%;" placeholder="输入：预览计划 / 启动 / 继续 / 总结 / PR 摘要 / 排查失败 / 加入后续事项"></textarea>
            <div class="actions" style="margin-top:10px;"><button id="chat-submit" type="submit">发送</button></div>
          </form>
        </div>
        <aside class="kv">
          <div class="kv-item"><strong>会话</strong>{_escape(session_id)}</div>
          <div class="kv-item"><strong>状态</strong><span id="chat-session-status">{_pill(str(status), _status_tone(str(status)))}</span></div>
          <div class="kv-item"><strong>当前运行</strong><span id="chat-active-run">{_escape(active_run_id)}</span></div>
          <div class="kv-item"><strong>LLM</strong><span id="chat-llm-status">检测中</span></div>
          <div class="kv-item"><strong>图节点</strong><span id="chat-graph-node">等待输入</span></div>
          <div class="kv-item"><strong>事件流</strong><code>{_escape(stream_url)}</code></div>
          <div class="kv-item"><strong>确认门</strong>继续 / 通过 / 拒绝 / 取消 / 启动并执行</div>
          <div class="kv-item"><strong>状态时间线</strong><div id="workflow-status-feed" class="muted">暂无状态事件。</div></div>
        </aside>
      </div>
      <script>
      (function() {{
        const stream = document.getElementById("chat-stream");
        const form = document.getElementById("chat-form");
        const submit = document.getElementById("chat-submit");
        const statusFeed = document.getElementById("workflow-status-feed");
        const sessionStatus = document.getElementById("chat-session-status");
        const activeRun = document.getElementById("chat-active-run");
        const llmStatus = document.getElementById("chat-llm-status");
        const graphNode = document.getElementById("chat-graph-node");
        if (!stream || !window.EventSource) {{
          return;
        }}
        const baseStreamUrl = "{_escape(stream_url)}";
        const seenEvents = new Set();
        let lastEventId = "";
        let reconnectTimer = null;
        const appendStatus = function(text) {{
          if (!statusFeed) return;
          if (statusFeed.textContent === "暂无状态事件。") {{
            statusFeed.textContent = "";
          }}
          const item = document.createElement("div");
          item.className = "stream-event";
          item.textContent = text;
          statusFeed.appendChild(item);
        }};
        const appendChat = function(message) {{
          if (!message || !message.message_id) {{
            return;
          }}
          const existing = stream.querySelector('[data-message-id="' + message.message_id + '"]');
          if (existing) {{
            if (existing.dataset.streaming === "true") {{
              const content = existing.querySelector(".chat-content");
              if (content) content.textContent = message.content || "";
              delete existing.dataset.streaming;
            }}
            return;
          }}
          const item = document.createElement("div");
          item.className = "chat-message chat-" + (message.role || "assistant");
          item.dataset.messageId = message.message_id;
          item.innerHTML = '<div class="chat-meta"><span class="pill pill-info">' + (message.role || "assistant") + '</span><span>' + (message.action_type || "message") + '</span></div><div class="chat-content"></div>';
          item.querySelector(".chat-content").textContent = message.content || "";
          const confirmation = message.payload_json && message.payload_json.confirmation;
          if (message.message_type === "confirmation_required" && message.status === "pending_confirmation" && confirmation) {{
            const card = document.createElement("div");
            card.className = "confirmation-card";
            card.innerHTML = '<strong>需要确认</strong><p class="muted">动作=' + (confirmation.action_type || "-") + ' 运行=' + (confirmation.run_id || "-") + '</p><div class="actions" style="margin:10px 0 0;"><button class="warn chat-confirm-button" type="button" data-chat-confirm-action="' + message.message_id + '">确认执行</button></div>';
            item.appendChild(card);
          }}
          stream.appendChild(item);
          stream.scrollTop = stream.scrollHeight;
        }};
        const appendAssistantDelta = function(payload) {{
          const messageId = payload && payload.message_id;
          if (!messageId) return;
          let item = stream.querySelector('[data-message-id="' + messageId + '"]');
          if (!item) {{
            item = document.createElement("div");
            item.className = "chat-message chat-assistant";
            item.dataset.messageId = messageId;
            item.dataset.streaming = "true";
            item.innerHTML = '<div class="chat-meta"><span class="pill pill-info">助手</span><span>流式输出</span></div><div class="chat-content"></div>';
            stream.appendChild(item);
          }}
          if (item.dataset.streaming !== "true") {{
            return;
          }}
          item.querySelector(".chat-content").textContent += payload.delta || "";
          stream.scrollTop = stream.scrollHeight;
        }};
        const handleEvent = function(label, payload, eventId) {{
          if (eventId && eventId.indexOf("chatevt_") === 0) {{
            lastEventId = eventId;
          }}
          const eventKey = eventId || (label + ":" + JSON.stringify(payload || {{}}));
          if (seenEvents.has(eventKey)) {{
            return;
          }}
          seenEvents.add(eventKey);
          if (label === "user_message" || label === "assistant_final" || label === "confirmation_required" || label === "confirmation_result" || label === "error") {{
            appendChat(payload);
            return;
          }}
          if (label === "assistant_delta") {{
            appendAssistantDelta(payload);
            return;
          }}
          if (label === "graph_update") {{
            if (graphNode) graphNode.textContent = payload.graph_node || payload.path?.slice(-1)[0] || "已更新";
            appendStatus("图更新：" + (payload.graph_node || "已更新"));
            return;
          }}
          if (label === "status_patch") {{
            const session = payload.session || {{}};
            if (sessionStatus && session.status) sessionStatus.textContent = session.status;
            if (activeRun) activeRun.textContent = payload.active_run_id || session.active_run_id || "-";
            if (llmStatus && payload.llm) {{
              const baseLlm = payload.llm.configured ? (payload.llm.provider + " / " + payload.llm.model) : "LLM 未配置，规则降级";
              const modelSelection = payload.model_selection || {{}};
              const selectedModel = modelSelection.selected_model || "";
              const selectionSource = modelSelection.model_selection_source || "";
              llmStatus.textContent = selectedModel ? (baseLlm + " | 执行模型 " + selectedModel + (selectionSource ? " · " + selectionSource : "")) : baseLlm;
            }}
            appendStatus("状态更新：已更新");
            return;
          }}
          if (label === "run_update" || label === "timeline_event" || label === "test_evidence" || label === "pr_ready_summary" || label === "review_required") {{
            appendStatus(label + "：" + (payload.headline || payload.event_type || payload.summary || payload.run_id || "已更新"));
          }}
        }};
        const parsePayload = function(event) {{
          try {{
            return JSON.parse(event.data);
          }} catch (_error) {{
            return {{content: event.data || "事件解析失败"}};
          }}
        }};
        stream.addEventListener("click", function(event) {{
          const target = event.target;
          const button = target && target.closest ? target.closest("[data-chat-confirm-action]") : null;
          if (!button) return;
          const actionId = button.getAttribute("data-chat-confirm-action");
          if (!actionId) return;
          button.disabled = true;
          fetch("/interaction/chat/actions/" + encodeURIComponent(actionId) + "/confirm", {{
            method: "POST",
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify({{rationale: "confirmed from workbench chat"}})
          }})
            .then(function(response) {{
              return response.json().then(function(payload) {{
                if (!response.ok) {{
                  const message = payload && payload.error && payload.error.message
                    ? payload.error.message
                    : "HTTP " + response.status;
                  throw new Error(message);
                }}
                return payload;
              }});
            }})
            .then(function(payload) {{
              (payload.chat_stream_events || []).forEach(function(item) {{
                handleEvent(item.event_type, item.payload_json, item.event_id);
              }});
            }})
            .catch(function(error) {{
              appendChat({{message_id: "error_" + Date.now(), role: "assistant", action_type: "error", content: "确认失败：" + error}});
              button.disabled = false;
            }});
        }});
        const connectStream = function() {{
          const url = lastEventId
            ? baseStreamUrl + "?after_event_id=" + encodeURIComponent(lastEventId)
            : baseStreamUrl;
          const source = new EventSource(url);
          let heartbeatReceived = false;
          ["user_message", "assistant_delta", "assistant_final", "tool_action_proposed", "confirmation_required", "confirmation_result", "graph_update", "run_update", "status_patch", "timeline_event", "review_required", "test_evidence", "pr_ready_summary", "error"].forEach(function(name) {{
            source.addEventListener(name, function(event) {{
              handleEvent(name, parsePayload(event), event.lastEventId);
            }});
          }});
          source.addEventListener("heartbeat", function() {{
            heartbeatReceived = true;
            source.close();
            if (!reconnectTimer) {{
              reconnectTimer = window.setTimeout(function() {{
                reconnectTimer = null;
                connectStream();
              }}, 3000);
            }}
          }});
          source.addEventListener("error", function() {{
            if (heartbeatReceived) {{
              source.close();
              return;
            }}
            appendStatus("事件流连接异常，稍后自动重试");
            source.close();
            if (!reconnectTimer) {{
              reconnectTimer = window.setTimeout(function() {{
                reconnectTimer = null;
                connectStream();
              }}, 5000);
            }}
          }});
        }};
        if (form) {{
          form.addEventListener("submit", function(event) {{
            event.preventDefault();
            const formData = new FormData(form);
            const message = (formData.get("message") || "").toString().trim();
            if (!message) return;
            if (submit) submit.disabled = true;
            fetch("/interaction/chat/messages", {{
              method: "POST",
              headers: {{"Content-Type": "application/json"}},
              body: JSON.stringify({{
                session_id: formData.get("session_id") || null,
                content: message,
                mode: "llm_assisted",
                client_message_id: "client_" + Date.now()
              }})
            }})
              .then(function(response) {{
                return response.json().then(function(payload) {{
                  if (!response.ok) {{
                    const message = payload && payload.error && payload.error.message
                      ? payload.error.message
                      : "HTTP " + response.status;
                    throw new Error(message);
                  }}
                  return payload;
                }});
              }})
              .then(function(payload) {{
                form.querySelector("textarea").value = "";
                const nextSessionId = payload && payload.session && payload.session.session_id;
                const currentSessionId = (formData.get("session_id") || "").toString();
                if (nextSessionId && currentSessionId && nextSessionId !== currentSessionId) {{
                  window.location.href = "/ui/workbench?session_id=" + encodeURIComponent(nextSessionId);
                  return;
                }}
                (payload.chat_stream_events || []).forEach(function(item) {{
                  handleEvent(item.event_type, item.payload_json, item.event_id);
                }});
              }})
              .catch(function(error) {{
                appendChat({{message_id: "error_" + Date.now(), role: "assistant", action_type: "error", content: "发送失败：" + error}});
              }})
              .finally(function() {{
                if (submit) submit.disabled = false;
                connectStream();
              }});
          }});
        }}
        connectStream();
      }})();
      </script>
    </section>
    """


def render_dashboard(
    *,
    snapshot: dict[str, Any],
    pending_reviews: list[dict[str, Any]],
    governance: dict[str, Any],
    effective_config: dict[str, Any],
    cluster_overview: dict[str, Any] | None = None,
    notice: str | None = None,
) -> str:
    focus = snapshot["focus_detail"]
    focus_block = (
        f"""
        <div class="kv">
          <div class="kv-item"><strong>选中运行</strong>{_escape(focus['run']['run_id'])}</div>
          <div class="kv-item"><strong>状态</strong>{_escape(_display(focus['run']['status']))}</div>
          <div class="kv-item"><strong>审查</strong>{_escape(_display(focus['effective_review_state']))}</div>
          <div class="kv-item"><strong>下一步</strong>{_escape(_display(focus['next_action']))}</div>
          <div class="kv-item"><strong>可恢复性</strong>{_escape(_display(focus['recoverability_hint']))}</div>
          <div class="kv-item"><strong>网关</strong>{_escape(snapshot['runtime_gateway']['provider'])}</div>
        </div>
        """
        if focus is not None
        else '<p class="muted">暂无聚焦运行。</p>'
    )
    review_rows = "".join(
        f"""
        <li>
          <a href="/ui/runs/{_escape(row['run']['run_id'])}">{_escape(row['run']['run_id'])}</a>
          — {_escape(row['run']['goal'])} — {_escape(_display(row['review_recommended_action']))}
        </li>
        """
        for row in pending_reviews[:6]
    ) or '<li class="muted">暂无待审查运行。</li>'
    cluster = cluster_overview or snapshot.get("cluster_overview") or {}
    body = f"""
    <section class="stats">
      <div class="stat"><div class="stat-label">运行数量</div><div class="stat-value">{snapshot['run_count']}</div></div>
      <div class="stat"><div class="stat-label">待审查</div><div class="stat-value">{len(pending_reviews)}</div></div>
      <div class="stat"><div class="stat-label">未偿还债务</div><div class="stat-value">{governance['tech_debt']['open_debt_count']}</div></div>
      <div class="stat"><div class="stat-label">配置路径</div><div class="stat-value">{_escape(effective_config['config_path'] or '-')}</div></div>
    </section>
    <div class="split">
      <section class="panel">
        <h2>最近运行</h2>
        {_run_table(snapshot['runs'])}
      </section>
      <section class="panel">
        <h2>当前焦点</h2>
        {focus_block}
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h2>待审查</h2>
        <ul class="timeline">{review_rows}</ul>
      </section>
      <section class="panel">
        <h2>治理快照</h2>
        <div class="kv">
          <div class="kv-item"><strong>发布就绪</strong>{_escape(_display(governance['release_readiness']['overall_ready']))}</div>
          <div class="kv-item"><strong>告警数</strong>{_escape(governance['alerts']['alert_count'])}</div>
          <div class="kv-item"><strong>追踪运行</strong>{_escape(governance['metrics']['runtime_inventory']['counts']['runs'])}</div>
          <div class="kv-item"><strong>策略数</strong>{_escape(governance['review_policy']['supported_policy_count'])}</div>
        </div>
      </section>
    </div>
    <section class="panel" style="margin-top:16px;">
      <h2>调度权威拓扑</h2>
      {_cluster_status_banner(cluster)}
      <div class="kv">
        <div class="kv-item"><strong>模式</strong>{_escape(cluster.get('mode', '-'))}</div>
        <div class="kv-item"><strong>权威节点</strong>{_escape(cluster.get('authority_node_id', cluster.get('leader_node_id', '-')))}</div>
        <div class="kv-item"><strong>权威任期</strong>{_escape(cluster.get('authority_term_no', cluster.get('term_no', '-')))}</div>
        <div class="kv-item"><strong>仲裁数</strong>{_escape(cluster.get('quorum_size', '-'))}</div>
        <div class="kv-item"><strong>活跃节点</strong>{_escape(cluster.get('active_node_count', '-'))}</div>
        <div class="kv-item"><strong>决策索引</strong>{_escape(cluster.get('decision_index', cluster.get('commit_index', '-')))}</div>
      </div>
    </section>
    """
    return _layout("操作台总览", body, notice=notice)


def render_runs(
    *,
    rows: list[dict[str, Any]],
    status_filter: str | None,
    preset_filter: str | None,
    limit: int,
    notice: str | None = None,
) -> str:
    body = f"""
    <section class="panel">
      <h2>运行目录</h2>
      <form class="actions" method="get" action="/ui/runs">
        <input type="text" name="status" placeholder="状态" value="{_escape(status_filter or '')}">
        <input type="text" name="preset_id" placeholder="预设 ID" value="{_escape(preset_filter or '')}">
        <input type="number" name="limit" min="1" value="{limit}">
        <button type="submit">应用筛选</button>
      </form>
      {_run_table(rows)}
    </section>
    """
    return _layout("运行浏览器", body, notice=notice)


def render_run_focus(*, operator_view: dict[str, Any], notice: str | None = None) -> str:
    run = operator_view["run"]
    summary = operator_view["summary"]
    detail = operator_view["status_detail"]
    inspection = operator_view["inspection"]
    cluster_overview = operator_view.get("cluster_overview") or {}
    scheduler_authority = operator_view.get("scheduler_authority") or {}
    active_committed = scheduler_authority.get("active_committed_lease") or {}
    takeover_state = scheduler_authority.get("takeover_state") or {}
    handoff_history = operator_view.get("handoffs") or scheduler_authority.get("handoff_history") or []
    timeline_items = "".join(
        f"<li><strong>{_escape(item['event_type'])}</strong><br><span class='muted'>{_escape(item['summary'])}</span></li>"
        for item in operator_view["timeline"][-10:]
    ) or "<li class='muted'>暂无时间线事件。</li>"
    problems = "".join(
        f"<li><strong>{_escape(problem['problem'])}</strong> — {_escape(problem['description'])}</li>"
        for problem in inspection["problems"]
    ) or "<li class='muted'>检查已干净通过。</li>"
    body = f"""
    <section class="panel">
      <h2>{_escape(run['run_id'])}</h2>
      <p>{_escape(run['goal'])}</p>
      <div class="actions">
        <form class="inline" method="post" action="/ui/actions/{_escape(run['run_id'])}/resume"><button type="submit">继续执行</button></form>
        <form class="inline" method="post" action="/ui/actions/{_escape(run['run_id'])}/approve"><button type="submit">通过审查</button></form>
        <form class="inline" method="post" action="/ui/actions/{_escape(run['run_id'])}/reject"><button class="warn" type="submit">拒绝审查</button></form>
        <form class="inline" method="post" action="/ui/actions/{_escape(run['run_id'])}/reconcile"><button class="secondary" type="submit">状态对账</button></form>
        <form class="inline" method="post" action="/ui/actions/{_escape(run['run_id'])}/cancel"><button class="danger" type="submit">取消运行</button></form>
      </div>
      <div class="kv">
        <div class="kv-item"><strong>状态</strong>{_escape(_display(run['status']))}</div>
        <div class="kv-item"><strong>审查状态</strong>{_escape(_display(detail['effective_review_state']))}</div>
        <div class="kv-item"><strong>下一步</strong>{_escape(_display(detail['next_action']))}</div>
        <div class="kv-item"><strong>可恢复性</strong>{_escape(_display(detail['recoverability_hint']))}</div>
        <div class="kv-item"><strong>适配器</strong>{_escape(detail['capability_resolution']['adapter_name'] if detail['capability_resolution'] else '-')}</div>
        <div class="kv-item"><strong>执行通道</strong>{_escape(detail['execution_lane'])}</div>
      </div>
    </section>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h3>摘要</h3>
        <p><strong>{_escape(summary['headline'])}</strong></p>
        <ul class="timeline">{''.join(f'<li>{_escape(line)}</li>' for line in summary['summary_lines'])}</ul>
      </section>
      <section class="panel">
        <h3>检查结果</h3>
        <div class="kv">
          <div class="kv-item"><strong>是否通过</strong>{_escape(_display(inspection['passed']))}</div>
          <div class="kv-item"><strong>问题数</strong>{_escape(inspection['problem_count'])}</div>
          <div class="kv-item"><strong>建议动作</strong>{_escape(_display(inspection['recommended_action']))}</div>
        </div>
        <ul class="timeline" style="margin-top:12px;">{problems}</ul>
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h3>最近时间线</h3>
        <ul class="timeline">{timeline_items}</ul>
      </section>
      <section class="panel">
        <h3>回放包摘要</h3>
        {_json_block(operator_view['replay_packet_excerpt'])}
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h3>编排信息</h3>
        {_json_block(operator_view['orchestration'])}
      </section>
      <section class="panel">
        <h3>状态详情</h3>
        {_json_block(detail)}
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h3>调度权威拓扑</h3>
        {_cluster_status_banner(cluster_overview)}
        <div class="kv">
          <div class="kv-item"><strong>权威节点</strong>{_escape(cluster_overview.get('authority_node_id', cluster_overview.get('leader_node_id', '-')))}</div>
          <div class="kv-item"><strong>权威任期</strong>{_escape(cluster_overview.get('authority_term_no', cluster_overview.get('term_no', '-')))}</div>
          <div class="kv-item"><strong>仲裁数</strong>{_escape(cluster_overview.get('quorum_size', '-'))}</div>
          <div class="kv-item"><strong>决策索引</strong>{_escape(cluster_overview.get('decision_index', cluster_overview.get('commit_index', '-')))}</div>
          <div class="kv-item"><strong>活跃节点</strong>{_escape(cluster_overview.get('active_node_count', '-'))}</div>
          <div class="kv-item"><strong>过期平面</strong>{_escape(_display(scheduler_authority.get('stale_plane_detected', False)))}</div>
        </div>
      </section>
      <section class="panel">
        <h3>已提交租约</h3>
        <div class="kv">
          <div class="kv-item"><strong>拥有者</strong>{_escape(active_committed.get('control_plane_id', '-'))}</div>
          <div class="kv-item"><strong>租约 Epoch</strong>{_escape(active_committed.get('lease_epoch', '-'))}</div>
          <div class="kv-item"><strong>栅栏令牌</strong>{_escape(active_committed.get('fencing_token', '-'))}</div>
          <div class="kv-item"><strong>本地平面</strong>{_escape(takeover_state.get('local_control_plane_id', '-'))}</div>
          <div class="kv-item"><strong>当前拥有者为本地</strong>{_escape(_display(takeover_state.get('active_owner_is_local', '-')))}</div>
          <div class="kv-item"><strong>交接次数</strong>{_escape(takeover_state.get('handoff_count', '-'))}</div>
        </div>
      </section>
    </div>
    <section class="panel" style="margin-top:16px;">
      <h3>接管历史</h3>
      {_json_block(handoff_history)}
    </section>
    """
    return _layout(f"运行 {run['run_id']}", body, notice=notice)


def render_reviews(*, rows: list[dict[str, Any]], notice: str | None = None) -> str:
    options = "".join(
        f"""
        <label style="display:flex; gap:8px; align-items:flex-start; padding:8px 0;">
          <input type="checkbox" name="run_id" value="{_escape(row['run']['run_id'])}" checked>
          <span><strong>{_escape(row['run']['run_id'])}</strong><br>{_escape(row['run']['goal'])}</span>
        </label>
        """
        for row in rows
    ) or "<p class='muted'>暂无待审查运行。</p>"
    table = "".join(
        f"""
        <tr>
          <td><a href="/ui/runs/{_escape(row['run']['run_id'])}">{_escape(row['run']['run_id'])}</a></td>
          <td>{_escape(row['run']['goal'])}</td>
          <td>{_escape(_display(row['latest_auto_review_verdict']['decision'] if row['latest_auto_review_verdict'] else '-'))}</td>
          <td>{_escape(_display(row['review_recommended_action']))}</td>
          <td>
            <form class="inline" method="post" action="/ui/actions/{_escape(row['run']['run_id'])}/approve"><button type="submit">通过</button></form>
            <form class="inline" method="post" action="/ui/actions/{_escape(row['run']['run_id'])}/reject"><button class="warn" type="submit">拒绝</button></form>
          </td>
        </tr>
        """
        for row in rows
    ) or '<tr><td colspan="5" class="muted">暂无待审查运行。</td></tr>'
    body = f"""
    <div class="split">
      <section class="panel">
        <h2>待审查控制台</h2>
        <table>
          <thead>
            <tr><th>运行</th><th>目标</th><th>最近自动审查结论</th><th>建议</th><th>动作</th></tr>
          </thead>
          <tbody>{table}</tbody>
        </table>
      </section>
      <section class="panel">
        <h2>批量继续</h2>
        <form method="post" action="/ui/actions/batch-resume">
          {options}
          <div style="margin-top:14px;">
            <button type="submit">批量继续选中运行</button>
          </div>
        </form>
      </section>
    </div>
    """
    return _layout("审查控制台", body, notice=notice)


def render_governance(*, reports: dict[str, Any], cluster_overview: dict[str, Any] | None = None, notice: str | None = None) -> str:
    cluster = cluster_overview or {}
    body = f"""
    <div class="grid">
      <section class="panel"><h2>技术债</h2>{_json_block(reports['tech_debt'])}</section>
      <section class="panel"><h2>审查策略</h2>{_json_block(reports['review_policy'])}</section>
      <section class="panel"><h2>指标</h2>{_json_block(reports['metrics'])}</section>
      <section class="panel"><h2>告警</h2>{_json_block(reports['alerts'])}</section>
      <section class="panel"><h2>发布就绪</h2>{_json_block(reports['release_readiness'])}</section>
      <section class="panel"><h2>领域包</h2>{_json_block(reports['domain_packs'])}</section>
      <section class="panel"><h2>调度权威拓扑</h2>{_cluster_status_banner(cluster)}{_json_block(cluster)}</section>
    </div>
    """
    return _layout("治理", body, notice=notice)


def render_workbench(
    *,
    session_payload: dict[str, Any] | None,
    presets: list[dict[str, Any]],
    cluster_templates: list[dict[str, Any]],
    recent_sessions: list[dict[str, Any]],
    effective_config: dict[str, Any],
    notice: str | None = None,
) -> str:
    preset_options = "".join(
        f'<option value="{_escape(item["preset_id"])}">{_escape(item["preset_id"])}</option>'
        for item in presets
    )
    cluster_options = "".join(
        f'<option value="{_escape(item["template_id"])}">{_escape(item["name"])}</option>'
        for item in cluster_templates
    )
    chat_panel = _workbench_chat_panel(session_payload)
    preview_form = f"""
    <section class="panel">
      <h2>交互式工作台</h2>
      <p class="muted">创建意图会话、查看目标包和集群预览、确认执行默认值，然后进入现有操作员流程。</p>
      <form method="post" action="/ui/workbench/preview">
        <div class="kv">
          <div class="kv-item"><strong>目标</strong><textarea name="goal" rows="4" style="width:100%;" placeholder="描述这次运行要产出的目标、文件或决策。"></textarea></div>
          <div class="kv-item"><strong>偏好预设</strong><select name="preset_id"><option value="">自动</option>{preset_options}</select></div>
          <div class="kv-item"><strong>偏好集群</strong><select name="cluster_template_id"><option value="">自动</option>{cluster_options}</select></div>
          <div class="kv-item"><strong>约束</strong><textarea name="constraints" rows="4" style="width:100%;" placeholder="每行一个约束。"></textarea></div>
          <div class="kv-item"><strong>假设</strong><textarea name="assumptions" rows="4" style="width:100%;" placeholder="每行一个假设。"></textarea></div>
          <div class="kv-item"><strong>相关文件路径</strong><textarea name="referenced_artifact_paths" rows="4" style="width:100%;" placeholder="每行一个相关路径。"></textarea></div>
          <div class="kv-item"><strong>后续事项背景</strong><textarea name="followup_context" rows="4" style="width:100%;" placeholder="之前的决策、拒绝原因或操作员上下文。"></textarea></div>
        </div>
        <div style="margin-top:14px;"><button type="submit">预览目标包</button></div>
      </form>
    </section>
    """
    if session_payload is None:
        body = f"""
        {chat_panel}
        {preview_form}
        <div class="split" style="margin-top:16px;">
          <section class="panel">
            <h2>执行默认值</h2>
            <p class="muted">当前执行默认值会投影到工作台中，便于启动前检查。</p>
            {_json_block(effective_config.get('execution_defaults'))}
          </section>
          <section class="panel">
            <h2>最近会话</h2>
            {_session_table(recent_sessions)}
          </section>
        </div>
        """
        return _layout("交互式工作台", body, notice=notice)

    session = session_payload["session"]
    clarification_state = session.get("clarification_state") or {}
    plan_draft = session_payload.get("plan_draft")
    goal_packet = session_payload.get("goal_packet") or {}
    selected_clusters = goal_packet.get("selected_clusters", [])
    followup_requests = session_payload.get("followup_requests") or []
    active_run_operator_view = session_payload.get("active_run_operator_view") or {}
    generated_profiles = session_payload.get("generated_profiles") or []
    automation_watchdogs = session_payload.get("automation_watchdogs") or []
    automation_evaluation = session_payload.get("automation_evaluation") or {}
    active_run = active_run_operator_view.get("run") or {}
    active_status_detail = active_run_operator_view.get("status_detail") or {}
    clarification_prompts = clarification_state.get("prompts") or []
    clarification_inputs = "".join(
        f"""
        <label class="kv-item">
          <strong>{_escape(prompt.get('question', '澄清问题'))}</strong>
          <input type="text" name="answer_{_escape(prompt.get('prompt_id', ''))}" value="{_escape(prompt.get('answer') or '')}">
        </label>
        """
        for prompt in clarification_prompts
    ) or '<div class="kv-item"><strong>澄清项</strong>暂无阻塞性澄清问题。</div>'
    selected_cluster_labels = ", ".join(item["name"] for item in selected_clusters) or "单路径预设"
    selected_cluster_ids = ", ".join(item["template_id"] for item in selected_clusters) or "自动"
    active_run_link = (
        f'<a href="/ui/runs/{_escape(session["active_run_id"])}">{_escape(session["active_run_id"])}</a>'
        if session.get("active_run_id")
        else "-"
    )
    launch_block = (
        f"""
        <form class="inline" method="post" action="/ui/workbench/{_escape(session['session_id'])}/launch">
          <label><input type="checkbox" name="execute" value="true"> 立即执行</label>
          <button type="submit">启动</button>
        </form>
        """
        if plan_draft is not None
        else "<span class='muted'>生成计划草案后即可启动。</span>"
    )
    followup_rows = "".join(
        f"""
        <tr>
          <td>{_escape(item.get('request_id'))}</td>
          <td>{_pill(str(item.get('status', '-')), _status_tone(str(item.get('status', '-'))))}</td>
          <td>{_escape(item.get('intent') or '-')}</td>
          <td>{_escape(_display(item.get('blocking')))}</td>
          <td>{_escape(item.get('instruction') or '-')}</td>
        </tr>
        """
        for item in followup_requests
    ) or '<tr><td colspan="5" class="muted">暂无后续事项请求。</td></tr>'
    generated_profile_rows = "".join(
        f"""
        <tr>
          <td>{_escape(item.get('generated_profile_id'))}</td>
          <td>{_escape(item.get('base_profile_id') or '-')}</td>
          <td>{_escape(item.get('role_label') or '-')}</td>
          <td>{_escape(item.get('cluster_template_id') or '-')}</td>
          <td>{_escape(', '.join(item.get('repo_scope_paths') or [])) or '-'}</td>
        </tr>
        """
        for item in generated_profiles
    ) or '<tr><td colspan="5" class="muted">暂无已生成的角色配置。</td></tr>'
    watchdog_rows = "".join(
        f"""
        <tr>
          <td>{_escape(item.get('watchdog_id'))}</td>
          <td>{_escape(item.get('trigger') or '-')}</td>
          <td>{_pill(str(item.get('status', '-')), _status_tone(str(item.get('status', '-'))))}</td>
          <td>{_escape(item.get('objective') or '-')}</td>
        </tr>
        """
        for item in automation_watchdogs
    ) or '<tr><td colspan="4" class="muted">暂无自动化观察器。</td></tr>'
    watchdog_action_rows = "".join(
        f"""
        <tr>
          <td>{_escape(item.get('trigger') or '-')}</td>
          <td>{_escape(_display(item.get('action_type') or '-'))}</td>
          <td>{_escape(_display(item.get('risk_level') or '-'))}</td>
          <td>{_escape(_display(item.get('requires_review')))}</td>
          <td>{_escape(item.get('summary') or '-')}</td>
        </tr>
        """
        for item in automation_evaluation.get("actions", [])
    ) or '<tr><td colspan="5" class="muted">暂无自动化动作投影。</td></tr>'
    active_checkpoint = (
        f"""
        <div class="kv">
          <div class="kv-item"><strong>运行</strong><a href="/ui/runs/{_escape(active_run.get('run_id'))}">{_escape(active_run.get('run_id'))}</a></div>
          <div class="kv-item"><strong>状态</strong>{_pill(str(active_run.get('status', '-')), _status_tone(str(active_run.get('status', '-'))))}</div>
          <div class="kv-item"><strong>审查状态</strong>{_pill(str(active_status_detail.get('effective_review_state', '-')), _review_tone(str(active_status_detail.get('effective_review_state', '-'))))}</div>
          <div class="kv-item"><strong>下一步</strong>{_escape(_display(active_status_detail.get('next_action') or '-'))}</div>
          <div class="kv-item"><strong>可恢复性</strong>{_escape(_display(active_status_detail.get('recoverability_hint') or '-'))}</div>
          <div class="kv-item"><strong>审查控制台</strong><a href="/ui/reviews">打开审查队列</a></div>
        </div>
        """
        if active_run
        else "<p class='muted'>当前会话还没有绑定 active run。</p>"
    )
    body = f"""
    {chat_panel}
    {preview_form}
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h2>会话</h2>
        <div class="kv">
          <div class="kv-item"><strong>会话 ID</strong>{_escape(session['session_id'])}</div>
          <div class="kv-item"><strong>状态</strong>{_escape(_display(session['status']))}</div>
          <div class="kv-item"><strong>目标</strong>{_escape(session.get('intent_packet', {}).get('goal') or '-')}</div>
          <div class="kv-item"><strong>偏好预设</strong>{_escape(_display(session.get('intent_packet', {}).get('preferred_preset_id') or 'auto'))}</div>
          <div class="kv-item"><strong>选中集群路径</strong>{_escape(selected_cluster_labels)}</div>
          <div class="kv-item"><strong>集群模板 ID</strong>{_escape(selected_cluster_ids)}</div>
          <div class="kv-item"><strong>当前运行</strong>{active_run_link}</div>
        </div>
        <form method="post" action="/ui/workbench/{_escape(session['session_id'])}/clarify" style="margin-top:16px;">
          <div class="kv">{clarification_inputs}</div>
          <div class="actions" style="margin-top:14px;"><button type="submit">刷新计划草案</button></div>
        </form>
        <div class="actions">{launch_block}</div>
      </section>
      <section class="panel">
        <h2>计划草案</h2>
        {_json_block(plan_draft)}
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h2>执行默认值</h2>
        {_json_block(effective_config.get('execution_defaults'))}
      </section>
      <section class="panel">
        <h2>当前运行检查点</h2>
        {active_checkpoint}
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h2>目标包</h2>
        {_json_block(goal_packet)}
      </section>
      <section class="panel">
        <h2>集群图</h2>
        {_json_block(goal_packet.get('cluster_graph'))}
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h2>策略预览</h2>
        {_json_block(goal_packet.get('capability_policy_preview'))}
      </section>
      <section class="panel">
        <h2>集群策略预览</h2>
        {_json_block(goal_packet.get('cluster_policy_preview'))}
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h2>后续事项队列</h2>
        <table>
          <thead>
            <tr><th>请求</th><th>状态</th><th>意图</th><th>是否阻塞</th><th>指令</th></tr>
          </thead>
          <tbody>{followup_rows}</tbody>
        </table>
        <form method="post" action="/ui/workbench/{_escape(session['session_id'])}/followup" style="margin-top:16px;">
          <input type="hidden" name="run_id" value="{_escape(session.get('active_run_id') or '')}">
          <div class="kv">
            <div class="kv-item"><strong>指令</strong><textarea name="instruction" rows="4" style="width:100%;" placeholder="记录下一条有边界的后续事项请求。"></textarea></div>
            <div class="kv-item"><strong>意图</strong><input type="text" name="intent" value="continue"></div>
            <div class="kv-item"><strong>阻塞</strong><label><input type="checkbox" name="blocking" value="true"> 收口前需要操作员处理</label></div>
          </div>
          <div class="actions" style="margin-top:14px;"><button type="submit">加入后续事项</button></div>
        </form>
      </section>
      <section class="panel">
        <h2>最近会话</h2>
        {_session_table(recent_sessions)}
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h2>已生成角色配置</h2>
        <p class="muted">M37 的会话级角色物化保持 additive 和可审查。</p>
        <form class="inline" method="post" action="/ui/workbench/{_escape(session['session_id'])}/generate-profiles" style="margin-bottom:12px;">
          <button type="submit">生成会话角色配置</button>
        </form>
        <table>
          <thead>
            <tr><th>配置</th><th>基础角色</th><th>角色标签</th><th>集群</th><th>仓库范围</th></tr>
          </thead>
          <tbody>{generated_profile_rows}</tbody>
        </table>
      </section>
      <section class="panel">
        <h2>自动化观察器</h2>
        <p class="muted">有边界的观察器只投影低风险自动化提示，不绕过审查门。</p>
        <table>
          <thead>
            <tr><th>观察器</th><th>触发器</th><th>状态</th><th>目标</th></tr>
          </thead>
          <tbody>{watchdog_rows}</tbody>
        </table>
        <table style="margin-top:16px;">
          <thead>
            <tr><th>触发器</th><th>动作</th><th>风险</th><th>审查</th><th>摘要</th></tr>
          </thead>
          <tbody>{watchdog_action_rows}</tbody>
        </table>
      </section>
    </div>
    """
    return _layout("交互式工作台", body, notice=notice)


def render_config(*, effective_config: dict[str, Any], notice: str | None = None) -> str:
    body = f"""
    <section class="panel">
      <h2>有效配置</h2>
      {_json_block(effective_config)}
    </section>
    """
    return _layout("配置", body, notice=notice)
