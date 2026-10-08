"""Audit panel query eligibility from frozen metadata, without truth responses."""
import csv
from pathlib import Path
from percorso import DATA, HERE, ROOT, now, pin, read, sha, write_new


def main(out):
    validation = ROOT/'reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/manifest_fold_v2.json'
    manifest = read(validation)
    panel_path = DATA/manifest['panel']['file']
    if sha(panel_path) != manifest['panel']['file_sha256']:
        raise ValueError('panel changed')
    with panel_path.open(encoding='utf-8-sig', newline='') as f:
        panel = sorted({r['target_gene'] for r in csv.DictReader(f)})
    if len(panel) != 300: raise ValueError('panel size changed')
    folds = {}
    for fold in ('C-K562', 'C-iPSC', 'J-K562', 'J-iPSC'):
        release_path = HERE/f'training_release_{fold}_r1.json'
        release = read(release_path)
        if sha(release['view']['path']) != release['view']['sha256']:
            raise ValueError('view changed')
        view = read(release['view']['path'])
        seen = {t for c in view['chunks'] for t in c['targets']}
        unseen = sorted(set(panel) - seen)
        eligible = sorted(set(panel) & seen) if view['regime'] == 'C' else view['effective_split']['hidden_targets']
        if view['regime'] == 'J' and set(eligible) & seen:
            raise ValueError('hidden target reached J')
        folds[fold] = dict(release=pin(release_path), eligible_query_targets=eligible,
            eligible_count=len(eligible), panel_targets_not_seen_in_training=unseen,
            held_context_ids=sorted(release['selection']['removed_contexts']),
            context_group=release['lineage'],
            query_truth_availability='not checked; VALIDAZIONE selects observed truth per registered fold',
            no_training_rows_dropped_for_query_support=True)
        print(fold, len(eligible), 'eligible panel queries;', len(unseen), 'panel targets unseen in training')
    write_new(out, dict(utc=now(), panel=pin(panel_path), validation_manifest=pin(validation),
        folds=folds, truth_responses_read=False, model_fit=False))


if __name__ == '__main__':
    import sys
    main(Path(sys.argv[1]))
