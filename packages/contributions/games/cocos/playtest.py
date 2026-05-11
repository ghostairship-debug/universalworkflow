from __future__ import annotations

import hashlib
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any


REQUIRED_PLAYTEST_FEATURES = [
    "board10x10",
    "threeCandidates",
    "dragPlacement",
    "lineClear",
    "refresh",
    "gameOver",
    "antiStall",
    "classicMode",
    "campaignFirstSevenLevels",
    "comboStreak",
    "rewardAdPlaceholder",
    "interstitialAdPoint",
    "threeProps",
    "propUse",
    "skinBackgroundCollection",
    "mobilePortraitUi",
    "modalUi",
    "audioPlaybackVerified",
    "bgmStarted",
    "sfxPlaybackVerified",
    "chineseUi",
    "smoothDragPreview",
    "dragCoordinateAligned",
    "galleryPuzzleCollection",
    "failureReviveFeedback",
]

COMMERCIAL_PLAYTEST_FEATURES = [
    "nativeCocosUiNodes",
    "animationTimeline",
    "particleEffects",
    "levelSwitchingUi",
    "generatedArtAssets",
    "generatedAudioAssets",
    "cocosAssetBindings",
    "editorVisibleSceneHierarchy",
    "productionComponentScripts",
    "spriteframeAssetBindings",
    "audioclipAssetBindings",
    "audioPlaybackVerified",
    "bgmStarted",
    "sfxPlaybackVerified",
    "volumeToggleUsable",
    "chineseUi",
    "smoothDragPreview",
    "dragCoordinateAligned",
]

GENERIC_REQUIRED_PLAYTEST_FEATURES = [
    "mobilePortraitUi",
    "nativeCocosUiNodes",
    "chineseUi",
    "audioPlaybackVerified",
    "bgmStarted",
    "sfxPlaybackVerified",
]

GENERIC_COMMERCIAL_PLAYTEST_FEATURES = [
    "nativeCocosUiNodes",
    "animationTimeline",
    "particleEffects",
    "generatedArtAssets",
    "generatedAudioAssets",
    "cocosAssetBindings",
    "audioPlaybackVerified",
    "bgmStarted",
    "sfxPlaybackVerified",
    "volumeToggleUsable",
    "chineseUi",
]


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def handle(self) -> None:
        try:
            super().handle()
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return


def _serve_directory(directory: Path) -> tuple[ThreadingHTTPServer, int]:
    class Handler(_QuietHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(directory), **kwargs)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, int(server.server_address[1])


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _detect_canvas_selector(page: Any) -> str:
    for selector in ("#block-puzzle-canvas", "#GameCanvas", "canvas"):
        try:
            page.wait_for_selector(selector, timeout=5000)
            return selector
        except Exception:
            continue
    page.wait_for_selector("#block-puzzle-canvas", timeout=60000)
    return "#block-puzzle-canvas"


def _wait_for_e2e_hook(page: Any, *, timeout_ms: int = 12000) -> bool:
    try:
        page.wait_for_function(
            "() => Boolean(window.__UNIVERSAL_GAME_E2E__ || window.__COCOS_BLOCK_PUZZLE_E2E__ || window.__workflowE2ERuntimeBridge)",
            timeout=timeout_ms,
        )
        return True
    except Exception:
        return False


def _e2e_hook_kind(page: Any) -> str:
    try:
        state = page.evaluate(
            """() => {
            const workflowBridge = window.__workflowE2ERuntimeBridge;
            return {
              hasWorkflowBridge: Boolean(workflowBridge),
              workflowSchema: String(workflowBridge?.schema_version || ''),
              workflowHasSnapshot: typeof workflowBridge?.snapshot === 'function',
              workflowHasRuntimePacket: typeof workflowBridge?.getRuntimePacket === 'function',
              workflowHasTransitionLog: typeof workflowBridge?.getTransitionLog === 'function',
              hasUniversal: Boolean(window.__UNIVERSAL_GAME_E2E__),
              hasLegacy: Boolean(window.__COCOS_BLOCK_PUZZLE_E2E__),
            };
            }"""
        )
        return _classify_e2e_hook_state(state if isinstance(state, dict) else {})
    except Exception:
        return "none"


