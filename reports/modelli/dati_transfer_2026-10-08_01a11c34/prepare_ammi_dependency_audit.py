"""Extend mount audit only to producer refs required by the consumer's frozen views."""
from percorso import HERE,ROOT,read,pin,write_new,now
path=ROOT/'reports/analisi/modelli_esterni_01a11c35_2026-10-08/ammi_input_dependencies_compact_r4.json'
deps=read(path);meta=read(HERE/'ammi_access_audit_metadata_r1.json')
refs=set(meta['kernel_sources'])
for fold in deps['folds'].values():refs.update(c['producer'] for c in fold['chunks'])
meta['kernel_sources']=sorted(refs)
out=HERE/'ammi_access_audit_metadata_r2.json';write_new(out,meta)
write_new(HERE/'ammi_access_audit_prepared_r2.json',dict(utc=now(),jobs=[dict(
    slug='davidmaisterx/read-only-pilot-input-audit',metadata=pin(out))],
    consumer_dependencies=pin(path),launch_forbidden=True))
print('Read-only producer refs: '+str(len(refs)+len(meta['dataset_sources'])))
