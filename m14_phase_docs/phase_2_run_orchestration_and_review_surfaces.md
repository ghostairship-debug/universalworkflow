# M14 Phase 2 - Run, Orchestration, And Review Surfaces

Status: complete

## Goal

Project the full operator truth into the new Web UI so a human can inspect run state, orchestration, replay context, and pending reviews without leaving the browser.

## Completed Outputs

- run focus page aggregates summary, status detail, inspection, timeline, replay excerpt, and orchestration
- pending review console shows awaiting-review runs, latest auto verdict, and recommended action
- operator-view aggregation remains a projection layer, not a second state source

## Verification

- `tests/test_web_ui.py`
- `tests/test_api.py`

## Next Phase

- `M14 Phase 3 - Human Control Actions`
