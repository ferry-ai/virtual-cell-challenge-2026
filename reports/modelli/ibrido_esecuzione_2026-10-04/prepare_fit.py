"""CPU assembly of lawful transfer anchors on the current aggregate corpus; explicit first cohort."""
import hashlib, json, os, shutil, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

def mount(slug):
    hits=[p for p in Path('/kaggle/input').glob('**/'+slug) if p.is_dir()]
    if len(hits)!=1: raise ValueError((slug,hits))
    return hits[0]

def main():
    p=json.loads(Path('params.json').read_text()); started=time.time()
    ds=mount('rlead-bench-cube-r2'); code=mount('rcell-d056-code-r1')
    cube_dir=Path('cube'); bench=Path('bench'); cube_dir.mkdir(); bench.mkdir()
    for f in ds.iterdir():
        if f.name.startswith('code__'): shutil.copyfile(f,bench/f.name[6:])
        if f.name.startswith('cube__'):
            dest=cube_dir/Path(*f.name[6:].split('__'));dest.parent.mkdir(parents=True,exist_ok=True);dest.symlink_to(f)
    sys.path.insert(0,str(bench.resolve()))
    from arms import Cube, table_means, group_mean, combine_groups, AMPLITUDE_T25
    from splits import Split, assert_no_leak
    cube=Cube(cube_dir); held=p['held']; split=Split('C',held,None,5)
    train=cube.training_rows(split);assert_no_leak(train,split,'hybrid-first-cohort')
    common,_=table_means(cube,split)
    genes=pd.read_csv(cube_dir/'genes.csv')['gene'].astype(str).tolist()
    desc=np.load(code/'descriptors.npy'); names=(code/'genes.txt').read_text().splitlines(); idx={g:i for i,g in enumerate(names)}
    if len(names)!=len(desc): raise ValueError('descriptor axis mismatch')
    out=Path('fit');out.mkdir()
    # Target identity remains a biological descriptor, without learned held-out preprocessing.
    zero=np.zeros(desc.shape[1],np.float32)
    rows=[]; exclusions=[]; tables=[t for t in cube.tables if cube.group[t]!=held]
    for t in tables:
        for key in cube.keys_of(t):
            sym=cube.symbol.get(key,'');di=idx.get(sym,-1)
            rows.append({'table':t,'group':cube.group[t],'study':cube.meta[t]['study'],'target_key':key,'target':sym,'descriptor_index':di})
    R=len(rows);G=len(genes)
    Y=np.lib.format.open_memmap(out/'truth_effect.npy',mode='w+',dtype=np.float16,shape=(R,G))
    S=np.lib.format.open_memmap(out/'anchor.npy',mode='w+',dtype=np.float16,shape=(R,G))
    D=np.lib.format.open_memmap(out/'target.npy',mode='w+',dtype=np.float32,shape=(R,desc.shape[1]))
    C=[]; context_ix={t:i for i,t in enumerate(tables)}
    for t in tables:
        basal=np.maximum(np.expm1(cube.basal[t]),0).astype(np.float32)
        if np.isinf(basal).any() or np.nansum(basal)<=0: raise ValueError('invalid basal '+t)
        C.append(basal/np.nansum(basal))
    frame=pd.DataFrame(rows)
    for t in tables:
        ix=np.flatnonzero(frame.table.to_numpy()==t);h=cube.group[t]
        sources=[g for g in cube.groups if g not in (held,h)]
        if held in sources or h in sources: raise AssertionError('leakage')
        for start in range(0,len(ix),128):
            ids=ix[start:start+128];keys=frame.iloc[ids].target_key.tolist()
            truth,_=cube.get(t,'raw',keys)
            anchor,support=combine_groups([group_mean(cube,g,keys,common) for g in sources])
            anchor*=AMPLITUDE_T25
            # Production convention: unsupported transfer entries emit zero effect; truth mask stays distinct.
            Y[ids]=truth;S[ids]=np.nan_to_num(anchor,nan=0);D[ids]=np.stack([desc[i] if i>=0 else zero for i in frame.iloc[ids].descriptor_index])
        print(json.dumps({'table':t,'rows':len(ix),'seconds':round(time.time()-started)}),flush=True)
    frame['context_index']=[context_ix[t] for t in frame.table]
    # Hierarchical loss mass: line -> study -> context -> target. Every admitted row is visited each epoch.
    ng=frame.group.nunique()
    studies=frame.groupby('group').study.transform('nunique')
    contexts=frame.groupby(['group','study']).table.transform('nunique')
    targets=frame.groupby('table').target_key.transform('size')
    weights=R/(ng*studies*contexts*targets)
    frame['weight']=weights;frame.to_csv(out/'rows.csv',index=False)
    np.save(out/'basal.npy',np.stack(C));(out/'genes.json').write_text(json.dumps(genes))
    Y.flush();S.flush();D.flush()
    if cube.fit_reads_of(held):raise AssertionError('held responses read')
    receipt={'complete':True,'held':held,'regime':'C','rows':R,'genes':G,'source_policy':'all',
             'cohort':'current cube r2 aggregates; CD4 donor-resolved bank being built separately; NOT complete catalogue',
             'truth':'legacy pseudobulk log effects; not claimed as mean per-cell proportions',
             'tables_expected':tables,'tables_used':frame.table.unique().tolist(),
             'groups':sorted(frame.group.unique()),'held_fit_reads':cube.fit_reads_of(held),
             'unknown_target_descriptors':int((frame.descriptor_index<0).sum()),'seconds':round(time.time()-started),
             'parameters':p,'cube_manifest_sha256':hashlib.sha256((cube_dir/'manifest.json').read_bytes()).hexdigest()}
    (out/'complete.json').write_text(json.dumps(receipt,indent=1));print(json.dumps(receipt),flush=True)
    # Source layout is transient; avoid exporting symlinked multi-GB input copies.
    for f in cube_dir.rglob('*'):
        if f.is_symlink(): f.unlink()

if __name__=='__main__':main()
