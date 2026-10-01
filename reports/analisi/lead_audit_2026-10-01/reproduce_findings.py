"""Small executable counterexamples for the audited CellNet code; no model training or real-data mutation."""
import argparse
import hashlib
import json
import pickle
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CODE = ROOT / "reports/modelli/risposta_biologica_2026-09-30"
sys.path.insert(0, str(CODE))
import cellnet as CN
import test_prepass as TP


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    a.out.mkdir(exist_ok=False)
    torch.set_num_threads(1)
    torch.manual_seed(13)
    model = CN.build_model(8, 2, 1, 1, np.arange(4), dim=4, rank=3, target_code="identity")
    with torch.no_grad():
        model.delta_out.weight.normal_(0, .1)
    x = torch.tensor([[10., 5., 9., 3., 5., 6., 8., 4.], [5., 6., 3., 6., 1., 8., 10., 2.]])
    mask = torch.ones_like(x, dtype=torch.bool)
    z, beta = model.context(x[:1, :4].reshape(1, 1, 4), torch.ones(1, 1, 4, dtype=torch.bool), x[:1].sum(-1).reshape(1, 1))
    beta = beta.expand(2, -1); z = z.expand(2, -1)
    delta, pi = model(z, beta, torch.tensor([0, 2]), torch.tensor([0, -1]), torch.zeros(2, dtype=torch.long))
    theta = torch.exp(model.log_theta[0])
    ll0 = CN.cell_loglik(x, x.sum(-1), beta, mask, theta)
    ll1 = CN.cell_loglik(x, x.sum(-1), beta + delta, mask, theta)
    mix = torch.logsumexp(torch.stack([pi.log() + ll1, (1-pi).log() + ll0]), 0)
    # A target-labelled perturbation and a control: the unknown branch on controls is never supervised.
    loss = -torch.where(torch.tensor([False, True]), ll0, mix).mean()
    loss.backward()
    known = float(model.target_emb.weight.grad[0].abs().max())
    unknown = float(model.target_emb.weight.grad[2].abs().max())
    assert known > 0 and unknown == 0
    model.zero_grad()
    z, beta = model.context(x[:1, :4].reshape(1, 1, 4), torch.ones(1, 1, 4, dtype=torch.bool), x[:1].sum(-1).reshape(1, 1))
    d, pi = model(z, beta, torch.tensor([0]), torch.tensor([0]), torch.tensor([0]))
    l0 = CN.cell_loglik(x[:1], x[:1].sum(-1), beta, mask[:1], theta.detach())
    l1 = CN.cell_loglik(x[:1], x[:1].sum(-1), beta+d, mask[:1], theta.detach())
    (-torch.logsumexp(torch.stack([pi.log()+l1, (1-pi).log()+l0]), 0).mean()).backward()
    baseline_grad = float(model.base.weight.grad.abs().max())
    assert baseline_grad > 0

    # A target exists only in a source with too few controls; the current prepass still calls its held-out rows C.
    with tempfile.TemporaryDirectory(prefix="vcc_lead_counterexample_") as temp:
        td = Path(temp).resolve()
        sh = td / "shards"; sh.mkdir()
        axis = td / "axis.csv"
        axis.write_text("gene_name\n" + "\n".join(TP.GENES) + "\n", encoding="utf-8")
        rng = np.random.default_rng(28)
        prob = np.ones(len(TP.GENES)) / len(TP.GENES)
        for study, context, nc, target in [("valid", "K", 40, "G1"), ("excluded", "Z", 2, "G2"), ("held", "H", 40, "G2")]:
            labels = ["NTC"]*nc + [target]*40
            counts = rng.poisson(30, (len(labels), len(TP.GENES)))
            TP.write_shard(sh / f"{study}.h5ad", counts, study, context, "L", labels,
                           [f"{study}_{i}" for i in range(len(labels))], f"synthetic:{study}")
        run = TP.run("prepass", "--shards", sh, "--axis", axis, "--holdout-context", "H", "--holdout-target-frac", 0,
                     "--min-controls-per-key", 20, "--eval-min-cells", 10, "--input-genes", 8, "--out", td / "pre")
        assert run.returncode == 0, run.stderr
        with (td / "pre/prepass.pkl").open("rb") as f:
            state = pickle.load(f)
        actual = set()
        for s in state["shards"]:
            rows = s["train_rows"]
            actual.update(state["symbols"][i] for i in s["tgt"][rows] if i >= 0)
        group = next(g for g in state["eval_groups"] if g["symbol"] == "G2")
        assert "G2" not in actual and group["class"] == "C"
        split_case = {"actual_training_targets": sorted(actual), "test_target": "G2", "reported_class": group["class"],
                      "correct_class": "J", "target_training_source_excluded": "fewer than 20 controls"}
        (a.out / "synthetic_prepass.log").write_text(run.stdout + run.stderr, encoding="utf-8")
    findings = {"unknown_target_embedding_gradient": unknown, "known_target_embedding_gradient": known,
                "baseline_gradient_from_perturbed_cells_only": baseline_grad, "post_qc_classification": split_case,
                "scope": "reproduced mechanisms, not their predictive effect size; code unchanged"}
    (a.out / "counterexamples.json").write_text(json.dumps(findings, indent=2), encoding="utf-8")
    (a.out / "manifest.json").write_text(json.dumps({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [CODE / "cellnet.py", CODE / "cell_data.py", CODE / "train_cellnet.py", CODE / "test_prepass.py", Path(__file__)]}, indent=2), encoding="utf-8")
    print(json.dumps(findings, indent=2))


if __name__ == "__main__":
    main()
