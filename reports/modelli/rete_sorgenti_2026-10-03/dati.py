"""Per-key tensors for the source-attention network (README.md in this folder), from the rlab shards.

One pass over the shards with the route C bench's own accumulator (`banco_tipo.Sums`, imported unchanged from
reports/trasferimento/strada_c_banco_2026-10-03/), then, for every key with enough controls, one file
``chiavi/<study>__<context>.npz`` holding:

* ``targets`` (T,), ``n_cells`` (T,): the key's targets and their cell counts;
* ``eff`` (T x G, float16, NaN off the usable genes): `banco_tipo.key_effects`, i.e. the effects_from_bulk formulas,
  z_shrink k = 4 and gamma = 1;
* ``basal`` (G, float32): log1p(1e4 x the controls' pooled fraction), 0 off the measured genes;
* ``measured`` (G, bool), and the key's ``group`` and ``type`` from the registered rule.

    python dati.py --inputs /kaggle/input --axis gene_names.csv --out chiavi --bench-code <strada_c folder>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--axis", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--bench-code", type=Path, required=True, help="folder holding banco_tipo.py")
    p.add_argument("--code", type=Path, default=None, help="folder holding the vcc2026 package (src/)")
    a = p.parse_args()
    for extra in (a.code, a.bench_code):
        if extra:
            sys.path.insert(0, str(extra))
    import banco_tipo as bt

    a.out.mkdir(parents=True, exist_ok=True)
    if any(a.out.glob("*.npz")):
        raise SystemExit(f"{a.out} already holds key files; choose a new --out")
    axis = pd.read_csv(a.axis, header=None).iloc[:, 0].astype(str).to_numpy()
    if axis[0].lower() in ("gene", "gene_name", "genes", "symbol"):
        axis = axis[1:]
    G = axis.size
    shards = sorted(a.inputs.rglob("*.h5ad"))
    sums, t0, skipped = bt.Sums(G), time.time(), []
    for sid, path in enumerate(shards):
        try:
            obs, oi, ok, x = bt.read_shard(path)
        except Exception as exc:
            skipped.append({"shard": str(path), "error": f"{type(exc).__name__}: {exc}"})
            continue
        sums.add(sid, obs, oi, ok, x, set(axis), keep_rows_for=set())
        if sid % 25 == 0:
            bt.log(f"{sid + 1}/{len(shards)} shards, {time.time() - t0:.0f}s")
    index = {}
    for key in sorted(sums.acc):
        group = bt.group_of(*key.split("|", 1))
        n_ntc = sums.n[key].get(bt.NTC, 0)
        row = {"group": group, "type": bt.TYPES.get(group), "ntc": int(n_ntc)}
        if group is None or n_ntc < bt.MIN_NTC_KEY:
            index[key] = row | {"written": False}
            continue
        targets, E = bt.key_effects(sums, key)
        m = sums.mask[key]
        frac = np.where(m, sums.acc[key][bt.NTC], 0.0)
        basal = np.log1p(1e4 * frac / frac.sum()).astype(np.float32)
        name = key.replace("|", "__").replace("/", "_") + ".npz"
        np.savez_compressed(a.out / name, targets=np.array(targets), eff=E.astype(np.float16), basal=basal,
                            measured=m, n_cells=np.array([sums.n[key][t] for t in targets]), key=key,
                            group=group, type=bt.TYPES[group])
        index[key] = row | {"written": True, "file": name, "targets": len(targets), "genes": int(m.sum())}
    (a.out / "index.json").write_text(json.dumps({"keys": index, "skipped": skipped, "axis_genes": G}, indent=1))
    bt.log(f"{sum(r['written'] for r in index.values())} key files written")


if __name__ == "__main__":
    main()
