"""The ESM2 + ridge predictions of the T view (MODELLI-ESTERNI), read-only: technical examination, conversion to
the stage-100 interface of the bench, one private dataset.

    prepara_esm2_t.py esamina <revision>                 structure, identity and scale of the native predictions
    prepara_esm2_t.py converti <revision>                the arms E2, E2g, E2c as stage-100 files in the data root
    prepara_esm2_t.py dataset-create <revision>
    prepara_esm2_t.py dataset-status <revision> <out.json>

The native file belongs to MODELLI-ESTERNI (session 01a11c35) and is never changed. It holds one row per query
(66 hidden panel targets x the training contexts) of a target-only model: the same target must get the same
effect in every context. The bench reads one row per target. No truth is read here.

Arms written by `converti` (rows of the 66 hidden targets only, the other panel rows are not predicted):
  E2   the native prediction, natural-log fold change, no amplitude and no cis head
  E2g  the generic part alone: one row, the same for every target (what a target-blind model would say)
  E2c  how it would enter the transfer: amplitude x E2, with the transfer's cis head where the transfer predicts
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prepara_banco as B  # noqa: E402

NATIVE = Path('C:/Users/ferra/vcc2026-data/external_models/01a11c35/verified_cloud_outputs/'
              'esm2-t-01a11c35-r3/esm2-t-01a11c35-r3/fit/native_predictions.npz')
RECEIPT = B.REPO / ('reports/analisi/modelli_esterni_01a11c35_2026-10-08/'
                    'esm2-t-01a11c35-r3.verified_terminal_collection_r1.json')
MANIFEST = HERE.parent / 'manifest_fold_v2.json'
CONTROLS = Path('C:/Users/ferra/vcc2026-data/raw/controls')
DATA = Path('C:/Users/ferra/vcc2026-data/processed/validazione_indipendente_8a8ca58a_2026-10-08')
CIS_KERNEL = 'davideferrante11/vcc-validazione-logo-8a8ca58a-r4'       # its J folds hold the cis head alone
CIS_FOLDS = ('J-K562', 'J-CD4T')
T1_PROD = HERE / 'r5/completion_extra/stage100_manifests/T1__PROD.json'  # carries the amplitude of the transfer
TOLERANCE = 1e-12        # revision r1 asked exact equality across contexts and met a rounding of 2.2e-16


def folder(revision):
    return HERE / ('esm2_t_%s' % revision)


def first_column(path):
    return [line.split(',')[0] for line in Path(path).read_text(encoding='utf-8').splitlines()[1:] if line.strip()]


def small(name):
    with np.load(NATIVE, allow_pickle=False) as z:
        return z[name]


def stream_rows(name):
    """Rows of a 2-D member of the native file, one at a time: the arrays do not fit this laptop's free memory."""
    with zipfile.ZipFile(NATIVE) as z, z.open(name + '.npy') as f:
        version = np.lib.format.read_magic(f)
        read = np.lib.format.read_array_header_1_0 if version == (1, 0) else np.lib.format.read_array_header_2_0
        shape, fortran, dtype = read(f)
        assert not fortran and len(shape) == 2
        size = dtype.itemsize * shape[1]
        for i in range(shape[0]):
            yield i, np.frombuffer(f.read(size), dtype=dtype)


def one_row_per_target(name, targets):
    """First row of every target and the largest absolute difference of its later rows from it."""
    first, gap = {}, {}
    for i, row in stream_rows(name):
        t = targets[i]
        if t not in first:
            first[t], gap[t] = row.copy(), 0.0
        elif row.dtype == bool:
            gap[t] = max(gap[t], float((row != first[t]).sum()))
        else:
            gap[t] = max(gap[t], float(np.nanmax(np.abs(row - first[t]))))
    return first, gap


def union_per_target(name, targets):
    seen, per_context = {}, {}
    contexts = [str(c) for c in small('context_ids')]
    for i, row in stream_rows(name):
        t = targets[i]
        seen[t] = row.copy() if t not in seen else (seen[t] | row)
        per_context[contexts[i]] = per_context.get(contexts[i], 0) + int(row.sum())
    return seen, per_context


def esamina(revision):
    here = folder(revision)
    here.mkdir(exist_ok=False)
    receipt = B.read(RECEIPT)
    got = B.pin(NATIVE)
    targets = [str(t) for t in small('targets')]
    genes = [str(g) for g in small('genes')]
    contexts = [str(c) for c in small('context_ids')]
    groups = [str(c) for c in small('context_groups')]
    manifest = B.read(MANIFEST)
    hidden = sorted(manifest['panel_hidden_groups'][str(manifest['hidden_target_rule']['test_group'])])
    axis = first_column(CONTROLS / 'gene_names.csv')
    effects, gap = one_row_per_target('effects', targets)
    generic, generic_gap = one_row_per_target('generic', targets)
    observed, per_context = union_per_target('observed', targets)
    support, _ = one_row_per_target('generic_observed', targets)
    names = sorted(effects)
    e = np.stack([effects[t] for t in names])
    g = np.stack([generic[t] for t in names])
    o = np.stack([observed[t] for t in names])
    spec = np.where(o, e - g, 0.0)
    full = np.where(o, e, 0.0)
    corr_full = np.corrcoef(full)
    corr_spec = np.corrcoef(spec)
    off = ~np.eye(len(names), dtype=bool)
    report = dict(
        utc=B.now(), native=dict(got, path=NATIVE.as_posix()), owner='MODELLI-ESTERNI, session 01a11c35',
        sha256_equal_to_their_receipt=got['sha256'] == receipt['predictions_sha256'],
        rows=len(targets), contexts=len(set(contexts)), lineages=sorted(set(groups)),
        genes_equal_official_axis=genes == axis, targets=len(names),
        targets_equal_hidden_group_of_the_manifest=names == hidden,
        rows_per_target=sorted(set(targets.count(t) for t in names)),
        esm2_available_for_every_query=bool(small('esm2_observed').all()),
        all_finite_where_observed=bool(np.isfinite(e[o]).all()),
        target_only=dict(largest_difference_of_a_target_across_contexts=max(gap.values()),
                         largest_difference_of_the_generic_across_rows=max(generic_gap.values()),
                         generic_identical_for_every_target=bool(np.abs(g - g[0]).max() == 0.0)),
        coverage=dict(genes_predicted_per_target_median=float(np.median(o.sum(axis=1))),
                      genes_in_the_model_support=int(next(iter(support.values())).sum()),
                      observed_pairs_per_context_min=min(per_context.values()),
                      observed_pairs_per_context_max=max(per_context.values())),
        scale=dict(abs_effect_median=float(np.median(np.abs(e[o]))), abs_effect_p95=float(np.quantile(np.abs(e[o]), 0.95)),
                   abs_effect_max=float(np.abs(e[o]).max()), row_norm_median=float(np.median(np.linalg.norm(full, axis=1))),
                   generic_norm=float(np.linalg.norm(np.where(o[0], g[0], 0.0))),
                   specific_share_of_the_norm=dict(
                       median=float(np.median(np.linalg.norm(spec, axis=1) / np.linalg.norm(full, axis=1))),
                       min=float((np.linalg.norm(spec, axis=1) / np.linalg.norm(full, axis=1)).min()),
                       max=float((np.linalg.norm(spec, axis=1) / np.linalg.norm(full, axis=1)).max()))),
        similarity_between_targets=dict(full_rows_mean_correlation=float(corr_full[off].mean()),
                                        specific_parts_mean_correlation=float(corr_spec[off].mean())),
        no_truth_read=True)
    report['usable'] = bool(report['sha256_equal_to_their_receipt'] and report['genes_equal_official_axis']
                            and report['targets_equal_hidden_group_of_the_manifest']
                            and report['all_finite_where_observed']
                            and report['target_only']['largest_difference_of_a_target_across_contexts'] <= TOLERANCE)
    report['tolerance_for_target_only'] = TOLERANCE
    B.write_new(here / 'esame.json', report)
    print(json.dumps({k: v for k, v in report.items() if k not in ('native',)}, indent=1))


def converti(revision):
    here = folder(revision)
    exam = B.read(here / 'esame.json')
    if not exam['usable']:
        raise ValueError('the native predictions did not pass the examination')
    stage = DATA / ('esm2_t_%s' % revision)
    stage.mkdir(parents=True, exist_ok=False)
    panel = first_column(CONTROLS / 'pert_counts.csv')
    axis = first_column(CONTROLS / 'gene_names.csv')
    targets = [str(t) for t in small('targets')]
    effects, _ = one_row_per_target('effects', targets)
    generic, _ = one_row_per_target('generic', targets)
    observed, _ = union_per_target('observed', targets)
    support, _ = one_row_per_target('generic_observed', targets)
    # the cis head of the transfer on the hidden targets: the J folds of run r4, where nothing else is predicted
    cis_dir = stage / 'cis'
    pattern = '|'.join('effects/T0__%s.npz' % f for f in CIS_FOLDS)
    rc, answer = B.call(B.OWNER, ['kernels', 'output', CIS_KERNEL, '-p', str(cis_dir), '--file-pattern', pattern])
    for p in list(cis_dir.rglob('*.log')):
        p.unlink()
    cis = {}
    for f in CIS_FOLDS:
        with np.load(next(cis_dir.rglob('T0__%s.npz' % f)), allow_pickle=False) as z:
            assert [str(t) for t in z['targets']] == panel and [str(g) for g in z['genes']] == axis
            cis[f] = (z['lfc'].astype(np.float32), z['observed'].astype(bool))
    amplitude = float(B.read(T1_PROD)['contexts']['PROD']['amplitude'])
    position = {t: i for i, t in enumerate(panel)}
    rows = sorted(position[t] for t in effects)
    same_cis = bool(np.array_equal(cis[CIS_FOLDS[0]][0][rows], cis[CIS_FOLDS[1]][0][rows])
                    and np.array_equal(cis[CIS_FOLDS[0]][1][rows], cis[CIS_FOLDS[1]][1][rows]))
    cis_lfc, cis_obs = cis[CIS_FOLDS[0]]
    arms = {name: (np.zeros((len(panel), len(axis)), np.float32), np.zeros((len(panel), len(axis)), bool))
            for name in ('E2', 'E2g', 'E2c')}
    for t, row in effects.items():
        i, seen = position[t], observed[t]
        arms['E2'][0][i], arms['E2'][1][i] = np.where(seen, row, 0.0), seen
        arms['E2g'][0][i], arms['E2g'][1][i] = np.where(support[t], generic[t], 0.0), support[t]
        combined = np.where(seen, amplitude * row, 0.0).astype(np.float32)
        combined[cis_obs[i]] = cis_lfc[i][cis_obs[i]]
        arms['E2c'][0][i], arms['E2c'][1][i] = combined, seen | cis_obs[i]
    files = {}
    for name, (lfc, obs) in arms.items():
        dest = stage / (name + '.npz')
        np.savez_compressed(dest, targets=np.array(panel), genes=np.array(axis), lfc=lfc, observed=obs)
        files[name] = B.pin(dest)
    shutil.rmtree(cis_dir)
    B.write_new(here / 'conversione.json', dict(
        utc=B.now(), stage=stage.as_posix(), native=exam['native'], files=files, amplitude=amplitude,
        cis_head_from=dict(kernel=CIS_KERNEL, folds=list(CIS_FOLDS), retrieval_returncode=rc,
                           identical_on_the_hidden_rows_in_both_folds=same_cis,
                           pairs_per_hidden_target_median=float(np.median(cis_obs[rows].sum(axis=1)))),
        rows_predicted=len(rows), not_production=True,
        arms=dict(E2='native prediction, ln fold change, no amplitude, no cis head',
                  E2g='generic part alone, the same row for every target',
                  E2c='amplitude x E2, with the cis head of the transfer where the transfer predicts')))
    print(json.dumps(dict(files={k: v['bytes'] for k, v in files.items()}, same_cis=same_cis, amplitude=amplitude,
                          cis_pairs_median=float(np.median(cis_obs[rows].sum(axis=1))))))


def dataset_create(revision):
    from pipeline_state import CONFIG
    here = folder(revision)
    record = B.read(here / 'conversione.json')
    stage = Path(record['stage'])
    dataset = '%s/vcc-validazione-esm2-t-%s-%s' % (B.OWNER, B.SESSION, revision)
    (stage / 'dataset-metadata.json').write_text(json.dumps(dict(
        title=dataset.split('/')[1], id=dataset, licenses=[dict(name='other')]), indent=1) + '\n')
    (stage / 'README.json').write_text(json.dumps(dict(
        what='ESM2 + ridge predictions of the T view (MODELLI-ESTERNI, session 01a11c35) for the 66 hidden panel '
             'targets, converted to the stage-100 interface for the independent bench; not a production artefact',
        files=record['files'], arms=record['arms']), indent=1) + '\n')
    env = {k: v for k, v in os.environ.items()
           if k not in ('KAGGLE_CONFIG_DIR', 'KAGGLE_USERNAME', 'KAGGLE_KEY', 'KAGGLE_API_TOKEN')}
    env['KAGGLE_CONFIG_DIR'] = str(Path.home() / CONFIG[B.OWNER])
    run = subprocess.run([str(Path(sys.executable).with_name('kaggle.exe')), 'datasets', 'create', '-p', str(stage)],
                         env=env, capture_output=True, encoding='utf-8', errors='replace', timeout=1800)
    B.write_new(here / 'dataset_create.json', dict(
        utc=B.now(), dataset=dataset, private=True, files=record['files'], returncode=run.returncode,
        answer=(run.stdout + run.stderr)[-600:],
        authorization='standing owner authorization for Colab and Kaggle (27 September 2026); a private dataset of '
                      'three small arrays derived from predictions already produced; nothing paid'))
    print(json.dumps(dict(dataset=dataset, returncode=run.returncode)))


def dataset_status(revision, out):
    record = B.read(folder(revision) / 'dataset_create.json')
    rc, status = B.call(B.OWNER, ['datasets', 'status', record['dataset']])
    rc2, listing = B.call(B.OWNER, ['datasets', 'files', record['dataset'], '--csv', '--page-size', '50'])
    listed = {l.split(',')[0]: l.split(',')[1] for l in listing.splitlines()[1:] if l.strip()}
    B.write_new(out, dict(utc=B.now(), dataset=record['dataset'], status=status, files=listed,
                          ready=rc == 0 and rc2 == 0 and status.strip() == 'ready'))
    print(json.dumps(dict(status=status, files=listed)))


if __name__ == '__main__':
    {'esamina': esamina, 'converti': converti, 'dataset-create': dataset_create,
     'dataset-status': dataset_status}[sys.argv[1]](*sys.argv[2:])
