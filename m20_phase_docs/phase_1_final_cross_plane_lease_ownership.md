# M20 Phase 1 - Final Cross-Plane Lease Ownership

Status: completed

## Goal

Finish cross-control-plane lease ownership and fencing semantics.

## Focus

- Every worker dispatch and callback must be bound to a committed lease and fencing token.
- stale control planes must be rejected without mutating lifecycle truth.

## Phase Gate

- every task in the current phase has a standalone detailed card
- declared tests pass
- closeout evidence is folded into the phase review

## Next Phase

- M20 Phase 2
