# Pre-M8 Phase B - Runtime Safety And Portability Hardening

**Phase status:** Completed  
**Phase position:** This phase begins after `PM8-A` establishes the hardening boundary, current-status trust rules, and source-package/worktree hygiene policy.

**Entry condition:** Pre-`M8` hardening is now a first-class phase series, but the runtime still had three concrete safety/portability gaps:

- declared adapter timeout budgets were not actually enforced
- subprocess-backed adapters inherited too much parent environment state
- compile-generated Python commands still used a hard-coded `"python"` invocation instead of the current interpreter

---

## 1. Reassessment

Current implementation status:

- `ShellAdapter` and `CliAdapterBase` exposed timeout budgets through cost estimation, but did not pass them into subprocess execution.
- `ShellAdapter` and `OpenCodeAdapter` inherited `os.environ` wholesale and then overlaid `packet.env`.
- compile-generated shell commands were still anchored to `"python"` instead of `sys.executable`.
- repository docs did not yet state the local-trusted execution boundary explicitly.

Decision:

- keep adapter semantics stable
- implement timeout enforcement as stable failure results rather than uncaught exceptions
- replace broad environment inheritance with a minimal allowlist + explicit packet env merge
- make compile-generated commands interpreter-portable
- document the local trust boundary for local CLI/API execution surfaces

---

## 2. In Scope

- enforce timeout budgets in `ShellAdapter`, `CliAdapterBase`, and `OpenCodeAdapter`
- add subprocess environment allowlist support for subprocess-backed adapters
- replace compile-generated `"python"` with `sys.executable`
- document the local-trusted execution boundary
- add targeted tests for timeout, env filtering, and interpreter portability

---

## 3. Out Of Scope

- new adapters
- subprocess sandboxing beyond local trust boundary documentation
- distributed worker isolation
- full governance contract restructuring
- service decomposition

---

## 4. Target Baseline

- timeout budgets declared by adapters are actually enforced
- timeout expiration becomes a stable execution failure result with diagnostic stderr
- subprocess-backed adapters do not inherit the full parent environment by default
- compile-generated subprocesses use the currently running interpreter
- operator docs explicitly state that CLI/API execution is a trusted local-machine boundary

---

## 5. Phase Task Breakdown Principle

This phase is split into:

1. timeout enforcement
2. subprocess environment allowlist
3. interpreter portability for compile-generated commands
4. trust-boundary docs, debt update, and verification

---

## 6. Outcome

- Added `packages/worker_adapters/subprocess_support.py` to centralize:
  - subprocess env allowlist construction
  - timeout-expiry normalization into stable `CompletedProcess` failure results
- Updated `CliAdapterBase`, `ShellAdapter`, and `OpenCodeAdapter` to:
  - pass `timeout=...`
  - use allowlisted subprocess envs
  - convert `TimeoutExpired` into return code `124` with a stable diagnostic message
- Updated compile-generated commands to use `sys.executable`.
- Added tests for:
  - shell timeout enforcement
  - env allowlist behavior
  - interpreter-portable compile commands
  - opencode timeout enforcement
- Added `docs/architecture/local_execution_trust_boundary.md`.
- Updated living docs and governance state so the next approved phase is now `PM8-C`.

Verification:

- `pytest tests/test_governance.py tests/test_execution_loop.py tests/test_cli.py tests/test_api.py -q`
  - `174 passed`
- `pytest -q`
  - `212 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

Result:

- Phase gate passed.
- The repository now enforces its declared local subprocess timeout budgets, bounds inherited environment state, and uses the active interpreter for compile-generated execution commands.

---

## 7. Next Reassessment

The next approved phase is:

- `Pre-M8 Phase C - Service Decomposition`

That phase should reduce `packages/core_domain/services.py` as the next major structural blocker before `M8`.
