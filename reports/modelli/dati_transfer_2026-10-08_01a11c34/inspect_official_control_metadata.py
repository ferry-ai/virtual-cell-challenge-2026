"""Read control-selection metadata only, never expression counts."""
import h5py
import numpy as np
from ntc_cells import column
from percorso import HERE,DATA,now,write_new
records={}
for label in ('A','B','C'):
    with h5py.File(DATA/'raw/controls'/('context_'+label+'.h5ad'),'r') as h:
        ntc=column(h['obs'],'ntc_id').astype(str)
        targets=column(h['obs'],'target_gene').astype(str)
        keys=column(h['obs'],'_index').astype(str)
        records[label]=dict(ntc_id_unique=len(set(ntc)),cells=len(ntc),
            unique_cell_keys=len(set(keys)),target_values=sorted(set(targets)),
            ntc_id_max_length=max(map(len,ntc)),ntc_id_missing=int(np.sum(ntc=='MISSING')))
out=dict(utc=now(),RNA_values_read=0,records=records)
write_new(HERE/'official_control_metadata_r1.json',out)
print(__import__('json').dumps(out))
