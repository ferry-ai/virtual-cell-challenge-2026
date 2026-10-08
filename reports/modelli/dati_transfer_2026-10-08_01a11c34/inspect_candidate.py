"""Read the small production effect artifact and freeze its delivery contract."""
import csv
import json
import numpy as np
from percorso import HERE,DATA,ROOT,now,pin,read,sha,write_new


def main():
    folder=HERE/'fit/dt1-01a11c34-r1'
    proof=read(folder/'verification.json')
    if not all(proof['checks'].values()): raise ValueError('unverified fit')
    axis=[r[0] for r in list(csv.reader((DATA/'raw/controls/gene_names.csv').open()))[1:]]
    targets=[r[0] for r in list(csv.reader((DATA/'raw/controls/pert_counts.csv').open()))[1:]]
    arrays={}
    for ctx,p in proof['effects'].items():
        if sha(p['path'])!=p['sha256']:raise ValueError('effect changed')
        if p['sha256'] in arrays:continue
        with np.load(p['path'],allow_pickle=False) as z:
            if z['genes'].astype(str).tolist()!=axis or z['targets'].astype(str).tolist()!=targets:
                raise ValueError('gene or target axis differs')
            y,m=z['lfc'],z['observed']
            if y.shape!=(len(targets),len(axis)) or m.shape!=y.shape or m.dtype!=bool:
                raise ValueError('array/mask contract')
            if not np.isfinite(y).all() or (y[~m]!=0).any():raise ValueError('nonfinite or unmasked missing effect')
            arrays[p['sha256']]=dict(shape=list(y.shape),dtype=str(y.dtype),observed_pairs=int(m.sum()),
                missing_pairs=int((~m).sum()),targets_observed=int(m.any(axis=1).sum()),
                effect_rms=float(np.sqrt(np.mean(y.astype(float)**2))),all_missing_exactly_zero=True)
    consumption=read(folder/'consumo.json')
    write_new(HERE/'candidate_t1_r1.json',dict(schema=1,name='T1',owner_session='01a11c34',utc=now(),
        state='production_effects_verified_comparative_validation_pending',base='T0/t36',
        contrast='canonical r1 source admission minus doubtful RFK vote; estimator unchanged',
        release=pin(HERE/'release_t1_r1.json'),verification=pin(folder/'verification.json'),
        consumption=pin(folder/'consumo.json'),production_effects=proof['effects'],array_checks=arrays,
        code=pin(folder.parent/'driver.py'),source_code=pin(ROOT/'scripts/100_build_context_effects.py'),
        folds={'state':'pending independent VALIDAZIONE reconstruction from frozen source release',
               'manifest':pin(ROOT/'reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/manifest_fold_v1.json')},
        quantity='natural log fold-change',scale=dict(transfer_amplitude=1.576,cis_already_applied=True,
            emitter_multiplier_not_applied=1.5,second_centering_forbidden=True),
        emitter='t28/stage45 trial-ext-profile; 400 cells; gene dispersion; generator seed 20260912',
        context_dependence='effects identical across A/B/C; controls enter emitter',
        fields={'targets':'ordered unique target symbol','genes':'official ordered response axis',
                'lfc':'finite float32, targets x genes','observed':'bool; missing lfc exactly zero'},
        source_counts=dict(expected=len(consumption['sources_expected']),read=len(consumption['sources_read_by_stage100'])),
        complete_d053=False,physical_training_cells_read=0,predictive_improvement_demonstrated=False,
        vcc_package_generated=False,reserve='t36'))
    print(json.dumps(arrays))


if __name__=='__main__':main()
