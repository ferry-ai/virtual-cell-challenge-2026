"""Registry and downloader for the public perturbation datasets we train on.

Runs unchanged locally and on Kaggle/Colab, so the same call fetches the same
bytes wherever the pipeline happens to be executing.

Two things are worth knowing before reaching for the single-cell files:

* The authors already publish **pseudobulk** versions. `k562_gwps_raw_bulk` is
  375 MB against 61 GB for the matching single-cell file, and carries the
  per-perturbation mean profiles that a transfer model actually trains on. Pull
  the single-cell files only for the held-out line being scored by cell-eval2.
* Download through `ndownloader.figshare.com`, the URL figshare's own API
  reports. The `plus.figshare.com` links printed on web pages sit behind an AWS
  WAF bot challenge and return `202 Accepted` with an empty body.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import httpx
from tqdm import tqdm

__all__ = ["FigshareFile", "REGISTRY", "fetch", "local_path"]

_NDOWNLOADER = "https://ndownloader.figshare.com/files/{file_id}"
_CHUNK = 1 << 20


@dataclass(frozen=True)
class FigshareFile:
    """One downloadable artifact, with the checksum figshare publishes for it."""

    file_id: int
    name: str
    size: int
    md5: str

    @property
    def url(self) -> str:
        return _NDOWNLOADER.format(file_id=self.file_id)

    @property
    def size_gb(self) -> float:
        return self.size / 1024**3


# Replogle et al. 2022, "Mapping information-rich genotype-phenotype landscapes
# with genome-scale Perturb-seq". CC BY 4.0, figshare article 20029387.
#   gwps      = genome-wide Perturb-seq (~9,800 perturbations)
#   essential = DepMap essential genes only (~2,000 perturbations)
#   bulk      = per-perturbation pseudobulk; singlecell = one row per cell
REGISTRY: dict[str, FigshareFile] = {
    "k562_essential_raw_bulk": FigshareFile(
        35773070, "K562_essential_raw_bulk_01.h5ad", 79766954,
        "8321d5d3ffc99db2a5c71edca4189735",
    ),
    "k562_essential_normalized_bulk": FigshareFile(
        35780870, "K562_essential_normalized_bulk_01.h5ad", 79766954,
        "30496767641cd2e660ee6ecb5baee132",
    ),
    "k562_essential_raw_singlecell": FigshareFile(
        35773219, "K562_essential_raw_singlecell_01.h5ad", 10661879995,
        "4f1122ce1c7f13299a68df6459a266d3",
    ),
    "k562_essential_normalized_singlecell": FigshareFile(
        35773075, "K562_essential_normalized_singlecell_01.h5ad", 10661879995,
        "f1e221fbf6eac774c21c4242ed440c3f",
    ),
    "k562_gwps_raw_bulk": FigshareFile(
        35774443, "K562_gwps_raw_bulk_01.h5ad", 374587922,
        "4570b53c9d62ff6df281e622f0350060",
    ),
    "k562_gwps_normalized_bulk": FigshareFile(
        35773217, "K562_gwps_normalized_bulk_01.h5ad", 374587922,
        "a3dfaa94ea8724217f5ecb1e14a5f0c8",
    ),
    "k562_gwps_raw_singlecell": FigshareFile(
        35775507, "K562_gwps_raw_singlecell_01.h5ad", 65830941948,
        "887e3e6a8c8df6eadf7a3030a53c9546",
    ),
    "k562_gwps_normalized_singlecell": FigshareFile(
        35774440, "K562_gwps_normalized_singlecell_01.h5ad", 65830941948,
        "6cd393e369506849ebf959175989d632",
    ),
    "rpe1_raw_bulk": FigshareFile(
        35775581, "rpe1_raw_bulk_01.h5ad", 95350546,
        "74765fa87635467a869ea972356ae0e7",
    ),
    "rpe1_normalized_bulk": FigshareFile(
        35775512, "rpe1_normalized_bulk_01.h5ad", 95350546,
        "6f1e7d6a09e2f869759e3c4526b7f171",
    ),
    "rpe1_raw_singlecell": FigshareFile(
        35775606, "rpe1_raw_singlecell_01.h5ad", 8700873216,
        "6a2a9d0d2bf4ec147f4d1104043b268c",
    ),
    "rpe1_normalized_singlecell": FigshareFile(
        35775554, "rpe1_normalized_singlecell_01.h5ad", 8700873216,
        "2c36a053960f3fae157adacdbccd4485",
    ),
}


def local_path(key: str, dest_dir: Path) -> Path:
    """Where `key` lands under `dest_dir`."""
    return dest_dir / REGISTRY[key].name


def fetch(
    key: str,
    dest_dir: Path,
    *,
    verify: bool = True,
    force: bool = False,
) -> Path:
    """Download one registry entry, resuming a partial file if one is there.

    Args:
        key: registry key, e.g. "rpe1_raw_bulk".
        dest_dir: directory to download into; created if missing.
        verify: check the md5 figshare publishes once the bytes are complete.
        force: re-download even if a complete, verified file already exists.

    Returns:
        Path to the downloaded file.

    Raises:
        KeyError: unknown key.
        ValueError: the completed download fails its checksum.
    """
    if key not in REGISTRY:
        raise KeyError(f"unknown dataset {key!r}; known: {sorted(REGISTRY)}")

    entry = REGISTRY[key]
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / entry.name

    if target.exists() and not force:
        if target.stat().st_size == entry.size:
            if not verify or _md5(target) == entry.md5:
                print(f"{entry.name}: already present ({entry.size_gb:.2f} GB)")
                return target
            print(f"{entry.name}: checksum mismatch, re-downloading")
            target.unlink()

    have = target.stat().st_size if target.exists() else 0
    if have > entry.size:
        target.unlink()
        have = 0

    headers = {"Range": f"bytes={have}-"} if have else {}
    mode = "ab" if have else "wb"
    if have:
        print(f"{entry.name}: resuming at {have / 1024**2:,.0f} MB")

    with httpx.stream(
        "GET", entry.url, headers=headers, follow_redirects=True, timeout=60.0
    ) as response:
        response.raise_for_status()
        with (
            target.open(mode) as fh,
            tqdm(
                total=entry.size,
                initial=have,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=entry.name[:38],
            ) as bar,
        ):
            for chunk in response.iter_bytes(_CHUNK):
                fh.write(chunk)
                bar.update(len(chunk))

    actual = target.stat().st_size
    if actual != entry.size:
        raise ValueError(
            f"{entry.name}: got {actual:,} bytes, expected {entry.size:,}"
        )
    if verify:
        digest = _md5(target)
        if digest != entry.md5:
            raise ValueError(f"{entry.name}: md5 {digest} != expected {entry.md5}")
        print(f"{entry.name}: checksum verified")

    return target


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()
