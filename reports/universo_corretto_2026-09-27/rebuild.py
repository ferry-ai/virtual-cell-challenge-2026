"""The genome-wide universes rebuilt with the corrected estimator (`min_expected`), from the same inputs.

The universes of 26 September (reports/universo_2026-09-26/) were estimated with the constant pseudocount,
whose artefact is measured in reports/pseudoconteggio_2026-09-27/. This runs the same scripts, unchanged,
with `effects_from_pseudobulk(..., min_expected=M)` in place of the default:
* ``--source cd4``: `cd4_universe.main` re-reads the CD4 genome-wide pseudobulk (44.6 GB, local);
* ``--source hct116`` / ``hek293t``: `orion_universe.finalize` re-estimates from the per-pool accumulators
  kept in <data_root>/interim/orion_universe_<line>/ (nothing is downloaded, nothing there is written).
Parity is checked against the stage-98 panel cache built with the same estimator (r9 by default), where
the panel targets must come out identical. Writes to NEW --out and --report folders, and adds
``correzione.json`` to --report, since the scripts' own manifests do not name the estimator's option.

    scripts/py.cmd reports/universo_corretto_2026-09-27/rebuild.py --source hct116 \
        --out <data_root>/processed/universe_orion_hct116_2026-09-27_me1 --report reports/universo_corretto_2026-09-27/orion_hct116
"""
from __future__ import annotations

import argparse
import functools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "reports" / "universo_2026-09-26"))

import vcc2026.multisource as ms  # noqa: E402
from vcc2026 import config  # noqa: E402

DATA = config.paths().data_root


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["cd4", "hct116", "hek293t"], required=True)
    ap.add_argument("--min-expected", type=float, default=1.0)
    ap.add_argument("--panel-cache", type=Path, default=DATA / "processed/multisource_2026-09-27_r9")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists() or args.report.exists():
        raise SystemExit("--out and --report must be new folders")
    patched = functools.partial(ms.effects_from_pseudobulk, min_expected=args.min_expected)
    started = datetime.now(timezone.utc).isoformat()
    if args.source == "cd4":
        import cd4_universe as cu
        cu.effects_from_pseudobulk = patched          # the script imported the name at module level
        sys.argv = [str(REPO / "reports/universo_2026-09-26/cd4_universe.py"), "--panel-first",
                    "--cache", str(args.panel_cache), "--out", str(args.out), "--report", str(args.report)]
        cu.main()
        script = "reports/universo_2026-09-26/cd4_universe.py (main, --panel-first)"
    else:
        ms.effects_from_pseudobulk = patched          # orion_universe imports it inside `estimate`
        import orion_universe as ou
        line = {"hct116": "HCT116", "hek293t": "HEK293T"}[args.source]
        ou.finalize(line, DATA / "interim" / f"orion_universe_{args.source}", args.out, args.report,
                    panel_cache=args.panel_cache)
        script = "reports/universo_2026-09-26/orion_universe.py (finalize)"
    note = {"script": "reports/universo_corretto_2026-09-27/rebuild.py", "runs": script, "source": args.source,
            "estimator": f"vcc2026.multisource.effects_from_pseudobulk with min_expected={args.min_expected:g}",
            "panel_cache_for_parity": str(args.panel_cache), "out": str(args.out), "started_utc": started,
            "finished_utc": datetime.now(timezone.utc).isoformat()}
    with (args.report / "correzione.json").open("x", encoding="utf-8") as fh:
        json.dump(note, fh, indent=1)
    print(json.dumps(note, indent=1))


if __name__ == "__main__":
    main()
