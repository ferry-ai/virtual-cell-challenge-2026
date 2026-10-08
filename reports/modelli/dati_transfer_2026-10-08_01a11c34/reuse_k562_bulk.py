"""Verify historical K562 chunks and reduce them to two small common vectors.

Local bounded reduction: existing 17 files, one shrunk chunk <=45 MB at a time,
no raw cells, model fit or download, output below 1 MB. Peak memory is measured.
"""
import json
import sys
import time
import numpy as np
import pandas as pd
from common_stream import hidden
from percorso import DATA,HERE,ROOT,now,pin,read,sha,write_new
sys.path.insert(0,str(ROOT/'src'))
from vcc2026.resources import snapshot,peak_rss_bytes


def main():
    start=time.monotonic();resources=snapshot(DATA).as_dict()
    if resources['ram_available_bytes']<512<<20:raise ValueError('insufficient available RAM for bounded verification')
    universe=DATA/'processed/universe_k562_2026-09-26';manifest=read(universe/'manifest.json')
    reference=DATA/'processed/multisource_2026-09-23_r5/k562.npz'
    expected=read(HERE/'release_t1_r1.json')['voted']['k562']
    if sha(reference)!=expected['sha256']:raise ValueError('historical T1 table changed')
    axis=pd.read_csv(DATA/'raw/controls/gene_names.csv').iloc[:,0].astype(str).tolist();width=len(axis)
    split=read(ROOT/'reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/splits_v1/T-all.json')
    with np.load(reference,allow_pickle=False) as z:
        panel=z['targets'].astype(str).tolist();panel_values=z['shrunk'];panel_n=z['n_cells']
    index={t:i for i,t in enumerate(panel)};checked=set();seen=set();previous=None;inputs=[]
    sums={r:np.zeros(width,np.float64) for r in ('production','T')};support={r:np.zeros(width,np.int64) for r in sums}
    counts={r:0 for r in sums};cells={r:0 for r in sums}
    for chunk in manifest['chunks']:
        path=universe/chunk['file']
        if sha(path)!=chunk['sha256']:raise ValueError('universe chunk changed')
        with np.load(path,allow_pickle=False) as z:
            targets=z['targets'].astype(str).tolist();values=z['shrunk'];n=z['n_cells']
        if values.shape!=(len(targets),width) or values.nbytes>48<<20:raise ValueError('chunk outside memory/axis budget')
        for target,value,population in zip(targets,values,n):
            if previous is not None and target<=previous or target in seen:raise ValueError('unordered or repeated target')
            previous=target;seen.add(target)
            if target in index:
                i=index[target]
                if not np.array_equal(value,panel_values[i],equal_nan=True) or population!=panel_n[i]:
                    raise ValueError('K562 universe differs from frozen T1 on '+target)
                checked.add(target)
            mask=np.isfinite(value);clean=np.where(mask,value,0).astype(np.float64)
            for regime in ('production','T'):
                if regime=='T' and hidden(target,split):continue
                sums[regime]+=clean;support[regime]+=mask;counts[regime]+=1;cells[regime]+=int(population)
        inputs.append(pin(path));del values
    if checked!=set(panel):raise ValueError('not every frozen panel target was verified')
    out=DATA/'processed/dati_transfer_2026-10-08_01a11c34/k562_bulk_common_r1';out.mkdir(parents=True,exist_ok=False)
    outputs={}
    for regime in sums:
        common=np.divide(sums[regime],support[regime],out=np.zeros(width),where=support[regime]>0)
        dest=out/(regime+'.npz');np.savez_compressed(dest,genes=np.asarray(axis),common=common,mask=support[regime]>0,contributing_targets=support[regime])
        outputs[regime]=dict(file=pin(dest),targets=counts[regime],target_cells=cells[regime])
    write_new(HERE/'k562_bulk_common_r1.json',dict(utc=now(),outputs=outputs,inputs=inputs,
        parent_manifest=pin(universe/'manifest.json'),source_script=pin(ROOT/'reports/sorgenti/universo_2026-09-26/k562_universe.py'),
        reference=pin(reference),panel_targets_exactly_equal=len(checked),regime_T_split=pin(ROOT/'reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/splits_v1/T-all.json'),
        split_safety='Historical bulk effects are target-local; fixed control rows and gene axis. Hidden target rows removed before sums/support.',
        resources_before=resources,peak_rss_bytes=peak_rss_bytes(),seconds=time.monotonic()-start,
        local_rationale=__doc__,raw_cells_read=0,model_fit=False,not_a_score=True))
    print(json.dumps(dict(outputs=outputs,panel_parity=len(checked),seconds=time.monotonic()-start,peak_rss=peak_rss_bytes())))


if __name__=='__main__':main()
