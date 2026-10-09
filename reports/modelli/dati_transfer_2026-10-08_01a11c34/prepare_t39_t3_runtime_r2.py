"""Build the exact T39 CPU runtime locally; draft has no working upload capability."""
import argparse
import ast
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile
from percorso import HERE, DATA, ROOT, read, pin, sha, write_new, now
from prepare_extended_generation import unpack

FOLDER = HERE / 't39_t3/r2'
PRIVATE = DATA / 'processed/dati_transfer_2026-10-08_01a11c34/t39_t3/r2'
SLUG = 'davideferrante11/dt-t39-t3-e2-upload-01a11c34-r1'
PREDICTION = ROOT / 'reports/invii/prediction_t39_t3_2026-10-10/prediction.json'
TRIAL = ROOT / 'reports/invii/trial_2026-10-10'


def prepare(draft=True):
    proof = read(HERE / 't39_t3_effect_verified_r1.json')
    candidate = proof['candidate']
    if not proof['status'].startswith('PASS') or sha(candidate['path']) != candidate['sha256']:
        raise ValueError('candidate verification differs')
    prediction_path=PREDICTION
    prediction = read(prediction_path)
    artifact_pin_path=PREDICTION.with_name('artifact_pin_r1.json')
    artifact_pin=read(artifact_pin_path)
    final_pin=artifact_pin['received_final_artifact']
    if any(final_pin[k]!=candidate[k] for k in ('path','bytes','sha256')):
        raise ValueError('companion artifact pin differs')
    if (artifact_pin['supplements_immutable_prediction']!=PREDICTION.relative_to(ROOT).as_posix()
            or not artifact_pin['artifact_gate_satisfied_by_receipt']
            or artifact_pin['frozen_formula_or_scientific_rule_changed']
            or prediction['candidate']!='t39-T3-ESM2-fallback'
            or prediction['reference']['name']!='t38'):
        raise ValueError('preregistration and companion are not linked')
    if sha(ROOT/final_pin['receipt'])!=sha(HERE/'t39_t3_effect_verified_r1.json'):
        raise ValueError('companion verification receipt differs')
    g=prediction['generator']
    expected=dict(generator_seed=20260912,effects_scale=1.5,gene_dispersion=True,
        gene_dispersion_scale=1.0,depth_bins=False,contexts=['A','B','C'],
        targets_per_context=300,cells_per_target=400,response_genes=18533)
    if any(g[k]!=v for k,v in expected.items()):raise ValueError('frozen emitter differs')
    texts_path=TRIAL/'submission_texts_t39_t3_r1.md'
    texts=texts_path.read_text(encoding='utf-8')
    model=texts.split('**Nome:**',1)[1].split('\n',1)[0].strip()
    description=' '.join(texts.split('**Descrizione:**',1)[1].split('**Previsione e regola:**',1)[0].split())
    if not model or not description:raise ValueError('exact submission text missing')
    original = ROOT / 'reports/modelli/percorso_riusabile_2026-10-05/generation_successors_r1/package/run.py'
    if sha(original) != '4a49bc7880dc9b877d71a9dd3b3bfc01ea4e584214ea0355fc98fd3c1293b021':
        raise ValueError('frozen generator bundle differs')
    members, old = unpack(original)
    members['emission_support.py'] = members.pop('driver.py')
    members['driver.py'] = (HERE / 'generate_upload_t39_t3_r1.py').read_bytes()
    members['quick_generation_driver.py'] = (HERE / 'quick_generation_driver.py').read_bytes()
    members['prediction_registered.json'] = prediction_path.read_bytes()
    members['artifact_pin_registered.json'] = artifact_pin_path.read_bytes()
    members['submission_texts_registered.md'] = texts_path.read_bytes()
    # Already-tested lossless intermediate storage change; emission math unchanged.
    name = 'repo/src/vcc2026/submission.py'
    s = members[name].decode()
    assert s.count('compression: str | None = "gzip",') == 1
    assert s.count('compression_opts: int | None = 4,') == 1
    members[name] = s.replace('compression: str | None = "gzip",', 'compression: str | None = "lzf",').replace('compression_opts: int | None = 4,', 'compression_opts: int | None = None,').encode()
    if draft:
        cap = dict(entry_id='DRAFT_NOT_CREATED', upload_url='https://storage.googleapis.com/DRAFT_NOT_VALID')
    else:
        consent = read(HERE / 't39_t3_private_egress_authorized_r1.json')
        if not (consent['original_human_response_read_directly'] and consent['authorized']
                and consent['candidate_sha256'] == candidate['sha256'] and consent['destination_job'] == SLUG):
            raise ValueError('specific egress consent absent')
        created = read(PRIVATE / 'created_private.json')
        cap = {k: created[k] for k in ('entry_id', 'upload_url')}
    members['delivery_capability.json'] = (json.dumps(cap) + '\n').encode()
    members.pop('params.json')
    params = dict(job_id=SLUG.split('/')[1], product='prediction_t39_T3_E2.vcc',
        protocol=pin(HERE / 't39_t3_effect_verified_r1.json'), prediction=pin(prediction_path),
        fit_receipt=pin(HERE / 't39_t3_effect_verified_r1.json'),
        artifact_pin=pin(artifact_pin_path),submission_texts=pin(texts_path),
        source_job='existing_frozen_T3_E2_export_no_new_fit',
        effects={c: candidate for c in 'ABC'}, controls=old['controls'], axis=old['axis'],
        emission=prediction['generator'], no_new_fit=True,
        incident_ids=['E-20260929-003','E-20260929-004','E-20260929-005'],
        embedded_sha256={n:hashlib.sha256(b).hexdigest() for n,b in members.items()})
    members['params.json'] = (json.dumps(params, indent=1) + '\n').encode()
    for n,b in members.items():
        p=PurePosixPath(n)
        if p.is_absolute() or '..' in p.parts or '\\' in n:
            raise ValueError('unsafe bundle path')
        if n.endswith('.py'):
            ast.parse(b, filename=n)
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,b in sorted(members.items()):z.writestr(n,b)
    payload=base64.b64encode(buf.getvalue()).decode()
    code='import os,sys,base64,io,zipfile,hashlib,runpy\nfrom pathlib import Path,PurePosixPath\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\n'
    code+='archive=base64.b64decode('+repr(payload)+')\nassert hashlib.sha256(archive).hexdigest()=='+repr(hashlib.sha256(buf.getvalue()).hexdigest())+'\n'
    code+='with zipfile.ZipFile(io.BytesIO(archive)) as z:\n for n in z.namelist():\n  p=PurePosixPath(n);assert not p.is_absolute() and ".." not in p.parts and chr(92) not in n;q=Path(n);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(z.read(n))\n'
    code+='import subprocess,importlib.metadata as md\ncore={n:md.version(n) for n in ("numpy","scipy","pandas","h5py")}\nPath("core_constraints.txt").write_text("".join(n+"=="+v+"\\n" for n,v in core.items()))\n'
    code+='subprocess.check_call([sys.executable,"-m","pip","install","--disable-pip-version-check","--constraint","core_constraints.txt","anndata==0.13.3.post0","zstandard==0.25.0","httpx==0.28.1"])\nassert {n:md.version(n) for n in core}==core\nrunpy.run_path("driver.py",run_name="__main__")\n'
    ast.parse(code)
    if len(code.encode())>900000:raise ValueError('provider source limit')
    stage=PRIVATE/('draft' if draft else 'package');stage.mkdir(parents=True,exist_ok=False)
    (stage/'run.py').write_text(code,encoding='utf-8',newline='\n')
    (stage/'extended_params.json').write_bytes(members['params.json'])
    write_new(stage/'kernel-metadata.json',dict(id=SLUG,title=SLUG.split('/')[1],code_file='run.py',language='python',
        kernel_type='script',is_private=True,enable_internet=True,enable_gpu=False,enable_tpu=False,
        dataset_sources=['davideferrante11/vcc-official-controls-r1','davideferrante11/dt-t39-t3-e2-effects-01a11c34-r1'],
        kernel_sources=[],competition_sources=[]))
    report=dict(utc=now(),slug=SLUG,owner='davideferrante11',stage=str(stage),draft=draft,
        code=pin(stage/'run.py'),params=pin(stage/'extended_params.json'),metadata=pin(stage/'kernel-metadata.json'),
        prediction=pin(prediction_path),artifact_pin=pin(artifact_pin_path),submission_texts=pin(texts_path),
        model_name=model,description=description,candidate=candidate,entry_id=cap['entry_id'],
        VCC_account_token_transferred=False,new_fit=False,source_frozen_bundle=pin(original),
        package_disk='TEMP for intermediate and archive; WORKING retains final archive and receipts',
        cloud_jobs_launched=0)
    write_new(FOLDER/('draft_prepared.json' if draft else 'prepared.json'),report)
    print(json.dumps(dict(draft=draft,slug=SLUG,source_bytes=len(code.encode()),entry_id=cap['entry_id'])))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--bind-authorized-capability',action='store_true');a=p.parse_args()
    prepare(not a.bind_authorized_capability)
