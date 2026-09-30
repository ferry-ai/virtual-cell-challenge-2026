"""Stage exactly the reviewed public Stack prompt bundle and compact manifest; never upload."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

HERE=Path(__file__).resolve().parent
EXPECTED='8c693c8457590edca74e626b08d7318a276c44f4b9737f5d4d4c13272814cf3e'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024**2),b''):
            h.update(block)
    return h.hexdigest()


def save(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,indent=2)
        f.write('\n')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--stage',type=Path,required=True)
    ap.add_argument('--report',type=Path,required=True)
    args=ap.parse_args()
    if args.stage.exists() or args.report.exists():
        raise FileExistsError('Both staging and review output must be new')
    if sha(args.source)!=EXPECTED or args.source.stat().st_size!=31984510:
        raise ValueError('Public bundle differs from reviewed preparation')
    allow=json.loads((HERE/'neural/STACK_ALLOWLIST.json').read_text())
    receipt=json.loads((HERE/'neural/stack_remote_receipt_r2/review_manifest.json').read_text())
    members={};bundle_manifest=None
    with tarfile.open(args.source,'r:gz') as archive:
        for item in archive.getmembers():
            if item.isdir():
                continue
            name=item.name.removeprefix('./')
            if not item.isfile() or name not in allow['inference_bundle_files'] or name in members:
                raise ValueError('Unexpected bundle member')
            content=archive.extractfile(item).read()
            members[name]={'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()}
            if name=='bundle.json':
                bundle_manifest=json.loads(content)
    if set(members)!=set(allow['inference_bundle_files']):
        raise ValueError('Incomplete bundle allowlist')
    if members['bundle.json']['sha256']!=receipt['bundle_manifest_sha256']:
        raise ValueError('Bundle metadata differs')
    for name,digest in bundle_manifest['files'].items():
        if members[name]['sha256']!=digest:
            raise ValueError('Inner input hash differs')
    args.stage.mkdir(parents=True)
    shutil.copyfile(args.source,args.stage/'bundle.tar.gz')
    if sha(args.stage/'bundle.tar.gz')!=EXPECTED:
        raise ValueError('Staging readback mismatch')
    manifest={'dataset':'davidmaisterx/vcc-stack-prompts-r1','private':True,
              'prepared_utc':datetime.now(timezone.utc).isoformat(),'bundle_archive_sha256':EXPECTED,
              'bundle_archive_bytes':31984510,'bundle_manifest_sha256':receipt['bundle_manifest_sha256'],
              'targets':receipt['targets'],'members':members,
              'public_sources_only':True,'destination':'public HepG2 controls only; no destination perturbation truth',
              'source':'selected public K562 cells and frozen transfer effects','credentials_included':False}
    save(args.stage/'input_manifest.json',manifest)
    metadata={'id':manifest['dataset'],'title':'VCC Stack Prompts R1','licenses':[{'name':'other'}],
              'isPrivate':True,'description':'Private inference pilot using selected public K562 cells and public HepG2 controls. '
                                            'No destination perturbation truth, competition ABC cells or credentials. Original source licenses apply.',
              'resources':[{'path':'bundle.tar.gz'},{'path':'input_manifest.json'}]}
    save(args.stage/'dataset-metadata.json',metadata)
    review={'prepared_utc':manifest['prepared_utc'],'stage':str(args.stage),'dataset':manifest['dataset'],
            'private':True,'new_upload_files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)}
               for p in sorted(args.stage.iterdir()) if p.name!='dataset-metadata.json'],
            'metadata':metadata,'metadata_sha256':sha(args.stage/'dataset-metadata.json'),
            'bundle_allowlist':members,'bundle_manifest':bundle_manifest,
            'same_bundle_as_authorized_colab':True,'upload_performed':False,'new_compute_started':False}
    args.report.mkdir(parents=True)
    save(args.report/'upload_review.json',review)
    print(json.dumps({'review':str(args.report/'upload_review.json'),'stage':str(args.stage),
                      'files':len(review['new_upload_files']),'bytes':sum(e['bytes'] for e in review['new_upload_files']),
                      'members':len(members),'bundle_sha256':EXPECTED,'upload_performed':False}))


if __name__=='__main__':
    main()
