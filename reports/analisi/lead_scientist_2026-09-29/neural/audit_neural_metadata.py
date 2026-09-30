"""Small metadata audit; never reads a model checkpoint or executes pickle code."""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import math
import pickletools
from pathlib import Path
import statistics
import urllib.request
import zipfile


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def number(value):
    try:
        out = float(value)
        return out if math.isfinite(out) else None
    except (ValueError, TypeError):
        return None


def summary(values):
    values = [v for v in values if v is not None]
    return {"n": len(values), "median": statistics.median(values) if values else None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--public-arc-metadata", action="store_true")
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    repo = Path(__file__).resolve().parents[4]
    rows = read_csv(args.data_root / "processed/rete_contesti_r2/targets.csv")
    panel = {r["target"] for r in rows if r["in_panel"] == "True"}
    essential = {r["target"] for r in rows if r["essential"] == "True"}
    out = {"claim_type": "measured, exploratory metadata, no model fit or scoring",
           "targets": len(rows), "panel": len(panel), "panel_in_essential_screen": len(panel & essential),
           "essential_screen_targets": len(essential),
           "prior_columns": [k for k in rows[0] if k.startswith(("p_", "x_"))],
           "prior_groups": {}}
    for name, keep in [("panel", panel), ("essential_screen", essential), ("all", {r["target"] for r in rows})]:
        selected = [r for r in rows if r["target"] in keep]
        out["prior_groups"][name] = {k: summary([number(r[k]) for r in selected]) for k in out["prior_columns"]}
    out["knockdown"] = {}
    for path in sorted((repo / "reports/sorgenti/profondita_silenziamento_2026-09-27/r1").glob("per_target_*.csv")):
        data = read_csv(path)
        groups = {}
        for name, select in [("all", data), ("panel", [r for r in data if r["target"] in panel]),
                             ("essential_screen", [r for r in data if r["target"] in essential])]:
            finite = [r for r in select if number(r["d"]) is not None and number(r["z_own"]) is not None]
            groups[name] = {"n": len(select), "finite": len(finite),
                            "clear_silencing_z_le_minus3": sum(float(r["z_own"]) <= -3 for r in finite),
                            "positive_own_effect": sum(float(r["d"]) <= 0 for r in finite),
                            "depth": summary([number(r["d"]) for r in select]),
                            "energy": summary([number(r["energy"]) for r in select])}
        out["knockdown"][path.stem.removeprefix("per_target_")] = groups
    if args.public_arc_metadata:
        def get(url):
            req = urllib.request.Request(url, headers={"User-Agent": "vcc2026-public-metadata-audit"})
            with urllib.request.urlopen(req, timeout=45) as response:
                payload = response.read(25_000_001)
            if len(payload) > 25_000_000:
                raise ValueError("Metadata response exceeds 25 MB audit limit")
            return payload
        url = "https://huggingface.co/arcinstitute/ST-HVG-Replogle/resolve/main/zeroshot/hepg2/pert_onehot_map.pt"
        blob = get(url)
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            entry = next(n for n in archive.namelist() if n.endswith("/data.pkl") or n == "data.pkl")
            # Inspect string opcodes only. Do NOT unpickle torch objects or execute GLOBAL/REDUCE.
            strings = {arg for op, arg, _ in pickletools.genops(archive.read(entry))
                       if op.name in {"BINUNICODE", "SHORT_BINUNICODE", "UNICODE", "BINUNICODE8"}}
        names = {r["target"] for r in rows}
        normalized = set(strings)
        for label in strings:
            # numpy.str_ scalar keys use UTF-32-LE bytes carried as a Latin-1
            # pickle string. Decode those statically, without numpy/pickle.load.
            if "\0" in label:
                try:
                    normalized.add(label.encode("latin-1").decode("utf-32-le"))
                except (UnicodeError, ValueError):
                    pass
            try:
                value = ast.literal_eval(label)
            except (SyntaxError, ValueError):
                continue
            if isinstance(value, (tuple, list)) and len(value) == 1 and isinstance(value[0], str):
                normalized.add(value[0])
        known = names & normalized
        out["state_onehot"] = {"url": url, "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest(),
                                 "method": "static pickle string opcodes; membership, not tensor execution",
                                 "strings": len(strings), "known_target_strings": len(known),
                                 "sample_strings": sorted(strings)[:15],
                                 "known_targets": sorted(known),
                                 "panel_overlap": sorted(panel & normalized),
                                 "panel_absent": sorted(panel - normalized),
                                 "essential_screen_overlap": len(essential & normalized)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in {"prior_groups", "state_onehot"}}, indent=2))
    if "state_onehot" in out:
        print(json.dumps({k: v for k, v in out["state_onehot"].items()
                          if k not in {"panel_absent", "known_targets", "sample_strings"}}, indent=2))


if __name__ == "__main__":
    main()
