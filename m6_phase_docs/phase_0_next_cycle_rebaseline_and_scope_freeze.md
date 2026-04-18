# M6 Phase 0 - Next-Cycle Rebaseline And Scope Freeze

**Phase status:** Planned  
**Phase position:** This phase starts after `M5 Phase 0` to `M5 Phase 2` are treated as the completed near-term cycle and after `M5` drift is explicitly recentered through the closeout reassessment. It does not reopen `M5`; it normalizes the current baseline, evaluates the next-cycle candidates under one planning frame, and freezes a single official mainline for `M6`.

**Entry condition:** `M5` is recognized as complete through `Phase 2`, `M5 Phase 3` is treated as exploratory rather than approved continuation, and the repository needs one clean next-cycle decision before more implementation.

---

## 1. Reassessment

Current implementation status:

- the shipped local-first workflow spine remains complete through the `M4` closeout baseline
- `M5 Phase 0` to `M5 Phase 2` added a real LLM-backed path plus a minimal terminal operator surface
- the repository also contains exploratory `CLI-first adapter correction` work that is architecturally meaningful but outside the frozen `M5` scope

Current planning problem:

- two different next-step instincts are now visible in the repository:
  - return to the original second-cycle roadmap
  - continue the newer adapter/operator expansion thread
- if both continue in parallel, scope discipline will loosen again and phase meaning will degrade

What must be answered now:

- what is the authoritative baseline that `M6` starts from
- which candidate line is the single approved next-cycle priority
- what must stay visible as candidate work without being silently promoted into the mainline

Decision framing:

- treat `M5 Phase 0` to `M5 Phase 2` as the completed current baseline
- keep later exploratory work documented but not auto-approved
- choose one official `M6` mainline before implementation resumes

---

## 2. Current Baseline To Carry Forward

`M6` should begin from the following accepted baseline:

- `M0` to `M4` remain the completed delivery spine
- `M5 Phase 0`
  - cycle revalidation
  - governance regression fix
  - next small-cycle scope freeze
- `M5 Phase 1`
  - real LLM integration through the existing runtime boundary
- `M5 Phase 2`
  - minimal read-mostly operator TUI

This means `M6` starts from a repository that already has:

- runtime execution, review, reconcile, repair, and governance surfaces
- one live LLM-backed path
- one minimal operator TUI
- one minimal enabled domain-pack seed

---

## 3. Candidate Next-Cycle Lines

Three candidate lines are currently visible.

### A. `optional` review-policy execution

Strength:

- smallest unresolved product gap
- direct continuation of the remaining review-policy discussion

Risk:

- tactical rather than foundational
- weaker match to the original second-cycle roadmap

### B. Domain Pack platformization baseline

Strength:

- best match to the original roadmap direction
- uses the existing minimal domain-pack seed as a real bridge into cycle two
- creates a cleaner platform base before any later `Memory` / `Simulation` work

Risk:

- needs strict scoping to avoid reopening broad architecture questions

### C. CLI-first adapter correction

Strength:

- meaningful alignment with the original worker-fabric intent
- improves the long-term execution-surface story

Risk:

- already the source of the most recent scope drift
- easy to expand into a broad runtime program
- weaker immediate fit than `Domain Pack` if the goal is to return to the original roadmap sequence

---

## 4. Scope-Freeze Recommendation

Recommended official `M6` mainline:

- **Domain Pack platformization baseline**

Why this should be frozen as the single next-cycle priority:

- it best matches the long-term master plan
- it turns the current minimal domain-pack proof into a platform boundary rather than a demo-only artifact
- it creates a more stable bridge into later `Memory` and `Simulation` work than continuing ad-hoc operator or adapter expansion

What remains visible but not approved as the mainline:

- `optional` review-policy execution
- `CLI-first adapter correction`

These should remain documented as candidate follow-ups or sidecar debts, not silent `M6` scope.

---

## 5. In Scope

- normalize the authoritative `M6` starting baseline from the completed `M5` cycle
- record the next-cycle priority decision in phase/task/review documentation
- freeze `Domain Pack platformization baseline` as the only approved `M6` implementation line
- define the first bounded problem set that turns the existing minimal domain-pack proof into a reusable platform baseline

---

## 6. Out Of Scope

- continuing `M5 Phase 3` as if it were approved mainline work
- expanding the TUI into a write surface
- adding new CLI adapters as default next-step work
- reopening broad frontend scope
- reopening distributed runtime semantics
- forcing `optional` into the same phase as domain-pack platformization
- jumping directly into `Memory` or `Simulation` before the domain-pack platform boundary is clarified

---

## 7. Target Baseline

At the end of this phase, the repository should have:

- one authoritative statement of what `M5` completed
- one authoritative statement of what `M6` is allowed to do next
- one approved next-cycle mainline: `Domain Pack platformization baseline`
- a bounded first implementation slice for that line, suitable for conversion into executable task cards

---

## 8. Phase Task Breakdown Principle

This phase is expected to split into:

1. Baseline normalization
   - restate the accepted `M5` closeout baseline
   - mark exploratory lines as candidate-only
2. Candidate-line evaluation
   - compare `optional`, `Domain Pack`, and `CLI-first adapter correction`
   - record the rationale for choosing one official mainline
3. New-cycle freeze
   - define the bounded first implementation slice for `Domain Pack platformization baseline`
   - convert that slice into the next executable phase entry

---

## 9. Phase Gate

The phase passes only if all of the following are true:

- `M5` closeout status is unambiguous
- only one official `M6` mainline is approved
- exploratory work remains visible but not silently promoted
- the next executable implementation phase can be named and bounded without reopening the entire roadmap

---

## 10. Expected Outputs

This phase should produce:

- an `M6` scope-freeze record
- the first `M6` implementation phase definition
- a task-card-ready problem slice for `Domain Pack platformization baseline`

Expected next implementation direction after this phase:

- `M6 Phase 1 - Domain Pack Platformization Baseline`

Its likely responsibility should be:

- clarify the reusable domain-pack contract surface
- separate `pack definition`, `capability exposure`, and `compile/runtime projection`
- keep the first domain-pack family narrow and executable

---

## 11. Final Rule

Until this phase is written and treated as the active freeze:

- do not continue `M5 Phase 3`
- do not treat adapter work as approved `M6` baseline
- do not expand the TUI into workflow mutation control

The next implementation should begin only after `M6 Phase 0` freezes the new cycle around a single mainline.
