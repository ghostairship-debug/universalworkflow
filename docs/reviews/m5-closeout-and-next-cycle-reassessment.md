# M5 Closeout And Next-Cycle Reassessment

## Purpose

This document recenters the repository after `M5 Phase 0` to `M5 Phase 2`.

It answers three questions:

1. What the frozen near-term plan actually required
2. Which work stayed inside that frozen scope and which work drifted beyond it
3. What the next planning action should be if the repository returns to the original roadmap discipline

---

## 1. Current Truth Snapshot

The repository has two different planning frames that now need to be read separately.

### A. Current-cycle freeze that was explicitly documented

`M5 Phase 0` froze the next cycle to:

- real LLM integration through the existing runtime boundary
- minimal terminal UI for operator visibility

That freeze explicitly did **not** reopen:

- richer review-policy breadth
- new domain-pack families
- Web frontend work
- distributed runtime semantics

This is the governing near-term scope for `M5`.

### B. Long-term master-plan direction

The master plan says the deeper expansion work enters the second 12-week cycle:

- Memory
- Domain Pack
- Simulation

It also keeps the operator surface CLI-first and delays heavier frontend work.

So the long-term plan is broader than the `M5` scope freeze, but the `M5` freeze still governs what should have happened immediately after `M4`.

---

## 2. What Was Actually In-Scope For M5

Inside the frozen `M5` scope, the expected sequence was:

1. `M5 Phase 0`
   Revalidate the shipped `M4` closeout and freeze the next small cycle
2. `M5 Phase 1`
   Add one real LLM-backed path through the existing `RuntimeGateway`
3. `M5 Phase 2`
   Add one minimal terminal operator surface
4. Then stop and reassess
   Do **not** keep expanding runtime architecture until a new scope freeze exists

So the correct immediate post-`M5 Phase 2` action was:

- close out `M5` as a small frozen cycle
- write the next-cycle reassessment
- decide the next official development track before more implementation

---

## 3. What Landed Inside The Frozen Scope

The following work stayed aligned with the frozen `M5` plan:

- `M5 Phase 0`
  - cycle revalidation
  - governance regression fix
  - explicit scope freeze to `LLM + minimal TUI`
- `M5 Phase 1`
  - `OpenAIRuntimeGateway`
  - `runtime_brief` projection
  - opt-in live provider path while keeping the no-LLM baseline green
- `M5 Phase 2`
  - minimal read-mostly operator TUI
  - no Web reopening
  - no inline mutation workflow

These three phases should be treated as the completed, scope-correct `M5` baseline.

---

## 4. Where Drift Began

Scope drift began **after `M5 Phase 2`**.

The drifted line was:

- `M5 Phase 3 - CLI-first architecture correction and OpenCode adapter`
- discussion about making TUI directly execute workflows

Why this is drift:

- it was not included in the `M5 Phase 0` scope freeze
- it reopens execution-architecture work after the small cycle had already been bounded
- it changes the cycle from `LLM + TUI validation` into a new adapter/runtime program

This does **not** mean the exploratory work was valueless.
It means it should not be treated as the approved continuation of the frozen `M5` plan.

---

## 5. Assessment Of The Drifted Work

### `CLI-first` architecture correction

Assessment:

- architecturally meaningful
- aligned with the original worker-fabric direction
- **not** wrong in substance
- wrong mainly in **timing and scope discipline**

So it should be reclassified as:

- candidate work for a **new cycle**
- not as unfinished `M5`

### TUI direct workflow execution

Assessment:

- useful operator enhancement
- even farther from the frozen `M5` scope than the adapter correction
- should not be the next immediate step if the goal is to return to the original roadmap discipline

So it should be reclassified as:

- later operator-surface expansion
- not current-cycle closeout work

---

## 6. Decision

The repository should now treat `M5` as follows:

- `M5 Phase 0` to `M5 Phase 2`: **completed and in-scope**
- `M5 Phase 3`: **exploratory / out-of-freeze candidate**, not the current approved baseline

This means the correct immediate action is:

- stop expanding `M5`
- close out `M5`
- freeze a new cycle before further implementation

---

## 7. Recommended Return-To-Plan Path

If the goal is to return to the original planning discipline, the next steps should be:

1. Treat `M5` as closed at `Phase 0-2`
2. Open a new cycle with a fresh scope-freeze phase
3. Choose one official development line and reject parallel drift

### Recommended immediate planning phase

Recommended next phase:

- `M6 Phase 0 - Next-Cycle Rebaseline And Scope Freeze`

Its job should be:

- record `M5 Phase 0-2` as the completed current baseline
- explicitly mark adapter-correction work as a candidate, not an already-approved line
- choose the single next-cycle priority

---

## 8. Candidate Next-Cycle Priorities

There are three realistic candidates now.

### Option A - `optional` review policy

Pros:

- smallest carry-over gap
- directly linked to `TD-006`

Cons:

- narrower than the original master-plan direction
- less foundational than the platform work below

Assessment:

- valid tactical debt repayment
- not the strongest “return to the original long-term plan” choice

### Option B - Domain Pack platformization baseline

Pros:

- best aligned with the master plan
- the master plan explicitly puts deeper `Domain Pack` work into the second cycle
- current repo already has a minimal enabled `Domain Pack`, so there is a natural next step
- creates a cleaner base before later `Memory` / `Simulation` hooks

Cons:

- larger than `optional`
- needs careful scoping to avoid reopening architecture too broadly

Assessment:

- **best fit** if the goal is to return to the original roadmap

### Option C - CLI-first adapter correction

Pros:

- meaningful architectural cleanup
- aligned with original worker-fabric intent

Cons:

- was already the source of the recent scope drift
- easier to over-expand into a broad runtime/CLI integration program
- less directly tied to the master plan than `Domain Pack / Memory / Simulation`

Assessment:

- worth doing later
- should not be the automatic next step if the team wants to regain planning discipline first

---

## 9. Recommendation

Recommended choice:

- **close `M5` at `Phase 0-2`**
- open `M6 Phase 0` as a true reassessment/scope-freeze phase
- choose **Domain Pack platformization baseline** as the preferred next official development line

Why this is the best return-to-plan move:

- it matches the master plan better than continuing TUI or adapter work
- it uses the minimal `M4` domain-pack seed as a real bridge into cycle two
- it leaves `optional` and `CLI-first adapter correction` visible as candidates instead of silently dropping them

---

## 10. Concrete Follow-Up Rule

Until `M6 Phase 0` is written and frozen:

- do not continue `M5 Phase 3`
- do not expand the TUI into a write surface
- do not keep adding new adapters

The next implementation should start only after the new cycle explicitly chooses:

- `optional`
- `Domain Pack`
- or `CLI-first adapter correction`

with one of them made the single approved mainline.

---

## Conclusion

The repository is **not blocked by broken code**.
It is at a **planning-boundary correction point**.

The correct recovery move is not rollback.
It is:

- recognize `M5 Phase 0-2` as the completed frozen cycle
- mark later expansion as out-of-freeze candidate work
- reopen the roadmap cleanly through a new scope-freeze phase
- prefer `Domain Pack platformization baseline` if returning to the original long-term plan is the priority
