# Week 3 AI Interaction Log

## Entry 1: Task `w3/a1-oracle` - Oracle Repair & Order Independence
- **Date:** 2026-10-12
- **Tool:** Antigravity IDE
- **Model:** Gemini 3.7 Flash
- **Task:** Repair `src/planning/oracle.py` (Defect 1: input order dependency in `run_exact_dp_oracle`), rename to `run_exhaustive_oracle` with backward-compatible deprecated alias, update call sites, add independent brute-force reference check over 200 random instances and permutations, add cap/timeout/zero-item edge tests.
- **Files Changed:**
  - `src/planning/oracle.py`
  - `src/planning/benchmark.py`
  - `tests/test_m3_oracle_order.py`
  - `tests/test_m3_oracle_bruteforce.py`
  - `tests/test_m3_path_planning.py`
  - `evaluation/results/w3/before_defect1.txt`
  - `evaluation/results/w3/after_defect1.txt`
- **Checks Run:**
  - `.venv_w2\Scripts\python.exe -m pytest tests/test_m3_oracle_order.py -v -rxX` (XFAIL observed before fix)
  - `.venv_w2\Scripts\python.exe -m pytest tests/test_m3_oracle_order.py -v` (PASSED after fix)
  - `.venv_w2\Scripts\python.exe -m pytest tests/test_m3_oracle_bruteforce.py -v` (6 passed: 200/200 brute-force agreement, 2-item & 4-item permutations, caps, timeout, zero feasible)
  - `.venv_w2\Scripts\python.exe -m pytest -q -rs` (42 passed, 9 skipped)
- **Reviewer Name:** 
