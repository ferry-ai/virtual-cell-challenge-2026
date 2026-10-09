"""Prepare one private CPU readout with the unchanged independent bank code.

All new outputs belong to MODELLI-ESTERNI, not to the independent reviewer. This
script does not launch a kernel; dataset upload is a separate explicit command.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil

from ammi_inputs_v3 import checked
from pie_adapter import sha256

HERE=Path(__file__).parent.resolve()
VALID=HERE.parent/'validazione_indipendente_8a8ca58a_2026-10-08/banco'


def main(dataset_dir):
    dataset_dir=Path(dataset_dir)
    if dataset_dir.exists():raise FileExistsError(dataset_dir)
    dataset_dir.mkdir(parents=True)
    conversion=json.loads((HERE/'esm2_closure_conversion_r1.json').read_text())
    external={};files={}
    for fold in ('C-K562','C-iPSC','J-iPSC'):
        record=conversion['folds'][fold]
        labels={'E2':record['stage100']['E2'],'E2g':record['stage100']['E2g']}
        if fold.startswith('C-'):labels['E2f']=record['integration']
        for label,pin in labels.items():
            final_label=label if fold.startswith('C-') else label.replace('E2','E2jip')
            dest=dataset_dir/(fold+'_'+label+'.npz')
            shutil.copyfile(checked(pin),dest)
            compact=dict(bytes=dest.stat().st_size,sha256=sha256(dest))
            external.setdefault(final_label,{})[fold]=compact
            files[dest.name]=compact
    # The already-read T fit is the fixed reference for the new J-iPSC contrast.
    t_plan=json.loads((VALID/'analisi_r7.json').read_text())
    external['E2T']={'J-iPSC':t_plan['external_arms']['E2']['J-iPSC']}
    dataset='davideferrante11/vcc-esm2-closure-01a11c35-r1'
    (dataset_dir/'dataset-metadata.json').write_text(json.dumps(dict(id=dataset,
        title='VCC ESM2 closure 01a11c35 r1',licenses=[dict(name='other')]),indent=2))
    plan=dict(what='MODELLI execution of unchanged independent bank; frozen C pairwise T0-priority fallback and J-iPSC readout',
        j_folds=True,external_arms=external,
        contrasts=[['C_integration','E2f','T0'],['C_native','E2','T0'],['C_specific','E2','E2g'],
            ['c_shufflein_E2','E2','E2~shufflein'],['J_specific','E2jip','E2jipg'],
            ['c_shufflein_E2jip','E2jip','E2jip~shufflein'],['J_minus_T','E2jip','E2T'],
            ['J_native','E2jip','T0']],
        extra_dataset_sources=[dataset,'davideferrante11/vcc-validazione-esm2-t-8a8ca58a-r2'])
    bank=HERE/'closure_bank_v1';bank.mkdir(exist_ok=False)
    revision='esm2closure-r1'
    for name in ('logo_driver.py','metrics.py','bench_core.py'):shutil.copyfile(VALID/name,bank/name)
    (bank/('analisi_'+revision+'.json')).write_text(json.dumps(plan,indent=2))
    definition=importlib.util.spec_from_file_location('closure_package_builder',VALID/'prepara_banco.py')
    builder=importlib.util.module_from_spec(definition);definition.loader.exec_module(builder)
    builder.HERE=bank;builder.MANIFEST=VALID.parent/'manifest_fold_v2.json'
    builder.OWNER='davideferrante11';builder.SESSION='01a11c35'
    builder.package(revision)
    receipt=dict(dataset=dataset,private=True,stage=str(dataset_dir),files=files,
        dataset_metadata_sha256=sha256(dataset_dir/'dataset-metadata.json'),
        bank_prepared=str(bank/revision/'prepared.json'),
        scientific_owner='VALIDAZIONE frozen protocol/code',execution_owner='MODELLI-ESTERNI 01a11c35',
        source_code={name:dict(path=str(VALID/name),sha256=sha256(VALID/name)) for name in ('logo_driver.py','metrics.py','bench_core.py')},
        unchanged_source_copies=True,uploaded=False,launched=False,
        metadata_only_or_model_predictions=True,new_RNA_downloaded=False)
    with (HERE/'esm2_closure_bank_prepared_r1.json').open('x',encoding='utf-8') as stream:json.dump(receipt,stream,indent=2)
    print(json.dumps(dict(dataset=dataset,files=len(files),bytes=sum(p['bytes'] for p in files.values()))))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--dataset-dir',required=True)
    a=p.parse_args();main(a.dataset_dir)
