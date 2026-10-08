"""Cloud reduction of pinned joint CD4 condition effects to one common vector."""
import json
import os
from pathlib import Path
import shutil
import time
import numpy as np
import pandas as pd
from common_stream import rows,mixed_common,sha


def main(*,input_root=Path('/kaggle/input'),ram_available=None):
    start=time.monotonic();params=json.loads(Path('params.json').read_text())
    for filename,pin in params['embedded'].items():
        if sha(filename)!=pin['sha256']:raise ValueError('embedded identity changed')
    ram=ram_available if ram_available is not None else next(int(s.split()[1])*1024 for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))
    if ram<512<<20:raise ValueError('insufficient measured RAM')
    resources=dict(cpu=os.cpu_count(),ram_available_bytes=ram,disk_free_bytes=shutil.disk_usage(Path.cwd()).free)
    genes=pd.read_csv('gene_names.csv').iloc[:,0].astype(str).tolist()
    sized={}
    for f in Path(input_root).rglob('*'):
        if f.is_file():sized.setdefault(f.stat().st_size,[]).append(f)
    def locate(pin):
        for path in sized.get(pin['bytes'],[]):
            if sha(path)==pin['sha256']:return path
        raise ValueError('missing frozen chunk '+pin['sha256'])
    streams=[];input_pins=[]
    for condition in params['conditions']:
        if condition['split']!=params['split']:raise ValueError('different training splits')
        chunks=[]
        for item in condition['chunks']:
            path=locate(item);chunks.append(dict(item,path=str(path)));input_pins.append(dict(item,path=str(path)))
        streams.append(rows(chunks,genes,params['split']))
    arrays,receipt=mixed_common(streams,len(genes),100.)
    np.savez_compressed('cd4_mix_common.npz',genes=np.asarray(genes),**arrays)
    receipt.update(params_sha256=sha('params.json'),split=params['split'],input_files=input_pins,
        output=dict(file='cd4_mix_common.npz',bytes=Path('cd4_mix_common.npz').stat().st_size,sha256=sha('cd4_mix_common.npz')),
        resources=resources,seconds=time.monotonic()-start,source='cd4_mix',model_fit=False,raw_cells_read=0)
    Path('common_receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
    Path('complete.json').write_text(json.dumps(dict(status='common_complete',receipt_sha256=sha('common_receipt.json')))+'\n')
    print(json.dumps(dict(targets=receipt['targets'],seconds=receipt['seconds'],output=receipt['output'])))


if __name__=='__main__':main()
