"""CLI dell'oracolo pairwise sulla loss.

Identificatori e flag in inglese; testi rivolti all'operatore in italiano.
Nessuna rete, nessun modello, nessuna esecuzione del contenuto degli input.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pairwise_loss import ERROR, FAIL, PASS, UNVERIFIED, verify_paths

EXIT = {PASS: 0, FAIL: 1, UNVERIFIED: 2, ERROR: 3}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m oracle",
        description=(
            "Verifica un'affermazione numerica di confronto fra due loss "
            "ricalcolando dal CSV. Il JSON candidato non è fidato e non può "
            "cambiare formule, soglie o regole."
        ),
    )
    parser.add_argument("--csv", required=True, type=Path,
                        help="CSV dei casi (case_id, loss_a, loss_b)")
    parser.add_argument("--candidate", required=True, type=Path,
                        help="JSON dell'affermazione da verificare")
    parser.add_argument("--config", type=Path, default=None,
                        help="JSON di configurazione dell'operatore (tolleranze e soglia)")
    parser.add_argument("--report", type=Path, default=None,
                        help="percorso del report JSON; se omesso, stdout")
    parser.add_argument("--summary", type=Path, default=None,
                        help="percorso del riepilogo testuale; se omesso, stderr")
    parser.add_argument("--force", action="store_true",
                        help="sovrascrivi i file di uscita se esistono già")
    return parser


def _refuse_overwrite(path: Path, force: bool) -> str | None:
    if path.exists() and not force:
        return f"rifiuto di sovrascrivere {path}; usa --force se è intenzionale"
    return None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = verify_paths(args.csv, args.candidate, args.config)
    json_text = report.to_json()
    summary = report.summary_text()

    if args.report is not None:
        reason = _refuse_overwrite(args.report, args.force)
        if reason:
            print(reason, file=sys.stderr)
            return EXIT[ERROR]
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json_text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(json_text)

    if args.summary is not None:
        reason = _refuse_overwrite(args.summary, args.force)
        if reason:
            print(reason, file=sys.stderr)
            return EXIT[ERROR]
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(summary, encoding="utf-8", newline="\n")
    else:
        sys.stderr.write(summary)

    return EXIT.get(report.verdict, EXIT[ERROR])


if __name__ == "__main__":
    raise SystemExit(main())
