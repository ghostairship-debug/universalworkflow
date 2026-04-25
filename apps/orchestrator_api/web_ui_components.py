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
        '<div class="notice notice-compact">'
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
  <link rel="stylesheet" href="/static/operator.css">
  <script defer src="/static/workbench.js"></script>
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
            <textarea class="field-full" name="rationale" rows="2" placeholder="可选：确认理由"></textarea>
            <div class="actions actions-compact"><button class="warn" type="submit">确认执行</button></div>
          </form>
        </div>
        """
    pr_block = ""
    if isinstance(pr_ready_summary, dict):
        pr_block = f"""
        <details class="details-spaced">
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
              <form class="form-spaced" method="post" action="/ui/workbench/chat">
                <textarea class="field-full" name="message" rows="4" placeholder="例如：为当前项目做 M39 流式聊天工作台的计划预览"></textarea>
                <div class="actions mt-10"><button type="submit">发送并创建会话</button></div>
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
          <div id="chat-stream" class="chat-transcript" data-session-id="{_escape(session_id)}" data-stream-url="{_escape(stream_url)}">
            {transcript}
          </div>
          <form id="chat-form" class="form-spaced" method="post" action="/ui/workbench/chat">
            <input type="hidden" name="session_id" value="{_escape(session_id)}">
            <textarea class="field-full" name="message" rows="4" placeholder="输入：预览计划 / 启动 / 继续 / 总结 / PR 摘要 / 排查失败 / 加入后续事项"></textarea>
            <div class="actions mt-10"><button id="chat-submit" type="submit">发送</button></div>
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
    </section>
    """
