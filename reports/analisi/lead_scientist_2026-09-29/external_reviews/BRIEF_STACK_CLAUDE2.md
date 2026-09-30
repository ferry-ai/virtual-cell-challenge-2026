# Independent Stack transfer audit

## Context
You are an independent reviewer working with the lead scientist. The owner explicitly authorizes using this Claude2 account even if it differs from the account recorded by the hub. Earlier Claude2 attempt hit a session quota reset at 21:20 Europe/Rome, not an authentication failure. Do not change authentication or use another account. Read repository CLAUDE.md and relevant folder instructions. Workspace is shared and dirty; do not modify any file.

We are preparing a VCC2026 candidate before 02:00 CEST. A 217M pretrained Stack pilot is starting on Colab. The owner confirmed personal/noncommercial participation and checkpoint use was checked against the 2026 FAQ. There is no authorized competition submission. The pilot uses frozen public K562 perturbation cells and destination HepG2 control cells, with no destination perturbation outcome in inference. A later scorer compares generated cells with true HepG2 perturbations on 12 preregistered development targets. This is NOT a clean pretraining holdout claim.

## Task
Read the following files under reports/analisi/lead_scientist_2026-09-29/neural/:
- stack_pilot.py, stack_plan_r1.json, STACK_ALLOWLIST.json, REVIEW_STACK.md
- score_stack_pilot.py and its tests
- stack_remote_receipt_r2/review_manifest.json and stack_remote_runner.py
- stack_production_pack.py and stack_confirmation_pack.py if present

Audit the biological and numerical contract: source/destination direction in the official Stack API, paired synthetic controls, raw counts vs log/CPM units, gene masking/closure, handling source prompt cardinality and duplicated symbols, comparison with transferred baseline, and whether the pilot can support the proposed production application. Prioritize a concrete failure that could invalidate the comparison or misapply weights. Inspect official upstream sources only when necessary, using WebSearch/WebFetch; no shell or model calls. Existing tests are evidence of what they check, not proof of biological validity. Do not edit or execute training.

## Constraints
Read-only. No secrets, private challenge identity hypotheses, uploads, submissions, orchestration, extra agents, account changes or installations. Do not repeat known limits as new fatal bugs: frozen 12-target exploratory pilot, incomplete gene overlap, baseline support-mass preservation, pretrained HepG2 exposure unknown, and null d=0 not necessarily equal full biological null under composition have already been recorded.

## Done means
Return a concise Italian report with actionable findings ranked by severity, exact file/line evidence, the consequence for model validity, and a minimal correction or diagnostic. Separate verified defect, inference, and open question. If no new defect is supported, say so. Do not claim a model has run or improved without an actual output artifact.
