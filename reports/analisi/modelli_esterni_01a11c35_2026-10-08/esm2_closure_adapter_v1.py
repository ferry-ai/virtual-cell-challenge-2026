"""Bounded conversion of verified native ESM2 outputs; no truth or model refit.

The frozen integration gives T0 priority per observed target-gene pair, with
ESM2 only outside that support. Amplitude applies once to the native fallback;
T0's final-scale values and cis head remain byte-identical where observed.
"""
import argparse
import csv
import json
from pathlib import Path
import shutil
import zipfile

import numpy as np
from ammi_inputs_v3 import checked, read_json
from pie_adapter import sha256


def rows(path,name):
    with zipfile.ZipFile(path) as archive, archive.open(name+'.npy') as stream:
        version=np.lib.format.read_magic(stream)
        read=np.lib.format.read_array_header_1_0 if version==(1,0) else np.lib.format.read_array_header_2_0
        shape,fortran,dtype=read(stream)
        if fortran or len(shape)!=2 or dtype.hasobject:raise ValueError('unsupported native matrix storage')
        size=shape[1]*dtype.itemsize
        for i in range(shape[0]):
            raw=stream.read(size)
            if len(raw)!=size:raise ValueError('truncated native matrix')
            yield i,np.frombuffer(raw,dtype=dtype)


def collapse(path,name,targets,union=False):
    output={};largest=0.
    for i,row in rows(path,name):
        target=targets[i]
        if target not in output:output[target]=row.copy()
        elif union:output[target]|=row
        else:
            valid=np.isfinite(row)&np.isfinite(output[target])
            if not np.array_equal(np.isfinite(row),np.isfinite(output[target])):
                raise ValueError('target-only missingness differs by context')
            if valid.any():largest=max(largest,float(np.abs(row[valid]-output[target][valid]).max()))
    if largest>1e-12:raise ValueError('target-only predictions differ by context')
    return output


def native_stage100(native_pin,panel,genes,out):
    path=checked(native_pin);out=Path(out)
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    with np.load(path,allow_pickle=False) as source:
        targets=source['targets'].tolist()
        if source['genes'].tolist()!=list(genes):raise ValueError('native gene axis differs')
    if not set(targets)<=set(panel):raise ValueError('native targets outside frozen panel')
    effects=collapse(path,'effects',targets)
    generic=collapse(path,'generic',targets)
    observed=collapse(path,'observed',targets,union=True)
    generic_observed=collapse(path,'generic_observed',targets,union=True)
    result={}
    for label,values,masks in [('E2',effects,observed),('E2g',generic,generic_observed)]:
        y=np.zeros((len(panel),len(genes)),np.float32);mask=np.zeros(y.shape,bool)
        for i,t in enumerate(panel):
            if t not in values:continue
            mask[i]=masks[t]
            if not np.isfinite(values[t][mask[i]]).all():raise ValueError('nonfinite observed native effects')
            y[i]=np.where(mask[i],values[t],0)
        dest=out/(label+'.npz')
        np.savez_compressed(dest,targets=np.asarray(panel),genes=np.asarray(genes),lfc=y,observed=mask)
        result[label]=dict(path=str(dest),bytes=dest.stat().st_size,sha256=sha256(dest),
            predicted_targets=int(mask.any(1).sum()),observed_pairs=int(mask.sum()))
    return result


