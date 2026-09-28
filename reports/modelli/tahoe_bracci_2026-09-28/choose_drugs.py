"""Select metadata single-gene CRISPRi overlaps and five mechanism controls, offline.

Usage: scripts/py.cmd reports/modelli/tahoe_bracci_2026-09-28/choose_drugs.py --out NEW
The selected CSV preserves exact Tahoe drug strings (including trailing spaces).
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import pandas as pd

from extract_arms import META


def choose(metadata, processed, explicit=None):
    preferred = processed/'universe_k562_2026-09-26/index.csv'
    candidates = [explicit] if explicit else [preferred] + sorted(processed.glob('**/universe*/index.csv'))
    used, targets = None, None
    for path in candidates:
        if path is None or not path.is_file(): continue
        frame = pd.read_csv(path)
        if 'target' in frame and frame.target.notna().any():
            used, targets = path, set(frame.target.dropna().astype(str)); break
    if used is None: raise ValueError('No universe index.csv with a target column; pass --targets-index')
    dm = pd.read_parquet(metadata/'drug_metadata.parquet')
    sm = pd.read_parquet(metadata/'sample_metadata.parquet')
    if dm.drug.duplicated().any(): raise ValueError('Duplicate drug annotations')
    # Match full labels, not substrings such as BET in unrelated words.
    mechanisms = {'proteasome': r'proteasome', 'HDAC': r'HDAC|histone deacetylase',
                  'BET': r'\bBET\b|bromodomain', 'mTOR': r'\bmTOR\b', 'CDK': r'\bCDK\b|cyclin.dependent'}
    controls = {}
    for family, pattern in mechanisms.items():
        hits = dm[dm['moa-fine'].fillna('').str.contains(pattern, case=False, regex=True)]
        hits = hits[hits.drug.isin(sm.drug)].sort_values('drug')
        if not hits.empty: controls[str(hits.iloc[0].drug)] = family
    rows = []
    for r in dm.to_dict('records'):
        raw = '' if pd.isna(r['targets']) else str(r['targets']).strip()
        single = bool(re.fullmatch(r'[A-Z][A-Z0-9-]*', raw)) and raw in targets
        control = controls.get(r['drug'])
        if not single and not control: continue
        if r['drug'] not in set(sm.drug): continue
        reasons = []
        if single: reasons.append('Single annotated symbol present as a knockdown target in the selected universe; selectivity unverified')
        if control: reasons.append(f'Candidate positive control: {control} mechanism; strong response is a hypothesis, not measured')
        rows.append(dict(drug=r['drug'], target=raw if single else '', annotated_targets=raw,
                         moa_fine=r['moa-fine'], bridge_candidate=single, positive_control=bool(control),
                         control_family=control or '', reason='; '.join(reasons), target_index=str(used)))
    selected = pd.DataFrame(rows).sort_values('drug')
    manifest = dict(target_index=str(used), target_index_sha256=hashlib.sha256(used.read_bytes()).hexdigest(),
                    universe_targets=len(targets), selected_drugs=len(selected),
                    bridge_candidates=int(selected.bridge_candidate.sum()),
                    positive_controls=int(selected.positive_control.sum()),
                    control_families=controls, absent_control_families=sorted(set(mechanisms)-set(controls.values())),
                    selected_samples=int(sm.drug.isin(selected.drug).sum()),
                    dmso_samples=int(sm.drug.eq('DMSO_TF').sum()),
                    metadata={p.name:dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                              for p in sorted(metadata.glob('*_metadata.parquet'))},
                    claim_type='metadata selection; no measured response or pharmacological selectivity')
    return selected, manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--metadata', type=Path, default=META)
    ap.add_argument('--processed', type=Path, default=Path('C:/Users/ferra/vcc2026-data/processed'))
    ap.add_argument('--targets-index', type=Path)
    args = ap.parse_args()
    selected, manifest = choose(args.metadata, args.processed, args.targets_index)
    args.out.mkdir(parents=True, exist_ok=False)
    selected.to_csv(args.out/'drugs.csv', index=False)
    with (args.out/'manifest.json').open('x', encoding='utf-8') as f: json.dump(manifest, f, indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__': main()
