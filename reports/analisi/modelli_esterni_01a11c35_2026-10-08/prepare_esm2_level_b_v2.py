"""Build executable CPU templates for the four-arm level B; never issue URLs or launch.

The original scorer/generator snapshot is reused byte-for-byte. Templates refuse
execution without the separately approved, exact private export transport bundle.
"""
import ast
import base64
import hashlib
import io
import json
from pathlib import Path
import zipfile
from bank_input_bridge_v1 import digest
from ammi_io_v4 import write

HERE=Path(__file__).resolve().parent
VALID=HERE.parent/'validazione_indipendente_8a8ca58a_2026-10-08'
NEW_VALID=HERE.parent/'validazione_banco_eace4d03_2026-10-09'


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def constants(source):
    result={}
    for node in ast.parse(source).body:
        if not isinstance(node,ast.Assign) or not isinstance(node.targets[0],ast.Name):continue
        name=node.targets[0].id
        if name=='SNAPSHOT':result[name]=ast.literal_eval(node.value)
        if name=='P':result[name]=json.loads(ast.literal_eval(node.value.args[0]))
    if set(result)!={'P','SNAPSHOT'}:raise ValueError('original kernel constants not found')
    return result


def main():
    root=HERE/'esm2_level_b_templates_r2'
    if root.exists():raise FileExistsError(root)
    delivery=read(HERE/'esm2_closure_bank_prepared_r1.json')
    files=[]
    for fold in ('C-K562','C-iPSC'):
        for label in ('E2','E2g','E2f'):
            name=fold+'_'+label+'.npz'
            files.append(dict(fold=fold,label=label,source=delivery['dataset'],file=name,
                destination='davidmaisterx',**delivery['files'][name]))
    transport=dict(status='PROPOSED_NOT_AUTHORIZED_NOT_TRANSFERRED',source_account='davideferrante11',
        destination_account='davidmaisterx',files=files,total_bytes=sum(f['bytes'] for f in files),
        reason='four arms per independent protocol v3: delivered fallback plus native/generic predictions for matched-mask controls',
        original_two_file_plan='esm2_validation_access_plan_r1.json: two-arm plan; superseded for proposed four-arm B',
        truth_or_NTC_or_checkpoint_transfer=False,cloud_only=True,private_only=True,
        URLs_issued=0,cloud_jobs_launched=0,executor_confirmation_pending=True)
    plan_path=HERE/'esm2_level_b_transport_plan_r2.json';write(plan_path,transport)
    transport_sha=digest(plan_path);root.mkdir()
    outputs=[]
    for line,fold in [('k562','C-K562'),('ipsc','C-iPSC')]:
        original=VALID/'banco'/('livello_b_'+line+'_r1')
        proof=read(original/'prepared.json');source=(original/'package/run.py').read_text(encoding='utf-8')
        if digest(original/'package/run.py')!=proof['code']['sha256']:raise ValueError('original kernel differs')
        values=constants(source);p=values['P'];snapshot=base64.b64decode(values['SNAPSHOT'])
        if hashlib.sha256(snapshot).hexdigest()!=p['snapshot_sha256']:raise ValueError('snapshot differs')
        with zipfile.ZipFile(io.BytesIO(snapshot)) as archive:
            if hashlib.sha256(archive.read('bench_v2.py')).hexdigest()!=p['bench_sha256']:
                raise ValueError('original bench differs inside snapshot')
        p.update(private_exports=[f for f in files if f['fold']==fold],transport_plan_sha256=transport_sha,
            reference_sha256=p['arms_sha256']['T0'],steps=[
                dict(name='control',targets='all',arms=['T0','T0shuffle'],pairs=['T0:T0shuffle'],gen_seeds=1),
                *[dict(name=name,targets=targets,arms=['T0','E2f','Generic','Swapped'],
                    pairs=['E2f:T0','Generic:T0','Swapped:T0','E2f:Generic','E2f:Swapped'],gen_seeds=5)
                    for name,targets in [('changed','changed'),('full','all')]]])
        # Reuse original orchestration after its literal configuration, not current repository modules.
        tree=ast.parse(source);assign=next(n for n in tree.body if isinstance(n,ast.Assign)
            and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='SNAPSHOT')
        body='\n'.join(source.splitlines()[assign.end_lineno:])+'\n'
        old='REAL, EFF = mount(P["real_kernel"]), mount(P["effects_dataset"])'
        if body.count(old)!=1:raise ValueError('original mount glue changed')
        body=body.replace(old,'''REAL = mount(P["real_kernel"])
from esm2_four_arms_v1 import materialize
EFF = OUT / "four_arms"
P["arms_sha256"], P["changed_targets"] = materialize(mount(P["effects_dataset"]), P, bundle, EFF)''',1)
        members={name:(HERE/name).read_bytes() for name in ('esm2_four_arms_v1.py','bank_input_bridge_v1.py')}
        members['metrics.py']=(VALID/'banco/metrics.py').read_bytes()
        buff=io.BytesIO()
        with zipfile.ZipFile(buff,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,content in members.items():archive.writestr(name,content)
        packed=buff.getvalue();bundle_hash=hashlib.sha256(packed).hexdigest()
        # Private files are inserted only after explicit approval; neither file exists in this template.
        header='''import base64, hashlib, io, json, os, subprocess, sys, time, zipfile, shutil
from pathlib import Path
P = json.loads(PARAMS_JSON)
SNAPSHOT = SNAPSHOT_B64
INPUT, OUT = Path("/kaggle/input"), Path("/kaggle/working")
bundle = Path("/kaggle/temp/esm2-level-b-runtime")
bundle.mkdir(parents=True, exist_ok=False)
raw_bundle = base64.b64decode(BUNDLE_B64)
assert hashlib.sha256(raw_bundle).hexdigest() == BUNDLE_SHA
with zipfile.ZipFile(io.BytesIO(raw_bundle)) as archive:
    assert all(not Path(n).is_absolute() and ".." not in Path(n).parts for n in archive.namelist())
    archive.extractall(bundle)
if not all((bundle/n).is_file() for n in ("transport_authorization.json", "private_locators.json")):
    raise SystemExit("private export authorization bundle absent; template cannot run")
sys.path.insert(0, str(bundle))
from bank_input_bridge_v1 import transport_gate
transport_gate(P["transport_plan_sha256"], P["private_exports"],
    json.loads((bundle/"transport_authorization.json").read_text()),
    json.loads((bundle/"private_locators.json").read_text()))
memory = {line.split(":",1)[0]:line.split(":",1)[1].strip() for line in Path("/proc/meminfo").read_text().splitlines()}
(OUT/"cpu_preflight.json").write_text(json.dumps({"cpu_count":os.cpu_count(),"available_RAM":memory.get("MemAvailable"),
    "free_disk":shutil.disk_usage("/kaggle/working").free,"compute":"CPU only; no training"}, indent=2))
'''
        code='\n'.join(k+'='+repr(v) for k,v in dict(PARAMS_JSON=json.dumps(p),SNAPSHOT_B64=values['SNAPSHOT'],
            BUNDLE_B64=base64.b64encode(packed).decode(),BUNDLE_SHA=bundle_hash).items())+'\n'+header+body
        compile(code,'run.py','exec')
        stage=root/line;stage.mkdir();(stage/'run.py').write_text(code,encoding='utf-8',newline='\n')
        meta=read(original/'package/kernel-metadata.json')
        slug='davidmaisterx/esm2-fallback-b-'+line+'-01a11c35-r2'
        meta.update(id=slug,title=slug.split('/')[1],is_private=True,enable_gpu=False)
        write(stage/'kernel-metadata.json',meta)
        item=dict(slug=slug,stage=str(stage),code=dict(path=str(stage/'run.py'),bytes=(stage/'run.py').stat().st_size,sha256=digest(stage/'run.py')),
            metadata=dict(path=str(stage/'kernel-metadata.json'),sha256=digest(stage/'kernel-metadata.json')),
            original_snapshot_sha256=p['snapshot_sha256'],original_bench_sha256=p['bench_sha256'],
            scorer_version=p['scorer_version'],transport_plan_sha256=transport_sha,
            executable_template=True,approval_bundle_present=False,launchable=False,
            no_training=True,private=True,cloud_jobs_launched=0,executor_confirmation_pending=True,
            pending='agree single executor, exact transfer approval, insert authorized locators, final code pin and fresh preflight')
        write(stage/'prepared.json',item);outputs.append(item)
    write(HERE/'esm2_level_b_templates_prepared_r2.json',dict(jobs=outputs,transport_plan=str(plan_path),
        unchanged_scorer_generator_snapshot=True,private_transfer_bytes=transport['total_bytes'],
        input_adapter_tests='esm2_four_arms_tests_r1.txt',support_audit_owner='VALIDAZIONE, already COMPLETE; not repeated'))
    print(json.dumps(dict(jobs=len(outputs),private_export_files=len(files),private_export_bytes=transport['total_bytes'],launched=False)))


if __name__=='__main__':main()
