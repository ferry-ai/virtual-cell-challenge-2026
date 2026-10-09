"""Inspect only official HDF5 metadata, without reading expression arrays."""
import h5py
from percorso import HERE, DATA, now, write_new

records={}
for label in ('A','B','C'):
    path=DATA/'raw/controls'/('context_'+label+'.h5ad')
    with h5py.File(path,'r') as h:
        x=h['X']
        records[label]=dict(bytes=path.stat().st_size,keys=sorted(h.keys()),
            X=dict(kind=type(x).__name__,shape=list(map(int,x.attrs.get('shape',x.shape if isinstance(x,h5py.Dataset) else []))),
                   encoding=str(x.attrs.get('encoding-type',''))),
            obs_columns=sorted(h['obs'].keys()),var_columns=sorted(h['var'].keys()),
            uns_keys=sorted(h['uns'].keys()) if 'uns' in h else [],
            layers=sorted(h['layers'].keys()) if 'layers' in h else [])
out=dict(utc=now(),schema_only=True,RNA_values_read=0,records=records)
write_new(HERE/'official_control_schema_r2.json',out)
print(__import__('json').dumps(out))
