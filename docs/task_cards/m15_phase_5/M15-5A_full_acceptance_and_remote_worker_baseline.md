# M15-5A Full Acceptance And Remote Worker Baseline

- Goal: run full acceptance against the shipped remote-worker baseline.
- Verification:
  - `python -m pytest -q`
  - `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `python -m infra.scripts.check_doc_links`
