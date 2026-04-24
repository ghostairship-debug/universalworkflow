from __future__ import annotations

import html
import json
from typing import Any


def _escape(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _json_block(payload: Any) -> str:
    return f"<pre>{_escape(json.dumps(payload, ensure_ascii=False, indent=2))}</pre>"


def _pill(value: str, tone: str = "neutral") -> str:
    return f'<span class="pill pill-{tone}">{_escape(value)}</span>'


def _cluster_status_banner(cluster: dict[str, Any] | None) -> str:
    payload = cluster or {}
    if payload.get("enabled", True):
        return ""
    return (
        '<div class="notice" style="margin-bottom:12px;">'
        "Scheduler authority cluster disabled (local-only mode)."
        "</div>"
    )


def _nav() -> str:
    links = [
        ('/ui', 'Dashboard'),
        ('/ui/runs', 'Runs'),
        ('/ui/workbench', 'Workbench'),
        ('/ui/reviews', 'Reviews'),
        ('/ui/governance', 'Governance'),
        ('/ui/config', 'Config'),
    ]
    items = "".join(
        f'<a class="nav-link" href="{href}">{_escape(label)}</a>'
        for href, label in links
    )
    return f'<nav class="nav">{items}</nav>'


def _layout(title: str, body: str, *, notice: str | None = None) -> str:
    notice_block = f'<div class="notice">{_escape(notice)}</div>' if notice else ""
    return f"""<!doctype html>
<html lang="en">
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
    .muted {{ color: var(--muted); }}
    @media (max-width: 900px) {{
      .split {{ grid-template-columns: 1fr; }}
      .hero h1 {{ font-size: 26px; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>{_escape(title)}</h1>
      <p>Universal Agentic Workflow OS Web Operator Surface</p>
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
          <td>{_escape(normalized['next_action'])}</td>
          <td>{_escape(normalized['run']['goal'])}</td>
        </tr>
        """
        for normalized in (_as_run_row(row) for row in rows)
    )
    if not body:
        body = '<tr><td colspan="6" class="muted">No runs found.</td></tr>'
    return f"""
    <table>
      <thead>
        <tr>
          <th>Run ID</th>
          <th>Preset</th>
          <th>Status</th>
          <th>Review</th>
          <th>Next</th>
          <th>Goal</th>
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
          <td>{_escape(row.get('intent_packet', {}).get('preferred_preset_id') or 'auto')}</td>
          <td>{_escape(row.get('active_run_id') or '-')}</td>
          <td>{_escape(row.get('intent_packet', {}).get('goal') or '-')}</td>
        </tr>
        """
        for row in rows
    )
    if not body:
        body = '<tr><td colspan="5" class="muted">No recent sessions yet.</td></tr>'
    return f"""
    <table>
      <thead>
        <tr>
          <th>Session</th>
          <th>Status</th>
          <th>Preset</th>
          <th>Active Run</th>
          <th>Goal</th>
        </tr>
      </thead>
      <tbody>{body}</tbody>
    </table>
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
          <div class="kv-item"><strong>Selected Run</strong>{_escape(focus['run']['run_id'])}</div>
          <div class="kv-item"><strong>Status</strong>{_escape(focus['run']['status'])}</div>
          <div class="kv-item"><strong>Review</strong>{_escape(focus['effective_review_state'])}</div>
          <div class="kv-item"><strong>Next Action</strong>{_escape(focus['next_action'])}</div>
          <div class="kv-item"><strong>Recoverability</strong>{_escape(focus['recoverability_hint'])}</div>
          <div class="kv-item"><strong>Gateway</strong>{_escape(snapshot['runtime_gateway']['provider'])}</div>
        </div>
        """
        if focus is not None
        else '<p class="muted">No focused run yet.</p>'
    )
    review_rows = "".join(
        f"""
        <li>
          <a href="/ui/runs/{_escape(row['run']['run_id'])}">{_escape(row['run']['run_id'])}</a>
          — {_escape(row['run']['goal'])} — {_escape(row['review_recommended_action'])}
        </li>
        """
        for row in pending_reviews[:6]
    ) or '<li class="muted">No pending reviews.</li>'
    cluster = cluster_overview or snapshot.get("cluster_overview") or {}
    body = f"""
    <section class="stats">
      <div class="stat"><div class="stat-label">Run Count</div><div class="stat-value">{snapshot['run_count']}</div></div>
      <div class="stat"><div class="stat-label">Pending Reviews</div><div class="stat-value">{len(pending_reviews)}</div></div>
      <div class="stat"><div class="stat-label">Open Debt</div><div class="stat-value">{governance['tech_debt']['open_debt_count']}</div></div>
      <div class="stat"><div class="stat-label">Config Path</div><div class="stat-value">{_escape(effective_config['config_path'] or '-')}</div></div>
    </section>
    <div class="split">
      <section class="panel">
        <h2>Recent Runs</h2>
        {_run_table(snapshot['runs'])}
      </section>
      <section class="panel">
        <h2>Focus</h2>
        {focus_block}
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h2>Pending Reviews</h2>
        <ul class="timeline">{review_rows}</ul>
      </section>
      <section class="panel">
        <h2>Governance Snapshot</h2>
        <div class="kv">
          <div class="kv-item"><strong>Release Ready</strong>{_escape(governance['release_readiness']['overall_ready'])}</div>
          <div class="kv-item"><strong>Alert Count</strong>{_escape(governance['alerts']['alert_count'])}</div>
          <div class="kv-item"><strong>Tracked Runs</strong>{_escape(governance['metrics']['runtime_inventory']['counts']['runs'])}</div>
          <div class="kv-item"><strong>Policy Count</strong>{_escape(governance['review_policy']['supported_policy_count'])}</div>
        </div>
      </section>
    </div>
    <section class="panel" style="margin-top:16px;">
      <h2>Authority Topology</h2>
      {_cluster_status_banner(cluster)}
      <div class="kv">
        <div class="kv-item"><strong>Mode</strong>{_escape(cluster.get('mode', '-'))}</div>
        <div class="kv-item"><strong>Authority Node</strong>{_escape(cluster.get('authority_node_id', cluster.get('leader_node_id', '-')))}</div>
        <div class="kv-item"><strong>Authority Term</strong>{_escape(cluster.get('authority_term_no', cluster.get('term_no', '-')))}</div>
        <div class="kv-item"><strong>Quorum</strong>{_escape(cluster.get('quorum_size', '-'))}</div>
        <div class="kv-item"><strong>Active Nodes</strong>{_escape(cluster.get('active_node_count', '-'))}</div>
        <div class="kv-item"><strong>Decision Index</strong>{_escape(cluster.get('decision_index', cluster.get('commit_index', '-')))}</div>
      </div>
    </section>
    """
    return _layout("Operator Dashboard", body, notice=notice)


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
      <h2>Run Catalog</h2>
      <form class="actions" method="get" action="/ui/runs">
        <input type="text" name="status" placeholder="status" value="{_escape(status_filter or '')}">
        <input type="text" name="preset_id" placeholder="preset_id" value="{_escape(preset_filter or '')}">
        <input type="number" name="limit" min="1" value="{limit}">
        <button type="submit">Apply Filters</button>
      </form>
      {_run_table(rows)}
    </section>
    """
    return _layout("Run Explorer", body, notice=notice)


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
    ) or "<li class='muted'>No timeline yet.</li>"
    problems = "".join(
        f"<li><strong>{_escape(problem['problem'])}</strong> — {_escape(problem['description'])}</li>"
        for problem in inspection["problems"]
    ) or "<li class='muted'>Inspection passed cleanly.</li>"
    body = f"""
    <section class="panel">
      <h2>{_escape(run['run_id'])}</h2>
      <p>{_escape(run['goal'])}</p>
      <div class="actions">
        <form class="inline" method="post" action="/ui/actions/{_escape(run['run_id'])}/resume"><button type="submit">Resume</button></form>
        <form class="inline" method="post" action="/ui/actions/{_escape(run['run_id'])}/approve"><button type="submit">Approve</button></form>
        <form class="inline" method="post" action="/ui/actions/{_escape(run['run_id'])}/reject"><button class="warn" type="submit">Reject</button></form>
        <form class="inline" method="post" action="/ui/actions/{_escape(run['run_id'])}/reconcile"><button class="secondary" type="submit">Reconcile</button></form>
        <form class="inline" method="post" action="/ui/actions/{_escape(run['run_id'])}/cancel"><button class="danger" type="submit">Cancel</button></form>
      </div>
      <div class="kv">
        <div class="kv-item"><strong>Status</strong>{_escape(run['status'])}</div>
        <div class="kv-item"><strong>Review State</strong>{_escape(detail['effective_review_state'])}</div>
        <div class="kv-item"><strong>Next Action</strong>{_escape(detail['next_action'])}</div>
        <div class="kv-item"><strong>Recoverability</strong>{_escape(detail['recoverability_hint'])}</div>
        <div class="kv-item"><strong>Adapter</strong>{_escape(detail['capability_resolution']['adapter_name'] if detail['capability_resolution'] else '-')}</div>
        <div class="kv-item"><strong>Execution Lane</strong>{_escape(detail['execution_lane'])}</div>
      </div>
    </section>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h3>Summary</h3>
        <p><strong>{_escape(summary['headline'])}</strong></p>
        <ul class="timeline">{''.join(f'<li>{_escape(line)}</li>' for line in summary['summary_lines'])}</ul>
      </section>
      <section class="panel">
        <h3>Inspection</h3>
        <div class="kv">
          <div class="kv-item"><strong>Passed</strong>{_escape(inspection['passed'])}</div>
          <div class="kv-item"><strong>Problem Count</strong>{_escape(inspection['problem_count'])}</div>
          <div class="kv-item"><strong>Recommended Action</strong>{_escape(inspection['recommended_action'])}</div>
        </div>
        <ul class="timeline" style="margin-top:12px;">{problems}</ul>
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h3>Timeline Tail</h3>
        <ul class="timeline">{timeline_items}</ul>
      </section>
      <section class="panel">
        <h3>Replay Packet Excerpt</h3>
        {_json_block(operator_view['replay_packet_excerpt'])}
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h3>Orchestration</h3>
        {_json_block(operator_view['orchestration'])}
      </section>
      <section class="panel">
        <h3>Status Detail</h3>
        {_json_block(detail)}
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h3>Authority Topology</h3>
        {_cluster_status_banner(cluster_overview)}
        <div class="kv">
          <div class="kv-item"><strong>Authority Node</strong>{_escape(cluster_overview.get('authority_node_id', cluster_overview.get('leader_node_id', '-')))}</div>
          <div class="kv-item"><strong>Authority Term</strong>{_escape(cluster_overview.get('authority_term_no', cluster_overview.get('term_no', '-')))}</div>
          <div class="kv-item"><strong>Quorum</strong>{_escape(cluster_overview.get('quorum_size', '-'))}</div>
          <div class="kv-item"><strong>Decision Index</strong>{_escape(cluster_overview.get('decision_index', cluster_overview.get('commit_index', '-')))}</div>
          <div class="kv-item"><strong>Active Nodes</strong>{_escape(cluster_overview.get('active_node_count', '-'))}</div>
          <div class="kv-item"><strong>Stale Plane</strong>{_escape(scheduler_authority.get('stale_plane_detected', False))}</div>
        </div>
      </section>
      <section class="panel">
        <h3>Committed Lease</h3>
        <div class="kv">
          <div class="kv-item"><strong>Owner</strong>{_escape(active_committed.get('control_plane_id', '-'))}</div>
          <div class="kv-item"><strong>Lease Epoch</strong>{_escape(active_committed.get('lease_epoch', '-'))}</div>
          <div class="kv-item"><strong>Fencing Token</strong>{_escape(active_committed.get('fencing_token', '-'))}</div>
          <div class="kv-item"><strong>Local Plane</strong>{_escape(takeover_state.get('local_control_plane_id', '-'))}</div>
          <div class="kv-item"><strong>Active Owner Is Local</strong>{_escape(takeover_state.get('active_owner_is_local', '-'))}</div>
          <div class="kv-item"><strong>Handoff Count</strong>{_escape(takeover_state.get('handoff_count', '-'))}</div>
        </div>
      </section>
    </div>
    <section class="panel" style="margin-top:16px;">
      <h3>Takeover History</h3>
      {_json_block(handoff_history)}
    </section>
    """
    return _layout(f"Run {run['run_id']}", body, notice=notice)


def render_reviews(*, rows: list[dict[str, Any]], notice: str | None = None) -> str:
    options = "".join(
        f"""
        <label style="display:flex; gap:8px; align-items:flex-start; padding:8px 0;">
          <input type="checkbox" name="run_id" value="{_escape(row['run']['run_id'])}" checked>
          <span><strong>{_escape(row['run']['run_id'])}</strong><br>{_escape(row['run']['goal'])}</span>
        </label>
        """
        for row in rows
    ) or "<p class='muted'>No pending review runs.</p>"
    table = "".join(
        f"""
        <tr>
          <td><a href="/ui/runs/{_escape(row['run']['run_id'])}">{_escape(row['run']['run_id'])}</a></td>
          <td>{_escape(row['run']['goal'])}</td>
          <td>{_escape(row['latest_auto_review_verdict']['decision'] if row['latest_auto_review_verdict'] else '-')}</td>
          <td>{_escape(row['review_recommended_action'])}</td>
          <td>
            <form class="inline" method="post" action="/ui/actions/{_escape(row['run']['run_id'])}/approve"><button type="submit">Approve</button></form>
            <form class="inline" method="post" action="/ui/actions/{_escape(row['run']['run_id'])}/reject"><button class="warn" type="submit">Reject</button></form>
          </td>
        </tr>
        """
        for row in rows
    ) or '<tr><td colspan="5" class="muted">No pending reviews.</td></tr>'
    body = f"""
    <div class="split">
      <section class="panel">
        <h2>Pending Review Console</h2>
        <table>
          <thead>
            <tr><th>Run</th><th>Goal</th><th>Latest Auto Verdict</th><th>Recommended</th><th>Actions</th></tr>
          </thead>
          <tbody>{table}</tbody>
        </table>
      </section>
      <section class="panel">
        <h2>Batch Resume</h2>
        <form method="post" action="/ui/actions/batch-resume">
          {options}
          <div style="margin-top:14px;">
            <button type="submit">Batch Resume Selected</button>
          </div>
        </form>
      </section>
    </div>
    """
    return _layout("Review Console", body, notice=notice)


def render_governance(*, reports: dict[str, Any], cluster_overview: dict[str, Any] | None = None, notice: str | None = None) -> str:
    cluster = cluster_overview or {}
    body = f"""
    <div class="grid">
      <section class="panel"><h2>Tech Debt</h2>{_json_block(reports['tech_debt'])}</section>
      <section class="panel"><h2>Review Policy</h2>{_json_block(reports['review_policy'])}</section>
      <section class="panel"><h2>Metrics</h2>{_json_block(reports['metrics'])}</section>
      <section class="panel"><h2>Alerts</h2>{_json_block(reports['alerts'])}</section>
      <section class="panel"><h2>Release Readiness</h2>{_json_block(reports['release_readiness'])}</section>
      <section class="panel"><h2>Domain Packs</h2>{_json_block(reports['domain_packs'])}</section>
      <section class="panel"><h2>Authority Topology</h2>{_cluster_status_banner(cluster)}{_json_block(cluster)}</section>
    </div>
    """
    return _layout("Governance", body, notice=notice)


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
    preview_form = f"""
    <section class="panel">
      <h2>Interaction-First Workbench</h2>
      <p class="muted">Create an intent session, inspect the goal packet and cluster preview, surface execution defaults, then launch into the existing operator surface.</p>
      <form method="post" action="/ui/workbench/preview">
        <div class="kv">
          <div class="kv-item"><strong>Goal</strong><textarea name="goal" rows="4" style="width:100%;" placeholder="Describe the objective, artifact, or decision you want this run to produce."></textarea></div>
          <div class="kv-item"><strong>Preferred Preset</strong><select name="preset_id"><option value="">auto</option>{preset_options}</select></div>
          <div class="kv-item"><strong>Preferred Cluster</strong><select name="cluster_template_id"><option value="">auto</option>{cluster_options}</select></div>
          <div class="kv-item"><strong>Constraints</strong><textarea name="constraints" rows="4" style="width:100%;" placeholder="One constraint per line."></textarea></div>
          <div class="kv-item"><strong>Assumptions</strong><textarea name="assumptions" rows="4" style="width:100%;" placeholder="One assumption per line."></textarea></div>
          <div class="kv-item"><strong>Artifact Paths</strong><textarea name="referenced_artifact_paths" rows="4" style="width:100%;" placeholder="One referenced path per line."></textarea></div>
          <div class="kv-item"><strong>Follow-Up Context</strong><textarea name="followup_context" rows="4" style="width:100%;" placeholder="Prior decision, rejection, or operator context."></textarea></div>
        </div>
        <div style="margin-top:14px;"><button type="submit">Preview Goal Packet</button></div>
      </form>
    </section>
    """
    if session_payload is None:
        body = f"""
        {preview_form}
        <div class="split" style="margin-top:16px;">
          <section class="panel">
            <h2>Execution Defaults</h2>
            <p class="muted">Current M35 execution defaults projected into the workbench.</p>
            {_json_block(effective_config.get('execution_defaults'))}
          </section>
          <section class="panel">
            <h2>Recent Sessions</h2>
            {_session_table(recent_sessions)}
          </section>
        </div>
        """
        return _layout("Interaction Workbench", body, notice=notice)

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
          <strong>{_escape(prompt.get('question', 'Clarification'))}</strong>
          <input type="text" name="answer_{_escape(prompt.get('prompt_id', ''))}" value="{_escape(prompt.get('answer') or '')}">
        </label>
        """
        for prompt in clarification_prompts
    ) or '<div class="kv-item"><strong>Clarifications</strong>No blocking clarification prompts.</div>'
    selected_cluster_labels = ", ".join(item["name"] for item in selected_clusters) or "single-path preset"
    selected_cluster_ids = ", ".join(item["template_id"] for item in selected_clusters) or "auto"
    active_run_link = (
        f'<a href="/ui/runs/{_escape(session["active_run_id"])}">{_escape(session["active_run_id"])}</a>'
        if session.get("active_run_id")
        else "-"
    )
    launch_block = (
        f"""
        <form class="inline" method="post" action="/ui/workbench/{_escape(session['session_id'])}/launch">
          <label><input type="checkbox" name="execute" value="true"> execute immediately</label>
          <button type="submit">Launch</button>
        </form>
        """
        if plan_draft is not None
        else "<span class='muted'>Launch becomes available once the session has a plan draft.</span>"
    )
    followup_rows = "".join(
        f"""
        <tr>
          <td>{_escape(item.get('request_id'))}</td>
          <td>{_pill(str(item.get('status', '-')), _status_tone(str(item.get('status', '-'))))}</td>
          <td>{_escape(item.get('intent') or '-')}</td>
          <td>{_escape(item.get('blocking'))}</td>
          <td>{_escape(item.get('instruction') or '-')}</td>
        </tr>
        """
        for item in followup_requests
    ) or '<tr><td colspan="5" class="muted">No follow-up requests queued.</td></tr>'
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
    ) or '<tr><td colspan="5" class="muted">No generated profiles materialized yet.</td></tr>'
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
    ) or '<tr><td colspan="4" class="muted">No automation watchdogs registered yet.</td></tr>'
    watchdog_action_rows = "".join(
        f"""
        <tr>
          <td>{_escape(item.get('trigger') or '-')}</td>
          <td>{_escape(item.get('action_type') or '-')}</td>
          <td>{_escape(item.get('risk_level') or '-')}</td>
          <td>{_escape(item.get('requires_review'))}</td>
          <td>{_escape(item.get('summary') or '-')}</td>
        </tr>
        """
        for item in automation_evaluation.get("actions", [])
    ) or '<tr><td colspan="5" class="muted">No automation actions projected yet.</td></tr>'
    active_checkpoint = (
        f"""
        <div class="kv">
          <div class="kv-item"><strong>Run</strong><a href="/ui/runs/{_escape(active_run.get('run_id'))}">{_escape(active_run.get('run_id'))}</a></div>
          <div class="kv-item"><strong>Status</strong>{_pill(str(active_run.get('status', '-')), _status_tone(str(active_run.get('status', '-'))))}</div>
          <div class="kv-item"><strong>Review State</strong>{_pill(str(active_status_detail.get('effective_review_state', '-')), _review_tone(str(active_status_detail.get('effective_review_state', '-'))))}</div>
          <div class="kv-item"><strong>Next Action</strong>{_escape(active_status_detail.get('next_action') or '-')}</div>
          <div class="kv-item"><strong>Recoverability</strong>{_escape(active_status_detail.get('recoverability_hint') or '-')}</div>
          <div class="kv-item"><strong>Review Console</strong><a href="/ui/reviews">Open review queue</a></div>
        </div>
        """
        if active_run
        else "<p class='muted'>No active run is attached to this session yet.</p>"
    )
    body = f"""
    {preview_form}
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h2>Session</h2>
        <div class="kv">
          <div class="kv-item"><strong>Session ID</strong>{_escape(session['session_id'])}</div>
          <div class="kv-item"><strong>Status</strong>{_escape(session['status'])}</div>
          <div class="kv-item"><strong>Goal</strong>{_escape(session.get('intent_packet', {}).get('goal') or '-')}</div>
          <div class="kv-item"><strong>Preferred Preset</strong>{_escape(session.get('intent_packet', {}).get('preferred_preset_id') or 'auto')}</div>
          <div class="kv-item"><strong>Selected Cluster Path</strong>{_escape(selected_cluster_labels)}</div>
          <div class="kv-item"><strong>Cluster Template IDs</strong>{_escape(selected_cluster_ids)}</div>
          <div class="kv-item"><strong>Active Run</strong>{active_run_link}</div>
        </div>
        <form method="post" action="/ui/workbench/{_escape(session['session_id'])}/clarify" style="margin-top:16px;">
          <div class="kv">{clarification_inputs}</div>
          <div class="actions" style="margin-top:14px;"><button type="submit">Refresh Plan Draft</button></div>
        </form>
        <div class="actions">{launch_block}</div>
      </section>
      <section class="panel">
        <h2>Plan Draft</h2>
        {_json_block(plan_draft)}
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h2>Execution Defaults</h2>
        {_json_block(effective_config.get('execution_defaults'))}
      </section>
      <section class="panel">
        <h2>Active Run Checkpoint</h2>
        {active_checkpoint}
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h2>Goal Packet</h2>
        {_json_block(goal_packet)}
      </section>
      <section class="panel">
        <h2>Cluster Graph</h2>
        {_json_block(goal_packet.get('cluster_graph'))}
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h2>Policy Preview</h2>
        {_json_block(goal_packet.get('capability_policy_preview'))}
      </section>
      <section class="panel">
        <h2>Cluster Policy Preview</h2>
        {_json_block(goal_packet.get('cluster_policy_preview'))}
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h2>Follow-Up Queue</h2>
        <table>
          <thead>
            <tr><th>Request</th><th>Status</th><th>Intent</th><th>Blocking</th><th>Instruction</th></tr>
          </thead>
          <tbody>{followup_rows}</tbody>
        </table>
        <form method="post" action="/ui/workbench/{_escape(session['session_id'])}/followup" style="margin-top:16px;">
          <input type="hidden" name="run_id" value="{_escape(session.get('active_run_id') or '')}">
          <div class="kv">
            <div class="kv-item"><strong>Instruction</strong><textarea name="instruction" rows="4" style="width:100%;" placeholder="Record the next bounded follow-up request."></textarea></div>
            <div class="kv-item"><strong>Intent</strong><input type="text" name="intent" value="continue"></div>
            <div class="kv-item"><strong>Blocking</strong><label><input type="checkbox" name="blocking" value="true"> requires operator attention before closure</label></div>
          </div>
          <div class="actions" style="margin-top:14px;"><button type="submit">Queue Follow-Up</button></div>
        </form>
      </section>
      <section class="panel">
        <h2>Recent Sessions</h2>
        {_session_table(recent_sessions)}
      </section>
    </div>
    <div class="split" style="margin-top:16px;">
      <section class="panel">
        <h2>Generated Profiles</h2>
        <p class="muted">M37 session-scoped role materialization stays additive and reviewable.</p>
        <form class="inline" method="post" action="/ui/workbench/{_escape(session['session_id'])}/generate-profiles" style="margin-bottom:12px;">
          <button type="submit">Generate Session Profiles</button>
        </form>
        <table>
          <thead>
            <tr><th>Profile</th><th>Base</th><th>Role Label</th><th>Cluster</th><th>Repo Scope</th></tr>
          </thead>
          <tbody>{generated_profile_rows}</tbody>
        </table>
      </section>
      <section class="panel">
        <h2>Automation Watchdogs</h2>
        <p class="muted">Bounded watchdogs project low-risk automation hints without bypassing review gates.</p>
        <table>
          <thead>
            <tr><th>Watchdog</th><th>Trigger</th><th>Status</th><th>Objective</th></tr>
          </thead>
          <tbody>{watchdog_rows}</tbody>
        </table>
        <table style="margin-top:16px;">
          <thead>
            <tr><th>Trigger</th><th>Action</th><th>Risk</th><th>Review</th><th>Summary</th></tr>
          </thead>
          <tbody>{watchdog_action_rows}</tbody>
        </table>
      </section>
    </div>
    """
    return _layout("Interaction Workbench", body, notice=notice)


def render_config(*, effective_config: dict[str, Any], notice: str | None = None) -> str:
    body = f"""
    <section class="panel">
      <h2>Effective Configuration</h2>
      {_json_block(effective_config)}
    </section>
    """
    return _layout("Configuration", body, notice=notice)
