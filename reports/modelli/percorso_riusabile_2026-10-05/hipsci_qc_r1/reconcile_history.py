"""Read small historic HIPSCI manifests; never consume their matrices as a fallback."""
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
historical=ROOT/'reports/sorgenti/universo_hipsci_2026-09-27/linee_p2'
records=[]
for manifest in sorted(historical.glob('*/manifest.json')):
    m=json.loads(manifest.read_text())
    qpath=manifest.parent/'on_target.json'
    q=json.loads(qpath.read_text())
    records.append(dict(context=m['context'],manifest=manifest.relative_to(ROOT).as_posix(),
        manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
        options=m['estimator']['options'],donors=m['estimator']['donors'],
        ntc_cells_per_pool=m['summary']['ntc_cells_per_pool'],
        qc_path=qpath.relative_to(ROOT).as_posix(),qc_sha256=hashlib.sha256(qpath.read_bytes()).hexdigest(),
        historic_own_gene_median=q['median'],own_gene_measured=q['own_gene_measured']))
assert len(records)==19
assert all(r['options']['pseudo']==.5 and r['options']['min_expected']==1 for r in records)
assert all(sum(n>0 for n in r['ntc_cells_per_pool'])==2 for r in records)
out=HERE/'historic_manifest_reconciliation.json'
with out.open('x',encoding='utf-8') as f:json.dump(dict(records=records,
    claim='All 19 linee_p2 manifests use pseudo0.5; p2 denotes two archive pools, not pseudo2',
    not_reuse_equivalence=True,new_bank_donors='real clones; historic donors are archive pools',
    no_historic_matrix_loaded=True),f,indent=1);f.write('\n')
print(json.dumps(dict(manifests=len(records),pseudo=.5,archive_pools=2,
    historic_medians={r['context']:r['historic_own_gene_median'] for r in records})))
