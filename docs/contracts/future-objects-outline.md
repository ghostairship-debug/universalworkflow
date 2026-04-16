# Future Objects Outline

## Claim

- Deferred to:
  M2
- Why deferred:
  M0 uses serial execution semantics and a claim placeholder only.
- Future problem solved:
  Conflict-safe parallel execution and write-domain reservation.

## WorkerLease

- Deferred to:
  M2
- Why deferred:
  M0 has no long-lived worker pool and no lease renewal loop.
- Future problem solved:
  Worker ownership, heartbeat, and interruption safety.

## BudgetLedger

- Deferred to:
  M2
- Why deferred:
  M0 only needs a preset-level budget policy shape.
- Future problem solved:
  Budget accounting, enforcement, and reporting.

## ApprovalGate

- Deferred to:
  M1+
- Why deferred:
  M0 only needs review policy defaults, not full approval workflows.
- Future problem solved:
  Human-in-the-loop release and escalation.

## RunSnapshot

- Deferred to:
  M2
- Why deferred:
  M0 timeline is enough for the bootstrap flow.
- Future problem solved:
  Replay and recovery checkpoints.

## ErrorSignature

- Deferred to:
  M3
- Why deferred:
  M0 only requires structured failures and timeline visibility.
- Future problem solved:
  Failure clustering and automated remediation.

## RecoveryAction

- Deferred to:
  M3
- Why deferred:
  M0 does not automate recovery beyond cancellation and reset.
- Future problem solved:
  Guided repair and semi-automatic retry strategies.
