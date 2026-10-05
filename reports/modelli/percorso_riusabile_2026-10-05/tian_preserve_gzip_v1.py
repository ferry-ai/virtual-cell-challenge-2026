"""Preserve gzip bytes under a binary suffix: Kaggle mounts .gz decompressed."""
import json,os,shutil
from pathlib import Path
from pipeline_state import HERE,CONFIG,sha


def main():
    os.environ['KAGGLE_CONFIG_DIR']=str(Path.home()/CONFIG['davideferante'])
    from kaggle.api.kaggle_api_extended import KaggleApi
    api=KaggleApi();api.authenticate();ref='davideferante/vcc-tian-ipsc-sample-input-r1'
    before=json.loads(api.dataset_status(ref,format='json(status,current_version_number)'))
    if before['current_version_number']!=1:raise ValueError('inspect existing version before mutation')
    root=Path('C:/Users/ferra/vcc2026-data/processed/percorso_riusabile_2026-10-05/tian_sample_input_r1/bank/tian2019_ipsc')
    source=root/'samples.jsonl.gz';dest=root/'samples.jsonl.gz.bin'
    expected=json.loads((HERE/'tian_rehouse_r1.json').read_text())['copied_files']['samples.jsonl.gz']
    if sha(source)!=expected['sha256']:raise ValueError('cached bytes changed')
    if not dest.exists():shutil.copyfile(source,dest)
    if sha(dest)!=expected['sha256']:raise ValueError('binary alias differs')
    api.dataset_create_version(str(root),'Preserve original gzip locator bytes as binary input alias; no resampling or raw ingestion',
                               quiet=True,convert_to_csv=False,delete_old_versions=False,dir_mode='skip')
    (HERE/'tian_rehouse_version2_r1.json').open('x').write(json.dumps({'dataset':ref,'expected_version':2,'previous':before,
            'file':dest.name,'sha256':sha(dest),'private':True,'old_versions_retained':True,
            'reason':'Kaggle runtime expands .gz; use binary alias with exact original bytes'},indent=1))
    print(json.dumps({'submitted_version':2,'binary_alias_bytes':dest.stat().st_size}))


if __name__=='__main__':main()
