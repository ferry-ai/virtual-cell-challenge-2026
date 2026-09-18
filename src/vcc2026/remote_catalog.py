"""Multi-source remote ingest: one catalog, independent checkpoints, one block at a time.

The Colab notebook and `scripts/68_remote_catalog.py` call this. Fetching uses
`ResumableFetcher`. Completing HepG2 does not re-download it when the md5
matches. A plan is not a fetch. `/content/vcc-persist` is the Colab VM disk:
the name does not make it persistent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from vcc2026.genes import official_axis
from vcc2026.manifest import RunManifest
from vcc2026.pseudobulk import _read_categorical
from vcc2026.remote_ingest import resolve_paths
from vcc2026.remote_job import ResumableFetcher, _md5_file
from vcc2026.resources import GiB, snapshot
from vcc2026.runtime import collect_inventory, disk_peak_estimate

__all__ = [
    "BlockSpec",
    "Catalog",
    "LARGE_FETCH_BYTES",
    "load_catalog",
    "dest_for",
    "persist_kind",
    "plan_block",
    "recommend_fetch_ids",
    "run_catalog",
]

LARGE_FETCH_BYTES = 8 * GiB

REPO_CATALOG = Path(__file__).resolve().parents[2] / "configs" / "remote_catalog.yaml"
NTC_CANDIDATES = (
    "non-targeting", "non_targeting", "nontargeting", "control", "ctrl",
    "ntc", "nt", "scrambled", "none",
)
PERT_CANDIDATES = (
    "perturbation", "gene", "target_gene", "gene_target", "target",
)


@dataclass(frozen=True)
class BlockSpec:
    id: str
    source_id: str
    title: str
    key: str | None
    url: str | None
    bytes: int | None
    md5: str | None
    format: str
    provenance: str
    evidence: str
    relpath: str | None
    advertised_bytes: int | None
    advertised_note: str | None
    ntc_column: str | None
    ntc_label: str | None
    ntc_note: str | None
    gene_column: str | None
    batch_column: str | None
    derive: str
    skip_if_checksum_matches: bool
    default_selected: bool
    stub: bool
    do_not_fetch: bool
    same_experiment_as: str | None
    notes: tuple[str, ...]
    raw: dict

    def fetchable(self) -> bool:
        return (
            not self.stub
            and not self.do_not_fetch
            and self.url is not None
            and self.bytes is not None
            and self.md5 is not None
            and self.key is not None
        )


@dataclass(frozen=True)
class Catalog:
    version: str
    default_order: tuple[str, ...]
    blocks: tuple[BlockSpec, ...]

    def by_id(self, ident: str) -> BlockSpec:
        for block in self.blocks:
            if block.id == ident:
                return block
        raise KeyError(ident)

    def selected(self, names: list[str] | None) -> list[BlockSpec]:
        if names:
            return [self.by_id(n) for n in names]
        return [self.by_id(n) for n in self.default_order]


def load_catalog(path: Path | str | None = None) -> Catalog:
    path = Path(path) if path else REPO_CATALOG
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    blocks = []
    for item in raw["blocks"]:
        blocks.append(BlockSpec(
            id=item["id"],
            source_id=str(item.get("source_id") or item["id"]),
            title=str(item.get("title") or item["id"]),
            key=item.get("key"),
            url=item.get("url"),
            bytes=item.get("bytes"),
            md5=(str(item["md5"]).lower() if item.get("md5") else None),
            format=str(item.get("format") or "unknown"),
            provenance=str(item.get("provenance") or ""),
            evidence=str(item.get("evidence") or ""),
            relpath=item.get("relpath"),
            advertised_bytes=item.get("advertised_bytes"),
            advertised_note=item.get("advertised_note"),
            ntc_column=item.get("ntc_column"),
            ntc_label=item.get("ntc_label"),
            ntc_note=item.get("ntc_note"),
            gene_column=item.get("gene_column"),
            batch_column=item.get("batch_column"),
            derive=str(item.get("derive") or "none"),
            skip_if_checksum_matches=bool(item.get("skip_if_checksum_matches", True)),
            default_selected=bool(item.get("default_selected", True)),
            stub=bool(item.get("stub", False)),
            do_not_fetch=bool(item.get("do_not_fetch", False)),
            same_experiment_as=item.get("same_experiment_as"),
            notes=tuple(item.get("notes") or ()),
            raw=item,
        ))
    return Catalog(
        version=str(raw.get("version")),
        default_order=tuple(raw.get("default_order") or ()),
        blocks=tuple(blocks),
    )


def persist_kind(path: Path) -> dict:
    text = str(path).replace("\\", "/")
    if "/content/drive/" in text:
        return {
            "kind": "colab_drive",
            "survives_session": True,
            "note": "Google Drive mount. Still not a laptop path.",
        }
    if text.startswith("/content/"):
        return {
            "kind": "colab_vm",
            "survives_session": False,
            "note": (
                "/content/vcc-persist is the Colab VM disk. The name does not "
                "make it persistent. Download artifacts before the runtime dies."
            ),
        }
    if text.startswith("/tmp/") or "/scratch" in text:
        return {
            "kind": "scratch",
            "survives_session": False,
            "note": "Scratch is not a delivery.",
        }
    return {
        "kind": "local_or_other",
        "survives_session": True,
        "note": "Treat as durable only if you control the disk.",
    }


def checkpoint_dir(state_root: Path) -> Path:
    path = Path(state_root) / "checkpoints"
    path.mkdir(parents=True, exist_ok=True)
    return path


def checkpoint_path(state_root: Path, block_id: str) -> Path:
    return checkpoint_dir(state_root) / f"{block_id}.json"


def read_checkpoint(state_root: Path, block_id: str) -> dict | None:
    path = checkpoint_path(state_root, block_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_checkpoint(state_root: Path, payload: dict) -> Path:
    """Write once. A completed checkpoint is evidence and is not rewritten."""
    path = checkpoint_path(state_root, payload["block_id"])
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("status") == "complete":
            return path
        raise FileExistsError(
            f"{path} exists with status {existing.get('status')!r}; "
            "move it aside rather than overwrite"
        )
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def dest_for(block: BlockSpec, data_root: Path) -> Path:
    rel = block.relpath or f"raw/{block.id}/{block.key}"
    return Path(data_root) / rel


def file_matches(block: BlockSpec, path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "matches": False}
    size = path.stat().st_size
    md5 = _md5_file(path)
    return {
        "exists": True,
        "bytes": size,
        "md5": md5,
        "bytes_ok": block.bytes is None or size == block.bytes,
        "md5_ok": block.md5 is None or md5 == block.md5,
        "matches": (
            (block.bytes is None or size == block.bytes)
            and (block.md5 is None or md5 == block.md5)
        ),
    }


def plan_block(
    block: BlockSpec,
    *,
    free_bytes: int,
    ram_available_bytes: int | None,
    floor_bytes: int,
    fetch: bool,
    already_complete: bool,
) -> dict:
    peak = disk_peak_estimate(
        input_bytes=int(block.bytes or 0),
        decompressed_bytes=None,
        derived_bytes=20_000_000 if block.format == "h5ad" else None,
        export_bytes=5_000_000,
        margin=0.25,
    )
    input_ok = (
        block.bytes is not None
        and (free_bytes - block.bytes) >= floor_bytes
    )
    ram_note = None
    if ram_available_bytes is not None and block.bytes and ram_available_bytes < 2 * 1024**3:
        ram_note = (
            "RAM available is under 2 GiB; do not materialise a dense matrix. "
            "obs/var QC and a contiguous X head only."
        )
    if already_complete:
        decision, reason = "skip_complete", "checkpoint complete or checksum matches"
    elif block.stub:
        decision, reason = "stub", "no verified url/bytes/md5; cannot fetch"
    elif block.do_not_fetch:
        decision, reason = "forbidden", "listed so it is not grabbed as raw counts"
    elif not block.fetchable():
        decision, reason = "not_fetchable", "url, bytes or md5 missing"
    elif not fetch:
        decision, reason = "plan_only", "not in FETCH_BLOCKS; no download"
    elif not input_ok:
        decision, reason = "skip_disk", "input would not leave the disk floor"
    else:
        decision, reason = "fetch", "operator selected and input leaves the floor"
    return {
        "block_id": block.id,
        "title": block.title,
        "bytes": block.bytes,
        "advertised_bytes": block.advertised_bytes,
        "advertised_note": block.advertised_note,
        "md5": block.md5,
        "url": block.url,
        "format": block.format,
        "evidence": block.evidence,
        "fetchable": block.fetchable(),
        "peak_estimate": peak,
        "input_leaves_floor": input_ok,
        "floor_bytes": floor_bytes,
        "free_bytes": free_bytes,
        "ram_available_bytes": ram_available_bytes,
        "ram_note": ram_note,
        "decision": decision,
        "reason": reason,
        "derive": block.derive,
        "same_experiment_as": block.same_experiment_as,
        "claim": "derived",
    }


def recommend_fetch_ids(
    catalog: Catalog,
    *,
    free_bytes: int,
    ram_available_bytes: int | None,
    floor_bytes: int,
    persist_survives_session: bool,
    complete_ids: set[str] | frozenset[str] | None = None,
    allow_ephemeral_large: bool = False,
    include_rds: bool = False,
    select_ids: list[str] | None = None,
    large_bytes: int = LARGE_FETCH_BYTES,
) -> dict:
    """Next fetchable blocks after a preflight. At most one large file.

    Walks catalog order. HepG2 is first: a matching size skips it. K562 GW
    (65_830_941_948 bytes) is next if the input leaves the disk floor.
    A large file is not auto-fetched onto ephemeral Colab disk unless
    `allow_ephemeral_large` is set. Later blocks are not a silent substitute
    when the priority large file does not fit. RDS conversion stays out of
    auto-fetch (`include_rds=False`).
    """
    done = set(complete_ids or ())
    remaining = int(free_bytes)
    chosen: list[str] = []
    notes: list[str] = []
    skipped: list[dict] = []
    for block in catalog.selected(select_ids):
        if block.id in done:
            skipped.append({"id": block.id, "reason": "already complete (size or checkpoint)"})
            continue
        if not block.fetchable():
            skipped.append({"id": block.id, "reason": "not fetchable"})
            continue
        if block.derive == "rds_blocked" and not include_rds:
            skipped.append({"id": block.id, "reason": "rds_blocked; conversion needs R"})
            continue
        is_large = bool(block.bytes and block.bytes >= large_bytes)
        if is_large and not persist_survives_session and not allow_ephemeral_large:
            skipped.append({
                "id": block.id,
                "reason": "large file refused on ephemeral persist; mount Drive",
            })
            notes.append(
                f"{block.id} is {block.bytes} bytes; persist does not survive "
                "the session. Mount Google Drive and re-run, or set "
                "ALLOW_EPHEMERAL_LARGE."
            )
            break
        plan = plan_block(
            block,
            free_bytes=remaining,
            ram_available_bytes=ram_available_bytes,
            floor_bytes=floor_bytes,
            fetch=True,
            already_complete=False,
        )
        if plan["decision"] != "fetch":
            skipped.append({"id": block.id, "reason": plan["reason"]})
            if is_large:
                notes.append(
                    f"{block.id} not auto-fetched ({plan['reason']}); "
                    "not falling through to a later block."
                )
                break
            continue
        chosen.append(block.id)
        remaining -= int(block.bytes or 0)
        notes.append(
            f"{block.id}: fetch; remaining after this file ~{remaining} bytes"
        )
        if is_large:
            notes.append(f"{block.id} is the one large auto-fetch; stop.")
            break
    return {
        "ids": chosen,
        "notes": notes,
        "skipped": skipped,
        "persist_survives_session": persist_survives_session,
        "allow_ephemeral_large": allow_ephemeral_large,
        "include_rds": include_rds,
        "remaining_bytes": remaining,
        "claim": "derived",
    }


def acquire_block(block: BlockSpec, dest: Path) -> dict:
    if not block.fetchable():
        raise ValueError(f"{block.id} is not fetchable")
    dest.parent.mkdir(parents=True, exist_ok=True)
    fetcher = ResumableFetcher(
        block.url,
        dest,
        expected_bytes=block.bytes,
        expected_md5=block.md5,
        max_bytes=int(block.bytes) + 1_000_000,
    )
    state = fetcher.fetch()
    return state.as_dict()


def qc_h5ad(path: Path, block: BlockSpec, *, n_x_rows: int = 64) -> dict:
    """Structure + NTC from obs. Never the full dense X."""
    import h5py
    import numpy as np

    with h5py.File(path, "r") as handle:
        x = handle["X"]
        shape = [int(v) for v in x.shape]
        obs_keys = [k for k in handle["obs"].keys() if not str(k).startswith("_")]
        var_keys = [k for k in handle["var"].keys() if not str(k).startswith("_")]
        gene_col = block.gene_column if block.gene_column in handle["var"] else (
            "gene_name" if "gene_name" in handle["var"] else None
        )
        genes = (
            np.asarray(_read_categorical(handle["var"], gene_col), dtype=str)
            if gene_col else None
        )
        pert_col = block.ntc_column
        if pert_col is None or pert_col not in handle["obs"]:
            pert_col = next((c for c in PERT_CANDIDATES if c in handle["obs"]), None)
        labels = (
            np.asarray(_read_categorical(handle["obs"], pert_col), dtype=str)
            if pert_col else None
        )
        batch_col = block.batch_column if block.batch_column in handle["obs"] else (
            "batch" if "batch" in handle["obs"] else None
        )
        batches = (
            np.asarray(_read_categorical(handle["obs"], batch_col), dtype=str)
            if batch_col else None
        )
        n_take = min(n_x_rows, int(x.shape[0]))
        head = np.asarray(x[:n_take, :], dtype=np.float32)

    ntc_label = block.ntc_label
    ntc_cells = None
    if labels is not None:
        if ntc_label is None:
            levels = {str(v) for v in labels}
            hits = sorted(lv for lv in levels if lv.strip().lower() in NTC_CANDIDATES)
            ntc_label = hits[0] if len(hits) == 1 else None
            discovered = hits
        else:
            discovered = [ntc_label]
        if ntc_label is not None:
            ntc_cells = int((labels == ntc_label).sum())
    else:
        discovered = []

    pairing = None
    if labels is not None and batches is not None and ntc_label is not None:
        ntc_by_batch = {}
        for b in sorted(set(batches.tolist())):
            ntc_by_batch[str(b)] = int(((batches == b) & (labels == ntc_label)).sum())
        pairing = {
            "batch_column": batch_col,
            "n_batches": len(ntc_by_batch),
            "batches_without_ntc": sorted(
                k for k, n in ntc_by_batch.items() if n == 0
            ),
            "ntc_per_batch_min": min(ntc_by_batch.values()) if ntc_by_batch else None,
        }

    on_axis = None
    try:
        axis = official_axis()
        if genes is not None:
            pos = axis.position()
            on_axis = int(sum(1 for g in genes if g in pos))
    except FileNotFoundError:
        axis = None

    return {
        "shape": shape,
        "obs_keys": obs_keys,
        "var_keys": var_keys,
        "pert_column_used": pert_col,
        "ntc_label_used": ntc_label,
        "ntc_labels_discovered": discovered,
        "ntc_cells": ntc_cells,
        "n_genes": None if genes is None else int(len(genes)),
        "n_on_official_axis": on_axis,
        "pairing": pairing,
        "x_head_rows": int(n_take),
        "x_min": float(head.min()),
        "x_max": float(head.max()),
        "x_nonnegative": bool(head.min() >= 0),
        "x_integral": bool(np.allclose(head, np.rint(head))),
        "ntc_note": block.ntc_note,
        "claim": "measured",
    }


def derive_h5ad_obs(path: Path, block: BlockSpec, dest: Path, qc: dict) -> dict:
    """Gene mask and NTC index from obs/var. Not a SignatureSet and not a VCC score."""
    import h5py
    import numpy as np

    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    gene_col = block.gene_column or "gene_name"
    pert_col = qc.get("pert_column_used")
    ntc_label = qc.get("ntc_label_used")
    with h5py.File(path, "r") as handle:
        genes = np.asarray(_read_categorical(handle["var"], gene_col), dtype=str) \
            if gene_col in handle["var"] else None
        labels = (
            np.asarray(_read_categorical(handle["obs"], pert_col), dtype=str)
            if pert_col else None
        )
    axis = official_axis()
    pos = axis.position()
    if genes is None:
        raise ValueError(f"{block.id}: no gene column to mask")
    observed = np.array([g in pos for g in genes], dtype=bool)
    mask_path = dest / "gene_mask.npz"
    if not mask_path.exists():
        np.savez_compressed(
            mask_path,
            symbols=genes.astype("U"),
            observed=observed,
            official_index=np.array([pos.get(g, -1) for g in genes], dtype=np.int64),
        )
    ntc_path = None
    if labels is not None and ntc_label is not None:
        ntc_idx = np.flatnonzero(labels == ntc_label)
        ntc_path = dest / "ntc_rows.npz"
        if not ntc_path.exists():
            np.savez_compressed(ntc_path, rows=ntc_idx, label=np.array(ntc_label))
    record = {
        "gene_mask": str(mask_path),
        "ntc_rows": None if ntc_path is None else str(ntc_path),
        "n_observed_on_official_axis": int(observed.sum()),
        "n_unmeasured_official_genes": int(len(axis) - observed.sum()),
        "unmeasured_are_masked_not_zeroed": True,
        "ntc_cells": None if labels is None or ntc_label is None else int((labels == ntc_label).sum()),
        "pairing": qc.get("pairing"),
        "signatures": None,
        "signatures_note": (
            "obs-level NTC pairing and gene mask only. Full log2FC signatures "
            "are scripts/53_build_hepg2_signatures.py (or equivalent) and are "
            "not this step."
        ),
        "claim": "measured",
    }
    out_json = dest / "derive.json"
    if not out_json.exists():
        out_json.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def _measure(paths) -> dict:
    inv = collect_inventory(
        repo=paths.repo, data_root=paths.data, persistent=paths.persist,
        forbid_windows_paths=paths.remote,
    )
    res = snapshot(paths.persist)
    return {
        "inventory": inv.as_dict(),
        "disk_free_bytes": int(res.disk_free_bytes),
        "ram_available_bytes": res.ram_available_bytes,
        "ram_total_bytes": res.ram_total_bytes,
        "persist": persist_kind(paths.persist),
    }


def run_catalog(
    *,
    out: Path,
    repo: Path,
    fetch_ids: list[str] | None = None,
    select_ids: list[str] | None = None,
    catalog_path: Path | None = None,
    disk_floor_gib: float | None = None,
    plan_only: bool = False,
    auto_fetch: bool = False,
    allow_ephemeral_large: bool = False,
) -> dict:
    """Plan, and optionally fetch, one catalog block after another.

    `fetch_ids` is the only explicit list that may download. `auto_fetch` on a
    remote runtime fills that list from `recommend_fetch_ids` after preflight.
    Auto-fetch is ignored on the laptop so 65.8 GiB cannot start here by
    accident. `select_ids` chooses what to plan. HepG2 with a matching md5 is
    skipped even if listed to fetch.
    """
    out = Path(out)
    report_path = out / "catalog_run.json"
    if report_path.exists():
        raise FileExistsError(f"{report_path} exists; give a new --out")
    out.mkdir(parents=True, exist_ok=True)
    paths = resolve_paths(repo=repo)
    catalog = load_catalog(catalog_path)
    selected = catalog.selected(select_ids)
    floor = (10.0 if not paths.remote else 2.0) if disk_floor_gib is None else disk_floor_gib
    floor_bytes = int(floor * GiB)
    preflight = _measure(paths)
    fetch_set = set(fetch_ids or ())
    recommendation = None
    if plan_only:
        fetch_set = set()
    elif not fetch_set and auto_fetch:
        pk = persist_kind(paths.persist)
        if paths.runtime == "local":
            recommendation = {
                "ids": [],
                "notes": ["auto_fetch ignored on local runtime; pass fetch_ids"],
                "skipped": [],
                "persist_survives_session": pk["survives_session"],
                "claim": "derived",
            }
            fetch_set = set()
        else:
            complete_ids = set()
            for block in selected:
                dest = dest_for(block, paths.data)
                if (
                    block.skip_if_checksum_matches
                    and dest.exists()
                    and block.bytes is not None
                    and dest.stat().st_size == block.bytes
                ):
                    complete_ids.add(block.id)
            recommendation = recommend_fetch_ids(
                catalog,
                free_bytes=preflight["disk_free_bytes"],
                ram_available_bytes=preflight["ram_available_bytes"],
                floor_bytes=floor_bytes,
                complete_ids=complete_ids,
                persist_survives_session=bool(pk["survives_session"]),
                allow_ephemeral_large=allow_ephemeral_large,
                select_ids=select_ids,
            )
            fetch_set = set(recommendation["ids"])
    rows = []
    for block in selected:
        metrics = _measure(paths)
        dest = dest_for(block, paths.data)
        prior = read_checkpoint(out, block.id)
        match = file_matches(block, dest) if block.md5 else {"exists": dest.exists(), "matches": False}
        complete = (
            (prior is not None and prior.get("status") == "complete")
            or (block.skip_if_checksum_matches and match.get("matches"))
        )
        want_fetch = block.id in fetch_set and not plan_only
        plan = plan_block(
            block,
            free_bytes=metrics["disk_free_bytes"],
            ram_available_bytes=metrics["ram_available_bytes"],
            floor_bytes=floor_bytes,
            fetch=want_fetch,
            already_complete=complete,
        )
        acquired = None
        qc = None
        derived = None
        status = plan["decision"]
        if complete:
            status = "complete"
            plan["decision"] = "skip_complete"
            plan["reason"] = "checksum matches or checkpoint complete; not re-fetched"
            derived_json = out / "derived" / block.id / "derive.json"
            if (
                block.format == "h5ad"
                and dest.exists()
                and match.get("matches")
                and not derived_json.exists()
                and block.derive == "h5ad_obs"
            ):
                qc = qc_h5ad(dest, block)
                derived = derive_h5ad_obs(dest, block, out / "derived" / block.id, qc)
        elif plan["decision"] == "fetch":
            try:
                acquired = acquire_block(block, dest)
                match = file_matches(block, dest)
                if not match.get("matches"):
                    raise RuntimeError(f"{block.id}: download did not match catalog bytes/md5")
                if block.format == "h5ad":
                    qc = qc_h5ad(dest, block)
                    if block.derive == "h5ad_obs":
                        derived = derive_h5ad_obs(
                            dest, block, out / "derived" / block.id, qc,
                        )
                elif block.derive == "rds_blocked":
                    derived = {
                        "signatures": None,
                        "blocked": "Seurat RDS; conversion needs R/Seurat; RAM unmeasured",
                        "claim": "missing",
                    }
                status = "complete"
                write_checkpoint(out, {
                    "block_id": block.id,
                    "status": "complete",
                    "path": str(dest),
                    "bytes": match.get("bytes"),
                    "md5": match.get("md5"),
                    "acquired_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "qc": qc,
                    "derived": derived,
                    "claim": "measured",
                })
            except FileExistsError:
                status = "blocked_checkpoint"
            except Exception as exc:  # noqa: BLE001
                status = "failed"
                plan["error"] = f"{type(exc).__name__}: {exc}"
        rows.append({
            "plan": plan,
            "status": status,
            "path": str(dest),
            "file": match,
            "acquired": acquired,
            "qc": qc,
            "derived": derived,
            "checkpoint": str(checkpoint_path(out, block.id)),
        })
    report = {
        "recorded_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "paths": paths.as_dict(),
        "persist_kind": persist_kind(paths.persist),
        "preflight": preflight,
        "disk_floor_gib": floor,
        "disk_floor_note": (
            "10 GiB is D-005 on the laptop. 2 GiB is a proposed remote floor, "
            "not a Colab quota. Remeasured before every block."
        ),
        "fetch_ids": sorted(fetch_set),
        "plan_only": plan_only or not fetch_set,
        "auto_fetch": auto_fetch,
        "allow_ephemeral_large": allow_ephemeral_large,
        "recommendation": recommendation,
        "colab_pilot": {
            "out": "/content/vcc-persist/remote_ingest_2026-09-15T140308Z",
            "persist_is_ephemeral": True,
            "hepg2_parity": "passed (byte, md5, shape, NTC, gene axis)",
            "resume_probe": "200 bytes then complete",
            "jiang": "skipped FETCH_JIANG=False",
            "disk_free_gib_after_pilot": 87.24895858764648,
            "ram_available_user_report_gib": 11,
            "ram_must_be_remeasured": True,
            "does_not_prove_large_ingest_or_training_resume": True,
        },
        "blocks": rows,
        "not_a_cloud_proof": paths.runtime == "local",
        "claim": "measured" if any(r["status"] == "complete" and r["acquired"] for r in rows) else "derived",
    }
    report_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    manifest = RunManifest(
        run_id=out.name, stage="68_remote_catalog",
        config={
            "fetch_ids": sorted(fetch_set),
            "plan_only": plan_only,
            "auto_fetch": auto_fetch,
        },
    )
    manifest.add_output("report", report_path)
    manifest.note("A local plan is not a Colab ingest.")
    manifest.note("/content/vcc-persist does not survive the Colab VM.")
    manifest.write(out / "manifest_68_remote_catalog.json")
    return report
