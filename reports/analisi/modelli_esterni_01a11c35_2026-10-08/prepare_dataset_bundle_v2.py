"""Keep an oversized authorized private package in a private dataset, not source code."""
import argparse
import json
from pathlib import Path
import zipfile

from prepare_cloud_fit_v6 import prepare, write
from pie_adapter import sha256


def main(inputs, inputs_sha256, out, receipt):
    if out.exists() or receipt.exists():raise FileExistsError('new package required')
    out.mkdir(parents=True)
    intermediate=out/'embedded_prepared.json'
    prepare('J-iPSC','r5',out/'embedded',intermediate,'davideferante',inputs,inputs_sha256)
    prior=json.loads(intermediate.read_text())
    dataset=out/'dataset';dataset.mkdir()
    binary=dataset/'bundle.bin'
    with zipfile.ZipFile(binary,'w',compression=zipfile.ZIP_LZMA) as z:
        for p in sorted((out/'embedded'/'bundle').iterdir()):z.write(p,arcname=p.name)
    slug='davideferante/esm2-j-ipsc-01a11c35-r5-private-bundle'
    write(dataset/'dataset-metadata.json',dict(id=slug,title='ESM2 J iPSC 01a11c35 r5 private bundle',
        licenses=[{'name':'other'}],description='Private execution package. Contains temporary access locators; never publish or redistribute.',
        resources=[{'path':'bundle.bin','description':'Private frozen execution package'}]))
    stage=out/'deploy';stage.mkdir()
    digest=sha256(binary)
    source=('import hashlib,os,sys,zipfile\nfrom pathlib import Path\n'
        'assert os.name=="posix"\n'
        'os.environ["OPENBLAS_NUM_THREADS"]="2"\nos.environ["OMP_NUM_THREADS"]="2"\nos.environ["MKL_NUM_THREADS"]="2"\n'
        'root=Path("/kaggle/temp/esm2-j-ipsc-01a11c35-r5-bundle")\n'
        f'bundle_sha256={digest!r}\n'
        'matches=[p for p in Path("/kaggle/input").rglob("bundle.bin") if hashlib.sha256(p.read_bytes()).hexdigest()==bundle_sha256]\n'
        'assert len(matches)==1,"Missing or ambiguous pinned private bundle"\n'
        'root.mkdir(parents=True,exist_ok=False)\n'
        'with zipfile.ZipFile(matches[0]) as z:\n'
        '    assert all(Path(n).name==n for n in z.namelist())\n'
        '    z.extractall(root)\n'
        'sys.path.insert(0,str(root))\nfrom cloud_fit import main\nmain(root)\n')
    (stage/'run.py').write_text(source,encoding='utf-8',newline='\n')
    metadata=json.loads((out/'embedded'/'kernel-metadata.json').read_text())
    metadata['dataset_sources']=[slug]
    write(stage/'kernel-metadata.json',metadata)
    prior.update(stage=str(stage.resolve()),code_sha256=sha256(stage/'run.py'),
        metadata_sha256=sha256(stage/'kernel-metadata.json'),
        bundle_dataset=dict(slug=slug,path=str(binary.resolve()),bytes=binary.stat().st_size,
                            sha256=digest,private=True,metadata_sha256=sha256(dataset/'dataset-metadata.json')),
        bootstrap_bytes=len(source.encode()),private_locator_values_in_bootstrap=False)
    write(receipt,prior)
    print(json.dumps(dict(job_id=prior['job_id'],bootstrap_bytes=prior['bootstrap_bytes'],
                         private_bundle_bytes=binary.stat().st_size,preparation_only=True)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--inputs-sha256',required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True);a=p.parse_args();main(a.inputs,a.inputs_sha256,a.out,a.receipt)
