# Week 5 AI Interaction Log

| Date | Tool and model | Task ID | Files changed | Checks run (command and result) | Reviewer (named) | What the reviewer checked |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-25 | Antigravity (Gemini 3.8 Flash) | w5/a1-acceptance-matrix | scripts/acceptance_matrix.py, experiments/w5_acceptance_map.yaml, tests/test_w5_a1_acceptance_matrix.py, evaluation/results/w5/acceptance_matrix_r1.md, evaluation/results/w5/acceptance_matrix_r1.csv | pytest tests/test_w5_a1_acceptance_matrix.py: 6 passed; python scripts/acceptance_matrix.py: exit 0; full suite: 208 passed, 1 skipped | | |
| 2026-10-25 | Antigravity (Gemini 3.8 Flash) | w5/a2-fix-planner-groups | None (A2 not needed) | Precondition suite check: 216 passed, 1 skipped; Acceptance matrix M3-a to M7-b audit: all 11 groups PASS except mentor-stated partial M4-a, 0 failed, 0 missing citations | | |
| 2026-10-25 | Antigravity (Gemini 3.8 Flash) | w5/a3-cli-evaluate | src/cli.py, scripts/clean_run.ps1, README.md, tests/test_w5_a3_cli_evaluate.py | pytest tests/test_w5_a3_cli_evaluate.py: 6 passed; pytest test_cli_demo.py test_w4_t2_slice.py: 27 passed; full suite: 231 passed, 1 skipped | | |
