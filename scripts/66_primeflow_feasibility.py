"""PRiMeFlow feasibility from the paper text. Not a run of the model.

Arc recommended reading PRiMeFlow. This script records what the v2 preprint
says about zero-shot context transfer versus finetuning on the query context,
and what is still missing (code, weights, cost). It does not download weights
and does not claim a VCC 2026 number.

Evidence is cited from arXiv:2604.13986v2 as retrieved 2026-09-15.

    scripts/py.cmd scripts/66_primeflow_feasibility.py --out reports/primeflow_2026-09-15
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.manifest import RunManifest

CLAIMS = [
    {
        "id": "A1",
        "statement": (
            "PRiMeFlow is an end-to-end flow-matching model in gene-expression "
            "space (U-Net velocity field)."
        ),
        "source": "arxiv:2604.13986v2 abstract and §methods",
        "section": "abstract",
        "claim": "cited",
        "access": "html abstract + selected sections, 2026-09-15",
    },
    {
        "id": "A2",
        "statement": (
            "Reported 'outstanding performance' on ARC VCC 2025 H1 uses a "
            "pretraining-then-finetuning strategy, not pretrained-only."
        ),
        "source": "arxiv:2604.13986v2 abstract; §4.4; Appendix B",
        "section": "4.4 / Appendix B",
        "claim": "cited",
        "access": "html, 2026-09-15",
    },
    {
        "id": "A3",
        "statement": (
            "On H1 public test, pretrained-only PDS 0.712 vs finetuned-200pts PDS 0.817 "
            "(Table 5). Finetuning helps. These are VCC 2025 metrics, not 2026."
        ),
        "source": "arxiv:2604.13986v2 Table 5",
        "section": "Appendix C Table 5",
        "claim": "cited",
        "access": "html, 2026-09-15",
        "not_vcc2026": True,
    },
    {
        "id": "A4",
        "statement": (
            "Finetuning variants include H1 perturbations and, in 300pts, external "
            "data covering public and private test perturbation identities. "
            "Control cells from external data are kept during finetuning."
        ),
        "source": "arxiv:2604.13986v2 Appendix B",
        "section": "Appendix B",
        "claim": "cited",
        "access": "html, 2026-09-15",
    },
    {
        "id": "A5",
        "statement": (
            "VCC 2025 H1 provided perturbative training in the query context. "
            "VCC 2026 query contexts have no perturbations. A 2025 H1 number "
            "does not demonstrate 2026 zero-shot context transfer."
        ),
        "source": "VCC 2026 task vs paper §2.2 / §4.4",
        "section": "interpretation",
        "claim": "derived",
        "access": "docs/PROGETTO.md + paper",
    },
    {
        "id": "A6",
        "statement": (
            "Covariate-transfer experiments on Srivatsan20 and Jiang24 in "
            "PerturBench are a closer analogue, but the paper's VCC headline "
            "result is the H1 finetuned number."
        ),
        "source": "arxiv:2604.13986v2 §2.1–2.2",
        "section": "2.1-2.2",
        "claim": "cited",
        "access": "html, 2026-09-15",
    },
    {
        "id": "A7",
        "statement": "Official code and weights were not located in this session.",
        "source": None,
        "section": None,
        "claim": "missing",
        "access": "web search 2026-09-15; arxiv page only",
    },
    {
        "id": "A8",
        "statement": (
            "Inference uses Dopri5 ODE integration from Gaussian noise with "
            "classifier-free guidance (weight 20 perturbed / 5 control) and "
            "manually zeros the target gene. Cost of a 18,533-gene U-Net ODE "
            "on this hardware is unmeasured."
        ),
        "source": "arxiv:2604.13986v2 Appendix B.3",
        "section": "B.3",
        "claim": "cited",
        "access": "html, 2026-09-15",
        "cost": None,
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    dest = args.out / "primeflow_feasibility.json"
    if dest.exists():
        raise FileExistsError(f"{dest} exists; give a new --out")

    report = {
        "paper": "arxiv:2604.13986v2",
        "url": "https://arxiv.org/abs/2604.13986",
        "html": "https://arxiv.org/html/2604.13986v2",
        "claims": CLAIMS,
        "vcc2026_zero_shot_context": {
            "paper_demonstrates_it_on_vcc2026": False,
            "pretrained_only_exists": True,
            "pretrained_only_weaker_on_vcc2025_h1": True,
            "finetuning_uses_query_context_perturbations": True,
            "code_weights": "missing",
            "pilot_cost": "missing",
        },
        "decision": "defer",
        "decision_note": (
            "Do not port PyTorch flow-matching before a measured cost and a "
            "protocol that holds out ALL query-context perturbations. The VCC "
            "2025 H1 headline is the wrong task. A minimum experiment, if code "
            "appears, is pretrained-only on our frozen splits versus "
            "ShrunkTransfer, with query perturbations excluded."
        ),
        "minimum_experiment_if_code_appears": {
            "model": "pretrained-only PRiMeFlow, no query-context finetuning",
            "split": "configs/eval_protocol.yaml confirmation seed 4242 after freeze",
            "baseline": "ShrunkTransfer",
            "budget": "unknown until weights and runtime are measured",
        },
        "claim": "cited/derived; no model was run",
    }
    dest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md = args.out / "primeflow_feasibility.md"
    lines = [
        "# PRiMeFlow — fattibilità per VCC 2026",
        "",
        "Fonte: [arXiv:2604.13986v2](https://arxiv.org/abs/2604.13986), consultato il 2026-09-15.",
        "Nessun peso è stato scaricato e nessun modello è stato eseguito.",
        "",
        "| ID | Tipo | Affermazione | Sezione |",
        "|---|---|---|---|",
    ]
    for item in CLAIMS:
        lines.append(
            f"| {item['id']} | {item['claim']} | {item['statement']} | {item.get('section') or '—'} |"
        )
    lines += [
        "",
        "## Decisione",
        "",
        report["decision_note"],
        "",
    ]
    md.write_text("\n".join(lines), encoding="utf-8")
    manifest = RunManifest(
        run_id=args.out.name, stage="66_primeflow_feasibility", config={},
    )
    manifest.add_output("json", dest)
    manifest.write(args.out / "manifest_66_primeflow_feasibility.json")
    print(f"wrote {dest}")
    print(f"decision: {report['decision']}")


if __name__ == "__main__":
    main()
