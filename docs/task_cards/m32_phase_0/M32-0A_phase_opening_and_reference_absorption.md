# M32-0A Phase Opening And Reference Absorption

Status: completed

## Goal

Open `M32 Phase 0` formally, establish the worktree/lane ownership model, and classify the dirty primary workspace as a governed reference source rather than execution truth.

## Acceptance

- add the `M32` phase doc
- add the `M32` task-card index and detailed cards
- update the current workflow guide so `M32` is the active bounded phase
- add a reference-absorption inventory for the dirty primary workspace
- record lane ownership and the bug-first rule in active `M32` materials

## Notes

- do not start broad `M32` feature work until this card has opened the phase
- the dirty primary workspace is reference-only; any absorbed delta must be reviewed and moved into the `integration` worktree intentionally

## Result

- opened `M32 Phase 0` formally through the phase doc and task-card pack
- added [docs/reviews/m32-reference-absorption-inventory.md](../reviews/m32-reference-absorption-inventory.md)
- completed governed backup-branch absorption in [docs/reviews/m32-backup-branch-absorption-review.md](../reviews/m32-backup-branch-absorption-review.md)
- collapsed long-horizon planning inputs into [docs/reviews/m32-archived-planning-inputs.md](../reviews/m32-archived-planning-inputs.md)
- cleaned the repository back to one primary `main` worktree and archived the leftover pre-merge state by tag
