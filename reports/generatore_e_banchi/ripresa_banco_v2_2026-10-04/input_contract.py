"""Verify every declared frozen input before effects/scoring, with portable runtime roots."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify(contract, roots=None):
    start = time.monotonic()
    checked = []
    for r in contract["inputs"]:
        path = Path(r["local"]) if roots is None else roots[r["root"]] / r["relative"]
        if not path.is_file() or path.stat().st_size != r["bytes"] or sha(path) != r["sha256"]:
            raise ValueError(f"input missing or changed: {r['root']}/{r['relative']}")
        checked.append({"path": str(path), "bytes": r["bytes"], "sha256": r["sha256"]})
    version = importlib.metadata.version("cell-eval2")
    if version != contract["scorer_version"]:
        raise ValueError("scorer version changed")
    return {"ok": True, "files": len(checked), "inputs": checked, "seconds": time.monotonic() - start,
            "scorer_version": version}


def build(repo, data, cache, held, record, prior):
    """All scientific inputs of HL.Setup and bench_v2, including every cube table."""
    train, prepass, anchor, real = record["kernel_sources"]
    if not (cache / train / "fetch_receipt.json").is_file():
        train += "-retry1"
    inputs = []
    def add(local, root, relative):
        local = Path(local)
        inputs.append({"local": str(local), "root": root, "relative": relative,
                       "bytes": local.stat().st_size, "sha256": sha(local)})
    for path in ["eval_groups.json", "eval_observed.npz", "ibrido/eval_shifts.npz",
                 "ibrido_mean/eval_shifts.npz", "ancora_sola/eval_shifts.npz"]:
        add(cache / train / "train" / path, "train", path)
    add(cache / prepass / "prepass/splits.json", "prepass", "splits.json")
    dirname = Path(prior["anchors_manifest"]).parent.name
    add(cache / anchor / dirname / "manifest.json", "anchors", "manifest.json")
    for name in (Path(prior["real"]).name, Path(prior["targets"]).name):
        add(cache / real / name, "real", name)
    code = data / "processed/ibrido_selettivo_2026-10-04/kaggle_code_r1/target_keys.json"
    add(code, "keys", "target_keys.json")
    cube = data / "processed/generalizzazione_contesti_2026-10-02/cube_r2"
    cm = json.loads((cube / "manifest.json").read_text())
    for rel in ["manifest.json", "genes.csv", "basal.npz"] + [f"{t}/{f}" for t in cm["tables"]
                                                               for f in ("rows.csv", "raw.npy", "se.npy", "shrunk.npy")]:
        add(cube / rel, "cube", rel)
    coords = data / "processed/generalizzazione_contesti_2026-10-02/kaggle_stage_cube_r2/gene_coordinates_gencode_v50.tsv"
    add(coords, "source", coords.name)
    add(repo / record["weights"].replace('\\', '/'), "working", "weights.json")
    add(repo / "reports/analisi/generalizzazione_contesti_2026-10-02/PROTOCOLLO.json", "repo",
        "reports/analisi/generalizzazione_contesti_2026-10-02/PROTOCOLLO.json")
    contract = {"version": 1, "held": held, "scorer_version": "0.16.0", "inputs": inputs,
                "incidents": ["E-20260929-004", "E-20260929-005", "E-20261003-001"],
                "guards": ["all input sizes and hashes", "target axis", "new output", "one explicit launch"]}
    return contract
