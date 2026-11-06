# Week 7 commit SHA map

On 2026-11-06 the Week 7 commits were rewritten to remove a commit-message trailer line. File contents did not change: the tree of the merge commit is `1a8a6f671b980a43065cda2fdf570d8f1a774cfe` before and after. Only the commit SHAs changed.

Run manifests under `evaluation/results/w7/` are run outputs and still record the pre-rewrite SHA they were produced at. Use this table to find the matching commit.

| Pre-rewrite SHA | Current SHA | Commit |
|---|---|---|
| `d8cec16` | `2a1603c` | docs(w7): pre-registration for best-singleton fallback and AI log header |
| `408be9a` | `c317a77` | chore(w7): phase 0 baseline outputs and BASELINE.md |
| `8a1fc80` | `9b50459` | test(w7): bad-case fixtures and xfail test for S1 daily forgetting defect |
| `fbce12a` | `d95ab7e` | test(w7): xfail tests for best-singleton fallback |
| `edc2315` | `d7e1ea2` | feat(w7): best-singleton fallback module for greedy scheduler |
| `142c83e` | `771e56a` | feat(w7): scheduling policy comparison greedy vs best-singleton |
| `0ec795c` | `f223b9d` | refactor(w7): move compare_policies to src/evaluation to respect planning import boundary |
| `1665bc3` | `47a3d4a` | results(w7): scheduling comparison greedy vs best-singleton |
| `1998685` | `d97da01` | feat(w7): opt-in non_adaptive_greedy_best_singleton integrated arm |
| `313c76d` | `c1f8099` | results(w7): integrated S0 run with best-singleton greedy arm |
| `2b4f47f` | `505df09` | docs(w7): comparison of greedy vs best-singleton fallback |
| `b475079` | `59969d8` | docs(w7): weekly report W7 |
| `0c4efd8` | `ffdb446` | docs(w7): fill decision lines and drop reviewer row |
| `616a458` | `eab97e4` | docs(w7): fill bandit no-go reason |
| `f28ad14` | `f041520` | Merge w7/solo: Week 7 best-singleton fallback |
