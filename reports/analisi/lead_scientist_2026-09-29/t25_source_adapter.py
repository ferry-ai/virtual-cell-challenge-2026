"""Export learned token modifiers and apply them as a delta to actual t25 effects.

This is a separately validated candidate, not the frozen five-fold neural predictor.
`export` runs beside a trusted production checkpoint and the same r2 data. `apply`
needs only the small modifier archives, stage-98 r9 cache and original t25 effects.
No inference or training feature in the frozen network is changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))
from vcc2026.multisource import AxisTable

CD4 = ("cd4_Rest", "cd4_Stim8hr", "cd4_Stim48hr")
TOKENS = ("k562", *CD4, "orion_hct116", "orion_hek293t")
SOURCES = ("k562", "cd4_mix", "orion_hct116", "orion_hek293t")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def safe_names(values, label):
    out = np.asarray(values, dtype=str)
    if out.ndim != 1 or len(np.unique(out)) != len(out):
        raise ValueError(f"{label} must be a unique one-dimensional axis")
    return out


def protected_mask(target, genes, coordinates, window=5000):
    mask = genes == target
    if target in coordinates.index:
        row = coordinates.loc[target]
        aligned = coordinates.reindex(genes)
        distance = np.abs(pd.to_numeric(aligned.tss, errors="coerce").to_numpy() - float(row.tss))
        # Convert before reindexing: missing genes must not coerce chromosome 1 into 1.0.
        chromosomes = coordinates.chrom.astype(str).reindex(genes).to_numpy()
        mask |= (chromosomes == str(row.chrom)) & (distance <= window)
    return mask


class ProductionContributions:
    """Six context tokens, exactly decomposing the four-source production mixture."""
    def __init__(self, tables, *, gamma=1., reliability_scale=100.):
        self.tables, self.gamma, self.scale = tables, gamma, reliability_scale
        if set(tables) != set(SOURCES) | set(CD4):
            raise ValueError("Need the four t25 sources and all three CD4 state tables")
        self.genes = tables["k562"].shrunk.shape[1]
        if any(t.shrunk.shape[1] != self.genes for t in tables.values()):
            raise ValueError("Source response axes differ")
        self.indices = {name: table.index() for name, table in tables.items()}
        self.centres = {name: tables[name].common() for name in SOURCES}
        if set(tables["cd4_mix"].meta.get("from", [])) != set(CD4):
            raise ValueError("CD4 mixture provenance does not name exactly the three expected states")

    def row(self, name, target):
        table = self.tables[name]
        index = self.indices[name].get(target)
        if index is None:
            return np.zeros(self.genes), np.zeros(self.genes, bool), 0.
        x = table.shrunk[index].astype(float)
        observed = np.isfinite(x)
        cells = float(table.n_cells[index])
        reliability = cells / (cells + self.scale) if np.isfinite(cells) and cells > 0 else 0.
        return np.where(observed, x, 0), observed, reliability

    def contributions(self, target, source_weights):
        values = np.zeros((len(TOKENS), self.genes))
        weights = np.zeros_like(values)
        for name in ("k562", "orion_hct116", "orion_hek293t"):
            x, observed, rel = self.row(name, target)
            slot = TOKENS.index(name)
            values[slot] = np.where(observed, x - self.gamma * self.centres[name], 0)
            weights[slot] = observed * rel * float(source_weights[name])
        mixed, observed, outer_rel = self.row("cd4_mix", target)
        states = [self.row(name, target) for name in CD4]
        inner_weight = np.stack([ok * rel for _, ok, rel in states])
        denom = inner_weight.sum(0)
        if np.any(observed & (denom <= 0)):
            raise ValueError("CD4 mixture has measured genes not reconstructible from its states")
        inner_weight = np.divide(inner_weight, denom, out=np.zeros_like(inner_weight), where=denom > 0)
        state_values = np.stack([x for x, _, _ in states])
        reconstructed = (inner_weight * state_values).sum(0)
        correction = np.where(observed, mixed - reconstructed, 0)
        if np.max(np.abs(correction), initial=0) > 2e-6:
            raise ValueError("CD4 mixture differs from state decomposition beyond float32 rounding")
        for j, name in enumerate(CD4):
            slot = TOKENS.index(name)
            values[slot] = state_values[j] + correction - self.gamma * self.centres["cd4_mix"]
            weights[slot] = inner_weight[j] * observed * outer_rel * float(source_weights["cd4_mix"])
        denominator = weights.sum(0)
        original = np.divide((weights * values).sum(0), denominator, out=np.zeros(self.genes), where=denominator > 0)
        return values, weights, original, denominator > 0


def relative_delta(values, weights, ratio, gate):
    """Difference of weighted means; exact neutral operator, with no effect division."""
    if values.shape != weights.shape or ratio.shape != values.shape or gate.shape != values.shape:
        raise ValueError("Token array shapes differ")
    if not (np.isfinite(ratio).all() and np.isfinite(gate).all()):
        raise ValueError("Modifiers must be finite")
    if ((ratio < np.exp(-2) - 1e-6) | (ratio > np.exp(2) + 1e-6)).any() or ((gate < .75 - 1e-6) | (gate > 1.25 + 1e-6)).any():
        raise ValueError("Modifiers exceed the frozen network bounds")
    if np.all(ratio == 1) and np.all(gate == 1):
        return np.zeros(values.shape[1])
    old_den = weights.sum(0)
    new_weight = weights * ratio
    new_den = new_weight.sum(0)
    old = np.divide((weights * values).sum(0), old_den, out=np.zeros_like(old_den), where=old_den > 0)
    new = np.divide((new_weight * gate * values).sum(0), new_den, out=np.zeros_like(new_den), where=new_den > 0)
    return new - old


def adapt(reference, factors, contributions, spec, coordinates):
    targets = safe_names(reference["targets"], "reference targets")
    genes = safe_names(reference["genes"], "reference genes")
    if len(genes) != contributions.genes:
        raise ValueError("Cache axis width differs from reference")
    ft = safe_names(factors["targets"], "factor targets")
    fg = safe_names(factors["genes"], "factor genes")
    names = safe_names(factors["tokens"], "factor tokens")
    if set(names) != set(TOKENS):
        raise ValueError("Factor token mapping is not the registered six-token mapping")
    shape = (len(names), len(ft), len(fg))
    if factors["ratio"].shape != shape or factors["gate"].shape != shape:
        raise ValueError("Factor dimensions do not match their labeled axes")
    fti = {t: i for i, t in enumerate(ft)}
    gene_pos = pd.Index(genes).get_indexer(fg)
    if (gene_pos < 0).any():
        raise ValueError("Factor archive contains genes outside the reference axis")
    token_pos = [list(names).index(t) for t in TOKENS]
    lfc = np.asarray(reference["lfc"]).copy()
    observed = np.asarray(reference["observed"], bool)
    amp = float(spec["amplitude"])
    diagnostics = []
    for i, target in enumerate(targets):
        values, weights, original, source_observed = contributions.contributions(target, spec["weights"])
        protected = protected_mask(target, genes, coordinates)
        check = ~protected
        if not np.array_equal(source_observed[check], observed[i, check]):
            raise ValueError(f"{target}: cache observed mask is not the saved t25 baseline")
        error = float(np.max(np.abs((amp * original)[check] - lfc[i, check]), initial=0))
        if error > 2e-6:
            raise ValueError(f"{target}: t25 reconstruction failed, max absolute error {error:g}")
        ratio, gate = np.ones_like(values), np.ones_like(values)
        if target in fti:
            ratio[:, gene_pos] = factors["ratio"][token_pos, fti[target], :]
            gate[:, gene_pos] = factors["gate"][token_pos, fti[target], :]
        delta = .5 * amp * relative_delta(values, weights, ratio, gate)
        change = observed[i] & ~protected & (delta != 0)
        lfc[i, change] = (lfc[i, change].astype(float) + delta[change]).astype(lfc.dtype)
        diagnostics.append({"target": str(target), "factor_target_present": target in fti,
                            "changed_pairs": int(change.sum()), "reconstruction_max_abs": error,
                            "delta_l2": float(np.linalg.norm(np.where(change, delta, 0)))})
    return {"targets": targets, "genes": genes, "lfc": lfc, "observed": observed.copy()}, diagnostics


def token_modifiers(model, batch):
    """Extract the trained operators on unchanged r2 inputs; unsupported/fallback -> identity."""
    import torch
    with torch.no_grad():
        prior = model.prior(batch["priors"])[:, None, None].expand(*batch["value"].shape, 16)
        logit, gate = model.token(torch.cat([batch["features"], prior], -1)).unbind(-1)
        direct = batch["mask"] & (batch["features"][..., 17] == 0)
        ratio = torch.where(direct, torch.exp(2 * torch.tanh(logit)), torch.ones_like(logit))
        value_gate = torch.where(direct, 1 + .25 * torch.tanh(gate), torch.ones_like(gate))
        return ratio, value_gate


def export(args):
    import torch
    from neural_sources import P, SourceView, SourceAttention
    if args.out.exists():
        raise FileExistsError(args.out)
    run_manifest = json.loads((args.checkpoint.parent / "manifest.json").read_text())
    for file, old_hash in run_manifest["code_hashes"].items():
        name = file.replace("\\", "/").rsplit("/", 1)[-1]
        current = Path(P.__file__) if name == "pool.py" else HERE / name
        if not current.exists() or digest(current) != old_hash:
            raise ValueError(f"Changed frozen training code {name}")
    # Only load a checkpoint produced by this project's own trusted training run.
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    if checkpoint["options"]["holdout"] != "none" or checkpoint["options"]["regime"] != "C":
        raise ValueError("Production modifier export requires a full production C fit")
    for name, record in run_manifest["data_files"].items():
        current = args.data / name
        if not current.exists() or current.stat().st_size != record["bytes"]:
            raise ValueError(f"Dataset identity differs: {name}")
        if record["sha256"] and digest(current) != record["sha256"]:
            raise ValueError(f"Dataset hash differs: {name}")
    pool = P.Pool.from_dir(args.data)
    view = SourceView(pool, checkpoint["visible_rows"])
    model = SourceAttention(checkpoint["n_priors"])
    model.load_state_dict(checkpoint["state_dict"])
    model.to(args.device).eval()
    targets = np.asarray([t.strip() for t in args.targets.read_text().splitlines() if t.strip()], dtype=str)
    safe_names(targets, "requested targets")
    args.out.mkdir(parents=True)
    record = {"candidate": "t25_relative_source_delta", "validation_inherited": False,
              "checkpoint_sha256": digest(args.checkpoint), "training_manifest_sha256": digest(args.checkpoint.parent / "manifest.json"),
              "adapter_sha256": digest(Path(__file__)), "neutral_for_unmapped_targets": [t for t in targets if t not in pool.target_index],
              "tokens": TOKENS, "contexts": {}}
    slots = {pool.context_names[c]: j for j, c in enumerate(view.contexts)}
    if not set(TOKENS) <= set(slots):
        raise ValueError("Production view lacks a required direct-source context")
    genes = np.asarray(pool.genes.gene, dtype=str)
    for context in args.contexts.split(","):
        ratio = np.ones((len(TOKENS), len(targets), pool.G), np.float32)
        gate = np.ones_like(ratio)
        for i, target in enumerate(targets):
            if target not in pool.target_index:
                continue
            t = pool.target_index[target]
            for start in range(0, pool.G, 1024):
                g = np.arange(start, min(start + 1024, pool.G))
                batch = view.batch([t], [pool.basal_index[context]], [-1], g, device=args.device)
                r, h = token_modifiers(model, batch)
                positions = [slots[name] for name in TOKENS]
                ratio[:, i, start:start + len(g)] = r[0, positions].cpu().numpy()
                gate[:, i, start:start + len(g)] = h[0, positions].cpu().numpy()
        output = args.out / f"factors_{context}.npz"
        np.savez_compressed(output, targets=targets, genes=genes, tokens=np.asarray(TOKENS), ratio=ratio, gate=gate)
        record["contexts"][context] = {"sha256": digest(output), "neutral": bool(np.all(ratio == 1) and np.all(gate == 1))}
    (args.out / "manifest.json").write_text(json.dumps(record, indent=2), encoding="utf-8")


def apply(args):
    if args.out.exists():
        raise FileExistsError(args.out)
    recipe = json.loads(args.recipe.read_text())
    original = json.loads((args.reference / "manifest.json").read_text())
    required = {"name": "t25", "effect": "shrunk", "gamma": 1., "reliability_scale": 100}
    for key, value in required.items():
        if recipe.get(key) != value or original["recipe"].get(key) != value:
            raise ValueError(f"This adapter is registered only for the actual t25 {key}")
    if any(key in recipe for key in ("pooling", "gene_share", "association", "expression_gate")) or recipe.get("common", "panel") != "panel":
        raise ValueError("Unsupported modification of the t25 recipe")
    if recipe["contexts"] != original["recipe"]["contexts"] or recipe["cis"] != original["recipe"]["cis"]:
        raise ValueError("Recipe differs from the saved reference manifest")
    coords = pd.read_csv(args.coords, sep="\t").drop_duplicates("symbol").set_index("symbol")
    if digest(args.coords) != original["cis"]["coords_sha256"]:
        raise ValueError("Cis coordinate identity differs from actual t25")
    tables, hashes = {}, {}
    for name in (*SOURCES, *CD4):
        path = args.cache / f"{name}.npz"
        with np.load(path, allow_pickle=False) as z:
            x = z["shrunk"]
            tables[name] = AxisTable(name, z["targets"].astype(str).tolist(), x, x, np.empty((0, 0)), z["n_cells"], json.loads(str(z["meta"])))
        hashes[name] = digest(path)
    contributions = ProductionContributions(tables)
    args.out.mkdir(parents=True)
    report = {"candidate": "t25_relative_source_delta", "validation_inherited": False, "cache_sha256": hashes,
              "recipe_sha256": digest(args.recipe), "reference_manifest_sha256": digest(args.reference / "manifest.json"),
              "factor_manifest_sha256": digest(args.factors / "manifest.json"), "adapter_sha256": digest(Path(__file__)), "contexts": {}}
    factor_manifest = json.loads((args.factors / "manifest.json").read_text())
    if factor_manifest.get("candidate") != "t25_relative_source_delta":
        raise ValueError("Factor manifest is not the registered source-modifier export")
    for context, spec in recipe["contexts"].items():
        if set(spec["weights"]) != set(SOURCES) or float(spec["amplitude"]) != 1.576:
            raise ValueError("Production sources/amplitude differ from t25")
        reference_path = args.reference / f"effects_{context}.npz"
        factor_path = args.factors / f"factors_{context}.npz"
        if digest(reference_path) != original["contexts"][context]["sha256"]:
            raise ValueError(f"Saved {context} reference hash mismatch")
        if digest(factor_path) != factor_manifest["contexts"][context]["sha256"]:
            raise ValueError(f"Modifier archive {context} hash mismatch")
        with np.load(reference_path, allow_pickle=False) as z:
            reference = {k: z[k] for k in z.files}
        with np.load(factor_path, allow_pickle=False) as z:
            factors = {k: z[k] for k in z.files}
        output, diagnostics = adapt(reference, factors, contributions, spec, coords)
        path = args.out / f"effects_{context}.npz"
        np.savez_compressed(path, **output)
        report["contexts"][context] = {"sha256": digest(path), "reference_sha256": digest(reference_path),
                                          "arrays_identical": output["lfc"].tobytes() == reference["lfc"].tobytes(),
                                          "diagnostics": diagnostics}
    (args.out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="phase", required=True)
    p = sub.add_parser("export")
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--targets", type=Path, required=True)
    p.add_argument("--contexts", default="A,B,C")
    p.add_argument("--device", default="cpu")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("apply")
    for option in ("cache", "reference", "factors", "coords", "recipe", "out"):
        p.add_argument("--" + option, type=Path, required=True)
    args = parser.parse_args()
    (export if args.phase == "export" else apply)(args)
