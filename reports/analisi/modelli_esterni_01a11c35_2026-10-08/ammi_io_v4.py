"""Pinned ESM2 input and portable checkpoint IO, without a legacy runner import."""
import json
from pathlib import Path
import numpy as np
import torch
from ammi_context import ContextCorrection
from ammi_inputs_v3 import checked,read_json
from pie_adapter import sha256

def write(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,allow_nan=False)

def features(spec,panel):
    meta=read_json(spec['meta'])
    array=np.load(checked(spec['array']),mmap_mode='r',allow_pickle=False)
    keys=meta['keys']
    if (len(set(keys))!=len(keys) or meta['name']!='esm2' or meta['index']!='pert'
            or meta['layout']!='dense' or array.shape!=(len(keys),meta['dim'])
            or array.dtype!=np.dtype(meta['dtype'])):
        raise ValueError('ESM2 identity/axes differ')
    positions={t:i for i,t in enumerate(keys)}
    available=np.array([t in positions for t in panel],dtype=bool)
    result=np.zeros((len(panel),meta['dim']),dtype=np.float32)
    for i,t in enumerate(panel):
        if available[i]:result[i]=array[positions[t]]
    if not np.isfinite(result).all():raise ValueError('nonfinite ESM2 features')
    return result,available

def save_checkpoint(model,path,identity):
    torch.save(dict(state={k:v.detach().cpu() for k,v in model.state_dict().items()},
        control_genes=model.control_genes,response_genes=model.decoder.out_features,
        context_mode=model.context_mode,identity=identity),path)
    return dict(path=str(path),bytes=path.stat().st_size,sha256=sha256(path))

def reload_checkpoint(pin,device):
    payload=torch.load(checked(pin),map_location='cpu',weights_only=True)
    model=ContextCorrection(payload['control_genes'],payload['response_genes'],
        payload['state']['reference_mean'],context_mode=payload['context_mode'])
    model.load_state_dict(payload['state'],strict=True)
    return model.to(device).eval(),payload['identity']