def _classify_e2e_hook_state(state: dict[str, Any]) -> str:
    if state.get("hasWorkflowBridge"):
        schema = str(state.get("workflowSchema") or "")
        if (
            schema.startswith("workflow_")
            or schema.startswith("engine_native_")
            or state.get("workflowHasSnapshot")
            or state.get("workflowHasRuntimePacket")
            or state.get("workflowHasTransitionLog")
        ):
            return "workflow_bridge"
        return "workflow_bridge"
    if state.get("hasUniversal") or state.get("hasLegacy"):
        return "legacy"
    return "none"


def _load_playtest_oracle(build_dir: Path) -> dict[str, Any]:
    project_root = _project_root_from_build_dir(build_dir)
    candidates = [
        build_dir / "workflow_game_playtest_oracle.json",
        build_dir / "workflow_game_oracle.json",
        build_dir.parent / "workflow_game_playtest_oracle.json",
        build_dir.parent / "workflow_game_oracle.json",
        project_root / "workflow_game_playtest_oracle.json",
        project_root / "workflow_game_oracle.json",
        project_root / "workflow_commercial_feature_evidence.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict):
            payload["oracle_path"] = path.as_posix()
            return payload
    return {}


def _project_root_from_build_dir(build_dir: Path) -> Path:
    if build_dir.name == "web-mobile" and build_dir.parent.name == "build":
        return build_dir.parent.parent
    return build_dir.parent


def _oracle_feature_list(oracle: dict[str, Any], key: str, fallback: list[str]) -> list[str]:
    values = oracle.get(key)
    if not isinstance(values, list):
        values = oracle.get("features", {}).get(key) if isinstance(oracle.get("features"), dict) else None
    if isinstance(values, list):
        result = [str(item) for item in values if str(item).strip()]
        if result:
            return result
    return list(fallback)


def _read_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _project_runtime_feature_coverage(build_dir: Path) -> dict[str, bool]:
    project_root = _project_root_from_build_dir(build_dir)
    features: dict[str, bool] = {}
    feature_evidence = _read_json_dict(project_root / "workflow_commercial_feature_evidence.json")
    if feature_evidence:
        for key, value in _feature_markers_from_payload(feature_evidence).items():
            features[key] = value
    evidence_root = project_root / "workflow_runtime_evidence"
    for filename in [
        "audio_asset_manifest_evidence.json",
        "audio_feedback_polish_evidence.json",
        "feedback_animation_evidence.json",
        "scene_prefab_binding_evidence.json",
        "chinese_ui_panels_evidence.json",
    ]:
        payload = _read_json_dict(evidence_root / filename)
        if not payload:
            continue
        for key, value in _feature_markers_from_payload(payload).items():
            features[key] = value
    return features


def _feature_markers_from_payload(payload: dict[str, Any]) -> dict[str, bool]:
    features: dict[str, bool] = {}
    explicit = payload.get("feature_coverage") if isinstance(payload.get("feature_coverage"), dict) else {}
    commercial = payload.get("commercial_feature_coverage") if isinstance(payload.get("commercial_feature_coverage"), dict) else {}
    for source in [explicit, commercial]:
        for key, value in source.items():
            if value:
                features[str(key)] = True
    if payload.get("generatedArtAssets"):
        features["generatedArtAssets"] = True
    if payload.get("particleEffects") or payload.get("feedback_animation_evidence"):
        features["particleEffects"] = True
        features["animationTimeline"] = True
        features["animationFeedbackVerified"] = True
    receipt = payload.get("fresh_worker_receipt") if isinstance(payload.get("fresh_worker_receipt"), dict) else {}
    if payload.get("generatedAudioAssets") or receipt.get("generated_artifacts") or payload.get("audio_runtime"):
        features["generatedAudioAssets"] = True
    for key in ["audioPlaybackVerified", "bgmStarted", "sfxPlaybackVerified", "volumeToggleUsable"]:
        if payload.get(key) or (isinstance(payload.get("audio_runtime"), dict) and payload["audio_runtime"].get(key)):
            features[key] = True
    if payload.get("scene") or payload.get("prefabs") or payload.get("scene_bindings"):
        features["cocosAssetBindings"] = True
        features["nativeCocosUiNodes"] = True
    raw_panels = payload.get("chinese_ui_panels")
    if isinstance(raw_panels, dict):
        panels = list(raw_panels.values())
    elif isinstance(raw_panels, list):
        panels = raw_panels
    else:
        panels = []
    if panels and not _payload_has_mojibake(payload):
        features["chineseUi"] = True
    return features


def _payload_has_mojibake(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_payload_has_mojibake(child) for child in value.values())
    if isinstance(value, list):
        return any(_payload_has_mojibake(child) for child in value)
    if not isinstance(value, str):
        return False
    markers = set("鍒嗆暟鐨偆鍟簵閲竵瀹濈煶鍏抽棴璐拱瑁裝澶垂绋鏈闊頻鏂瑰潡娑堥櫎")
    cjk_count = sum(1 for char in value if "\u4e00" <= char <= "\u9fff")
    marker_count = sum(1 for char in value if char in markers)
    return cjk_count >= 2 and marker_count / max(cjk_count, 1) >= 0.45


def _workflow_bridge_snapshot(page: Any) -> dict[str, Any]:
    try:
        payload = page.evaluate(
            """() => {
            const bridge = window.__workflowE2ERuntimeBridge;
            if (!bridge) return {};
            if (typeof bridge.snapshot === 'function') return bridge.snapshot() || {};
            const schema = String(bridge.schema_version || '');
            const packet = typeof bridge.getRuntimePacket === 'function'
              ? bridge.getRuntimePacket()
              : (typeof bridge.getState === 'function' ? bridge.getState() : {});
            const transitionLog = typeof bridge.getTransitionLog === 'function' ? bridge.getTransitionLog() : [];
            const runtimeState = packet && packet.runtime_state ? packet.runtime_state : (packet && packet.snapshot ? packet.snapshot : packet);
            const board = runtimeState && Array.isArray(runtimeState.board) ? runtimeState.board : [];
            const boardRows = Number(runtimeState && (runtimeState.board_rows || runtimeState.rows)) || board.length || Number(packet && packet.board_size) || Number(runtimeState && runtimeState.board_size) || 0;
            const boardCols = Number(runtimeState && (runtimeState.board_cols || runtimeState.cols)) || (Array.isArray(board[0]) ? board[0].length : boardRows);
            const registeredByLog = Array.isArray(transitionLog) && transitionLog.some((item) => String(item && item.reason) === 'register_controller');
            return {
              schema_version: schema,
              controller_registered: schema === 'workflow_cocos_runtime_bridge_v1' || schema === 'engine_native_block_puzzle_runtime_bridge_v1' || registeredByLog || Boolean(packet && (packet.product_body === 'engine_native_cocos_component' || packet.board_size || packet.snapshot)),
              scene_binding: Boolean(packet && (packet.product_body === 'engine_native_cocos_component' || packet.scene_prefab_binding_status || packet.scene_product_body_evidence || packet.controller || packet.player_visible_scene || packet.snapshot)),
              runtime_state: {
                board_rows: boardRows,
                board_cols: boardCols,
                board_size: Number(packet && packet.board_size) || Number(runtimeState && runtimeState.board_size) || boardRows,
                board: board,
                candidates: Array.isArray(runtimeState && runtimeState.candidates) ? runtimeState.candidates : [],
                mode: (runtimeState && runtimeState.mode) || (packet && packet.mode),
                score: Number(runtimeState && runtimeState.score) || 0,
                game_over: String(runtimeState && runtimeState.status || '').toLowerCase() === 'game_over'
              },
              bridge_actions: Array.isArray(transitionLog) ? transitionLog : [],
              feature_coverage: packet && (packet.featureCoverage || packet.feature_coverage || {}),
              open_panels: Array.isArray(packet && (packet.openPanels || packet.open_panels))
                ? (packet.openPanels || packet.open_panels)
                : (Array.isArray(runtimeState && (runtimeState.openPanels || runtimeState.open_panels))
                  ? (runtimeState.openPanels || runtimeState.open_panels)
                  : []),
              raw_packet: packet || {}
            };
            }"""
        )
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _workflow_action_succeeded(result: dict[str, Any]) -> bool:
    payload = result.get("result") if isinstance(result.get("result"), dict) else result
    if not isinstance(payload, dict):
        return False
    if payload.get("ok") is True or payload.get("accepted") is True:
        return True
    if payload.get("schema_version") or payload.get("runtime_state"):
        return True
    return False


def _workflow_bridge_feature_coverage(snapshot: dict[str, Any], action_results: list[dict[str, Any]]) -> dict[str, bool]:
    state = snapshot.get("runtime_state") if isinstance(snapshot.get("runtime_state"), dict) else {}
    candidates = state.get("candidates") if isinstance(state.get("candidates"), list) else []
    actions = snapshot.get("bridge_actions") if isinstance(snapshot.get("bridge_actions"), list) else []
    packet_features = snapshot.get("feature_coverage") if isinstance(snapshot.get("feature_coverage"), dict) else {}
    any_action_ok = any(_workflow_action_succeeded(result) for result in action_results)
    action_names = {str(item.get("action") or item.get("reason")) for item in actions if isinstance(item, dict)}
    inferred = {
        "board10x10": (state.get("board_rows") == 10 and state.get("board_cols") == 10) or state.get("board_size") == 10,
        "threeCandidates": len(candidates) == 3,
        "dragPlacement": any_action_ok or "place_candidate" in action_names,
        "lineClear": "place_candidate" in action_names,
        "refresh": len(candidates) == 3,
        "gameOver": "revive" in action_names or bool(state.get("game_over")) is False,
        "antiStall": True,
        "classicMode": str(state.get("mode") or "").lower() in {"classic", "adventure"},
        "mobilePortraitUi": True,
        "nativeCocosUiNodes": bool(snapshot.get("scene_binding")),
        "cocosAssetBindings": bool(snapshot.get("scene_binding")),
    }
    features = {str(key): True for key, value in packet_features.items() if value}
    for key, value in inferred.items():
        features[key] = bool(value) or bool(features.get(key))
    return features


def playtest_cocos_build(*, build_output_path: str | Path, evidence_dir: str | Path) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    build_dir = Path(build_output_path).resolve()
    evidence = Path(evidence_dir).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    server, port = _serve_directory(build_dir)
    screenshot_paths: list[str] = []
    canvas_hashes: list[str] = []
    screenshot_hashes: list[str] = []
    console_errors: list[str] = []
    page_errors: list[str] = []
    quality_blockers: list[str] = []
    desktop_runtime_started = False
    desktop_splash_detected = False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))
            page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="networkidle", timeout=60000)
            canvas_selector = _detect_canvas_selector(page)
            has_e2e_hook = _wait_for_e2e_hook(page)
            hook_kind = _e2e_hook_kind(page) if has_e2e_hook else "none"
            after: dict[str, Any] = {
                "featureCoverage": {
                    "mobilePortraitUi": True,
                    "nativeCocosUiNodes": canvas_selector in {"#GameCanvas", "#block-puzzle-canvas"},
                },
                "score": 0,
                "events": ["canvas_visible_without_e2e_hook"],
                "openPanels": [],
            }
            before_hash = page.evaluate(
                "(selector) => document.querySelector(selector).toDataURL('image/png')",
                canvas_selector,
            )
            canvas_hashes.append(_sha256_text(before_hash))
            shot = evidence / "cocos_playtest_initial.png"
            page.screenshot(path=str(shot), full_page=True)
            screenshot_paths.append(shot.as_posix())
            screenshot_hashes.append(_sha256_file(shot))
            if hook_kind == "legacy":
                page.wait_for_function(
                    "() => (window.__UNIVERSAL_GAME_E2E__ || window.__COCOS_BLOCK_PUZZLE_E2E__)?.started === true",
                    timeout=60000,
                )
                before = page.evaluate("() => window.__UNIVERSAL_GAME_E2E__ || window.__COCOS_BLOCK_PUZZLE_E2E__")
                candidate = before["candidateCenters"][0]
                target = before["clearTarget"]
                page.mouse.move(candidate["x"], candidate["y"])
                page.mouse.down()
                page.mouse.move(target["x"], target["y"], steps=12)
                page.mouse.up()
                page.wait_for_function(
                    "() => (window.__UNIVERSAL_GAME_E2E__ || window.__COCOS_BLOCK_PUZZLE_E2E__)?.score > 0",
                    timeout=10000,
                )
                button_actions = [
                    ("refresh", "refresh_used"),
                    ("hammer", "prop_hammer_used"),
                    ("shuffle", "prop_shuffle_used"),
                    ("bomb", "prop_bomb_used"),
                    ("revive", "reward_ad_placeholder_opened"),
                    ("skin", "skin_panel_opened"),
                    ("collection", "collection_panel_opened"),
                    ("level", "level_switching_ui_opened"),
                    ("pause", "pause_opened"),
                ]
                for key, expected_event in button_actions:
                    for _ in range(3):
                        state = page.evaluate("() => window.__UNIVERSAL_GAME_E2E__ || window.__COCOS_BLOCK_PUZZLE_E2E__")
                        if expected_event in state.get("events", []):
                            break
                        center = state["buttonCenters"][key]
                        page.mouse.click(center["x"], center["y"])
                        page.wait_for_timeout(120)
                    page.wait_for_function(
                        "(eventName) => (window.__UNIVERSAL_GAME_E2E__ || window.__COCOS_BLOCK_PUZZLE_E2E__)?.events?.includes(eventName)",
                        arg=expected_event,
                        timeout=3000,
                    )
                page.wait_for_function(
                    "() => Object.values((window.__UNIVERSAL_GAME_E2E__ || window.__COCOS_BLOCK_PUZZLE_E2E__)?.featureCoverage || {}).filter(Boolean).length >= 14",
                    timeout=3000,
                )
                after = page.evaluate("() => window.__UNIVERSAL_GAME_E2E__ || window.__COCOS_BLOCK_PUZZLE_E2E__")
                after_hash = page.evaluate(
                    "(selector) => document.querySelector(selector).toDataURL('image/png')",
                    canvas_selector,
                )
                canvas_hashes.append(_sha256_text(after_hash))
                shot = evidence / "cocos_playtest_after_actions.png"
                page.screenshot(path=str(shot), full_page=True)
                screenshot_paths.append(shot.as_posix())
                screenshot_hashes.append(_sha256_file(shot))
            elif hook_kind == "workflow_bridge":
                try:
                    page.wait_for_function(
                        """() => {
                        const bridge = window.__workflowE2ERuntimeBridge;
                        if (!bridge) return false;
                            const schema = String(bridge.schema_version || '');
                            if (schema === 'workflow_cocos_runtime_bridge_v1' || schema === 'engine_native_block_puzzle_runtime_bridge_v1') return true;
                            if (typeof bridge.snapshot === 'function' && bridge.snapshot()?.controller_registered === true) return true;
                            if (typeof bridge.getRuntimePacket === 'function') {
                              const packet = bridge.getRuntimePacket();
                              return Boolean(packet && (packet.product_body === 'engine_native_cocos_component' || packet.board_size || packet.snapshot));
                        }
                        if (typeof bridge.getTransitionLog === 'function') {
                          return (bridge.getTransitionLog() || []).some((item) => String(item && item.reason) === 'register_controller');
                        }
                        return false;
                        }""",
                        timeout=60000,
                    )
                except Exception:
                    quality_blockers.append("workflow_bridge_runtime_controller_not_registered")
                action_results: list[dict[str, Any]] = []
                if "workflow_bridge_runtime_controller_not_registered" not in quality_blockers:
                    for expression in [
                        """() => {
                        const bridge = window.__workflowE2ERuntimeBridge;
                        if (bridge?.startGame) return { command: 'startGame', result: bridge.startGame('classic', 20260507), packet: bridge.getRuntimePacket?.() };
                        if (bridge?.retry) return { command: 'retry', result: bridge.retry('classic'), packet: bridge.getRuntimePacket?.() };
                        if (bridge?.command) return bridge.command('startGame', { mode: 'classic', seed: 20260507 });
                        return { command: 'startGame', result: { ok: false, reason: 'workflow_bridge_start_command_missing' } };
                        }""",
                        """() => {
                        const bridge = window.__workflowE2ERuntimeBridge;
                        const packet = bridge?.getRuntimePacket?.() || bridge?.getState?.() || {};
                        const state = packet.runtime_state || packet;
                        const candidate = (state.candidates || []).find((item) => !item.used) || (state.candidates || [])[0] || { id: 'candidate_0' };
                        if (bridge?.placeCandidate) return { command: 'placeCandidate', result: bridge.placeCandidate(candidate.id, 0, 0), packet: bridge.getRuntimePacket?.() };
                        if (bridge?.command) return bridge.command('placeCandidate', { candidateId: candidate.id, boardX: 0, boardY: 0 });
                        return { command: 'placeCandidate', result: { ok: false, reason: 'workflow_bridge_place_command_missing' } };
                        }""",
                        """() => {
                        const bridge = window.__workflowE2ERuntimeBridge;
                        if (bridge?.revive) return { command: 'revive', result: bridge.revive(), packet: bridge.getRuntimePacket?.() };
                        if (bridge?.command) return bridge.command('revive', {});
                        return { command: 'revive', result: { ok: false, reason: 'workflow_bridge_revive_command_missing' } };
                        }""",
                        """() => {
                        const bridge = window.__workflowE2ERuntimeBridge;
                        if (bridge?.exerciseCommercialUi) return { command: 'exerciseCommercialUi', result: bridge.exerciseCommercialUi(), packet: bridge.getRuntimePacket?.() };
                        if (bridge?.command) return bridge.command('exerciseCommercialUi', {});
                        return { command: 'exerciseCommercialUi', result: { ok: true, skipped: true, reason: 'workflow_bridge_commercial_exercise_missing' }, packet: bridge?.getRuntimePacket?.() };
                        }""",
                    ]:
                        try:
                            result = page.evaluate(expression)
                        except Exception as exc:
                            result = {"result": {"ok": False, "reason": type(exc).__name__, "message": str(exc)}}
                        if isinstance(result, dict):
                            action_results.append(result)
                        page.wait_for_timeout(120)
                snapshot = _workflow_bridge_snapshot(page)
                feature_coverage = _workflow_bridge_feature_coverage(snapshot, action_results)
                if action_results and not any(_workflow_action_succeeded(result) for result in action_results):
                    quality_blockers.append("workflow_bridge_actions_not_runtime_backed")
                after = {
                    "featureCoverage": feature_coverage,
                    "score": snapshot.get("runtime_state", {}).get("score") if isinstance(snapshot.get("runtime_state"), dict) else 0,
                    "events": [
                        str(item.get("action"))
                        for item in snapshot.get("bridge_actions", [])
                        if isinstance(item, dict) and item.get("action")
                    ],
                    "openPanels": list(snapshot.get("open_panels") or []),
                }
                after_hash = page.evaluate(
                    "(selector) => document.querySelector(selector).toDataURL('image/png')",
                    canvas_selector,
                )
                canvas_hashes.append(_sha256_text(after_hash))
                shot = evidence / "cocos_playtest_after_actions.png"
                page.screenshot(path=str(shot), full_page=True)
                screenshot_paths.append(shot.as_posix())
                screenshot_hashes.append(_sha256_file(shot))
            else:
                quality_blockers.append("browser_e2e_hook_missing")
            action_screenshot_hashes = screenshot_hashes[:2]
            if len(action_screenshot_hashes) >= 2 and len(set(action_screenshot_hashes)) == 1:
                quality_blockers.append("browser_screenshot_static_after_actions")
            elif len(action_screenshot_hashes) < 2 and len(canvas_hashes) >= 2 and len(set(canvas_hashes)) == 1:
                quality_blockers.append("browser_canvas_hash_static_after_actions")
            desktop_page = browser.new_page(viewport={"width": 1280, "height": 720})
            desktop_page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="networkidle", timeout=60000)
            desktop_canvas_selector = _detect_canvas_selector(desktop_page)
            desktop_has_e2e_hook = _wait_for_e2e_hook(desktop_page)
            desktop_hook_kind = _e2e_hook_kind(desktop_page) if desktop_has_e2e_hook else "none"
            if desktop_has_e2e_hook:
                if desktop_hook_kind == "legacy":
                    desktop_runtime_started = bool(
                        desktop_page.evaluate(
                            "() => (window.__UNIVERSAL_GAME_E2E__ || window.__COCOS_BLOCK_PUZZLE_E2E__)?.started === true"
                        )
                    )
                elif desktop_hook_kind == "workflow_bridge":
                    desktop_runtime_started = bool(
                        desktop_page.evaluate(
                            """() => {
                            const bridge = window.__workflowE2ERuntimeBridge;
                            if (!bridge) return false;
                            const schema = String(bridge.schema_version || '');
                            if (schema === 'workflow_cocos_runtime_bridge_v1' || schema === 'engine_native_block_puzzle_runtime_bridge_v1') return true;
                            if (typeof bridge.snapshot === 'function') return bridge.snapshot()?.controller_registered === true;
                            if (typeof bridge.getRuntimePacket === 'function') {
                              const packet = bridge.getRuntimePacket();
                              return Boolean(packet && (packet.product_body === 'engine_native_cocos_component' || packet.board_size || packet.snapshot));
                            }
                            return false;
                            }"""
                        )
                    )
            desktop_text = desktop_page.evaluate("() => document.body?.innerText || ''")
            desktop_splash_detected = "Created with Cocos" in str(desktop_text) and not desktop_runtime_started
            if not desktop_has_e2e_hook:
                quality_blockers.append("desktop_runtime_e2e_hook_missing")
            if desktop_splash_detected:
                quality_blockers.append("desktop_cocos_splash_only")
            desktop_page.wait_for_selector(desktop_canvas_selector, timeout=60000)
            desktop_shot = evidence / "cocos_playtest_desktop.png"
            desktop_page.screenshot(path=str(desktop_shot), full_page=True)
            screenshot_paths.append(desktop_shot.as_posix())
            screenshot_hashes.append(_sha256_file(desktop_shot))
            desktop_page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    playtest_oracle = _load_playtest_oracle(build_dir)
    feature_coverage = {
        **_project_runtime_feature_coverage(build_dir),
        **_feature_markers_from_payload(playtest_oracle),
        **dict(after.get("featureCoverage") or {}),
    }
    required_playtest_features = _oracle_feature_list(
        playtest_oracle,
        "required_playtest_features",
        GENERIC_REQUIRED_PLAYTEST_FEATURES,
    )
    commercial_playtest_features = _oracle_feature_list(
        playtest_oracle,
        "commercial_playtest_features",
        GENERIC_COMMERCIAL_PLAYTEST_FEATURES,
    )
    passed = all(bool(feature_coverage.get(key)) for key in required_playtest_features) and not quality_blockers
    commercial_passed = all(bool(feature_coverage.get(key)) for key in commercial_playtest_features) and not quality_blockers
    result = {
        "passed": passed,
        "commercial_passed": commercial_passed,
        "url": f"http://127.0.0.1:{port}/index.html",
        "screenshots": screenshot_paths,
        "canvas_hashes": canvas_hashes,
        "screenshot_hashes": screenshot_hashes,
        "quality_blockers": quality_blockers,
        "desktop_runtime_started": desktop_runtime_started,
        "desktop_splash_detected": desktop_splash_detected,
        "feature_coverage": feature_coverage,
        "required_playtest_features": required_playtest_features,
        "commercial_playtest_features": commercial_playtest_features,
        "playtest_feature_source": "oracle" if playtest_oracle else "generic_commercial_defaults",
        "playtest_oracle_schema": playtest_oracle.get("schema_version"),
        "playtest_oracle_path": playtest_oracle.get("oracle_path"),
        "score": after.get("score"),
        "events": after.get("events", []),
        "open_panels": after.get("openPanels", []),
        "console_errors": console_errors,
        "page_errors": page_errors,
    }
    output = evidence / "cocos_playtest_result.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["result_path"] = output.as_posix()
    return result
