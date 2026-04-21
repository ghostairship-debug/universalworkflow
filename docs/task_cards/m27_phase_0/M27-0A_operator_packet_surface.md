# M27-0A Operator Packet Surface

Status: completed

## Goal

Add a compact packet for operator-facing tools that combines summary, policy preview, operator projection, plan graph, and trace/session context.

## Result

- added `get_run_operator_packet()` and embedded it into operator view
- added CLI/API entry points for the packet
- kept all existing detailed surfaces intact; this is additive convergence, not replacement
