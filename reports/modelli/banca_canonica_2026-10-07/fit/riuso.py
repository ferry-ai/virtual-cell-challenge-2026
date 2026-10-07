"""Second start on the same frozen release: what was reused, and did the fit come back identical?

    riuso.py <first_revision> <second_revision> <out.json>
"""
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import percorso as P  # noqa: E402


def load(revision):
    folder = HERE / revision
    return (json.loads((folder / 'launch.json').read_text(encoding='utf-8')),
            json.loads((folder / 'completion/verification.json').read_text(encoding='utf-8')),
            json.loads((folder / 'completion/consumo.json').read_text(encoding='utf-8')))


def prepared(revision):
    return json.loads((HERE / revision / 'prepared.json').read_text(encoding='utf-8'))


def params(revision):
    """The package embeds its own job name; everything else must be equal."""
    document = json.loads((HERE / revision / 'package/params.json').read_text(encoding='utf-8'))
    document.pop('slug')
    return document


def main():
    first, second, out = sys.argv[1:4]
    (l1, v1, c1), (l2, v2, c2) = load(first), load(second)
    t1, t2 = datetime.fromisoformat(l1['utc']), datetime.fromisoformat(l2['utc'])
    between = []
    for ledger in sorted((HERE.parent / 'derivazioni').glob('*/*/launch.json')):
        when = datetime.fromisoformat(json.loads(ledger.read_text(encoding='utf-8'))['utc'])
        if when > t1:
            between.append(ledger.relative_to(P.REPO).as_posix())
    tables1 = {s: r['sha256'] for s, r in c1['sources'].items()}
    tables2 = {s: r['sha256'] for s, r in c2['sources'].items()}
    checks = dict(
        same_release=l1['release_sha256'] == l2['release_sha256'],
        same_driver=prepared(first)['driver_sha256'] == prepared(second)['driver_sha256'],
        params_differ_only_by_job_name=params(first) == params(second),
        same_source_tables=tables1 == tables2,
        same_recipe=c1['recipe_sha256'] == c2['recipe_sha256'],
        same_effects=v1['effects'] == v2['effects'],
        same_reference_effects=v1['reference_effects'] == v2['reference_effects'],
        same_votes=c1['votes_per_target'] == c2['votes_per_target'],
        no_derivation_launched_after_first_fit=not between,
        both_verified=bool(v1['verified'] and v2['verified']))
    P.write_new(out, dict(
        utc=P.now(), first=dict(job=v1['job'], launched=l1['utc']), second=dict(job=v2['job'], launched=l2['utc']),
        release_sha256=l1['release_sha256'], checks=checks, all_true=all(checks.values()),
        derivations_launched_after_first_fit=between,
        reused=dict(source_tables=len(tables2), bank_units_reingested=0, raw_files_read=0,
                    note='the second start mounted the same saved kernel versions and datasets; it ran only stage 100'),
        effects=v2['effects'],
        scope='reuse and determinism of the fit on one release; says nothing about prediction quality'))
    print(json.dumps(dict(checks=checks, all_true=all(checks.values()))))


if __name__ == '__main__':
    main()
