# Commercial Game Specialized Agent Pipeline Design

Date: 2026-05-08

This document records the post-repair pipeline upgrade requested for unattended commercial game generation. It is an active design/development record for `commercial_game_production`, subordinate to `CURRENT_DEVELOPMENT_WORKFLOW.md`.

## Research Anchors

- GameCI's public GitHub Actions workflow model emphasizes checkout, cache, test runner, builder, deployment, and uploaded build/test artifacts. This maps directly to our build/playtest/evidence-loop contract rather than a one-shot generator. Source: https://game.ci/docs/github/getting-started/
- Cocos Creator 3.8 command-line publishing requires an explicit `--project` and supports `--build` parameters, so our Cocos build stage must keep strict command evidence and cannot treat scaffold metadata as a build. Source: https://docs.cocos.com/creator/3.8/manual/zh/editor/publish/publish-in-command-line.html
- Open Cocos match-3 examples show that puzzle quality depends on engine-native architecture, smooth animation, configurable boards, and no-dead-state mechanics such as "always have moves", not just UI screenshots. Sources: https://github.com/AlexKutepov/Match3-algorithm-TS-Cocos-creator and https://github.com/Ghamza-Jd/Match-3
- Industry role maps split game production into design, art, audio, programming, production, and QA disciplines; King specifically exposes level design, economy design, audio, art, UX/UI, and analytics as distinct crafts. Sources: https://intogames.org/careers and https://careers.king.com/us/en/our-crafts
- Game QA should produce reproducible detailed reports, and technical testers/SDETs build automated test cases and frameworks. This supports a dedicated AI playtest oracle role instead of letting final QA be an unstructured reviewer. Source: https://en.wikipedia.org/wiki/Game_testing

## Role Split

The pipeline remains on the already executable `single_agent_role_v1` executor. It does not claim a new cluster backend. The upgrade is a role-specialization split that gives each role a narrower contract and makes task-card ownership explicit.

Role sequence:

1. `intake_packaging_agent`: source-preserving unified brief.
2. `product_gameplay_agent`: product promise and player loop.
3. `mechanics_system_designer_agent`: mechanics, state invariants, fail/revive logic, input feel, anti-soft-lock.
4. `level_economy_designer_agent`: level goals, difficulty curve, economy, rewards, unlock pacing.
5. `ui_experience_agent`: screen flow, HUD, panels, mobile constraints.
6. `ui_ux_polish_agent`: commercial UI polish, hierarchy, readable Chinese copy, screenshot expectations.
7. `art_direction_agent`: style bible, palette, board materials, iconography, non-placeholder asset acceptance.
8. `animation_vfx_feedback_agent`: motion grammar, VFX timing, state-linked feedback.
9. `audio_feedback_designer_agent`: BGM, SFX event map, mix rules, runtime audio proof.
10. `technical_plan_agent`: Cocos/runtime/write-set/test/evidence integration.
11. `multimodal_generation_agent`: provider asset generation and visual review routes, including Vertex/GCP fallback where valid.
12. `ai_playtest_oracle_agent`: scripted, exploratory, persona, visual, audio, regression, and device-matrix playtest rubrics.
13. `task_card_generation_agent`: compiles specialist outputs into DB task cards.
14. `qa_player_perspective_agent`: player-visible red-team review from evidence.
15. `supervisor`: repair-loop governance and no-go protection.

## Pipeline Changes

- `commercial_game_production` now exposes the specialized role chain before asset generation and implementation.
- Role outputs carry specialized structured fields such as `mechanic_contract`, `level_progression_plan`, `commercial_ui_polish_rubric`, `asset_style_bible`, `motion_feedback_plan`, `audio_design_sheet`, and `playtest_modes`.
- `PhaseExecutionBlueprint` slices compile into task cards with `specialist_owner_role`, `specialist_review_roles`, and `role_output:<role_id>` read sets.
- Product implementation cards split mechanics, level curve, economy, art direction, animation/VFX, audio assets, audio runtime, UI, performance, and AI playtest quality instead of collapsing them into broad product/UI/audio buckets.
- Asset generation style prompts now consume the specialist role outputs, so art/audio/UI/mechanics evidence influences provider prompts and fallback routes.

## Quality Bar

Machine readiness for unattended runs requires the same gates as before plus stronger specialist coverage:

- Cocos command-line build evidence is strict and source-bound.
- Browser playtest evidence must include screenshots, open-panel trace, audio proof, and player-visible interactions.
- AI surrogate evidence must cover visual, audio, core-loop, first-session, requirement-fidelity, and regression modes.
- Reference comparison against the accepted R5 project remains a no-degradation gate for score, features, screenshots, panels, events, and visual density.
- Human acceptance remains the only path to `commercial_playable_go=true`; unattended mode may reach machine GO only.

