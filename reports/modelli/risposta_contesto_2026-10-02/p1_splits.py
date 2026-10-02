"""R-LEAD P1: frozen split manifest, real exposures and the history of the reserves.

Writes ``split_manifest.json`` (+ ``split_folds.csv.gz``), ``exposure_manifest.json`` and
``reserve_manifest.json``. Splits come from `splits.py` (folds by sha256 of the reconciled target key);
regimes are recomputed after QC against the training rows that remain; QC losses are listed, never
reassigned. Exposures of earlier models are read from their own prepass files, not inferred from
names; the reserve history extends the R-LAB registry of 30/09 with every reading since.

    py.cmd p1_splits.py --p0 <report>/p0_r1 --cube <data>/.../cube_r1 --out <report>/p1_r1
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import REPO, Timer, log, now_utc, sha256, write_json
from registry import NOT_LOCAL, TABLES
from splits import SALT, Split, evaluation_rows, make_splits, target_fold, training_mask

N_FOLDS = 5


def stability_check(rows: pd.DataFrame, rng_seed: int = 7) -> dict:
    """Roles of shared keys before/after dropping a fifth of the tables and reordering everything."""
    rng = np.random.default_rng(rng_seed)
    tables = sorted(rows.table.unique())
    drop = set(rng.choice(tables, max(1, len(tables) // 5), replace=False))
    sub = rows[~rows.table.isin(drop)].sample(frac=1.0, random_state=rng_seed)
    folds_a = {k: target_fold(k, N_FOLDS) for k in rows.target_key.unique()}
    folds_b = {k: target_fold(k, N_FOLDS) for k in sub.target_key.unique()}
    same = all(folds_a[k] == v for k, v in folds_b.items())
    changed_roles = 0
    for split in make_splits(sorted(rows.group.unique()), ('C', 'J', 'T'), N_FOLDS):
        a = pd.Series(training_mask(rows, split), index=rows.index)
        b = pd.Series(training_mask(sub, split), index=sub.index)
        changed_roles += int((a.loc[b.index] != b).sum())
    return dict(dropped_tables=sorted(drop), folds_identical_for_shared_keys=same,
                rows_with_changed_training_role=changed_roles, passed=same and changed_roles == 0)


def prior_exposures() -> dict:
    """Exposures of r2 and r3 (cellnet) from their prepass files, and of the production transfer."""
    mod = REPO / 'reports' / 'modelli'
    out = {}
    for name, path in (('cellnet_r2', mod / 'cellnet_esteso_2026-10-01/esito/prepass_r5/prepass/splits.json'),
                       ('cellnet_r3', mod / 'cellnet_completo_2026-10-01/esito/prepass_r7/prepass/splits.json')):
        s = json.loads(path.read_text(encoding='utf-8'))
        out[name] = dict(source=str(path.relative_to(REPO)), sha256=sha256(path), seed=s['seed'],
                         holdout_context=s['holdout_context'], hidden_symbols=len(s['hidden_symbols']),
                         trainable_symbols=s['trainable_symbols'], admitted_cells_by_class=s['admitted_cells_by_class'],
                         evaluation_groups=s['evaluation_groups'],
                         studies=sorted(s['labels']['cells_by_kind_and_study']),
                         note=('K562, RPE1, Jurkat, H1 train/val and HIPSCI perturbed cells are training for this '
                               'model: none of them is a new context for it; HepG2 is its held-out context '
                               '(C/J classes), already read (lead audit 1/10)'))
    r5 = set(json.loads((mod / 'cellnet_esteso_2026-10-01/esito/prepass_r5/prepass/splits.json')
                        .read_text(encoding='utf-8'))['hidden_symbols'])
    r7 = set(json.loads((mod / 'cellnet_completo_2026-10-01/esito/prepass_r7/prepass/splits.json')
                        .read_text(encoding='utf-8'))['hidden_symbols'])
    out['r2_vs_r3_hidden_lists'] = dict(r2=len(r5), r3=len(r7), shared=len(r5 & r7),
                                        jaccard=len(r5 & r7) / len(r5 | r7),
                                        reading='reproduces lead audit 1/10 §2.1: the J barrier changed with the corpus')
    out['production_transfer_t22_t25'] = dict(
        sources=['k562 (Replogle GWPS)', 'cd4_mix (Marson, three states)', 'orion_hct116', 'orion_hek293t'],
        targets='the A/B/C panel', recipe='configs/recipes/t25.json (cache r9, estimator min_expected 1)',
        note='every panel target of these four lines is training for the production transfer')
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--p0', type=Path, required=True)
    p.add_argument('--cube', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    timer = Timer()
    with gzip.open(a.p0 / 'context_target_study.csv.gz', 'rt', encoding='utf-8') as f:
        cts = pd.read_csv(f, low_memory=False)
    bench_ids = [t['id'] for t in TABLES if t['role'] == 'bench']
    rows = cts[cts.table.isin(bench_ids)].reset_index(drop=True)
    rows['qc_ok'] = True                                  # table-level QC: bench tables passed the registry
    keys_info = pd.read_csv(a.cube / 'keys.csv')
    cube_keys = set(keys_info.target_key)
    groups = sorted(rows.group.unique())
    a.out.mkdir(parents=True)
    folds = pd.DataFrame(dict(target_key=sorted(rows.target_key.unique())))
    folds['fold'] = [target_fold(k, N_FOLDS) for k in folds.target_key]
    folds.to_csv(a.out / 'split_folds.csv.gz', index=False, compression='gzip')
    splits = []
    for split in make_splits(groups, ('C', 'J', 'T'), N_FOLDS):
        ev = evaluation_rows(rows, split, min_cells=10)
        in_cube = ev.rows[ev.rows.target_key.isin(cube_keys)]
        train = rows[training_mask(rows, split)]
        splits.append(dict(
            name=split.name, regime=split.regime, held_group=split.held_group, fold=split.fold,
            role='diagnostic' if split.regime == 'T' else 'bench',
            held_tables=sorted(rows[rows.group == split.held_group].table.unique()),
            training_tables=sorted(train.table.unique()), training_rows=int(len(train)),
            excluded_target_keys=int(sum(split.target_held(k) for k in rows.target_key.unique()))
            if split.regime != 'C' else 0,
            evaluated_rows_all_keys=int(len(ev.rows)), evaluated_rows_in_cube=int(len(in_cube)),
            evaluated_by_stratum=in_cube.target_key.map(keys_info.set_index('target_key')['stratum'])
            .value_counts().to_dict(),
            lost_after_qc=ev.lost.groupby('reason').size().to_dict() if len(ev.lost) else {},
            support_median=float(ev.rows.support.median()) if len(ev.rows) else None))
    alias_info = json.loads((a.p0 / 'aliases.json').read_text(encoding='utf-8'))
    write_json(a.out / 'split_manifest.json', dict(
        written_utc=now_utc(), salt=SALT, n_folds=N_FOLDS, unit='line group (all studies, states, donors, clones)',
        groups={g: sorted(rows[rows.group == g].table.unique()) for g in groups},
        fold_rule='fold = floor(N * U(sha256(salt + ":fold:" + target_key))); key = Ensembl ID reconciled in P0',
        regimes=dict(C='held group removed from every fit; target needs QC-passing support in another group',
                     J='held group removed; held fold keys removed from every table (aliases merged by key)',
                     T='held fold keys removed from every table; the group stays (diagnostic only)'),
        qc='rows with < 10 cells are not evaluable nor training; lost rows are listed, never reassigned',
        aliases=dict(keys_with_several_symbols=len(alias_info['one_id_several_symbols']),
                     symbols_with_several_ids=len(alias_info['one_symbol_several_ids']),
                     unresolved_symbols=alias_info['key_sources'].get('unresolved', 0)),
        stability=stability_check(rows[['table', 'group', 'target_key']].copy()),
        splits=splits, inputs=dict(p0=str(a.p0), cube_keys=str(a.cube / 'keys.csv'),
                                   cube_keys_sha256=sha256(a.cube / 'keys.csv')),
        folds_file=dict(name='split_folds.csv.gz', sha256=sha256(a.out / 'split_folds.csv.gz'))))
    write_json(a.out / 'exposure_manifest.json', dict(
        written_utc=now_utc(),
        this_bench=dict(rule='every arm of a split (transfer included) is fitted only on rows that '
                             'splits.Split.row_allowed admits; p3_run.py asserts it on the rows and logs '
                             'every table read with its purpose, failing if a fit reads the held group',
                        controls='held-out controls enter only as the basal profile of the held table',
                        pretraining='none: closed-form fits on the cube; no pretrained representation'),
        prior_models=prior_exposures()))
    registry = json.loads((REPO / 'reports/modelli/risposta_biologica_2026-09-30/holdout_registry.json')
                          .read_text(encoding='utf-8'))
    added = {
        'hepg2_nadig': ['lead audit 1/10: C/J/T readings of r2 desc (reports/analisi/lead_audit_2026-10-01/)',
                        'this study 2/10: held-out group of the C/J bench (development)'],
        'replogle_k562_gwps': ['r2 T diagnostics (315 groups), lead audit 1/10', 'this study 2/10: bench group K562'],
        'replogle_k562_essential': ['r2 T diagnostics (30 groups)', 'this study 2/10: bench group K562'],
        'replogle_rpe1': ['r2 T diagnostics (17 groups)', 'this study 2/10: bench group RPE1'],
        'viperturb_k562_flex': ['this study 2/10: bench group K562'],
        'cd4_marson2025': ['this study 2/10: bench group CD4T'],
        'orion_hct116': ['this study 2/10: bench group HCT116'],
        'orion_hek293t': ['this study 2/10: bench group HEK293T'],
        'kolf21j': ['this study 2/10: bench group iPSC'],
        'hipsci_targeted_19': ['this study 2/10: bench group iPSC'],
        'gara_ABC': ['t29 scored 1/10 (CP-0055)'],
        'h1_vcc2025': ['train/val in r1-r3 training; r2 T diagnostics read 17 H1 groups (lead audit 1/10 §3.1); '
                       'the 2025 test split was never downloaded nor read'],
    }
    datasets = []
    for d in registry['dataset']:
        d = dict(d)
        d['letture_dopo_30_09'] = added.get(d['id'], [])
        datasets.append(d)
    write_json(a.out / 'reserve_manifest.json', dict(
        written_utc=now_utc(), base=dict(path='reports/modelli/risposta_biologica_2026-09-30/holdout_registry.json',
                                         sha256=sha256(REPO / 'reports/modelli/risposta_biologica_2026-09-30/holdout_registry.json')),
        rule=registry['regola_riserva'],
        datasets=datasets, not_local=NOT_LOCAL,
        status=('No line on this machine is an intact reserve for C/J: every bench group has had outcome readings. '
                'The bench is development; a confirmation (P5) needs a line never read, appropriate to the regime.'),
        candidates_for_p5=[
            dict(id='tian2019_neurons', why='CRISPRi in iPSC-derived neurons, a cell type absent from the bench; '
                 'outcomes never read (in r3 training only)', needs='its effect table (Kaggle rlab-tian-norman or '
                 'Drive shards) and a target-overlap check with the bench sources before opening'),
            dict(id='h1_vcc2025_test', why='a line absent from this bench, competition assay; outcomes never read',
                 needs='closed by D-052/R-LEAD during development; download of the test split authorised by the owner, '
                 'and C/J classes recomputed against this bench'),
            dict(id='jurkat_gse249595', why='Jurkat outcomes of this study never read',
                 needs='a proven guide assignment (multi-guide, high MOI); Jurkat Nadig readings in r2 make the line '
                 'not new for r2, but this bench never used Jurkat'),
        ],
        seconds=timer()))
    log(f'done in {timer()} s')


if __name__ == '__main__':
    main()
