"""Synthetic contract shards for the tests of version 4.

GENES, counts, write_shard and key_in_fold are copies of the helpers of test_prepass.py and test_v2_stages.py in
reports/modelli/rete_ancorata_2026-10-03 (unchanged code, so that this folder's tests do not import another report's
files); make_twins writes the compact twins of a folder of shards with the package manifest the training checks.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import scipy.sparse as sp

import cell_data as CD
import fastshard as FS

GENES = [f"G{i}" for i in range(1, 37)] + ["MT-CO1", "MT-ND1", "MT-ND2", "MT-CO2"]


def counts(rng, p, n, scale=1.0):
    lib = np.maximum(1, np.exp(rng.normal(8, 0.3, n)) * scale).astype(int)
    return np.stack([rng.multinomial(L, p) for L in lib])


def write_shard(path, x, study, context, library, targets, barcodes, source):
    """A contract shard with one library per cell (a string, or an array of them)."""
    import anndata as ad
    import pandas as pd
    n = x.shape[0]
    library = np.broadcast_to(np.asarray(library, dtype=object), (n,))
    targets = np.asarray(targets, dtype=object)
    control = np.where(targets == "NTC", "NTC", "none")
    obs = pd.DataFrame({"study": study, "context": context, "library": library, "target": targets,
                        "control_kind": control, "modality": "CRISPRi", "barcode": barcodes,
                        "cell_key": [f"{study}|{l}|{b}" for l, b in zip(library, barcodes)]},
                       index=[f"c{i}" for i in range(n)])
    var = pd.DataFrame({"symbol": GENES, "official_index": np.arange(len(GENES), dtype=np.int64),
                        "measured": np.ones(len(GENES), bool)}, index=[f"f{i}" for i in range(len(GENES))])
    ad.AnnData(X=sp.csr_matrix(x.astype(np.int32)), obs=obs, var=var,
               uns={"source": {"locator": source, "release": "test"}}).write_h5ad(path)


def key_in_fold(symbol, fold, want=True):
    for i in range(10000):
        k = f"KEY_{symbol}_{i}"
        if (CD.target_fold(k, 5) == fold) == want:
            return k
    raise AssertionError


def make_twins(shard_dir: Path, out_dir: Path, block_rows=64) -> dict:
    """The compact twin of every shard of shard_dir in out_dir, and out_dir/fast_manifest.json (as the build kernel
    writes it)."""
    out_dir.mkdir(parents=True)
    receipts = [FS.encode(p, out_dir / FS.twin_name(p.name), block_rows=block_rows)
                for p in sorted(Path(shard_dir).glob("*.h5ad"))]
    manifest = {"format": FS.FORMAT, "version": FS.FORMAT_VERSION, "shards": receipts}
    (out_dir / "fast_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest
