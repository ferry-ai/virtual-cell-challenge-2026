"""Prepare the unchanged independent bank after four complete AMMI metadata receipts.

Primary contexts are fixed before training. A0 is the nested query anchor;
the original bank's T0 is kept and explicitly contrasted separately. No files
are uploaded, no jobs launched and no private access is inferred here.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil

from ammi_inputs_v3 import checked
from pie_adapter import sha256

HERE = Path(__file__).resolve().parent
VALID = HERE.parent/'validazione_indipendente_8a8ca58a_2026-10-08/banco'
PRIMARY = {'C-K562': 'k562_gwps:48d8d89e89785608',
           'C-iPSC': 'kolf_pan_genome:1e7354e259028404'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def plan(receipts):
    fits = {}; sources = set(); external = {}; routes = {}
    for path in receipts:
        report = read(path)
        if report['status'] != 'METADATA_PASS_BINARY_HASH_AND_READOUT_PENDING':
            raise ValueError('four metadata-passing fits required')
        complete = read(checked(report['files']['complete.json']))
        key = complete['fold'], complete['mode']
        if key in fits or key[0] not in PRIMARY or key[1] not in ('cells', 'none') or complete['seed'] != 17:
            raise ValueError('duplicate or undeclared fit')
        fits[key] = report
        sources.add(report['slug'])
    if set(fits) != {(f, m) for f in PRIMARY for m in ('cells', 'none')}:
        raise ValueError('both cells and none required on both folds')
    for fold, primary in PRIMARY.items():
        anchors = []
        for mode in ('cells', 'none'):
            report = fits[fold, mode]
            anchors.append(read(checked(report['files']['zero_residual_parity.receipt.json'])))
            exports = report['verification']['exports']
            for entry in exports:
                context = entry['context_id']
                is_primary = context == primary
                base = 'Acells' if mode == 'cells' else 'Anone'
                label = base if is_primary else base+'ctx'+__import__('hashlib').sha256(context.encode()).hexdigest()[:12]
                if entry['intervention'] == 'swapped': label += 'swap'
                external.setdefault(label, {})[fold] = {k: entry[k] for k in ('bytes', 'sha256')}
                routes.setdefault(label, {})[fold] = dict(context_id=context, primary_context=is_primary,
                    source=entry['source'], file=entry['file'], intervention=entry['intervention'])
            if not any(e['context_id'] == primary and e['intervention'] == 'native' for e in exports):
                raise ValueError('predeclared primary context absent')
        if anchors[0]['anchor_sha256'] != anchors[1]['anchor_sha256']:
            raise ValueError('cells and none used different anchors')
        external.setdefault('A0', {})[fold] = dict(bytes=anchors[0]['bytes'], sha256=anchors[0]['output_sha256'])
    contrasts = [['AMMI_cells_minus_anchor', 'Acells', 'A0'],
                 ['AMMI_cells_minus_none', 'Acells', 'Anone'],
                 ['AMMI_cells_minus_swapped', 'Acells', 'Acellsswap'],
                 ['AMMI_cells_minus_original_T0', 'Acells', 'T0'],
                 ['AMMI_anchor_minus_original_T0', 'A0', 'T0'],
                 ['AMMI_shuffle_control', 'Acells', 'Acells~shufflein']]
    return dict(what='Four AMMI fits; unchanged bank and original support; no new fit or tuning',
        external_arms=external, contrasts=contrasts, extra_kernel_sources=sorted(sources),
        context_routes=routes, primary_contexts=PRIMARY,
        anchor_semantics='A0 excludes outer and inner; original T0 excludes outer only; never relabel them',
        replication_policy='one primary context per fold; other contexts descriptive; one seed only',
        readout_status='PACKAGE_PREPARATION_ONLY_ACCESS_AND_REMOTE_CODE_CHECKS_PENDING')


def prepare(receipts, out):
    out = Path(out)
    if out.exists(): raise FileExistsError(out)
    analysis = plan(receipts)
    out.mkdir(parents=True)
    revision = 'ammireadout-r1'
    for name in ('logo_driver.py', 'metrics.py', 'bench_core.py'):
        shutil.copyfile(VALID/name, out/name)
    (out/('analisi_'+revision+'.json')).write_text(json.dumps(analysis, indent=2), encoding='utf-8')
    definition = importlib.util.spec_from_file_location('ammi_frozen_bank_builder', VALID/'prepara_banco.py')
    builder = importlib.util.module_from_spec(definition); definition.loader.exec_module(builder)
    builder.HERE = out; builder.MANIFEST = VALID.parent/'manifest_fold_v2.json'
    builder.OWNER = 'davidmaisterx'; builder.SESSION = '01a11c35'
    builder.package(revision)
    report = dict(status='PREPARED_NOT_AUTHORIZED_BY_THIS_FILE_NOT_LAUNCHED',
        metadata_receipts=[dict(path=str(Path(p)), sha256=sha256(p)) for p in receipts],
        original_bank_code={n:sha256(VALID/n) for n in ('logo_driver.py','metrics.py','bench_core.py')},
        remote_fit_code_verification_pending=True, mount_access_preflight_pending=True,
        output_payload_hashes_verified=False,
        output_payload_hash_policy='verify full size and SHA during bank consumption',
        biological_benefit_measured=False, production_decision_pending=True)
    (out/'readout_preparation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--receipts', nargs=4, required=True)
    parser.add_argument('--out', required=True)
    args=parser.parse_args(); prepare(args.receipts,args.out)
