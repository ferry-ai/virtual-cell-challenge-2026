"""Bind the successful consumer package and correct the reuse guide's stale catalog selection."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[2]
def pin(p):return {'path':p.relative_to(REPO).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
launch=json.loads((HERE/'generation_successors_r1/dispatch_r1/launch.json').read_text(encoding='utf-8'))
package=HERE/'generation_successors_r1/package'
assert pin(package/'run.py')['sha256']==launch['code_sha256']
assert pin(package/'params.json')['sha256']==launch['params_sha256']
storage=HERE/'cloud_catalog_r11/manifest.json'
expected=REPO/'reports/analisi/riconciliazione_banca_2026-10-05/frozen/expected_r3.json'
assert pin(storage)['sha256']=='d833b8808c69e1d95200ef95ccc60bb76c585ec73b18fdac2fb6d171692fee9d'
assert pin(expected)['sha256']=='304e8a660d7f69952c62c2e6ccf3a990da48647a186e179db4584941b4b21a30'
out={'kind':'successful_partial_consumer_package_fingerprint_not_complete_training_manifest','cloud_job':launch['slug'],'cloud_version':1,'storage':pin(storage),'expected':pin(expected),'package_files':[pin(package/name) for name in ('run.py','params.json','driver.py','generate_contract.py','kernel-metadata.json')],'runtime_evidence':[pin(HERE/'generation_successors_r1/completion_r1'/name) for name in ('generation_manifest.json','status.json','runtime_versions.json','packaging.json')],'frozen_input_record':pin(HERE/'generation_successors_r1/records_r1/prediction_record.json'),'successful_entry_receipt':pin(REPO/'reports/invii/trial_2026-10-06/submit_t36_public_receipt.json'),'limitations':['Package restores partial t36 release, not full catalog.','Mount references alone are not immutable versions: runtime byte hashes must match.','No replay of concluded job or submission is authorized by this manifest.']}
with (HERE/'release_t36_reuse_r1.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
for relative in ('README.md','docs/piani/strategia-scientifica.md','reports/analisi/riconciliazione_banca_2026-10-05/README.md','reports/modelli/percorso_riusabile_2026-10-05/README.md'):
 p=REPO/relative;t=p.read_text(encoding='utf-8').replace('RIUSO_r2.md','RIUSO_r3.md')
 p.write_text(t,encoding='utf-8')
p=REPO/'docs/REGISTRO.md';t=p.read_text(encoding='utf-8')
marker='| `reports/modelli/percorso_riusabile_2026-10-05/RIUSO_r1.md`'
pos=t.index(marker)
row='| `reports/modelli/percorso_riusabile_2026-10-05/RIUSO_r2.md` | superato | `reports/modelli/percorso_riusabile_2026-10-05/RIUSO_r3.md` | Guida preservata; selezione r10/r2 antecedente ai due blocchi GWPS. r3 include storage45unità ed expected r3, distingue pacchetto t36 parziale dalla copertura completa | — |\n'
t=t[:pos]+row+t[pos:];p.write_text(t,encoding='utf-8')
print('Verified t36 code/params and r11/expected-r3 hashes; active reuse guide now includes both GWPS blocks.')
