from __future__ import annotations

import hashlib
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
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


def playtest_cocos_build(*, build_output_path: str | Path, evidence_dir: str | Path) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    build_dir = Path(build_output_path).resolve()
    evidence = Path(evidence_dir).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    server, port = _serve_directory(build_dir)
    screenshot_paths: list[str] = []
    canvas_hashes: list[str] = []
    console_errors: list[str] = []
    page_errors: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))
            page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="networkidle", timeout=60000)
            page.wait_for_selector("#block-puzzle-canvas", timeout=60000)
            page.wait_for_function("() => window.__COCOS_BLOCK_PUZZLE_E2E__?.started === true", timeout=60000)
            before = page.evaluate("() => window.__COCOS_BLOCK_PUZZLE_E2E__")
            before_hash = page.evaluate(
                "() => document.querySelector('#block-puzzle-canvas').toDataURL('image/png').slice(0, 2000)"
            )
            canvas_hashes.append(_sha256_text(before_hash))
            shot = evidence / "cocos_playtest_initial.png"
            page.screenshot(path=str(shot), full_page=True)
            screenshot_paths.append(shot.as_posix())
            candidate = before["candidateCenters"][0]
            target = before["clearTarget"]
            page.mouse.move(candidate["x"], candidate["y"])
            page.mouse.down()
            page.mouse.move(target["x"], target["y"], steps=12)
            page.mouse.up()
            page.wait_for_function("() => window.__COCOS_BLOCK_PUZZLE_E2E__?.score > 0", timeout=10000)
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
                    state = page.evaluate("() => window.__COCOS_BLOCK_PUZZLE_E2E__")
                    if expected_event in state.get("events", []):
                        break
                    center = state["buttonCenters"][key]
                    page.mouse.click(center["x"], center["y"])
                    page.wait_for_timeout(120)
                page.wait_for_function(
                    "(eventName) => window.__COCOS_BLOCK_PUZZLE_E2E__?.events?.includes(eventName)",
                    arg=expected_event,
                    timeout=3000,
                )
            page.wait_for_function(
                "() => Object.values(window.__COCOS_BLOCK_PUZZLE_E2E__?.featureCoverage || {}).filter(Boolean).length >= 14",
                timeout=3000,
            )
            after = page.evaluate("() => window.__COCOS_BLOCK_PUZZLE_E2E__")
            after_hash = page.evaluate(
                "() => document.querySelector('#block-puzzle-canvas').toDataURL('image/png').slice(0, 2000)"
            )
            canvas_hashes.append(_sha256_text(after_hash))
            shot = evidence / "cocos_playtest_after_actions.png"
            page.screenshot(path=str(shot), full_page=True)
            screenshot_paths.append(shot.as_posix())
            desktop_page = browser.new_page(viewport={"width": 1280, "height": 720})
            desktop_page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="networkidle", timeout=60000)
            desktop_page.wait_for_selector("#block-puzzle-canvas", timeout=60000)
            desktop_shot = evidence / "cocos_playtest_desktop.png"
            desktop_page.screenshot(path=str(desktop_shot), full_page=True)
            screenshot_paths.append(desktop_shot.as_posix())
            desktop_page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    feature_coverage = dict(after.get("featureCoverage") or {})
    required_playtest_features = [
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
    ]
    commercial_playtest_features = [
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
    ]
    result = {
        "passed": all(bool(feature_coverage.get(key)) for key in required_playtest_features),
        "commercial_passed": all(bool(feature_coverage.get(key)) for key in commercial_playtest_features),
        "url": f"http://127.0.0.1:{port}/index.html",
        "screenshots": screenshot_paths,
        "canvas_hashes": canvas_hashes,
        "feature_coverage": feature_coverage,
        "required_playtest_features": required_playtest_features,
        "commercial_playtest_features": commercial_playtest_features,
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
