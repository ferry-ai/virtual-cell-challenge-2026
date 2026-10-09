"""Reload frozen ESM2 ridge and emit native target effects without any refit.

All response genes are predicted in blocks. Missing target ESM2 remains unsupported;
the saved generic model is separate. Context does not enter this model.
"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from ammi_inputs_v3 import checked
from ammi_io_v4 import features,write
from feature_policy import POLICY
from pie_adapter import sha256

def predict_block(model_pin,feature_spec,panel,gene_indices):
    x,available=features(feature_spec,panel)
    with np.load(checked(model_pin),allow_pickle=False) as source:
        if str(source['feature_policy'].item())!=POLICY:raise ValueError('frozen feature policy differs')
        x=x.astype(np.float64);x[~available]=source['imputation_mean']
        x=np.column_stack([x,~available])
        z=(x-source['feature_mean'])/source['feature_scale']
        coef=source['coef'][:,gene_indices]
        values=z@coef+source['intercept'][gene_indices]
        support=available[:,None]&source['support'][gene_indices][None,:]
        values[~support]=0
        return values.astype(np.float32),support

def infer(spec_path,out):
    spec=json.loads(Path(spec_path).read_text())
    if Path(out).exists():raise FileExistsError(out)
    panel,genes=spec['panel'],spec['genes']
    for key,column,expected in [('panel_file','target_gene',panel),('axis_file','gene_name',genes)]:
        with checked(spec[key]).open(newline='',encoding='utf-8') as stream:
            if [r[column] for r in csv.DictReader(stream)]!=expected:raise ValueError('frozen inference axes differ')
    # Full production inference belongs on cloud; local tests use small blocks.
    if not Path('/kaggle').exists() and not Path('/content').exists():
        raise RuntimeError('full inference requires declared cloud runtime')
    x,available=features(spec['features'],panel)
    with np.load(checked(spec['model']),allow_pickle=False) as source:
        if str(source['feature_policy'].item())!=POLICY:raise ValueError('feature policy differs')
        x=x.astype(np.float64);x[~available]=source['imputation_mean']
        z=(np.column_stack([x,~available])-source['feature_mean'])/source['feature_scale']
        coef=source['coef'];intercept=source['intercept'];support=source['support']
        if coef.shape!=(z.shape[1],len(genes)):raise ValueError('model gene axis differs')
        values=np.zeros((len(panel),len(genes)),np.float32)
        for start in range(0,len(genes),128):
            stop=min(start+128,len(genes));values[:,start:stop]=z@coef[:,start:stop]+intercept[start:stop]
        mask=available[:,None]&support[None,:];values[~mask]=0
    np.savez_compressed(out,targets=np.asarray(panel),genes=np.asarray(genes),lfc=values,observed=mask)
    write(str(out)+'.json',dict(path=str(out),sha256=sha256(out),model_sha256=spec['model']['sha256'],
        spec_sha256=sha256(spec_path),scale='natural logarithm fold-change, native unscaled',
        no_refit=True,no_context_input=True,no_amplitude_or_cis_applied=True))

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--spec',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();infer(a.spec,a.out)
