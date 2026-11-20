# Presentation Script: Final Presentation (about 15 minutes)

Slides: the *Adaptive Learning-Path Planner: Final Presentation* deck (Claude Slides; it exports to PowerPoint or PDF). The speaker notes in the deck hold the same text as this file.

Every number on the slides comes from a committed result file (named in each slide's footer); `docs/Project_Report.pdf` and `docs/final/LIMITATIONS.md` have the details.

## Who says what

- **Bhuvan (Track A):** slides 1–8 (problem, system, planner) and slides 20–21 (way forward, summary).
- **Abdur (Track B):** slides 9–19 (evaluation, results, the Week 8 extension, demo pages, limitations).

| # | Slide | Speaker | Time |
|---|---|---|---|
| 1 | Adaptive Learning, Diagnostic Assessment and Personalized Path-Planning Engine | Bhuvan | 30 s |
| 2 | One fixed course order cannot serve every learner | Bhuvan | 45 s |
| 3 | Eight modules, one Python service, 303 passing tests | Bhuvan | 45 s |
| 4 | The planner never sees the simulator’s truth | Bhuvan | 40 s |
| 5 | Diagnose once, then plan, act and replan every day | Bhuvan | 50 s |
| 6 | Four classes decide what is unlocked; every decision gets a reason | Bhuvan | 45 s |
| 7 | Cold start → Integrals in 8 days | Bhuvan | 40 s |
| 8 | A missed day shifts the plan; an impossible request gets a proof | Bhuvan | 40 s |
| 9 | Greedy reaches 97% of the exact optimum; a fallback lifts it to 98% | Abdur | 45 s |
| 10 | Same simulated learners for every arm; a claim needs a CI that excludes zero | Abdur | 50 s |
| 11 | Adaptive beats the static course order in every scenario | Abdur | 60 s |
| 12 | The advantage holds on a bigger curriculum and a different simulator | Abdur | 45 s |
| 13 | When the engine says 0.93, the learner really knows it | Abdur | 40 s |
| 14 | Does our learner model fit real students? | Abdur | 20 s |
| 15 | Fitted BKT predicts held-out students better than our defaults | Abdur | 60 s |
| 16 | The headline result survives; so does the diagnostic problem | Abdur | 50 s |
| 17 | Watch a simulated learner, step by step | Abdur | 45 s |
| 18 | Or answer the questions yourself | Abdur | 40 s |
| 19 | Only the whole adaptive arm can be credited, not its parts | Abdur | 60 s |
| 20 | Each next step has a test that says when it is done | Bhuvan | 40 s |
| 21 | A prerequisite-safe, budget-bounded, explainable planner that beats a static course order, checked on real-student parameters | Bhuvan | 30 s |

Total about 15 min 20 s, which leaves time for questions in a 15–20 minute slot. If time is short, skip slide 8 (replanning) and slide 12 (robustness): their numbers also appear on slides 11 and 21.

## Before the presentation

- **Laptop:** plugged in, sleep off, Claude app not needed.
- **Terminal 1:** `.venv\Scripts\python site\serve_live.py`. Open <http://127.0.0.1:8001/site/sim.html> and <http://127.0.0.1:8001/site/live.html> in two browser tabs.
- **Live site:** open <https://bhuvan-56.github.io/adaptive-learning-path-planner-DAT/site/demos.html> once, with internet, so Pyodide is cached for demo B (slides 7–8).
- **Fallback:** every slide has a screenshot, so if a live page fails, just stay on the slide.

## Script

### 1. Adaptive Learning, Diagnostic Assessment and Personalized Path-Planning Engine
*Bhuvan, about 30 s*

Good morning. We are Bhuvan and Abdur, group 11. Our project is an adaptive learning engine: given what a learner already knows, a target topic, a deadline and a daily time budget, it builds a day-by-day study plan, never schedules a topic before its prerequisites, never goes over the day’s minutes, changes the plan after every answer, and writes down why every topic was included or left out. In the next fifteen minutes: what we built, how we tested it, what the results show — including one result that goes against us — and what we added this week: a check on real student data and two new demo pages.

### 2. One fixed course order cannot serve every learner
*Bhuvan, about 45 s*

The brief starts from a simple observation: a beginner with ten minutes a day and an experienced learner who wants a quick refresher should not get the same course order. So the engine takes three inputs — what the learner knows, the target and deadline, and the daily time budget — and produces a day-by-day plan. Three requirements shaped every design decision. First, two hard rules: prerequisites must actually be learned before a dependent concept, and the daily budget is never exceeded. Second, the plan must adapt to new answers, missed days and changed constraints without throwing away completed work. Third, every decision must be explainable: each concept, on each day, carries a machine-readable reason.

### 3. Eight modules, one Python service, 303 passing tests
*Bhuvan, about 45 s*

We built a backend service in Python with eight modules that map one-to-one to the milestones in the brief. M1 holds the curriculum graph and the learner state: a Bayesian Knowledge Tracing mastery probability, an evidence count, and a classifier with four states. M2 is the computerized adaptive diagnostic. M3 to M6 are planning, difficulty, review and remediation, and replanning with feasibility proofs. M7 is the audit trace, and M8 is the evaluation harness with simulated learners. We froze 21 acceptance groups early; 20 pass, and one — repair suggestions for a heuristic no-plan case — is partial, which we agreed with the mentor. The full suite is 303 passing tests.

### 4. The planner never sees the simulator’s truth
*Bhuvan, about 40 s*

Here is the data flow. On the left, the inputs: the curriculum graph, the learner’s request, and the item bank for the diagnostic. In blue, the engine: the graph validator, the learner state, the diagnostic, and the planning engine with its four policy modules, producing the daily plan and the audit trace. In amber, the evaluation side: a simulated learner answers the questions and an evaluator scores the outcome. The key design rule is the dashed boundary — the simulator’s true knowledge is read only by the evaluator. The planner sees answers, never the truth, and a test enforces that no planning code can import it.

### 5. Diagnose once, then plan, act and replan every day
*Bhuvan, about 50 s*

This is the loop the engine runs. It validates the graph, runs a diagnostic of at most ten adaptive questions, and turns the ability estimate into starting beliefs. Then, every day: update the beliefs, find the frontier of concepts whose prerequisites are satisfied, score them by value per minute including reviews and repairs, check feasibility, log a reason for every candidate, and after any event — new answers, a missed day, a budget or deadline change — replan from step three. Three properties: a concept that is only planned does not unlock its dependents; lessons are indivisible blocks inside the budget; and when the deadline can’t be met, the engine proves it, names the smallest fix, and still gives the learner a best-effort plan instead of idling.

### 6. Four classes decide what is unlocked; every decision gets a reason
*Bhuvan, about 45 s*

The learner state is a BKT probability plus an evidence count, and a classifier with four classes checked in this order. Uncertain if we have fewer than three answers or the evidence is thin — this closed a loophole the mentor found in week one. Mastered needs high probability and three of the last four answers right; only Mastered unlocks dependents. Weak needs low probability and repeated failures; it blocks and can trigger remediation. Everything else is Developing. On the right are some of the reason codes. Every candidate concept on every day gets one, and a checker verifies full coverage — in every evaluated run the coverage is 100 percent.

### 7. Cold start → Integrals in 8 days
*Bhuvan, about 40 s; or switch to the live site here*

This is the plan builder on the website, running our own Python code in the browser through Pyodide. Cold start, target Integrals, thirty minutes a day, ten days. The plan is drawn on the prerequisite graph: darker means later. Fractions, variables and exponents on day one, through to Integrals on day eight. Concepts that Integrals does not need — logarithms, trigonometry, inequalities, systems — are faded and never scheduled. Starred items are conditional: their prerequisite was only planned earlier, so they are re-checked before they are done. Clicking any day opens the trace with a reason code for every concept.

### 8. A missed day shifts the plan; an impossible request gets a proof
*Bhuvan, about 40 s*

Two more behaviours from the same demo. On the left, the event “missed day one”: completed work is kept, the remaining plan shifts by a day, and because a mastered concept’s recall has decayed, a review appears in leftover minutes with the code REVIEW_DUE. On the right, a request that cannot work: eight minutes a day, but two lessons take ten. Instead of a silent empty plan, the engine returns INFEASIBLE_PROVED, names the blocking concepts, and gives the minimum fix — raise the budget to ten — and notes that more days would not help. When only the deadline is too short, it also returns a best-effort plan so the learner keeps working.

### 9. Greedy reaches 97% of the exact optimum; a fallback lifts it to 98%
*Abdur, about 45 s; Abdur takes over here*

Thanks, Bhuvan. Now, how good is it, and how do we know? First, scheduling. Choosing which lessons fit in a day is a knapsack-like problem, so we compared the greedy planner with an exact oracle on 250 random instances. Greedy averages 0.974 of the optimum. In week seven we added a best-singleton fallback — if one valuable item beats the whole greedy pick, take it — which lifts the mean to 0.981. The paired difference is small but real: its confidence interval excludes zero, ten instances reach the optimum, and none get worse. We do not claim a worst-case guarantee; there is a known 12-versus-18 counterexample, which we keep as a test.

### 10. Same simulated learners for every arm; a claim needs a CI that excludes zero
*Abdur, about 50 s*

Real learners could not use the planner in this course, so we evaluate in a closed loop with simulated learners, and we are explicit about the bias of each simulator. S0 is matched: learners behave exactly as the engine assumes, the most favourable case. S1 adds forgetting and a delayed retention quiz. S3 is deliberately mismatched: learning comes from practice counts. S4 is new this week: parameters drawn from real students — more on that later. Each run puts 1,000 learners through nine arms: our adaptive system, the two baselines the brief names, and five ablations. Every arm sees the same learners, so differences are paired, and we only call something better if the paired 95 percent bootstrap interval excludes zero.

### 11. Adaptive beats the static course order in every scenario
*Abdur, about 60 s*

The main result. Each row is a scenario; each dot is a paired difference with its 95 percent interval; right of the dashed line means our adaptive system is better. Blue is against the static course order: positive in every scenario, from plus 0.056 concepts on the small toy curriculum to plus 0.727 on the maths curriculum under the mismatched simulator. Retained recall also favours adaptive everywhere. Orange is against greedy: better in three of five, no difference shown in two. And green is the honest part: the ablation without the diagnostic beats the full system in every run. That’s defect B12. After we connected the diagnostic properly in week eight, a single ability estimate gives every probed concept the same middling probability, so few start as Mastered. A plausible but untested reason for the loss is that those concepts no longer get the extra practice a cold start gets. We report it rather than switching the default after seeing results.

### 12. The advantage holds on a bigger curriculum and a different simulator
*Abdur, about 45 s*

Is the result an artifact of a tiny curriculum or a simulator that matches our model? We ran a two-by-two: the 4-concept toy and the 16-concept maths curriculum, each with the matched and the mismatched simulator. Adaptive beats static in all four cells. We are careful about the mismatched simulator: it rewards practice directly, which favours an arm that practises more, so we say the result survives a different simulator, not that it would be larger with real people. On the right, the hard constraints: zero prerequisite violations and zero budget violations across 54,000 learner-runs, counted independently of the planner, and 100 percent trace coverage.

### 13. When the engine says 0.93, the learner really knows it
*Abdur, about 40 s*

Next: are the engine’s probabilities trustworthy? At the end of each run we score the engine’s mastery probability against the simulator’s truth. The reliability diagram shows the high-confidence bins sit near the diagonal: when the engine says about 0.93, 99.5 percent of those concepts are truly mastered. The worst bin is around 0.5, which is simply concepts the learner never practised. In the table, calibration gets worse in the harder settings — forgetting, the larger curriculum, and S4, where learners don’t follow the engine’s assumed parameters. That last row leads into what we added this week.

### 14. Does our learner model fit real students?
*Abdur, about 20 s*

Everything so far uses simulated learners whose parameters we chose. The obvious question from a reviewer is: does the model behind the engine fit real students at all? This week we went back to the public data route from our original plan and answered it for the learner model.

### 15. Fitted BKT predicts held-out students better than our defaults
*Abdur, about 60 s*

We used the ASSISTments 2009 to 2010 skill-builder data, the corrected release. After cleaning — original questions only, single-skill rows, first attempts, skills with enough students — that is 196 thousand answers from almost four thousand students in 56 skills, split by student so no one is in both training and testing. We fitted one BKT model per skill on the training students and predicted the test students’ answers one by one. The fitted model reaches AUC 0.714, better than our default parameters at 0.681 and the per-skill average at 0.621, and its log loss per student is better than the defaults with an interval excluding zero. The chart shows why: real students slip about twice as often as we assumed and guess less, and skills differ a lot. The engine still uses its defaults — changing them after seeing results would be an unregistered change, so it’s listed as future work.

### 16. The headline result survives; so does the diagnostic problem
*Abdur, about 50 s*

Then we used those fits to build a new scenario, S4. Each simulated learner gets its slip, guess and learn rates per concept from the real-student fits, while the engine keeps its own defaults — so the planner now faces learners who don’t behave the way it assumes. Same configuration as our main run otherwise. The headline holds: adaptive beats static by plus 0.055 concepts, almost exactly the S0 value, and retained recall too. The diagnostic problem B12 also holds, so it is not an artifact of the matched simulator. The small best-singleton gain disappears, and calibration gets worse, as expected. We re-ran S4 a second time and every per-learner file matched exactly.

### 17. Watch a simulated learner, step by step
*Abdur, about 45 s; switch to the live page if time allows*

We also built two demo pages this week. The Simulation page plays a whole session automatically. Pick a learner, press Start, and the evaluation’s simulated learner answers the adaptive diagnostic and then the daily practice towards Integrals — about 35 steps. On the right, the engine’s estimate sits beside the evaluator-only truth, so you can see mistakes happen: here Fractions is classed Weak although this learner actually knows it, after some unlucky slips. Below it, a chart shows every concept’s estimate moving after each answer, and the plan changing. The runs are recorded from the real engine, so the page also works on the public site.

### 18. Or answer the questions yourself
*Abdur, about 40 s*

The Live session page is the same loop with a person answering. It runs the real adaptive diagnostic — ten questions chosen by Fisher information — then daily practice towards Linear functions, and replans after every answer. Each wrong option is tagged with the mistake it reveals, so the feedback says, for example, “multiplied instead of adding.” Because the diagnostic needs SciPy, which is too large to download into the browser reliably, this page runs from a small local server using our own Python environment. The questions are hand-written for the demo, not from a dataset. While building this page we found a real bug, which brings me to the limitations.

### 19. Only the whole adaptive arm can be credited, not its parts
*Abdur, about 60 s*

We want to be clear about what does not work. B12, the diagnostic hurting, we have discussed, and it holds even on calibrated learners. B14 we found while building the live page: when the planner scheduled a review for a future day, it wrote that review into the log as if it had already happened, so a replan or a missed day made it disappear. In a minimal reproduction, a mastered concept lost its day-nine review after missed days, even though its recall was 0.67. We fixed it, then re-ran all six scenarios: results moved by at most 0.002 concepts and every conclusion stands. So B14 was not why the review ablation barely differs. Remediation works in unit tests but never fires in the closed loop. And all planning results are from simulated learners.

### 20. Each next step has a test that says when it is done
*Bhuvan, about 40 s*

Each next step is written with a test that says when it is done. First, per-concept diagnostic priors, so the diagnostic helps: done when the no-diagnostic ablation no longer wins. Second, make remediation actually reachable in the loop. Third — already done — B14 is fixed and re-measured. Next, adopt the fitted parameters — but as a pre-registered change, judged by calibration under S4. And finish the public-data work: fit the review half-life and run S4 with forgetting and on the maths curriculum.

### 21. A prerequisite-safe, budget-bounded, explainable planner that beats a static course order, checked on real-student parameters
*Bhuvan, about 30 s*

To summarise: the engine never violated a prerequisite or the budget in 54 thousand learner-runs, it explains every decision, and it beats a static course order — including on learners whose parameters come from real students. Its learner model predicts real held-out students with AUC 0.714. And we have been explicit about what does not work yet: the diagnostic, remediation, and the review logging bug. Everything is reproducible from the repository, and the website and demo pages are linked here. Thank you — we’re happy to take questions.

## Likely questions

**Why simulated learners and not real students?** Real learners could not use the planner during the course, and public logs cannot compare plans: they have no ground-truth mastery and no outcome for the plans a learner did not follow (ADR-010). We use simulators with stated biases, and since Week 8 we check the learner model on real ASSISTments students and calibrate one scenario (S4) to them.

**Why does the no-diagnostic ablation win (B12)?** One ability estimate gives every probed concept the same probability, and even an all-correct diagnostic reaches only p ≈ 0.76, below the Mastered threshold of 0.85. Why this lowers mastery was not tested. A plausible reason is that those concepts lose the practice-for-evidence a cold start gets. We kept the diagnostic in the delivered system (ADR-022) and list per-concept priors as P1.

**Why BKT and not deep knowledge tracing or an LLM?** The planner needs an explicit, per-concept mastery value and uncertainty to gate prerequisites and to explain decisions (ADR-001). BKT gives that, and on ASSISTments it predicts held-out students with AUC 0.714. A recent EDM 2026 study also found small knowledge-tracing models more accurate than general LLMs at predicting student answers.

**If fitted parameters predict better, why not use them?** Switching after seeing the results would be an unregistered change, and the 56 ASSISTments skills map to only a few of our curriculum concepts. It is listed as P7, to be judged by calibration under S4.

**What is B14, and does it change your results?** `replan` wrote a planned review into the log as if it had happened, so a later replan or a missed day dropped it. We fixed it on 20 November and re-ran all six integrated scenarios: adaptive_full's mastery moved by at most 0.002 concepts, every before/after interval contains 0, and every conclusion stands (`evaluation/results/w8/final_v3/b14_before_after.txt`). It was not the reason the review ablation rarely differs.

**Why is the greedy improvement so small?** Greedy is already at 0.974 of the optimum on average. The fallback fixes the cases where one valuable item beats the whole greedy pick: 10 of 250 instances, none made worse.

**How do we know the numbers are reproducible?** Every run writes a manifest with the git SHA, a config hash and output checksums. The S4 run was repeated and all five per-learner files matched exactly. `scripts/clean_run.ps1` reproduces the suite and the demo commands from a fresh clone.
