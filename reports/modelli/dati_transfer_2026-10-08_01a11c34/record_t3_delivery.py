"""Record verified T3 effects and map all 45 bank units to actual estimator roles."""
from collections import Counter
from percorso import HERE,read,pin,write_new,now


def main():
    folder=HERE/'extended_transfer/r1';receipt_path=folder/'fit_completion_r1/t3_consumption.json'
    receipt=read(receipt_path);plan=read(folder/'protocol.json')
    t1=read(HERE/'fit/dt1-01a11c34-r1/consumo.json');audit=read(HERE/'audit_r1.json')
    ko={s['unit'] for s in plan['sources']};roles={}
    for unit,entry in audit['units'].items():
        history=entry['historical_sources'];current=[s for s in history if s in t1['sources']]
        if unit in ko:
            actual=[c for c in receipt['ko_contexts'] if c['unit']==unit]
            role='KO_direct_vote_pooled_by_study_lineage'
            contribution=dict(contexts=len(actual),panel_context_profiles=sum(len(c['targets']) for c in actual),
                target_cells_contributing=sum(sum(c['target_cells'].values()) for c in actual),
                measured_context_pairs=sum(c['measured_pairs'] for c in actual),receipt=pin(receipt_path))
        elif current:
            source=current[0];n=t1['sources'][source]['panel_targets_voted']
            role='CRISPRi_core_direct_vote' if n else 'CRISPRi_table_read_without_panel_vote'
            contribution=dict(source=source,panel_targets=n,source_sha256=t1['sources'][source]['sha256'],
                aggregation_preserved=True,not_a_new_independent_vote=True,
                current_alltarget_chunks_read_by_T3=False)
        elif unit.startswith('k562_gwps_'):
            role='same_experiment_represented_by_legacy_K562_bulk'
            contribution=dict(source='k562',panel_targets=t1['sources']['k562']['panel_targets_voted'],
                current_SC_chunks_read_by_T3=False,no_double_vote=True)
        elif unit in ('norman2019','tian2021_crispra'):
            role='CRISPRa_separate_mechanism_not_in_LOF_transfer'
            contribution=dict(reason='no validated activation-to-loss-of-function mapping; no automatic sign inversion')
        elif unit in ('tian2019_ipsc','tian2019_neuron'):
            role='prior_CRISPRi_admission_exclusion_retained'
            contribution=dict(reason='prior own-target QC or singleton zero vote; no post-hoc reversal',
                other_role='frozen all-target ESM2 training views; actual fit consumption requires its independent receipt')
        else:
            role='not_eligible_for_direct_panel_transfer'
            contribution=dict(reason=entry['historical_destination']['role'],
                not_excluded_for_speed_or_size=True)
        roles[unit]=dict(role=role,contribution=contribution,bank_cells=entry['bank_cells'],
            original_strata_and_masks_preserved=True,bank_metadata=entry['parts'])
    if len(roles)!=45:raise ValueError('incomplete bank ledger')
    ledger=dict(utc=now(),bank_units=roles,counts=dict(Counter(v['role'] for v in roles.values())),
        protocol=pin(folder/'protocol.json'),fit_receipt=pin(receipt_path),source_audit=pin(HERE/'audit_r1.json'),
        claims_complete_D053=False,off_panel_rows_not_counted_as_direct_prediction_contributions=True,
        protected_test='H1 test never read',catalogue_gaps=pin(HERE/'coverage_ledger_r2.json'))
    write_new(HERE/'coverage_t3_r1.json',ledger)
    candidate=dict(utc=now(),name='T3-CRISPRi-KO',status='effects_verified_generation_pending',
        source_job=read(folder/'prepared.json')['slug'],protocol=pin(folder/'protocol.json'),
        receipt=pin(receipt_path),verification=pin(folder/'fit_completion_r1/verification.json'),
        coverage=pin(HERE/'coverage_t3_r1.json'),effects=receipt['effects'],
        expected_shape=[300,18533],dtype='float32',mask='observed bool; unobserved zero',
        units='natural log fold change; amplitude1.576 and original cis applied once; emitter not applied',
        ko_study_tables=receipt['ko_study_votes'],T1_null_parity=True,
        claims_improvement=False,claims_complete_D053=False,submitted=False)
    write_new(HERE/'candidate_t3_r1.json',candidate)
    print(__import__('json').dumps(dict(bank_units=len(roles),roles=ledger['counts'],effects=receipt['effects']['A'])))


if __name__=='__main__':main()
