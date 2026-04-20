# M14-5A Full Acceptance And Operator Baseline

- Goal: run full acceptance for the shipped Web-operator milestone.
- Verification:
  - `python -m pytest -q`
  - `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `python -m infra.scripts.check_doc_links`
