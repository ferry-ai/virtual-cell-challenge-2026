"""Exact small-fixture equivalence against the frozen pre-amendment v4 capsule."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import types
import zipfile
import numpy as np
import torch
from ammi_encoder_v4 import ControlsNotConsumed, forward_grouped
from ammi_train_v4 import fit
from ammi_guard_v4 import predict, discrimination
from ammi_inputs_v3 import module
from ammi_io_v4 import save_checkpoint, reload_checkpoint
from pie_adapter import sha256

HERE=Path(__file__).resolve().parent


def prove(out):
    out=Path(out)
    if out.exists():raise FileExistsError(out)
    torch.set_num_threads(1)
    capsule=HERE/'ammi_code_package_r6/ammi_code.zip'
    if sha256(capsule)!='ae1e9d109bda661f43cfd8facfd2a8dd125ff9bd153b3573a073f391eac328ce':
        raise ValueError('frozen pre-amendment capsule differs')
    with zipfile.ZipFile(capsule) as archive:
        legacy_encoder=types.ModuleType('legacy_encoder')
        exec(compile(archive.read('ammi_encoder_v4.py'),'legacy_encoder.py','exec'),legacy_encoder.__dict__)
        legacy_train=types.ModuleType('legacy_train')
        exec(compile(archive.read('ammi_train_v4.py'),'legacy_train.py','exec'),legacy_train.__dict__)
    legacy_train.forward_grouped=legacy_encoder.forward_grouped
    metrics_path=HERE.parent/'validazione_indipendente_8a8ca58a_2026-10-08/banco/metrics.py'
    metrics=module(dict(path=str(metrics_path),bytes=metrics_path.stat().st_size,sha256=sha256(metrics_path)),'none_proof_metrics')
    rng=np.random.default_rng(17);n=24;g=16;d=5
    panel=[f't{i}' for i in range(n)];genes=[f'g{i}' for i in range(g)]
    features=rng.normal(size=(n,d)).astype('float32')
    anchor=rng.normal(size=(n,g)).astype('float32');mask=np.ones((n,g),bool)
    data=dict(contexts=['a']*12+['b']*12,lineages=['A']*12+['B']*12,
        row_ids=list(panel),features=features,anchor=anchor,observed=mask,
        response=anchor+.05*rng.normal(size=(n,g)).astype('float32'),
        input_receipt_sha256='fixture',anchor_receipt_sha256='fixture')
    contexts=['a','b','inner','outer']
    actual={c:(rng.normal(size=(3,g)).astype('float32'),np.ones((3,g),bool)) for c in contexts}
    changed={c:(x*83+12,m) for c,(x,m) in actual.items()}
    empty=ControlsNotConsumed(contexts,g)
    truth=dict(targets=np.array(panel),shrunk=anchor.copy(),raw=anchor.copy(),se=np.ones((n,g)))
    models=[];receipts=[];guards=[]
    for engine,controls in ((legacy_train.fit,actual),(legacy_train.fit,changed),(fit,empty)):
        seen=[]
        def guard(model,epoch):
            output,_,structure=predict(model,features,np.ones(n,bool),'inner',controls,anchor,mask)
            score=discrimination(metrics,anchor,output,mask,truth,panel,genes)
            if not score['pass']:raise AssertionError('actual metric positive control failed')
            seen.append(dict(epoch=epoch,structural=structure,disc95=score))
            return dict(**{'pass':True},score=score,structural=structure)
        model,receipt=engine(data,controls,['HELD'],'none',17,guard,fixture=True)
        models.append(model);receipts.append(receipt);guards.append(seen)
    for model in models[1:]:
        for name,value in models[0].state_dict().items():
            torch.testing.assert_close(value,model.state_dict()[name],atol=0,rtol=0)
        for a,b in zip(models[0].parameters(),model.parameters()):
            if a.grad is None:assert b.grad is None
            else:torch.testing.assert_close(a.grad,b.grad,atol=0,rtol=0)
    for receipt in receipts[1:]:
        for name in ('row_ids','weights','reference_sha256','excluded_lineages'):
            assert receipt[name]==receipts[0][name],name
        for a,b in zip(receipts[0]['epochs'],receipt['epochs']):
            for name in ('coverage','loss','residual_penalty','guard'):
                assert a[name]==b[name],name
    with torch.no_grad():
        args=(torch.from_numpy(features),['outer']*n,torch.from_numpy(anchor),torch.device('cpu'))
        reference=legacy_encoder.forward_grouped(models[0],args[0],args[1],actual,args[2],args[3])[0]
        observed=forward_grouped(models[2],args[0],args[1],empty,args[2],args[3])[0]
        torch.testing.assert_close(reference,observed,atol=0,rtol=0)
    with tempfile.TemporaryDirectory() as temporary:
        saved=save_checkpoint(models[2],Path(temporary)/'checkpoint.pt',dict(mode='none',seed=17))
        restored,identity=reload_checkpoint(saved,torch.device('cpu'))
        assert identity==dict(mode='none',seed=17)
        for name,value in models[2].state_dict().items():
            torch.testing.assert_close(value,restored.state_dict()[name],atol=0,rtol=0)
        restored_prediction,_,_=predict(restored,features,np.ones(n,bool),'outer',empty,anchor,mask)
        np.testing.assert_array_equal(restored_prediction,observed.numpy())
    try:fit(data,empty,[],'cells',17,lambda m,e:{'pass':True},fixture=True)
    except ValueError:pass
    else:raise AssertionError('cells accepted a control-free registry')
    names=['ammi_inputs_v3.py','ammi_encoder_v4.py','ammi_train_v4.py','ammi_context.py','ammi_guard_v4.py',
           'run_ammi_v4.py','ammi_bootstrap_v4.py','build_ammi_runtime_v4.py']
    result=dict(status='PASS',utc=datetime.now(timezone.utc).isoformat(),seed=17,
        old_capsule_sha256=sha256(capsule),code={name:sha256(HERE/name) for name in names},
        fixture=dict(rows=n,response_genes=g,control_genes=g,feature_dimensions=d),
        max_parameter_difference=0,max_gradient_difference=0,max_prediction_difference=0,
        rows_weights_mu_loss_coverage_identical=True,independent_positive_control_pass=True,
        structural_guards_pass=True,checkpoint_reload_exact=True,cells_without_NTC_rejected=True,
        biological_RNA_read=False,biological_benefit_measured=False)
    with out.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--out',required=True)
    prove(parser.parse_args().out)
