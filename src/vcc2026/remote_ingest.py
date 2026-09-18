"""First remote job: HepG2 parity, resume proof, then a gated Jiang block.

The notebook and `scripts/67_remote_ingest.py` call this module. Kaggle and
Colab are not assumed: the runtime is measured here. Heavy files are fetched
from the publisher, not uploaded from the laptop.

HepG2 constants are copied from `reports/hepg2_2026-09-14/` (acquired 2026-09-14).
A mismatch against those numbers is a failed parity, not a new measurement of
the biology.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np

from vcc2026.genes import official_axis
from vcc2026.manifest import RunManifest, snapshot_source
from vcc2026.pseudobulk import _read_categorical
from vcc2026.remote_job import ResumableFetcher, _md5_file, export_and_verify, simulate_interrupt
from vcc2026.resources import GiB
from vcc2026.runtime import collect_inventory, disk_peak_estimate

__all__ = [
    "HEPG2",
    "JIANG_TGFB",
    "RESUME_PROBE",
    "JobPaths",
    "colab_default_roots",
    "detect_runtime",
    "refuse_windows_paths",
    "resolve_paths",
    "hepg2_parity",
    "extract_hepg2_sample",
    "resume_selftest",
    "jiang_tgfb_gate",
    "run_job",
    "prepare_upload_bundle",
]


HEPG2 = {
    "key": "NadigOConner2024_hepg2.h5ad",
    "url": "https://zenodo.org/api/records/13350497/files/NadigOConner2024_hepg2.h5ad/content",
    "bytes": 850_590_740,
    "md5": "af2be47f7477cf32fa6e4bec1c6a4868",
    "shape": (145_473, 9_624),
    "ntc_label": "control",
    "ntc_cells": 4_976,
    "n_on_official_axis": 9_023,
    "n_official_axis": 18_533,
    "dense_bytes": 5_600_128_608,
    "evidence": "reports/hepg2_2026-09-14/nadig_hepg2_audit.json",
}

JIANG_TGFB = {
    "key": "Seurat_object_TGFB_Perturb_seq.rds",
    "url": "https://zenodo.org/api/records/14518762/files/Seurat_object_TGFB_Perturb_seq.rds/content",
    "bytes": 2_642_041_433,
    "md5": "8e9b4d39a95ec5881a30be6a2df541d1",
    "evidence": "reports/jiang_2026-09-15/jiang_probe.json",
}

RESUME_PROBE = {
    "key": "A_readme.txt",
    "url": "https://zenodo.org/api/records/14518762/files/A_readme.txt/content",
    "bytes": 1_539,
    "md5": "b05ff3d3117887faa4aaff1414030317",
}


@dataclass(frozen=True)
class JobPaths:
    runtime: str
    repo: Path
    data: Path
    persist: Path
    scratch: Path
    remote: bool

    def as_dict(self) -> dict:
        return {
            "runtime": self.runtime,
            "repo": str(self.repo),
            "data": str(self.data),
            "persist": str(self.persist),
            "scratch": str(self.scratch),
            "remote": self.remote,
        }


def detect_runtime() -> str:
    if Path("/kaggle/working").is_dir():
        return "kaggle"
    if "COLAB_RELEASE_TAG" in os.environ or "COLAB_GPU" in os.environ:
        return "colab"
    try:
        import google.colab  # noqa: F401,PLC0415
        return "colab"
    except ImportError:
        pass
    return "local"


def refuse_windows_paths(*paths: Path) -> None:
    for path in paths:
        text = str(path)
        if len(text) > 1 and text[1] == ":":
            raise ValueError(
                f"Windows path {text} is forbidden in a remote job. "
                "Set VCC2026_DATA_ROOT to a POSIX path."
            )


def colab_default_roots(*, drive_mydrive_exists: bool) -> dict[str, str]:
    """POSIX defaults. Drive holds both matrices and run reports when mounted.

    A 65.8 GiB fetch to `/content/vcc-data` dies with the VM even if reports
    go to Drive. When MyDrive is present, both roots sit under it.
    """
    if drive_mydrive_exists:
        root = "/content/drive/MyDrive/vcc2026"
        return {
            "data": f"{root}/data",
            "persist": f"{root}/runs",
            "scratch": "/tmp/vcc-scratch",
        }
    return {
        "data": "/content/vcc-data",
        "persist": "/content/vcc-persist",
        "scratch": "/tmp/vcc-scratch",
    }


def resolve_paths(*, repo: Path | None = None) -> JobPaths:
    runtime = detect_runtime()
    remote = runtime != "local"
    repo = Path(repo or os.environ.get("VCC2026_REPO") or Path.cwd()).resolve()
    if runtime == "kaggle":
        data = Path(os.environ.get("VCC2026_DATA_ROOT", "/kaggle/working/vcc-data"))
        persist = Path(os.environ.get("VCC2026_PERSIST", "/kaggle/working"))
        scratch = Path(os.environ.get("VCC2026_SCRATCH", "/tmp/vcc-scratch"))
    elif runtime == "colab":
        roots = colab_default_roots(
            drive_mydrive_exists=Path("/content/drive/MyDrive").is_dir(),
        )
        data = Path(os.environ.get("VCC2026_DATA_ROOT", roots["data"]))
        persist = Path(os.environ.get("VCC2026_PERSIST", roots["persist"]))
        scratch = Path(os.environ.get("VCC2026_SCRATCH", roots["scratch"]))
    else:
        from vcc2026.config import paths as config_paths
        cfg = config_paths()
        data = Path(os.environ.get("VCC2026_DATA_ROOT", str(cfg.data_root)))
        persist = Path(os.environ.get("VCC2026_PERSIST", str(cfg.data_root / "interim" / "remote_job")))
        scratch = Path(os.environ.get("VCC2026_SCRATCH", str(persist / "scratch")))
    data, persist, scratch = data.resolve(), persist.resolve(), scratch.resolve()
    if remote:
        refuse_windows_paths(data, persist, scratch, repo)
    for path in (data, persist, scratch):
        path.mkdir(parents=True, exist_ok=True)
    return JobPaths(runtime, repo, data, persist, scratch, remote)


def hepg2_parity(path: Path) -> dict:
    """Compare an on-disk HepG2 file to the 2026-09-14 acquisition, without
    materialising the dense matrix."""
    size = path.stat().st_size
    md5 = _md5_file(path)
    with h5py.File(path, "r") as handle:
        x = handle["X"]
        shape = tuple(int(v) for v in x.shape)
        labels = np.asarray(_read_categorical(handle["obs"], "perturbation"), dtype=str)
        genes = np.asarray(_read_categorical(handle["var"], "gene_name"), dtype=str)
    ntc = int((labels == HEPG2["ntc_label"]).sum())
    axis = official_axis()
    on_axis = int(sum(1 for g in genes if g in axis.position()))
    checks = {
        "bytes": size == HEPG2["bytes"],
        "md5": md5 == HEPG2["md5"],
        "shape": shape == HEPG2["shape"],
        "ntc_cells": ntc == HEPG2["ntc_cells"],
        "n_on_official_axis": on_axis == HEPG2["n_on_official_axis"],
    }
    return {
        "path": str(path),
        "bytes": size,
        "md5": md5,
        "shape": list(shape),
        "ntc_label": HEPG2["ntc_label"],
        "ntc_cells": ntc,
        "n_genes": int(len(genes)),
        "n_on_official_axis": on_axis,
        "n_official_axis": len(axis),
        "checks": checks,
        "ok": all(checks.values()),
        "evidence": HEPG2["evidence"],
        "claim": "measured",
    }


def extract_hepg2_sample(path: Path, dest: Path, *, n_rows: int = 64, seed: int = 2026) -> dict:
    """Write gene mask + a contiguous count sample. Never the full dense X."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    axis = official_axis()
    pos = axis.position()
    with h5py.File(path, "r") as handle:
        genes = np.asarray(_read_categorical(handle["var"], "gene_name"), dtype=str)
        labels = np.asarray(_read_categorical(handle["obs"], "perturbation"), dtype=str)
        n_rows = min(n_rows, int(handle["X"].shape[0]))
        sample = np.asarray(handle["X"][:n_rows, :], dtype=np.float32)
    observed = np.array([g in pos for g in genes], dtype=bool)
    mask_path = dest / "gene_mask.npz"
    if mask_path.exists():
        raise FileExistsError(f"{mask_path} exists")
    np.savez_compressed(
        mask_path,
        symbols=genes.astype("U"),
        observed=observed,
        official_index=np.array([pos.get(g, -1) for g in genes], dtype=np.int64),
    )
    sample_path = dest / "x_head64.npz"
    if sample_path.exists():
        raise FileExistsError(f"{sample_path} exists")
    np.savez_compressed(sample_path, X=sample, perturbation=labels[:n_rows].astype("U"))
    record = {
        "n_rows_sampled": n_rows,
        "sample_contiguous_from": 0,
        "sample_is_not_a_random_draw": True,
        "n_genes": int(len(genes)),
        "n_observed_on_official_axis": int(observed.sum()),
        "n_unmeasured_official_genes": int(len(axis) - observed.sum()),
        "unmeasured_are_masked_not_zeroed": True,
        "ntc_in_sample": int((labels[:n_rows] == HEPG2["ntc_label"]).sum()),
        "x_min": float(sample.min()),
        "x_max": float(sample.max()),
        "x_integral": bool(np.allclose(sample, np.rint(sample))),
        "x_nonnegative": bool(sample.min() >= 0),
        "gene_mask": str(mask_path),
        "x_sample": str(sample_path),
        "seed_unused_because_contiguous": seed,
        "claim": "measured",
    }
    (dest / "extract.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    return record


def resume_selftest(dest: Path) -> dict:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / RESUME_PROBE["key"]
    for leftover in dest.glob(RESUME_PROBE["key"] + "*"):
        leftover.unlink()
    fetcher = ResumableFetcher(
        RESUME_PROBE["url"],
        target,
        expected_bytes=RESUME_PROBE["bytes"],
        expected_md5=RESUME_PROBE["md5"],
        max_bytes=2_000_000,
        chunk_bytes=256,
    )
    first, second = simulate_interrupt(fetcher, first_bytes=200)
    exported = export_and_verify(target, dest / "export" / RESUME_PROBE["key"])
    return {
        "interrupted_at": first.received,
        "resumed_done": second.done,
        "md5": second.md5,
        "prefix_preserved": first.received == 200,
        "export": exported,
        "claim": "measured",
    }


def jiang_tgfb_gate(*, free_bytes: int, floor_bytes: int, fetch: bool) -> dict:
    peak = disk_peak_estimate(
        input_bytes=JIANG_TGFB["bytes"],
        decompressed_bytes=None,
        derived_bytes=None,
        export_bytes=None,
        margin=0.25,
    )
    input_leaves_floor = (free_bytes - JIANG_TGFB["bytes"]) >= floor_bytes
    decision = "fetch" if fetch and input_leaves_floor else "skip"
    reason = (
        "operator asked to fetch and the input alone leaves the disk floor"
        if decision == "fetch"
        else (
            "input alone would break the disk floor"
            if not input_leaves_floor
            else "fetch not requested; TGFB conversion needs R/Seurat on the remote runtime"
        )
    )
    return {
        "block": JIANG_TGFB,
        "peak_estimate": peak,
        "input_leaves_floor": input_leaves_floor,
        "floor_bytes": floor_bytes,
        "free_bytes": free_bytes,
        "decision": decision,
        "reason": reason,
        "readRDS_ram": None,
        "claim": "derived",
    }


def prepare_upload_bundle(dest: Path, *, repo: Path) -> dict:
    """Tiny code+axis bundle for Colab/Kaggle. No matrices."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    snap = dest / "source_snapshot.tar.gz"
    snapshot = snapshot_source(snap, repo_root=repo)
    from vcc2026.config import paths as config_paths
    genes = config_paths().raw / "controls" / "gene_names.csv"
    if not genes.exists():
        raise FileNotFoundError(genes)
    copied = dest / "gene_names.csv"
    copied.write_bytes(genes.read_bytes())
    notebook = repo / "notebooks" / "remote_ingest_hepg2.ipynb"
    nb_copy = None
    if notebook.exists():
        target = dest / notebook.name
        target.write_bytes(notebook.read_bytes())
        nb_copy = str(target)
    readme = dest / "LEGGIMI.txt"
    readme.write_text(
        "Bundle for the remote ingest notebook.\n"
        "1. Upload this folder (or a zip of it) to Colab or a private Kaggle Dataset.\n"
        "2. Do NOT upload HepG2 or Jiang RDS from the laptop. The notebook fetches them.\n"
        "3. On Colab: Runtime -> CPU. Unpack source_snapshot.tar.gz into the working dir.\n"
        "4. Set VCC2026_REMOTE=1 and VCC2026_DATA_ROOT to a POSIX path.\n"
        "5. Copy gene_names.csv to $VCC2026_DATA_ROOT/raw/controls/gene_names.csv.\n",
        encoding="utf-8",
    )
    return {
        "dest": str(dest),
        "snapshot": snapshot,
        "gene_names_bytes": copied.stat().st_size,
        "notebook": nb_copy,
        "contains_matrices": False,
        "claim": "measured",
    }


def run_job(
    *,
    out: Path,
    repo: Path,
    skip_hepg2_download: bool = True,
    fetch_jiang: bool = False,
    disk_floor_gib: float | None = None,
    n_sample_rows: int = 64,
) -> dict:
    """Execute the contract. Refuses to overwrite `out`."""
    out = Path(out)
    dest = out / "remote_ingest.json"
    if dest.exists():
        raise FileExistsError(f"{dest} exists; give a new --out")
    out.mkdir(parents=True, exist_ok=True)
    paths = resolve_paths(repo=repo)
    floor = (10.0 if not paths.remote else 2.0) if disk_floor_gib is None else disk_floor_gib
    floor_bytes = int(floor * GiB)
    inventory = collect_inventory(
        repo=paths.repo, data_root=paths.data, persistent=paths.persist,
        forbid_windows_paths=paths.remote,
    )
    free = int(inventory.persistent_paths["free_bytes"])
    hepg2_peak = disk_peak_estimate(
        input_bytes=HEPG2["bytes"],
        decompressed_bytes=HEPG2["dense_bytes"],
        derived_bytes=20_000_000,
        export_bytes=5_000_000,
        margin=0.25,
    )

    hepg2_path = paths.data / "raw" / "nadig_hepg2" / HEPG2["key"]
    fetched = None
    if hepg2_path.exists() and skip_hepg2_download:
        fetched = {"skipped": True, "reason": "file on disk and skip_hepg2_download=True"}
    elif hepg2_peak["peak_bytes"] is not None and (free - hepg2_peak["peak_bytes"]) < floor_bytes:
        raise RuntimeError(
            f"refusing HepG2 fetch: peak {hepg2_peak['peak_bytes']} would break "
            f"the {floor} GiB floor with {free} free"
        )
    else:
        hepg2_path.parent.mkdir(parents=True, exist_ok=True)
        fetcher = ResumableFetcher(
            HEPG2["url"], hepg2_path,
            expected_bytes=HEPG2["bytes"], expected_md5=HEPG2["md5"],
            max_bytes=HEPG2["bytes"] + 1_000_000,
        )
        fetched = fetcher.fetch().as_dict()

    parity = hepg2_parity(hepg2_path) if hepg2_path.exists() else None
    extract = None
    if parity is not None and parity["ok"]:
        extract = extract_hepg2_sample(
            hepg2_path, out / "hepg2_extract", n_rows=n_sample_rows,
        )
    resume = resume_selftest(paths.scratch / "resume_probe")
    exported_resume = resume["export"]
    jiang = jiang_tgfb_gate(free_bytes=free, floor_bytes=floor_bytes, fetch=fetch_jiang)

    snapshot = None
    snap_path = out / "source_snapshot.tar.gz"
    if not snap_path.exists():
        snapshot = snapshot_source(snap_path, repo_root=paths.repo)

    report = {
        "paths": paths.as_dict(),
        "inventory": inventory.as_dict(),
        "disk_floor_gib": floor,
        "disk_floor_note": (
            "10 GiB is D-005 on the laptop. 2 GiB is a proposed remote floor, "
            "not a measured Kaggle/Colab quota."
        ),
        "hepg2_peak": hepg2_peak,
        "hepg2_fetch": fetched,
        "hepg2_parity": parity,
        "hepg2_extract": extract,
        "resume_selftest": resume,
        "jiang_tgfb": jiang,
        "source_snapshot": snapshot,
        "export_is_on_persist": str(out.resolve()).startswith(str(paths.persist)),
        "claim": "measured",
    }
    dest.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    if exported_resume.get("persistent"):
        bundle = out / "export" / RESUME_PROBE["key"]
        bundle.parent.mkdir(parents=True, exist_ok=True)
        bundle.write_bytes(Path(exported_resume["persistent"]).read_bytes())
    manifest = RunManifest(
        run_id=out.name, stage="67_remote_ingest",
        config={"skip_hepg2_download": skip_hepg2_download, "fetch_jiang": fetch_jiang},
    )
    manifest.add_output("report", dest)
    manifest.note("HepG2 parity is against the 2026-09-14 acquisition, not a new biology.")
    manifest.note("Jiang TGFB was not converted: R/Seurat is required and disk may refuse.")
    manifest.write(out / "manifest_67_remote_ingest.json")
    return report
