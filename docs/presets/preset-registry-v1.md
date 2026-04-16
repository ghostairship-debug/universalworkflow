# Preset Registry v1

## M0 rule

Preset selection is `manual only`. M0 never infers or auto-selects a preset from goal text.

## Value domains

- `task_kind`:
  `shell_exec`, `noop`
- `review_policy`:
  `auto_only`, `human_required`
- `budget_policy`:
  `{"max_retries": int, "timeout_seconds": int}`

## `feature_delivery`

- Intent:
  Execute a narrow implementation-oriented task that can produce an artifact.
- Allowed task kinds:
  `shell_exec`
- Default review policy:
  `auto_only`
- Default budget policy:
  `{"max_retries": 1, "timeout_seconds": 120}`
- Not for:
  Open-ended research and multi-stage human approval.

### Example seed

```json
{
  "preset_id": "feature_delivery",
  "name": "Feature Delivery",
  "description": "Produce a narrow implementation artifact through one shell-backed runtime task.",
  "allowed_task_kinds": ["shell_exec"],
  "default_review_policy": "auto_only",
  "default_budget_policy": {
    "max_retries": 1,
    "timeout_seconds": 120
  },
  "requires_manual_approval": false
}
```

## `research_spike`

- Intent:
  Produce a short research note or investigation artifact without planner inference.
- Allowed task kinds:
  `shell_exec`, `noop`
- Default review policy:
  `human_required`
- Default budget policy:
  `{"max_retries": 0, "timeout_seconds": 90}`
- Not for:
  Multi-task execution trees or autonomous routing.

### Example seed

```json
{
  "preset_id": "research_spike",
  "name": "Research Spike",
  "description": "Capture a narrow research artifact with conservative execution and manual review preference.",
  "allowed_task_kinds": ["shell_exec", "noop"],
  "default_review_policy": "human_required",
  "default_budget_policy": {
    "max_retries": 0,
    "timeout_seconds": 90
  },
  "requires_manual_approval": true
}
```
