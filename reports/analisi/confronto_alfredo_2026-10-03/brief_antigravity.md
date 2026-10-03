# Independent critique of the teammate research direction

## Context

The owner explicitly authorized consulting Antigravity in this chat. Work read-only on the VCC2026 repository. First read root CLAUDE.md and PROGETTO section 0, then only relevant sources. Two Claude sessions own ingestion and cell-level neural training. Do not duplicate those tasks. Output your complete report in Italian in your final response; the launcher will preserve it. Do not edit files, run shell commands, launch jobs, download datasets, invoke other agents, or commit. Use file reading tools only (headless command permissions cannot be granted). No web access is needed for this critique. Facts below attributed to Alfredo are reported by him, not independently verified.

Alfredo reports: R-LEAD r1 with learned mixture probability pi and floor zero collapsed after 400-500 steps; responder effects then received negligible gradient. Technical gate failed and he correctly refuses Q1-Q4 interpretation. He proposes floor 0.05 or fixed pi early, early stop at pi_mean <0.05 in the first 1000 steps and early checkpoints. He says a floor increases gradients 50,000-fold. He also reports abandoning a two-moment emission approach: MSE approximately 1 + prediction energy/4786, aggregate cosine around 0.12 allegedly required for a positive scaled MSE. He speculates high leaderboard MSE is largely a correction/layout exploit. He reports equivalent scorer outputs under cell_eval2 0.16 and 0.18. His reports and code are on another machine/branch, not available here; do not invent their implementation.

His current Strada C: leave one line out among H1, KOLF, HepG2, Jurkat; evaluate same-type sources, cross-type, all, K562, alloc and normrest; shuffled target controls; paired bootstrap with MSE ratio of sums. Primary registered rule: on H1 the lower confidence bound for same-cross >0; on KOLF mean >=0; same beats same_shuf. Kernel already launching on his account; do not amend its rule retrospectively. Ambiguity: "same" might mean same broad cell type or same exact line in an independent study. Ask explicitly how the verdict should differ. He guesses final D/E/F might be stem-like, without evidence supplied.

Verified local developments to investigate:
- reports/modelli/rete_cellulare_2026-10-03/PROTOCOLLO.md sections 7-9: even floor 0.01 failed; a fixed pi=0.5 warmup still saw posterior responsibility drop to zero. Latest r3 removes mixture entirely (pi=1), bounded shifts, health gate at step 5000. This is not Alfredo's r1 nor the previous September r3.
- reports/modelli/rete_cellulare_2026-10-03/esito/decision_r3/decision.json: all three technical gates pass; Q1 cells-versus-mean and Q3 cells-versus-generic pass in the effects lane, Q2 versus transfer fails on all 3 lines. Expansion allowed by preregistered OR rule, not production adoption. Full-cell metric results are a separate lane.
- reports/analisi/generalizzazione_contesti_2026-10-02/p4_decision_nn_r2/LETTURA.md and p3_six_member_r2/LETTURA.md: simple and nonlinear pseudobulk context approaches have not justified adoption.
- reports/sorgenti/archivio_cloud_2026-10-02/INGESTIONE.md: ingestion proposals include CD4/Orion cells, completing Southard, KOLF pan-genome, Jiang=Mixscale (one source); acquired, integrated and actually used are separate states. H1 test stays closed.
- docs/GENERALIZZAZIONE.md: hold out full biological line groups across sources; missing genes masked; C and J separate; previous models and target-only bootstrap do not make a new context confirmation.

## Task

1. Challenge the mixture diagnosis and adequacy of the proposed safeguards. Distinguish prior pi from posterior responsibility and recovery of gradients from evidence of transfer.
2. Audit what Strada C could establish and cannot establish. Consider same type versus same line, source numbers/coverage/quality, target shuffles, common support, study confounding, direction and uncertainty of ratio MSE, and the meaning of KOLF mean >=0.
3. Recommend two complementary work packages for Alfredo that are distinct from ongoing ingestion and neural training, with frozen contrasts, data requirements, interpretable outcomes and fallback decisions. Prefer useful measured questions over another model shopping list. Do not require spending quota or opening reserves.
4. Identify unjustified claims about MSE thresholds, final context identities and leaderboard exploits. Derive ordinary squared-error geometry if helpful; do not assert it equals the exact scorer without implementation evidence.

## Done means

A concrete prioritized critique and proposed division of work, source paths for checked local facts, clear separation of measured/reported/hypothesis/proposed, and unresolved input requirements. Do not promote proxy metrics to official VCC score or call synthetic fixture success evidence of scientific benefit.