def fallback(t0_pin,e2_pin,out,amplitude):
    out=Path(out)
    if out.exists():raise FileExistsError(out)
    with np.load(checked(t0_pin),allow_pickle=False) as source:base={k:source[k] for k in source.files}
    with np.load(checked(e2_pin),allow_pickle=False) as source:other={k:source[k] for k in ('targets','genes','lfc','observed')}
    for key in ('targets','genes'):
        if not np.array_equal(base[key],other[key]):raise ValueError('fallback axes differ')
    a,m=base['lfc'],base['observed'];b,n=other['lfc'],other['observed']
    if (m.dtype!=bool or n.dtype!=bool or a.dtype!=np.float32 or b.dtype!=np.float32
            or not np.isfinite(a).all() or not np.isfinite(b).all() or np.any(a[~m]!=0)
            or np.any(b[~n]!=0) or not np.isfinite(amplitude) or amplitude<=0):
        raise ValueError('invalid stage100 scale/support')
    fill=~m&n
    combined=a.copy();combined[fill]=(amplitude*b[fill]).astype(np.float32)
    mask=m|fill
    changed=(combined!=a)|(mask!=m)
    if not changed.any():shutil.copyfile(t0_pin['path'],out)
    else:
        base['lfc']=combined;base['observed']=mask
        np.savez_compressed(out,**base)
    return dict(path=str(out),bytes=out.stat().st_size,sha256=sha256(out),
        t0_sha256=t0_pin['sha256'],native_stage100_sha256=e2_pin['sha256'],
        policy='T0 observed target-gene pairs dominate; ESM2 fallback only',
        amplitude_applied_once_to_fallback=amplitude,cis_reapplied=False,emission_scale_applied=False,
        t0_predicted_targets=int(m.any(1).sum()),fallback_pairs=int(fill.sum()),
        fallback_targets=int(fill.any(1).sum()),changed_targets=int(changed.any(1).sum()),
        changed_pairs=int(changed.sum()),byte_parity_t0=sha256(out)==t0_pin['sha256'],
        full_row_fallback_targets=int((~m.any(1)&n.any(1)).sum()),no_truth_read=True)


def main(out,receipt_path):
    here=Path(__file__).parent;root=here.parents[2]
    data=Path('C:/Users/ferra/vcc2026-data');out=Path(out);receipt_path=Path(receipt_path)
    if out.exists() or receipt_path.exists():raise FileExistsError('fresh output required')
    records=json.loads((here/'completed_fits_handoff_r1.json').read_text())
    manifest=json.loads((here.parent/'validazione_indipendente_8a8ca58a_2026-10-08/manifest_fold_v2.json').read_text())
    control=data/'raw/controls'
    with (control/'gene_names.csv').open(newline='') as stream:genes=[r['gene_name'] for r in csv.DictReader(stream)]
    with (control/'pert_counts.csv').open(newline='') as stream:panel=[r['target_gene'] for r in csv.DictReader(stream)]
    if sha256(control/'gene_names.csv')!=manifest['axis']['sha256'] or sha256(control/'pert_counts.csv')!=manifest['panel']['file_sha256']:
        raise ValueError('panel/axis pin differs')
    anchors=json.loads((root/'reports/modelli/dati_transfer_2026-10-08_01a11c34/ammi_anchors_verified_r1.json').read_text())
    recipe=json.loads((root/'reports/invii/trial_2026-10-06/t36_recipe_extbank.json').read_text())
    amplitudes={r['amplitude'] for r in recipe['contexts'].values()}
    if len(amplitudes)!=1:raise ValueError('ambiguous frozen amplitude')
    amplitude=amplitudes.pop();result={}
    out.mkdir(parents=True)
    for record in records['jobs']:
        fold=record['fold']
        if fold not in ('C-K562','C-iPSC','J-iPSC','production'):continue
        native=record['artifacts']['predictions']
        stage=native_stage100(native,panel,genes,out/fold)
        row=dict(native=native,stage100=stage,model=record['artifacts']['model'])
        if fold.startswith('C-'):
            baseline=anchors['anchors']['parity_'+('k562' if fold=='C-K562' else 'ipsc')]['effects']
            row['integration']=fallback(baseline,stage['E2'],out/fold/'T0_E2_fallback.npz',amplitude)
        result[fold]=row
    receipt=dict(schema='ESM2-closure-conversion/1',folds=result,panel_sha256=manifest['panel']['file_sha256'],
        gene_axis_sha256=manifest['axis']['sha256'],amplitude=amplitude,code_sha256=sha256(__file__),
        no_truth_read=True,no_new_model_fit=True,scientific_benefit='pending frozen readout')
    with receipt_path.open('x',encoding='utf-8') as stream:json.dump(receipt,stream,indent=2)
    print(json.dumps({f:r.get('integration',{}).get('changed_pairs') for f,r in result.items()}))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--out',required=True);p.add_argument('--receipt',required=True)
    a=p.parse_args();main(a.out,a.receipt)
