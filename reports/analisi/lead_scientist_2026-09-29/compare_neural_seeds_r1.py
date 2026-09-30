"""Describe both complete seeds and cross-check downloaded cluster evidence; no new gate."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent


def main():
    roots = [HERE / 'kaggle_neural_r1/readout_verified_r1',
             HERE / 'kaggle_neural_seed1_r1/readout_verified_r1']
    verdicts = [json.loads((path / 'verdict.json').read_text()) for path in roots]
    rows = [pd.read_csv(path / 'per_target.csv', keep_default_na=False) for path in roots]
    keys = ['context', 'family', 'target', 'arm']
    rows = [data.set_index(keys).sort_index() for data in rows]
    assert rows[0].index.equals(rows[1].index)
    assert np.array_equal(rows[0]['common_genes'], rows[1]['common_genes'])
    assert all(json.loads((path / 'provenance.json').read_text())['verified'] for path in roots)
    families = ['k562', 'cd4', 'orion', 'ipsc', 'rpe1']
    family_rows, context_rows = [], []
    for family in families:
        item = {'family': family}
        for contrast in ['transfer', 'blind', 'swap']:
            for seed, value in enumerate(verdicts):
                item[f'{contrast}_s{seed}'] = value['contrasts'][contrast]['per_family'][family]
        family_rows.append(item)
    for context, family in rows[0].reset_index()[['context', 'family']].drop_duplicates().itertuples(index=False):
        item = {'context': context, 'family': family}
        for seed, data in enumerate(rows):
            selected = data.reset_index().query('context == @context').pivot(index='target', columns='arm', values='rank')
            assert len(selected) == 512
            for contrast in ['transfer', 'blind', 'swap']:
                item[f'{contrast}_s{seed}'] = float((selected.net - selected[contrast]).mean())
        context_rows.append(item)
    cluster_path = HERE / 'kaggle_lead_monitor/r6/seed1/neural_seed1_r1/cluster_diagnostic/diagnostic.json'
    cluster = json.loads(cluster_path.read_text())
    assert cluster['code_sha256'] == '4413ad2662b6315c9f08c396a766ba6d9d4fa066d22ad5661b06226eb416c1e9'
    assert cluster['provenance_guard']['verified']
    assert len(cluster['contexts']) == 12 and all(v['original_rank_reproduced'] for v in cluster['contexts'].values())
    for contrast in ['transfer', 'blind']:
        assert abs(cluster['contrasts'][contrast]['macro_family_delta'] - verdicts[1]['contrasts'][contrast]['macro_family_delta']) < 1e-12
    truth_pairs = rows[0].reset_index().query('arm == "net"')[['context', 'target']]
    result = {'scope': 'All five frozen folds of both seeds, no selection of a favorable seed',
              'unique_targets': int(truth_pairs.target.nunique()), 'target_context_pairs_per_seed': len(truth_pairs),
              'same_target_context_arm_index': True, 'same_common_gene_counts': True,
              'primary_eligible_by_seed': [v['eligible_for_cell_scorer'] for v in verdicts],
              'seed_contrasts': {str(i): v['contrasts'] for i, v in enumerate(verdicts)},
              'families': family_rows, 'contexts': context_rows,
              'cluster_seed1': cluster['contrasts'],
              'cluster_report_sha256': hashlib.sha256(cluster_path.read_bytes()).hexdigest(),
              'cluster_original_ranks_reproduced_all12': True,
              'context_flag_definition': 'Reader flag is only net-minus-blind point >0; not a significance test',
              'context_flag_by_seed': [v['evidence_for_context_use'] for v in verdicts],
              'new_pooled_confidence_interval_computed': False,
              'new_training_or_submission': False}
    out = HERE / 'neural_two_seeds_r1'
    out.mkdir()
    (out / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    pd.DataFrame(family_rows).to_csv(out / 'families.csv', index=False)
    pd.DataFrame(context_rows).to_csv(out / 'contexts.csv', index=False)
    print(json.dumps({key: result[key] for key in ['unique_targets', 'target_context_pairs_per_seed',
          'same_target_context_arm_index', 'primary_eligible_by_seed', 'context_flag_by_seed',
          'cluster_original_ranks_reproduced_all12']}))


if __name__ == '__main__':
    main()
