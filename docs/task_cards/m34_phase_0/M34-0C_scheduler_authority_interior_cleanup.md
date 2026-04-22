# M34-0C Scheduler-Authority Interior Cleanup

Status: completed

## Goal

Continue the scheduler-authority semantic honesty line behind the already-correct public wording by reducing legacy interior naming where it still overstates the actual guarantee.

## Acceptance

- identify the remaining storage/event/diagnostic names that still retain legacy consensus-era wording
- rename, wrap, or alias those semantics where safe without breaking external compatibility
- preserve the accepted public honesty baseline for `/healthz`, cluster/operator surfaces, CLI, and API
- update tests and governance/readiness evidence where naming or wording changes

## Notes

- this card is semantic honesty cleanup, not a claim that the runtime has become a stronger distributed system
- prefer additive compatibility and bounded interior cleanup over risky migrations unless a migration becomes necessary and safe

## Result

- renamed the remaining scheduler-authority private helper symbols from generic `term`-oriented names to more honest authority-oriented names where that change stayed implementation-only
- propagated additive `authority_term_no` / `decision_index` aliases deeper into committed-lease payloads, arbitration provenance, scheduler dispatch context, remote-worker execution/renewal diagnostics, and projection/state read models
- kept the legacy compatibility keys (`term_no` / `commit_index`) in place everywhere public compatibility still depends on them
- fixed a bug-first regression uncovered during targeted tests where `status-detail` and `operator-view` projection still bypassed the new alias-shaping path for `active_committed_lease`
- intentionally did not rename storage-backed models, tables, or persisted event vocabulary such as `SchedulerConsensusTerm`, `scheduler_consensus_terms`, `scheduler_vote_records`, `term_no`, or `commit_index`
