# M36-2B Operator And Workbench Checkpoint Consistency

Status: completed

## Goal

Keep the workbench aligned with the operator truth instead of inventing a second review or launch authority.

## Acceptance

- project active run checkpoint state from the existing operator/control-plane read models
- keep review action ownership in the operator surfaces
- keep launch and follow-up visibility coherent across session payloads

## Result

- workbench checkpoint state now projects the same active run and review-state truth used by the operator console
- review ownership remains explicit in the operator surfaces
- launch and follow-up visibility now stay aligned across workbench, CLI, and API session payloads
