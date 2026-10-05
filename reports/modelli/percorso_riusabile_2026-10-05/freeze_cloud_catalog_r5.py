"""Finalize this unpublished release with frozen copies of resumable launch journals."""
import json
from pipeline_state import HERE,REPO,sha


def main():
    root=HERE/'cloud_catalog_r5';manifest=root/'manifest.json';old=sha(manifest)
    c=json.loads(manifest.read_text());mapping={}
    for name,path in [('hipsci_launches_at_release.jsonl',HERE/'hipsci_partition_r1/launches.jsonl'),
                      ('tian_launches_at_release.jsonl',HERE/'tian_resume_r2/launches.jsonl')]:
        frozen=root/name;frozen.open('xb').write(path.read_bytes())
        mapping[path.relative_to(REPO).as_posix()]={'path':frozen.relative_to(REPO).as_posix(),'sha256':sha(frozen)}
    c['sources']=[mapping.get(r['path'],r) for r in c['sources']]
    c['sources'].append(mapping[(HERE/'tian_resume_r2/launches.jsonl').relative_to(REPO).as_posix()])
    c['execution']['recovery']['tian']='tian_partial_r1/state.json; four accepted jobs in tian_resume_r2/launches.jsonl; private sample input ready'
    c['execution']['recovery']['frozen_launch_journals']=list(mapping.values())
    c['execution']['recovery']['private_sample_input']=json.loads((HERE/'tian_rehouse_r1.json').read_text())
    manifest.write_text(json.dumps(c,indent=1)+'\n',encoding='utf-8',newline='\n')
    readme=root/'README.md';readme.write_text(readme.read_text().replace(old,sha(manifest)),encoding='utf-8')
    print(json.dumps({'final_manifest_sha256':sha(manifest),'frozen_journals':len(mapping)}))


if __name__=='__main__':main()
