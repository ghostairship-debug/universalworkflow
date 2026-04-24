# M36-1B Plan, Execution Defaults, And Checkpoint Projection

Status: completed

## Goal

Make the workbench show the same planning and checkpoint truth already available in the control plane.

## Acceptance

- show plan draft, goal packet, cluster graph, and policy preview coherently
- surface accepted `M35` execution defaults from the workbench
- project the active run checkpoint and review state without bypassing the operator surface

## Result

- the workbench now shows plan draft, goal packet, cluster graph, and policy preview together
- accepted `M35` execution defaults are projected directly into the workbench
- active run status, review state, next action, and recovery hint are visible without merging the workbench into the operator review console
