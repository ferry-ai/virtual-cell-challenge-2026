# Independent review of the two current neural candidates

## Context

The owner has explicitly authorized the lead scientist (Codex) to use this agent hub,
including Claude2 and Grok. This is a read-only review of a shared working tree at
`C:/Users/ferra/OneDrive/Desktop/vcc2026`. Do not edit, commit, run jobs, consume GPU
quota, send submissions, launch agents, or change any external service. Read root
`CLAUDE.md` and the applicable folder instructions. Other agents are actively editing
the tree; a changed-tree warning does not by itself mean your review modified it.

Reports for the current session are under
`reports/analisi/lead_scientist_2026-09-29/` (called R below). The source-attention
model has already been pushed to a private Kaggle notebook; five family-held-out
folds are running. No neural improvement is claimed. Stack is a separate pretrained
217M-parameter pilot using real K562 perturbation prompts and destination HepG2
controls; no perturbed HepG2 truth enters inference. The owner confirmed personal,
noncommercial participation, allowed for these checkpoints by the current VCC FAQ.

## Task

If you are **Grok**, review the scientific validity and implementation of source-attention:
`R/PROTOCOLLO_NEURALE.md`, `R/neural_sources.py`, `R/train_neural_sources.py`,
`R/read_neural_sources.py`, `R/verify_neural_runs.py`, and their local dependencies.
Look for leakage through targets/families, mislabeled metrics, wrong holdout logic,
mask-dependent ranking, misleading baselines, and train/inference inconsistencies.
The old reader's pandas parsing of the literal `null` is already fixed separately;
do not report that as an undiscovered bug. Training is frozen and should not be
restarted for cosmetic issues. Distinguish fatal validity bugs from limitations.

If you are **Claude2**, review the Stack pilot:
`R/neural/PROTOCOLLO_STACK.md`, `stack_pilot.py`, `stack_remote_runner.py`,
`score_stack_pilot.py`, `STACK_ALLOWLIST.json`, `requirements_stack.txt`, and the
pinned official API where necessary. Look for raw-count/axis errors, source prompt
size/API mismatches, synthetic-control correction mistakes, dependency incompatibility,
leakage and scorer aggregation. The plan hash CRLF/LF mismatch is already diagnosed
and fixed in launcher r2 by exact JSON field equality. The MSE ratio-of-sums versus
mean-of-ratios check has also been flagged and is being fixed; focus on other defects.
The local 12-target PDS panel and unknown pretraining overlap are explicit limitations.

## Constraints

Use only file reading/searching and primary-source web tools; no shell commands.
Do not read credentials or private context-identity hypotheses. Do not read the
generator confirmation results: the candidate selection must remain frozen.
No broad review of the entire repository, no stylistic rewrite, no invented results.
If a read is unavailable, state exactly what was not verified.

## Done means

Return a concise Italian report with concrete findings, file and line references,
severity and a minimal correction or diagnostic for each. Say explicitly if there
are no additional fatal findings. Separate measured code facts from scientific
limitations and unverified hypotheses. The lead will reproduce and integrate findings.
