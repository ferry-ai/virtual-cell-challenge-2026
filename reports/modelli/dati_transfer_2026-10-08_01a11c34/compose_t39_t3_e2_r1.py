"""Compose existing T3 and ESM2 aggregate effects locally; no fit or cloud action."""
import csv
import numpy as np
from percorso import HERE, DATA, pin, sha, write_new, now

T3 = DATA / 'processed/validazione_indipendente_8a8ca58a_2026-10-08/t3_effetti_r1/effects/effects_A.npz'
E2 = DATA / 'external_models/01a11c35/closure_stage100_r1/production/E2.npz'
OUT = DATA / 'processed/dati_transfer_2026-10-08_01a11c34/t39_t3/r1/delivery/T3_E2_fallback.npz'


def main():
    assert sha(T3) == 'b8c61f6da684f6c28107199469ac42ef030a4644176371b9723ae6e3f863f6a6'
    assert sha(E2) == 'd20fb209469a37cfe525f9a332f4cebc1dfdad9b657b4b571f0ccac8ac4cab3d'
    if OUT.exists():raise FileExistsError(OUT)
    with np.load(T3, allow_pickle=False) as z:base={k:z[k] for k in z.files}
    with np.load(E2, allow_pickle=False) as z:other={k:z[k] for k in ('lfc','observed','genes','targets')}
    for k in ('targets','genes'):assert np.array_equal(base[k],other[k])
    for key,filename,column in [('genes','gene_names.csv','gene_name'),('targets','pert_counts.csv','target_gene')]:
        with (DATA/'raw/controls'/filename).open(newline='') as f:axis=[r[column] for r in csv.DictReader(f)]
        assert base[key].astype(str).tolist()==axis
    x,m=base['lfc'],base['observed'];e,n=other['lfc'],other['observed']
    assert x.shape==e.shape==m.shape==n.shape==(300,18533)
    assert x.dtype==e.dtype==np.float32 and m.dtype==n.dtype==bool
    assert np.isfinite(x).all() and np.isfinite(e).all()
    assert np.all(x[~m]==0) and np.all(e[~n]==0)
    fill=(~m)&n;union=m|n;y=x.copy();y[fill]=(1.576*e[fill]).astype(np.float32)
    assert int(m.sum())==4467808 and int(fill.sum())==380820 and int(union.sum())==4848628
    assert np.array_equal(y.view(np.uint32)[m],x.view(np.uint32)[m])
    assert np.isfinite(y).all() and np.all(y[~union]==0)
    out=dict(base,lfc=y,observed=union);OUT.parent.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(OUT,**out)
    with np.load(OUT,allow_pickle=False) as saved:
        assert set(saved.files)==set(base)
        for key in base:
            assert np.array_equal(saved[key],out[key])
        assert np.array_equal(saved['lfc'].view(np.uint32)[m],x.view(np.uint32)[m])
    report=dict(utc=now(),status='PASS_EXACT_T3_PRESERVED_ESM2_ONLY_MISSING',candidate=pin(OUT),
        T3=pin(T3),native_E2=pin(E2),composition_code=pin(__file__),shape=[300,18533],
        axes_official=True,dtypes={'lfc':'float32','observed':'bool'},finite=True,zero_outside_mask=True,
        T3_support_pairs=4467808,T3_values_bit_identical_on_support=True,
        fallback_pairs=380820,fallback_targets=int(fill.any(1).sum()),fallback_genes=int(fill.any(0).sum()),
        union_pairs=4848628,full_row_fallback_targets=int((~m.any(1)&n.any(1)).sum()),
        amplitude_applied_once_to_fallback=1.576,cis_reapplied=False,emission_scale_applied=False,
        emitter_scale_to_apply_once=1.5,other_T3_NPZ_fields_preserved=True,reload_all_arrays_exact=True,
        no_new_fit=True,no_truth_read=True,scientific_promotion=False,complete_D053=False,
        private_dataset='davideferrante11/dt-t39-t3-e2-effects-01a11c34-r1',
        private_CPU_job='davideferrante11/dt-t39-t3-e2-upload-01a11c34-r1',
        egress_authorized=False,cloud_jobs_launched=0,VCC_entry_created=False)
    write_new(HERE/'t39_t3_effect_verified_r1.json',report)
    print(__import__('json').dumps(report))


if __name__=='__main__':main()
