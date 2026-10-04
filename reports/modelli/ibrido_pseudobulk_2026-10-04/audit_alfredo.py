"""Recount panel coverage and CD4 readiness for the received Alfredo proposal."""
import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    vip = ROOT / 'reports/sorgenti/universo_nuovi_2026-09-27/viperturb_p1/index.csv'
    bridge = ROOT / 'reports/analisi/lead_scientist_2026-09-29/ponte_plan_r2/panel_coverage.csv'
    cd4 = ROOT / 'reports/generatore_e_banchi/ripresa_banco_v2_2026-10-04/copertura_cd4_r2.json'
    t28 = ROOT / 'reports/invii/prediction_t28_2026-09-29/comparison.json'
    rows = read_csv(vip)
    panel = [r for r in rows if r['in_panel'] == 'True']
    assert len({r['target'] for r in panel}) == len(panel)
    b = read_csv(bridge)
    c = json.loads(cd4.read_text())
    t = json.loads(t28.read_text())
    doc = {
        'utc': datetime.now(timezone.utc).isoformat(),
        'sources': {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest()
                    for f in (vip, bridge, cd4, t28)},
        'remote_branch_checked': 'codex/teammate-rlead',
        'fetched_head': '3d0646f90327c51feee484a397f0e433e749539c',
        'later_claims': 'Not yet available on fetched branch; attributed to Alfredo, not independently verified.',
        'viperturb': {'index_rows': len(rows), 'panel_in_index': len(panel),
                     'panel_n_ge_10': sum(float(r['n_cells']) >= 10 for r in panel),
                     'panel_n_ge_30': sum(float(r['n_cells']) >= 30 for r in panel),
                     'bridge_panel_rows': len(b),
                     'bridge_both_halves': sum(r['has_a'] == r['has_b'] == 'True' for r in b),
                     'below_10': [r['target'] for r in panel if float(r['n_cells']) < 10],
                     'scope': 'Index eligibility, not cell-level ingestion or read of every effect gene.'},
        'cd4': {'verified_units': c['verified_units'], 'complete': c['complete'],
                'eligible_cells': sum(u['cells'] for u in c['units'].values()),
                'bytes': sum(u['bytes'] for u in c['units'].values()),
                'donor_resolved_effect_bank_ready': False, 'alfredo_access_verified': False},
        't28_minus_t25_scaled': t['scaled_published']['t28_minus_t25'],
    }
    with a.out.open('x', encoding='utf-8') as f:
        json.dump(doc, f, indent=2)
    print(json.dumps({'viperturb': doc['viperturb'], 'cd4': doc['cd4']}))


if __name__ == '__main__':
    main()
