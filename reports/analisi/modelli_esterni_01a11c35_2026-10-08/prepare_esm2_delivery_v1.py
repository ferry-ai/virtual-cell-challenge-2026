"""Finish production interface export and verify a small frozen inference block."""
import csv
import json
from pathlib import Path
import numpy as np
from ammi_controls_v4 import available_memory
from ammi_inputs_v3 import checked
from ammi_io_v4 import write
from esm2_closure_adapter_v1 import fallback
from esm2_inference_v1 import predict_block
from pie_adapter import sha256

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
DATA=Path('C:/Users/ferra/vcc2026-data')
def pin(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=sha256(p))

def prepare():
    if available_memory()<512*1024**2:raise RuntimeError('small interface check needs 512 MiB free')
    conversion=json.loads((HERE/'esm2_closure_conversion_r1.json').read_text())
    anchors=json.loads((ROOT/'reports/modelli/dati_transfer_2026-10-08_01a11c34/production_anchors_verified_r1.json').read_text())
    if anchors['status']!='PASS':raise ValueError('production T0 not verified')
    t0=anchors['anchors']['production_query']['effects']
    production=conversion['folds']['production']
    out=DATA/'external_models/01a11c35/esm2_production_delivery_r1';out.mkdir(exist_ok=False)
    export=fallback(t0,production['stage100']['E2'],out/'T0_E2_fallback.npz',conversion['amplitude'])
    with checked(production['stage100']['E2']).open('rb') as stream:
        with np.load(stream,allow_pickle=False) as source:genes=source['genes'].tolist();panel=source['targets'].tolist()
    esm=DATA/'external_models/01a11c35/PIE_sources/cb1aaa4e7655605bdc70a9bd77bbd62016b8c7d7/esm2'
    feature_spec=dict(meta=pin(esm/'meta.json'),array=pin(esm/'embeddings.npy'))
    spec=dict(model=production['model'],features=feature_spec,panel=panel,genes=genes,
        panel_file=pin(DATA/'raw/controls/pert_counts.csv'),axis_file=pin(DATA/'raw/controls/gene_names.csv'),
        training_manifest='completed_fits_handoff_r1.json: production',
        prediction_scale='natural logarithm fold-change, native unscaled',
        model_uses_context=False,missing_target_policy='unsupported; generic exported separately')
    write(HERE/'esm2_production_inference_r1.json',spec)
    # 8 rows x 8 genes is an interface check, not a local biological fit/score.
    positions=list(range(7))+[panel.index('TMEM104')]
    gene_positions=[0,17,257,1000,5000,10000,15000,len(genes)-1]
    predicted,mask=predict_block(production['model'],feature_spec,[panel[i] for i in positions],gene_positions)
    with np.load(checked(production['stage100']['E2']),allow_pickle=False) as source:
        expected=source['lfc'][np.ix_(positions,gene_positions)]
        expected_mask=source['observed'][np.ix_(positions,gene_positions)]
    np.testing.assert_array_equal(mask,expected_mask)
    np.testing.assert_allclose(predicted,expected,rtol=2e-6,atol=1e-7)
    write(HERE/'esm2_production_delivery_r1.json',dict(status='INTERFACE_VERIFIED_SCIENTIFIC_READOUT_PENDING',
        export=export,native=production['stage100'],model=production['model'],
        inference_spec=pin(HERE/'esm2_production_inference_r1.json'),reload_test=dict(rows=8,genes=8,
        maximum_absolute_difference=float(np.max(np.abs(predicted-expected))),support_equal=True),
        no_truth_read=True,no_new_fit=True,no_submission=True))
    print(json.dumps(dict(changed_pairs=export['changed_pairs'],reload_block_pass=True)))

if __name__=='__main__':prepare()
