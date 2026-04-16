# M1 Run / Runtime Transition Matrix

## Goal

Freeze the M1 hardening baseline for run status transitions and runtime graph-step terminality.

## Run status transitions

- `pending -> prepared`
- `pending -> cancelled`
- `prepared -> prepared`
- `prepared -> running`
- `prepared -> cancelled`
- `running -> awaiting_review`
- `running -> completed`
- `running -> failed`
- `awaiting_review -> completed`
- `awaiting_review -> failed`
- `awaiting_review -> cancelled`
- `completed -> completed`
- `failed -> failed`
- `cancelled -> cancelled`

## Explicitly invalid examples

- `completed -> running`
- `failed -> prepared`
- `cancelled -> awaiting_review`
- `pending -> running`
- `awaiting_review -> prepared`

## Runtime graph steps

Non-terminal:

- `compiled`
- `resuming`
- `awaiting_review`

Terminal:

- `completed`
- `failed`
- `cancelled`

## Rule

`RuntimeStateRef.is_terminal` must always match the terminality of `graph_step`.
