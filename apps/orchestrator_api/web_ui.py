from __future__ import annotations

from typing import Any

from apps.orchestrator_api.web_ui_components import (
    _cluster_status_banner,
    _display,
    _escape,
    _json_block,
    _layout,
    _pill,
    _review_tone,
    _run_table,
    _session_table,
    _status_tone,
    _workbench_chat_panel,
)

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


def render_action_confirmation(*, receipt: dict[str, Any], notice: str | None = None) -> str:
    action_type = str(receipt.get("action_type") or "")
    metadata = receipt.get("metadata") if isinstance(receipt.get("metadata"), dict) else {}
    run_id = metadata.get("run_id") or "-"
    run_ids = metadata.get("run_ids") or []
    if run_ids:
        run_block = f'<div class="kv-item"><strong>Runs</strong>{_escape(", ".join(str(item) for item in run_ids))}</div>'
    else:
        run_block = f'<div class="kv-item"><strong>Run</strong>{_escape(run_id)}</div>'
    body = f"""
    <section class="panel">
      <h2>Confirm high-risk action</h2>
      <p class="muted">The original button only issues a receipt; this page performs the state-changing action.</p>
      <div class="kv">
        <div class="kv-item"><strong>Action</strong>{_escape(_display(action_type))}</div>
        <div class="kv-item"><strong>Receipt</strong><code>{_escape(receipt.get('receipt_id'))}</code></div>
        <div class="kv-item"><strong>Risk</strong>{_escape(receipt.get('risk_level') or 'high')}</div>
        <div class="kv-item"><strong>Status</strong>{_escape(receipt.get('status') or '-')}</div>
        {run_block}
      </div>
      <form method="post" action="/ui/actions/confirm" style="margin-top:16px;">
        <input type="hidden" name="receipt_id" value="{_escape(receipt.get('receipt_id'))}">
        <div class="actions"><button class="warn" type="submit">Confirm execution</button></div>
      </form>
    </section>
    """
    return _layout("High-risk Action Confirmation", body, notice=notice)
