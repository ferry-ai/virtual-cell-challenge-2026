"""Derive a new production-only metadata draft without changing pilot source."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from ammi_inputs_v3 import checked
from build_ammi_runtime_v4 import pin
from continue_ammi_cells_once_v1 import write_new

HERE = Path(__file__).resolve().parent
OUT = Path('C:/Users/ferra/vcc2026-data/external_models/01a11c35/ammi_cloud/production-cells-cache-draft-r1')


def adapted_runner(source):
    replacements = [
        ('from ammi_controls_v4 import stage_controls, resources_required, available_memory',
         'from ammi_controls_v4 import resources_required, available_memory\nfrom ammi_normalized_cache_v1 import stage_controls_cached as stage_controls'),
        ("    production=spec.get('mode')=='production'",
         "    production=spec.get('mode')=='production'\n    if not production: raise ValueError('cached runtime is production-only')"),
        ("'pie_adapter.py','ammi_timing_v1.py')", "'pie_adapter.py','ammi_timing_v1.py','ammi_normalized_cache_v1.py')"),
        ("        write(out/'training_receipt.json',receipt)",
         "        receipt['normalization_cache_after_fit']=controls.cache.stats()\n        write(out/'training_receipt.json',receipt)"),
        ("        write(out/'complete.json',dict(status='COMPLETE'",
         "        write(out/'normalization_cache_final.json',controls.cache.stats())\n        write(out/'complete.json',dict(status='COMPLETE'")]
    for old,new in replacements:
        if source.count(old)!=1: raise ValueError('runner adaptation point changed')
        source=source.replace(old,new)
    compile(source,'run_ammi_v4.py','exec')
    return source


def main():
    verified = json.loads((HERE/'ammi_normalized_cache_verified_r1.json').read_text())
    if verified['status']!='PASS' or verified['tests']!=3: raise ValueError('cache parity required')
    for name,digest in verified['code'].items():
        if pin(HERE/name)['sha256']!=digest: raise ValueError('tested cache code changed')
    old = json.loads((HERE/'ammi_production_draft_prepared_r1.json').read_text())
    source = checked(old['runtime_template']).parent
    spec = json.loads((source/'runtime_template.json').read_text())
    for name,digest in spec['code'].items():
        if pin(source/name)['sha256']!=digest: raise ValueError('original runtime changed')
    if OUT.exists(): raise FileExistsError(OUT)
    source_files = {str(p.relative_to(source)):pin(p) for p in source.rglob('*') if p.is_file()}
    OUT.mkdir(parents=True)
    for name,original in source_files.items():
        if name in ('runtime_template.json','prepared.json','run_ammi_v4.py'): continue
        dest=OUT/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(checked(original),dest)
    (OUT/'run_ammi_v4.py').write_text(adapted_runner((source/'run_ammi_v4.py').read_text()),encoding='utf-8')
    shutil.copyfile(HERE/'ammi_normalized_cache_v1.py',OUT/'ammi_normalized_cache_v1.py')
    for name in ('run_ammi_v4.py','ammi_normalized_cache_v1.py'): spec['code'][name]=pin(OUT/name)['sha256']
    write_new(OUT/'runtime_template.json',spec)
    prepared=json.loads((source/'prepared.json').read_text())
    prepared.update(template=pin(OUT/'runtime_template.json'),code=spec['code'],
        embedded={p.name:pin(p) for p in (OUT/'assets').iterdir()})
    write_new(OUT/'prepared.json',prepared)
    # Only code pins differ: all data, sampling, optimizer and readout inputs remain exact.
    before=json.loads((source/'runtime_template.json').read_text())
    assert {k:v for k,v in before.items() if k!='code'}=={k:v for k,v in spec.items() if k!='code'}
    report=dict(utc=datetime.now(timezone.utc).isoformat(),status='DRAFT_READY_CLOSED_GATES',
        runtime_template=prepared['template'],runtime_package=str(OUT),
        source_template=old['runtime_template'],source_files=source_files,
        code=spec['code'],cache_verification=pin(HERE/'ammi_normalized_cache_verified_r1.json'),
        builder=pin(Path(__file__)),data_and_scientific_settings_unchanged=True,
        launchable=False,production_readout_pending=True,production_transfer_consent_pending=True,
        running_pilots_modified=False,cloud_speedup_measured=False,complete_D053=False)
    write_new(HERE/'ammi_cached_production_draft_prepared_r1.json',report)
    print(json.dumps({k:report[k] for k in ('status','launchable','data_and_scientific_settings_unchanged')}))


if __name__=='__main__': main()
