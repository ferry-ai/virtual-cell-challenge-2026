"""Lane B: the real cells of the chosen held-out targets and controls, extracted from the corpus shards where they are
(Kaggle), so that the six members can be computed elsewhere on the same cells (PROTOCOLLO.md §5).

From the prepass state: for the held-out key of each target, its admitted cells whose target is that symbol (at most
--cap per target, seeded) and its admitted control cells (at most --max-controls, seeded), read with
cellnet.read_csr_rows on the model genes, restricted to the genes the key measures (key_mask). Writes one npz: CSR
counts, labels (symbol, or 'non-targeting' for controls), the genes, and a JSON sidecar.

    python extract_cells.py --prepass <prepass dir> --targets targets.json --shard-roots /kaggle/input
        --out real_cells.npz [--cap 64] [--max-controls 2048] [--seed 2026]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cellnet as CN  # noqa: E402

CONTROL = "non-targeting"


def resolve(shards, roots):
    by_name = defaultdict(list)
    for root in roots:
        for p in Path(root).rglob("*.h5ad"):
            by_name[p.name].append(p)
    out = {}
    for i, s in enumerate(shards):
        hits = [p for p in by_name.get(s["name"], []) if p.stat().st_size == s["bytes"]]
        if len(hits) == 1:
            out[i] = hits[0]
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prepass", type=Path, required=True)
    p.add_argument("--targets", type=Path, required=True)
    p.add_argument("--shard-roots", nargs="+", required=True)
    p.add_argument("--cap", type=int, default=64)
    p.add_argument("--max-controls", type=int, default=2048)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    with open(a.prepass / "prepass.pkl", "rb") as fh:
        st = pickle.load(fh)
    targets = json.loads(a.targets.read_text(encoding="utf-8"))
    keys = sorted({t["key"] for t in targets})
    if len(keys) != 1:
        raise SystemExit(f"one held-out key per extraction, got {keys}")
    k = st["key_names"].index(keys[0])
    sidx = {s: i for i, s in enumerate(st["symbols"])}
    want = {sidx[t["symbol"]]: t["symbol"] for t in targets if t["symbol"] in sidx}
    shards = st["shards"]
    paths = resolve(shards, a.shard_roots)
    pert, ctrl = defaultdict(list), []
    for i, s in enumerate(shards):
        on_key = (np.asarray(s["key"]) == k) & np.asarray(s["admitted"], bool)
        if not on_key.any():
            continue
        if i not in paths:
            raise SystemExit(f"shard {s['name']} of the held-out key not found under {a.shard_roots}")
        ctrl += [(i, int(r)) for r in np.flatnonzero(on_key & np.asarray(s["control"], bool))]
        tg = np.asarray(s["tgt"])
        for t_i in want:
            pert[t_i] += [(i, int(r)) for r in np.flatnonzero(on_key & (tg == t_i))]
    rng = np.random.default_rng(a.seed)
    pick = {}
    for t_i, cells in pert.items():
        if len(cells) > a.cap:
            cells = [cells[j] for j in np.sort(rng.choice(len(cells), a.cap, replace=False))]
        pick[want[t_i]] = cells
    if len(ctrl) > a.max_controls:
        ctrl = [ctrl[j] for j in np.sort(np.random.default_rng(a.seed + 1).choice(len(ctrl), a.max_controls,
                                                                                    replace=False))]
    mask = np.asarray(st["key_mask"][k], bool)
    cols = np.flatnonzero(mask)
    blocks, labels = [], []
    for lab, cells in list(pick.items()) + [(CONTROL, ctrl)]:
        by_shard = defaultdict(list)
        for i, r in cells:
            by_shard[i].append(r)
        for i, rows in sorted(by_shard.items()):
            s = shards[i]
            x, _ = CN.read_csr_rows(paths[i], np.asarray(rows), s["official_index"], s["measured"], st["gene_of_axis"],
                                    st["G"])
            blocks.append(x[:, cols].tocsr())
            labels += [lab] * len(rows)
    X = sp.vstack(blocks).tocsr()
    genes = np.array(st["genes"])[cols]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(a.out, data=X.data.astype(np.float32), indices=X.indices.astype(np.int32),
                        indptr=X.indptr.astype(np.int64), shape=np.array(X.shape), labels=np.array(labels),
                        genes=genes)
    side = {"key": keys[0], "targets": {lab: len(c) for lab, c in pick.items()}, "missing_targets":
            sorted(t["symbol"] for t in targets if t["symbol"] not in pick), "controls": len(ctrl),
            "genes": int(cols.size), "cap": a.cap, "max_controls": a.max_controls, "seed": a.seed,
            "sha256": hashlib.sha256(a.out.read_bytes()).hexdigest()}
    a.out.with_suffix(".json").write_text(json.dumps(side, indent=1), encoding="utf-8")
    print(json.dumps({k_: side[k_] for k_ in ("key", "controls", "genes")}))


if __name__ == "__main__":
    main()
