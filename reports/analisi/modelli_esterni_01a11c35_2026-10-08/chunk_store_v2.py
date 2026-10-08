"""Verify DATI-TRANSFER chunks and stage float32/bool NPY mmap inputs once.

No downloads, scores or hidden-label selection. The owner supplies a frozen fold
manifest, explicit biological identities, target order and positive row weights.
Failure leaves an incomplete directory without manifest; never reuse it as ready.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil

import numpy as np

from pie_adapter import sha256, unique


class FiniteMask:
    """Bounded mask reads, admitted only after original-mask equivalence checks."""
    dtype = np.dtype(bool)

    def __init__(self, effects):
        self.effects = effects
        self.shape = effects.shape

    def __getitem__(self, key):
        return np.isfinite(self.effects[key])


def build_store(manifest_path, out):
    manifest_path, out = Path(manifest_path), Path(out)
    repo = Path(__file__).resolve().parents[3]
    if (repo/"CLAUDE.md").is_file() and (repo/"scripts").is_dir() and out.resolve().is_relative_to(repo):
        raise ValueError("data store must be outside the repository")
    if out.exists():
        raise FileExistsError(out)
    spec = json.loads(manifest_path.read_text(encoding="utf-8"))
    if spec.get("schema") != "external-ridge-chunks/1" or spec.get("modality") != "CRISPRi":
        raise ValueError("explicit CRISPRi chunk contract required")
    if not spec.get("validation_review") or not spec.get("quantity") or not spec.get("normalization"):
        raise ValueError("review and native units required")
    if spec.get("regime") not in {"C", "T", "J", "production"}:
        raise ValueError("explicit fold regime required")
    for name in ("release_sha256", "split_manifest_sha256"):
        digest = spec.get(name, "")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("pinned release and split provenance required")
    if spec.get("effect_field") not in {"raw", "shrunk"}:
        raise ValueError("choose raw or shrunk explicitly")
    mask_storage = spec.get("mask_storage", "explicit")
    if mask_storage not in {"explicit", "finite_verified"}:
        raise ValueError("unknown mask storage")
    genes = unique(spec["genes"], "genes")
    chunks = spec["chunks"]
    maximum = spec.get("max_chunk_rows", 128)
    if not isinstance(maximum, int) or maximum < 1:
        raise ValueError("positive maximum chunk rows required")
    targets, ids, groups, weights = [], [], [], []
    identities = {}
    for chunk in chunks:
        ts = unique(chunk["targets"], "chunk targets")
        if len(ts) > maximum:
            raise ValueError("chunk exceeds declared row memory bound")
        cid, group = chunk["context_id"], chunk["context_group"]
        if not cid or not group or chunk.get("protected", False):
            raise ValueError("invalid/protected context")
        identity = chunk["identity"]
        if identity.get("modality") != "CRISPRi" or identity.get("line_group") != group:
            raise ValueError("biological identity differs from CRISPRi/group")
        if identities.setdefault(cid, identity) != identity:
            raise ValueError("one context_id has inconsistent biological identities")
        if group in spec["excluded_contexts"] or set(ts) & set(spec["excluded_targets"]):
            raise ValueError("excluded labels reached chunk staging")
        ws = np.asarray(chunk["weights"], dtype=float)
        if ws.shape != (len(ts),) or not np.isfinite(ws).all() or np.any(ws <= 0):
            raise ValueError("explicit positive row weights required")
        targets.extend(ts); ids.extend([cid]*len(ts)); groups.extend([group]*len(ts)); weights.extend(ws.tolist())
    n, g = len(targets), len(genes)
    if not n or len(set(zip(ids, targets))) != n:
        raise ValueError("empty or duplicate context-target rows")
    if dict(Counter(ids)) != spec["expected_rows_by_context"]:
        raise ValueError("D-053 context counts differ")
    # Readiness checks before allocation; include space for headers/receipt margin.
    out.parent.mkdir(parents=True, exist_ok=True)
    required_bytes = n*g*(5 if mask_storage == "explicit" else 4) + 1024*1024
    if shutil.disk_usage(out.parent).free < required_bytes:
        raise ValueError("insufficient space for float32+bool mmap store")
    out.mkdir(exist_ok=False)
    effects = np.lib.format.open_memmap(out/"effects.npy", mode="w+", dtype="float32", shape=(n,g), fortran_order=True)
    observed = (np.lib.format.open_memmap(out/"observed.npy", mode="w+", dtype=bool, shape=(n,g), fortran_order=True)
                if mask_storage == "explicit" else None)
    offset = 0
    for chunk in chunks:
        path = Path(chunk["path"])
        if not path.is_absolute(): path = manifest_path.parent/path
        if sha256(path) != chunk["sha256"]:
            raise ValueError("chunk checksum mismatch")
        with np.load(path, allow_pickle=False) as data:
            if data["genes"].tolist() != genes or data["targets"].tolist() != chunk["targets"]:
                raise ValueError("chunk axis/order differs")
            if json.loads(str(data["meta"].item())) != chunk["identity"]:
                raise ValueError("chunk biological identity differs")
            y, m = data[spec["effect_field"]], data["mask"]
            shape = (len(chunk["targets"]), g)
            if y.shape != shape or m.shape != shape or y.dtype != np.float32 or m.dtype != bool:
                raise ValueError("chunk dtype/shape mismatch")
            if not np.isfinite(y[m]).all() or not np.isnan(y[~m]).all():
                raise ValueError("invalid observed/missing values")
            effects[offset:offset+len(y)] = y
            if observed is not None:
                observed[offset:offset+len(y)] = m
            offset += len(y)
    effects.flush()
    if observed is not None:
        observed.flush()
    del effects, observed
    np.savez_compressed(out/"axes.npz", targets=targets, context_ids=ids,
                        context_groups=groups, genes=genes, weights=np.asarray(weights))
    array_names = ("effects.npy", "axes.npz") + (("observed.npy",) if mask_storage == "explicit" else ())
    result = dict(schema="external-ridge-mmap/2", source_manifest=spec,
                  source_manifest_sha256=sha256(manifest_path), builder_sha256=sha256(__file__),
                  shape=[n,g], order="F", context_rows=dict(Counter(ids)),
                  mask_storage=mask_storage, original_mask_equivalence_verified_chunks=len(chunks),
                  arrays={name:sha256(out/name) for name in array_names},
                  full_response_float64_materialized=False, scientific_benefit="not_evaluated")
    (out/"manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def load_store(root, receipt_sha256):
    root = Path(root)
    if sha256(root/"manifest.json") != receipt_sha256:
        raise ValueError("store receipt differs")
    receipt = json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    if receipt.get("schema") not in {"external-ridge-mmap/1", "external-ridge-mmap/2"}:
        raise ValueError("unsupported store")
    mask_storage = receipt.get("mask_storage", "explicit")
    if mask_storage not in {"explicit", "finite_verified"}:
        raise ValueError("unknown stored mask policy")
    if mask_storage == "finite_verified" and receipt.get("original_mask_equivalence_verified_chunks") != len(receipt['source_manifest']['chunks']):
        raise ValueError("unverified implicit mask")
    names = ("effects.npy", "axes.npz") + (("observed.npy",) if mask_storage == "explicit" else ())
    for name in names:
        if sha256(root/name) != receipt["arrays"][name]:
            raise ValueError("staged array checksum mismatch")
    y = np.load(root/"effects.npy", mmap_mode="r", allow_pickle=False)
    m = (np.load(root/"observed.npy", mmap_mode="r", allow_pickle=False)
         if mask_storage == "explicit" else FiniteMask(y))
    if list(y.shape) != receipt["shape"] or m.shape != y.shape or y.dtype != np.float32 or m.dtype != bool:
        raise ValueError("store shape/dtype differs")
    with np.load(root/"axes.npz", allow_pickle=False) as data:
        axes = {name:data[name] for name in data.files}
    return y, m, axes, receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = build_store(args.manifest, args.out)
    print(json.dumps({k:result[k] for k in ("schema", "shape", "context_rows")}))
