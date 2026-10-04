"""GPU training of bounded residual T+R; first aggregate cohort, both context arms."""
import hashlib, json, os, time
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from hybrid import Hybrid, predict_effect

def main():
    p=json.loads(Path('params.json').read_text());started=time.time()
    hits=list(Path('/kaggle/input').glob('**/'+p['fit_dataset']+'/complete.json'))
    if len(hits)!=1:raise ValueError(('fit receipt',hits))
    root=hits[0].parent;receipt=json.loads(hits[0].read_text())
    if not receipt['complete'] or receipt['held']!=p['held'] or receipt['held_fit_reads']:raise ValueError('invalid fold')
    if not torch.cuda.is_available():raise RuntimeError('training requires actual CUDA')
    torch.set_num_threads(2);device=torch.device('cuda')
    rows=pd.read_csv(root/'rows.csv');Y=np.load(root/'truth_effect.npy',mmap_mode='r');S=np.load(root/'anchor.npy',mmap_mode='r')
    D=np.load(root/'target.npy',mmap_mode='r');B=np.load(root/'basal.npy')
    if receipt['held'] in set(rows.group):raise ValueError('held-line training leakage')
    if set(rows.table)!=set(receipt['tables_expected']):raise ValueError('context coverage mismatch')
    # Deterministic, unlearned control descriptor; no held-line control participates in fitting.
    context=np.concatenate([np.log1p(np.nan_to_num(B)*1e6)/10.,np.isfinite(B)],axis=1).astype(np.float32)
    weights=rows.weight.to_numpy(np.float32);ci=rows.context_index.to_numpy(int);R,G=Y.shape
    model_spec=dict(genes=G,target_dim=D.shape[1],context_dim=context.shape[1],width=p['width'],rank=p['rank'],residual_bound=p['residual_bound'])
    env={'gpu':torch.cuda.get_device_name(),'gpu_memory':torch.cuda.get_device_properties(0).total_memory,
         'cuda':torch.version.cuda,'rows':R,'genes':G,'parameters':p,'fit':receipt}
    Path('training_started.json').write_text(json.dumps(env,indent=1));print(json.dumps(env),flush=True)
    for seed in p.get('seeds',[0,1,2]):
        for with_context in (False,True):
            name=('context' if with_context else 'no_context')+f'_s{seed}';out=Path(name);out.mkdir()
            torch.manual_seed(seed);rng=np.random.default_rng(seed)
            model=Hybrid(**model_spec,with_context=with_context).to(device);opt=torch.optim.AdamW(model.parameters(),lr=p['lr'],weight_decay=1e-4)
            order=rng.permutation(R);at=0;visited=np.zeros(R,np.int32);curve=[]
            for step in range(p['steps']):
                if at>=R:order=rng.permutation(R);at=0
                ix=order[at:at+p['batch']];at+=len(ix);visited[ix]+=1
                a=torch.as_tensor(np.asarray(S[ix],np.float32),device=device)
                y=torch.as_tensor(np.asarray(Y[ix],np.float32),device=device)
                t=torch.as_tensor(np.asarray(D[ix],np.float32),device=device)
                c=torch.as_tensor(context[ci[ix]],device=device);mask=torch.isfinite(y)
                w=torch.as_tensor(weights[ix],device=device)
                if not mask.any(-1).all():raise ValueError('empty truth row')
                residual=model(a,t,c,mask);pred=predict_effect(model,a,t,c,mask)
                if step==0 and not torch.equal(pred,a):raise AssertionError('zero initial correction parity')
                err=torch.where(mask,pred-torch.nan_to_num(y),0)
                per=(err.square().sum(-1)+p['residual_l2']*residual.square().sum(-1))/mask.sum(-1)
                loss=(w*per).mean()
                if not torch.isfinite(loss):raise FloatingPointError('nonfinite loss')
                opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.);opt.step()
                if (step+1)%100==0:
                    item={'arm':name,'step':step+1,'loss':float(loss.detach()),'seconds':round(time.time()-started)}
                    curve.append(item);print(json.dumps(item),flush=True)
            if not (visited>0).all():raise ValueError('unvisited admitted training rows: increase predeclared steps')
            torch.save({'state_dict':model.cpu().state_dict(),'model_spec':{**model_spec,'with_context':with_context},
                        'parameters':p,'seed':seed,'source_policy':'all','held':p['held'],'composition':'T + R; t28 downstream once'},out/'model.pt')
            pd.DataFrame(curve).to_csv(out/'curve.csv',index=False)
            exposure=rows[['group','study','table','target_key']].copy();exposure['visits']=visited;exposure.to_csv(out/'exposure.csv',index=False)
            (out/'complete.json').write_text(json.dumps({'complete':True,'rows_used':int((visited>0).sum()),'contexts_used':int(rows.table.nunique()),'seed':seed}))
            del model,opt;torch.cuda.empty_cache()
    Path('training_done.json').write_text(json.dumps({'complete':True,'held':p['held'],'seconds':round(time.time()-started),
        'cohort':receipt['cohort'],'promoted':False,'bench_pending':True,'seeds':p.get('seeds',[0,1,2])},indent=1))

if __name__=='__main__':main()
