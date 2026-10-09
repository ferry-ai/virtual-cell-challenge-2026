"""Forecast ledger: what was registered before each submission, what the site published, and how they differ.

Contract v3, section 4. One command rebuilds the whole ledger from committed files; no number is typed by hand:

    registro.py costruisci <ledger out.json>      every submission: registered forecasts, official members, errors
    registro.py rapporto <ledger.json> <out.md>   the tables, in Italian
    registro.py dopo-invio <ledger.json> <tNN>    the diagnosis of one submission, printed
    registro.py leggi-stato <entry id> <out dir>  one read-only status request to the site, saved as a new file

Sources: `reports/invii/prediction_t*/prediction.json` (forecasts and their reading rules), the status files the
site returned (`reports/invii/trial_*/status_*.json`, plus the folders given with --stati), and three small
curated files next to this script that hold POINTERS, not numbers: `previsioni_di_banco.json` (where a bench
forecast is written), `banchi.json` (bench versions) and `spiegazioni.json` (explanations with their evidence
status). A forecast that was not registered stays absent. Official scores are those of the validation
leaderboard on contexts A, B, C; a bench forecast is a local number and never a VCC score.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
MEMBERS = ('pds', 'mse', 'nmae', 'fid', 'reach', 'jac')
SCALED_KEY = {m: 'score_' + m for m in MEMBERS}
RAW_KEY = {'pds': 'pds_cosine', 'mse': 'expr_mse_unbiased_capped_norm', 'nmae': 'de_wilcoxon_lfc_nmae',
           'fid': 'de_wilcoxon_direction_fidelity_yield_raw', 'reach': 'de_wilcoxon_direction_reach_raw',
           'jac': 'de_wilcoxon_sig_jaccard'}
ALIASES = {**{v: k for k, v in RAW_KEY.items()}, **{k.upper(): k for k in MEMBERS}, **{k: k for k in MEMBERS}}
INDISTINCT = 0.005          # operating threshold of the submission procedure, not a statistical interval
MIN_FOR_CALIBRATION = 8     # contract v3, section 4: below this even a perfect sign agreement is not resolved at 1%
LABEL = re.compile(r'^(?:trial-|t)0*(\d+)\b')
DELTA_BAND = re.compile(r'^(t\d+)_minus_(t\d+)_band$')
SINGLE_FACTOR = re.compile(r'^single_factor_against_(t\d+)$')
UNCERTAINTY_TEXT = {'within_two_seed_sd': 'entro due deviazioni standard dei semi del banco',
                    'inside_registered_interval': "nell'intervallo registrato dal banco",
                    'inside_registered_band': 'nella banda registrata'}
MEMBER_TEXT_KEYS = ('pds_raw', 'mse_raw', 'mse', 'nmae_raw', 'fid_raw', 'reach_raw', 'jac_raw', 'jaccard_raw', 'members',
                    'others', 'frac_up_of_calls')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def label_of(name: str | None):
    match = LABEL.match(name or '')
    return 't%02d' % int(match.group(1)) if match else None


def pointer(document, dotted):
    node = document
    for key in dotted.split('.'):
        node = node[int(key)] if isinstance(node, list) else node[key]
    return node


def first_commit_utc(repo: Path, rel: str):
    """When the file entered the repository: the only time a registration can be verified against."""
    try:
        out = subprocess.run(['git', '-C', str(repo), 'log', '--diff-filter=A', '--follow', '--format=%aI', '--', rel],
                             capture_output=True, text=True, timeout=60).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return None
    return datetime.fromisoformat(out[-1]).astimezone(timezone.utc).isoformat() if out else None


def parse_time(text):
    if not text:
        return None
    try:
        when = datetime.fromisoformat(str(text).replace('Z', '+00:00'))
    except ValueError:
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


# --- what the site published ------------------------------------------------------------------------------

def read_official(repo: Path, extra_dirs=()) -> dict:
    """{label: record} from every saved status that carries a score; the last saved file of an entry wins.
    A status without a score is kept as pending."""
    paths = sorted((repo / 'reports/invii').glob('trial_*/status_*.json'))
    for folder in extra_dirs:
        paths += sorted(Path(folder).glob('status_*.json'))
    scored, pending = {}, {}
    for path in paths:
        try:
            body = read(path)
        except (ValueError, OSError):
            continue
        if not isinstance(body, dict) or not body.get('entry_id'):
            continue
        label = label_of(body.get('model_name'))
        if label is None:
            continue
        rel = path.resolve().relative_to(repo.resolve()).as_posix() if repo.resolve() in path.resolve().parents else str(path)
        if body.get('score_avg') is None:
            pending[label] = {'entry_id': body['entry_id'], 'status': body.get('status'), 'model_name': body.get('model_name'),
                              'submission_date': body.get('submission_date'), 'status_file': rel,
                              'error_info': body.get('error_info')}
            continue
        scaled = {m: body.get(SCALED_KEY[m]) for m in MEMBERS}
        present = [v for v in scaled.values() if v is not None]
        mean = sum(present) / 6 if len(present) == 6 else None
        scored[label] = {
            'entry_id': body['entry_id'], 'model_name': body.get('model_name'), 'status': body.get('status'),
            'submission_date': body.get('submission_date'), 'score_avg': body['score_avg'], 'rank': body.get('rank'),
            'scaled': scaled, 'raw': {m: body.get(RAW_KEY[m]) for m in MEMBERS},
            'panel_id': body.get('panel_id'), 'anchor_version': body.get('anchor_version'), 'status_file': rel,
            'mean_of_six_scaled': mean,
            'mean_matches_score_avg': None if mean is None else abs(mean - body['score_avg']) < 1e-9}
    for label in scored:
        pending.pop(label, None)
    return {'scored': scored, 'pending': pending}


# --- what was registered ----------------------------------------------------------------------------------

def read_prediction(repo: Path, folder: Path) -> dict:
    path = folder / 'prediction.json'
    doc = read(path)
    rel = path.relative_to(repo).as_posix()
    expected = doc.get('expected') if isinstance(doc.get('expected'), dict) else {}
    band = expected.get('score_avg_band') or doc.get('expected_score_band') or doc.get('expected_band')
    delta_bands = {}
    for key, value in expected.items():
        match = DELTA_BAND.match(key)
        if match and isinstance(value, list) and len(value) == 2:
            delta_bands[match.group(2)] = [float(value[0]), float(value[1])]
    reference = next(iter(delta_bands), None)
    how = 'delta band' if reference else None
    if reference is None:
        for key in doc:
            match = SINGLE_FACTOR.match(key)
            if match:
                reference, how = match.group(1), 'single factor'
    if reference is None and isinstance(doc.get('reference'), dict):
        reference = label_of(doc['reference'].get('name') or doc['reference'].get('label'))
        how = 'reference' if reference else None
    expected_delta = doc.get('expected_delta')
    centre = expected.get('working_centre')
    out = {
        'file': rel, 'label_text': doc.get('label') or doc.get('candidate') or doc.get('submission_name'),
        'written_utc_declared': doc.get('written_utc'), 'first_commit_utc': first_commit_utc(repo, rel),
        'score_band': [float(band[0]), float(band[1])] if band else None,
        'working_centre': float(centre) if centre is not None else None,
        'delta_bands': delta_bands,
        'expected_delta': float(expected_delta) if expected_delta is not None else None,
        'decision_threshold': doc.get('decision_threshold_absolute'),
        'reference': reference, 'reference_from': how,
        'stage84_score': doc.get('predicted_score_avg'),
        'member_expectations_verbatim': {k: expected[k] for k in MEMBER_TEXT_KEYS if k in expected} or
                                        doc.get('member_predictions') or None,
        'numeric_forecast_registered': not doc.get('numeric_forecast_not_registered', False) and bool(
            band or delta_bands or expected_delta is not None or doc.get('predicted_score_avg') is not None),
        'rule': doc.get('reading_rule_fixed_before_the_result') or doc.get('rule') or doc.get('readout_rule')
                or doc.get('falsified_if') or doc.get('reading_rule'),
    }
    return out


def registration_state(prediction: dict, submission_date) -> str:
    """verificata: the file was committed before the entry existed; dichiarata: the file says so but its commit
    is later or unknown; non preregistrata: neither."""
    sent = parse_time(submission_date)
    if sent is None:
        return "data dell'invio non salvata"
    committed = parse_time(prediction.get('first_commit_utc'))
    declared = parse_time(prediction.get('written_utc_declared'))
    if committed and committed < sent:
        return 'verificata dal commit'
    if declared and declared < sent:
        return 'dichiarata nel file'
    return 'non preregistrata'


# --- errors -----------------------------------------------------------------------------------------------

def sign(x):
    return 0 if abs(x) < 1e-12 else (1 if x > 0 else -1)


def direction(predicted, official):
    """How a signed forecast of a delta reads against the official delta."""
    if predicted is None or official is None:
        return None
    if abs(official) < INDISTINCT:
        return 'attesa nulla confermata' if sign(predicted) == 0 else 'indistinta'
    if sign(predicted) == 0:
        return 'attesa nulla smentita'
    return 'giusta' if sign(predicted) == sign(official) else 'sbagliata'


def amplitude(predicted, official):
    if predicted is None or official is None:
        return None
    return {'predicted': predicted, 'official': official, 'official_minus_predicted': official - predicted,
            'official_over_predicted': official / predicted if abs(predicted) >= 1e-9 else None}


def inside(band, value):
    if not band or value is None:
        return None
    lo, hi = band
    return {'inside': bool(lo <= value <= hi), 'distance_outside': 0.0 if lo <= value <= hi else
            (value - hi if value > hi else value - lo), 'width': hi - lo}


def bench_record(repo: Path, spec: dict, official: dict) -> dict:
    """One bench forecast, re-read from the file it was written in."""
    if not (repo / spec['path']).is_file():
        raise SystemExit('bench forecast cites a missing file: ' + spec['path'])
    doc = read(repo / spec['path']) if spec['kind'] != 'indistinct' else None
    out = {k: spec.get(k) for k in ('label', 'bench', 'kind', 'reference', 'path', 'registered_before_submission',
                                    'candidate_is_a_bench_arm', 'candidate_note', 'what_it_saw')}
    if spec['kind'] == 'score':
        out['predicted_score'] = float(pointer(doc, spec['pointer']))
    elif spec['kind'] == 'delta':
        out['predicted_delta'] = float(pointer(doc, spec['pointer']))
    elif spec['kind'] == 'delta_of_two':
        out['predicted_delta'] = float(pointer(doc, spec['pointer_a'])) - float(pointer(doc, spec['pointer_b']))
        out['bench_levels'] = {'candidate': float(pointer(doc, spec['pointer_a'])), 'reference': float(pointer(doc, spec['pointer_b']))}
    elif spec['kind'] == 'indistinct':
        out['predicted_delta'], out['band_half_width'] = 0.0, float(spec['band_half_width'])
        out['statement'] = spec['statement']
    else:
        raise ValueError('unknown forecast kind: ' + spec['kind'])
    for name in ('seeds_pointer', 'sd_pointer', 'interval_pointer'):
        if spec.get(name):
            out[name.replace('_pointer', '')] = pointer(doc, spec[name])
    members = None
    if spec.get('members'):
        m = spec['members']
        mdoc = read(repo / m['path']) if m.get('path') else doc
        node = pointer(mdoc, m['pointer'])
        values = {}
        for key, value in node.items():
            canon = ALIASES.get(key)
            if canon is None:
                continue
            value = value.get(m['field']) if isinstance(value, dict) else value
            if value is not None:
                values[canon] = float(value)
        members = {'unit': m['unit'], 'values': values, 'registered_before_submission': m.get('registered_before_submission', True),
                   'path': m.get('path') or spec['path'], 'note': m.get('note')}
    out['members'] = members
    here = official.get(spec['label'])
    ref = official.get(spec['reference']) if spec.get('reference') else None
    if here is None:
        out['official'] = None
        return out
    if spec['kind'] == 'score':
        out['official'] = {'score': here['score_avg']}
        out['amplitude'] = amplitude(out['predicted_score'], here['score_avg'])
        out['direction'] = None
        if members and members['unit'] == 'scaled_level':
            out['member_errors'] = {m: {'predicted': members['values'].get(m), 'official': here['scaled'].get(m),
                                        'official_minus_predicted': None if members['values'].get(m) is None or here['scaled'].get(m) is None
                                        else here['scaled'][m] - members['values'][m]} for m in MEMBERS}
        return out
    if ref is None:
        out['official'] = {'delta': None, 'note': 'reference without an official status'}
        return out
    delta = here['score_avg'] - ref['score_avg']
    out['official'] = {'delta': delta, 'score': here['score_avg'], 'reference_score': ref['score_avg']}
    out['direction'] = direction(out['predicted_delta'], delta)
    out['amplitude'] = amplitude(out['predicted_delta'], delta)
    uncertainty = {}
    if out.get('sd') is not None:
        uncertainty['within_two_seed_sd'] = bool(abs(delta - out['predicted_delta']) <= 2 * float(out['sd']))
    if out.get('interval') is not None:
        uncertainty['inside_registered_interval'] = bool(out['interval'][0] <= delta <= out['interval'][1])
    if spec['kind'] == 'indistinct':
        uncertainty['inside_registered_band'] = bool(abs(delta) <= out['band_half_width'])
    out['uncertainty'] = uncertainty or None
    if members:
        errors = {}
        for m in MEMBERS:
            official_delta = (None if here['scaled'].get(m) is None or ref['scaled'].get(m) is None
                              else here['scaled'][m] - ref['scaled'][m])
            predicted = members['values'].get(m)
            if members['unit'] == 'contribution_to_mean':            # compare like with like: a sixth of the member delta
                official_value = None if official_delta is None else official_delta / 6
            else:
                official_value = official_delta
            errors[m] = {'predicted': predicted, 'official': official_value,
                         'direction': None if predicted is None or official_value is None else (
                             'nessun movimento' if sign(official_value) == 0 and sign(predicted) == 0 else
                             'giusta' if sign(predicted) == sign(official_value) else 'sbagliata'),
                         'official_over_predicted': None if predicted is None or official_value is None or abs(predicted) < 1e-9
                         else official_value / predicted}
        out['member_errors'] = {'unit': members['unit'], 'members': errors}
    return out


def build(repo: Path, extra_status_dirs=(), curated_dir: Path = HERE) -> dict:
    official_all = read_official(repo, extra_status_dirs)
    official, pending = official_all['scored'], official_all['pending']
    predictions = {}
    for folder in sorted((repo / 'reports/invii').glob('prediction_t*')):
        match = re.match(r'prediction_(t\d+)_', folder.name)
        if match and (folder / 'prediction.json').is_file():
            predictions[match.group(1)] = read_prediction(repo, folder)
    for folder in sorted((repo / 'reports/invii').glob('prediction_t*')):
        match = re.match(r'prediction_(t\d+)_', folder.name)
        comparison = folder / 'comparison.json'
        if not match or match.group(1) in official or not comparison.is_file():
            continue
        label, doc = match.group(1), read(comparison)
        published = (doc.get('scaled_published') or {}).get(label) or doc.get('published_scaled') or {}
        if doc.get('score_avg') is None:
            continue
        scaled = {m: published.get(SCALED_KEY[m]) for m in MEMBERS}
        present = [v for v in scaled.values() if v is not None]
        mean = sum(present) / 6 if len(present) == 6 else None
        official[label] = {'entry_id': doc.get('entry_id'), 'model_name': None, 'status': 'published',
                           'submission_date': doc.get('submission_date'), 'score_avg': doc['score_avg'],
                           'rank': doc.get('rank') or doc.get('rank_at_scoring'), 'scaled': scaled,
                           'raw': {m: None for m in MEMBERS}, 'panel_id': doc.get('panel_id'),
                           'anchor_version': doc.get('anchor_version'),
                           'status_file': comparison.relative_to(repo).as_posix(),
                           'from_comparison_only': True, 'mean_of_six_scaled': mean,
                           'mean_matches_score_avg': None if mean is None else abs(mean - doc['score_avg']) < 1e-9}
        pending.pop(label, None)
    benches = read(curated_dir / 'banchi.json')
    bench_specs = read(curated_dir / 'previsioni_di_banco.json')
    explanations = read(curated_dir / 'spiegazioni.json')
    for spec in bench_specs:
        if spec['bench'] not in benches:
            raise SystemExit('unknown bench version: ' + spec['bench'])
    for key, bench in benches.items():
        if not (repo / bench['source']).exists():
            raise SystemExit('bench %s cites a missing source: %s' % (key, bench['source']))
    for label, items in explanations.items():
        for item in items:
            if item['stato'] not in ('verificata', 'ipotizzata', 'ignota'):
                raise SystemExit('explanation without an evidence label: ' + label)
            if item.get('fonte') and not (repo / item['fonte']).exists():
                raise SystemExit('explanation cites a missing file: ' + item['fonte'])
    submissions = {}
    for label in sorted(set(official) | set(predictions) | set(pending)):
        record = {'label': label, 'official': official.get(label), 'pending': pending.get(label),
                  'prediction': predictions.get(label), 'explanations': explanations.get(label, []),
                  'bench_forecasts': [bench_record(repo, s, official) for s in bench_specs if s['label'] == label]}
        pred, off = record['prediction'], record['official']
        sent = (off or pending.get(label) or {}).get('submission_date')
        if pred:
            pred['registration'] = registration_state(pred, sent)
        errors = {}
        if pred and off:
            band = inside(pred['score_band'], off['score_avg'])
            if band is not None:                       # an absent forecast leaves no error entry behind
                errors['score_band'] = band
            ref = official.get(pred['reference']) if pred['reference'] else None
            if ref:
                delta = off['score_avg'] - ref['score_avg']
                predicted = pred['expected_delta']
                if predicted is None and pred['working_centre'] is not None:
                    predicted = pred['working_centre'] - ref['score_avg']
                errors['delta'] = {
                    'reference': pred['reference'], 'reference_from': pred['reference_from'], 'official_delta': delta,
                    'official_is_indistinct': abs(delta) < INDISTINCT,
                    'band': inside(pred['delta_bands'].get(pred['reference']), delta),
                    'signed_forecast': predicted,
                    'signed_forecast_from': None if predicted is None else (
                        'expected_delta' if pred['expected_delta'] is not None else 'working centre minus reference'),
                    'direction': direction(predicted, delta), 'amplitude': amplitude(predicted, delta),
                    'members_official_delta': {m: (None if off['scaled'].get(m) is None or ref['scaled'].get(m) is None
                                                   else off['scaled'][m] - ref['scaled'][m]) for m in MEMBERS}}
        record['errors'] = errors or None
        submissions[label] = record
    return {'schema': 'registro-previsioni/1', 'built_utc': datetime.now(timezone.utc).isoformat(),
            'contract': 'PROTOCOLLO_v3 section 4', 'indistinct_threshold': INDISTINCT,
            'min_forecasts_for_calibration': MIN_FOR_CALIBRATION, 'benches': benches, 'submissions': submissions,
            'summary': summarise(submissions, benches)}


def summarise(submissions: dict, benches: dict) -> dict:
    scored = [s for s in submissions.values() if s['official']]
    with_prediction = [s for s in scored if s['prediction']]
    usable = [s for s in with_prediction if s['prediction']['registration'] != 'non preregistrata']
    bands = [s['errors']['score_band'] for s in usable if s['errors'] and s['errors'].get('score_band')]
    delta_bands = [s['errors']['delta']['band'] for s in usable
                   if s['errors'] and s['errors'].get('delta') and s['errors']['delta'].get('band')]
    by_bench = {}
    for s in scored:
        for f in s['bench_forecasts']:
            if f['official'] is None or not f.get('registered_before_submission', True):
                continue
            row = by_bench.setdefault(f['bench'], {'name': benches[f['bench']]['name'], 'forecasts': 0,
                                                   'signed_delta_forecasts': 0, 'direction': {}, 'labels': []})
            row['forecasts'] += 1
            row['labels'].append(s['label'])
            if f.get('direction') and f['kind'] in ('delta', 'delta_of_two'):
                row['signed_delta_forecasts'] += 1
                row['direction'][f['direction']] = row['direction'].get(f['direction'], 0) + 1
    for row in by_bench.values():
        row['calibration'] = ('sostenuta' if row['signed_delta_forecasts'] >= MIN_FOR_CALIBRATION else
                              'non sostenuta: %d previsioni puntuali con segno, ne servono almeno %d'
                              % (row['signed_delta_forecasts'], MIN_FOR_CALIBRATION))
    directions = {}
    for s in usable:
        d = (s['errors'] or {}).get('delta') or {}
        if d.get('direction'):
            directions[d['direction']] = directions.get(d['direction'], 0) + 1
    return {
        'submissions_scored': len(scored), 'with_a_registered_prediction': len(with_prediction),
        'scored_without_any_registered_prediction': sorted(s['label'] for s in scored if not s['prediction']),
        'registered_without_numeric_forecast': sorted(s['label'] for s in with_prediction
                                                      if not s['prediction']['numeric_forecast_registered']),
        'score_bands': {'read': len(bands), 'inside': sum(b['inside'] for b in bands),
                        'outside': sorted(s['label'] for s in usable if s['errors'] and s['errors'].get('score_band')
                                          and not s['errors']['score_band']['inside'])},
        'delta_bands': {'read': len(delta_bands), 'inside': sum(b['inside'] for b in delta_bands)},
        'official_deltas_below_threshold': sum(1 for s in usable if s['errors'] and s['errors'].get('delta')
                                               and s['errors']['delta']['official_is_indistinct']),
        'official_deltas_read': sum(1 for s in usable if s['errors'] and s['errors'].get('delta')),
        'signed_forecasts_direction': directions, 'by_bench': by_bench,
        'pending': sorted(s['label'] for s in submissions.values() if s['pending'] and not s['official'])}


# --- the report -------------------------------------------------------------------------------------------

def num(x, digits=4, signed=False):
    if x is None:
        return '—'
    text = ('%+.*f' if signed else '%.*f') % (digits, x)
    return text.replace('.', ',')


def report(ledger: dict) -> str:
    subs, summary = ledger['submissions'], ledger['summary']
    lines = ['# Registro previsione → punteggio', '',
             'Scritto da `invii/registro.py rapporto` dal registro costruito alle %s UTC; nessun numero è ricopiato a '
             'mano. Punteggi ufficiali: classifica di validazione sui contesti A, B, C. Le previsioni di banco sono '
             'numeri locali, mai punteggi VCC. Soglia operativa per un delta «indistinto»: %s.'
             % (ledger['built_utc'][:16].replace('T', ' '), num(ledger['indistinct_threshold'], 3)), '',
             '## 1. Ogni invio: che cosa era registrato, che cosa è uscito', '',
             '| Invio | Data | Ufficiale | PDS | MSE | NMAE | FID | REACH | JAC | Banda registrata | Esito | Riferimento | Delta ufficiale | Banda del delta | Registrazione |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---:|---|---|']
    for label, s in subs.items():
        off, pred, err = s['official'], s['prediction'], s['errors'] or {}
        if not off:
            continue
        band = err.get('score_band')
        delta = err.get('delta') or {}
        dband = delta.get('band')
        lines.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            label, (off['submission_date'] or '')[:10], num(off['score_avg'], 6, True),
            *[num(off['scaled'][m], 3, True) for m in MEMBERS],
            '—' if not pred or not pred['score_band'] else '%s … %s' % (num(pred['score_band'][0], 3), num(pred['score_band'][1], 3)),
            '—' if band is None else ('dentro' if band['inside'] else 'fuori di %s' % num(band['distance_outside'], 4, True)),
            delta.get('reference') or '—', num(delta.get('official_delta'), 4, True) if delta else '—',
            '—' if dband is None else ('dentro' if dband['inside'] else 'fuori di %s' % num(dband['distance_outside'], 4, True)),
            (pred or {}).get('registration') or 'nessuna previsione'))
    lines += ['', '**Identità di ogni riga.**', '',
              '| Invio | Candidato, come registrato | Entry | Pannello | Ancore | Stato salvato |', '|---|---|---|---|---|---|']
    for label, s in subs.items():
        off, pred = s['official'], s['prediction'] or {}
        if not off:
            continue
        text = str(pred.get('label_text') or off.get('model_name') or '—')
        lines.append('| %s | %s | `%s` | %s | %s | `%s`%s |' % (
            label, text if len(text) <= 150 else text[:147] + '…', off.get('entry_id') or '—', off.get('panel_id') or '—',
            off.get('anchor_version') or '—', off['status_file'],
            ' (solo `comparison.json`: lo stato completo non fu salvato)' if off.get('from_comparison_only') else ''))
    lines += ['', 'Banchi e scorer locale: ' + '; '.join('**%s** %s, scorer %s' % (k, b['period'], b.get('scorer', 'non registrato'))
                                                         for k, b in ledger['benches'].items()) + '.']
    lines += ['', 'Membri: valori scalati pubblicati. «Registrazione»: *verificata dal commit* se il file della '
              'previsione è entrato nel repository prima della creazione dell\'entry; *dichiarata nel file* se lo dice '
              'solo il file.', '',
              '## 2. Previsioni con un verso: direzione, ampiezza, incertezza', '',
              '| Invio | Fonte della previsione | Banco | Previsto | Ufficiale | Direzione | Ufficiale − previsto | Ufficiale / previsto | Incertezza registrata | Il candidato era un braccio del banco? |',
              '|---|---|---|---:|---:|---|---:|---:|---|---|']
    for label, s in subs.items():
        delta = (s['errors'] or {}).get('delta') or {}
        if delta.get('signed_forecast') is not None:
            a = delta['amplitude']
            lines.append('| %s | %s (contro %s) | — | %s | %s | %s | %s | %s | %s | — |' % (
                label, 'centro di lavoro' if delta['signed_forecast_from'].startswith('working') else 'delta atteso',
                delta['reference'], num(a['predicted'], 4, True), num(a['official'], 4, True), delta['direction'],
                num(a['official_minus_predicted'], 4, True), num(a['official_over_predicted'], 2),
                '—' if delta.get('band') is None else ('banda del delta: ' + ('dentro' if delta['band']['inside'] else 'fuori'))))
        for f in s['bench_forecasts']:
            if f['official'] is None:
                continue
            a = f.get('amplitude') or {}
            unc = f.get('uncertainty') or {}
            unc_text = '; '.join('%s: %s' % (UNCERTAINTY_TEXT[k], 'sì' if v else 'no') for k, v in unc.items()) or '—'
            what = 'punteggio' if f['kind'] == 'score' else 'delta contro %s' % f['reference']
            lines.append('| %s | banco, %s%s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
                label, what, '' if f.get('registered_before_submission', True) else ' (**non preregistrata**)', f['bench'],
                num(a.get('predicted'), 4, True), num(a.get('official'), 4, True), f.get('direction') or '—',
                num(a.get('official_minus_predicted'), 4, True), num(a.get('official_over_predicted'), 2), unc_text,
                {True: 'sì', False: '**no**', None: 'non noto'}[f.get('candidate_is_a_bench_arm')]))
    lines += ['', '## 3. Dove il banco ha sbagliato membro per membro', '']
    for label, s in subs.items():
        for f in s['bench_forecasts']:
            me = f.get('member_errors')
            if not me or f['official'] is None:
                continue
            if 'members' in me:
                unit = {'contribution_to_mean': 'contributo alla media (ufficiale: un sesto del delta scalato del membro)',
                        'scaled_delta': 'delta scalato del membro'}[me['unit']]
                when = '' if f['members']['registered_before_submission'] else \
                    ' La scomposizione per membro è stata riletta **dopo** l\'invio da uscite del banco che esistevano prima: serve alla diagnosi, non conta come previsione registrata.'
                lines += ['**%s, banco %s** — %s.%s' % (label, f['bench'], unit, when), '',
                          '| Membro | Banco | Ufficiale | Direzione | Ufficiale / banco |', '|---|---:|---:|---|---:|']
                for m in MEMBERS:
                    e = me['members'][m]
                    lines.append('| %s | %s | %s | %s | %s |' % (m.upper(), num(e['predicted'], 4, True), num(e['official'], 4, True),
                                                             e['direction'] or '—', num(e['official_over_predicted'], 2)))
            else:
                lines += ['**%s, banco %s** — livello scalato previsto per membro.' % (label, f['bench']), '',
                          '| Membro | Banco | Ufficiale | Ufficiale − banco |', '|---|---:|---:|---:|']
                for m in MEMBERS:
                    e = me[m]
                    lines.append('| %s | %s | %s | %s |' % (m.upper(), num(e['predicted'], 4, True), num(e['official'], 4, True),
                                                        num(e['official_minus_predicted'], 4, True)))
            lines.append('')
    lines += ['## 4. Spiegazioni degli errori, con il loro stato di prova', '',
              '| Invio | Spiegazione | Stato | Fonte |', '|---|---|---|---|']
    for label, s in subs.items():
        for item in s['explanations']:
            lines.append('| %s | %s | **%s** | %s |' % (label, item['testo'], item['stato'],
                                                       '`%s`' % item['fonte'] if item.get('fonte') else '—'))
    sb, db = summary['score_bands'], summary['delta_bands']
    lines += ['', '## 5. Che cosa si può dire, e che cosa no', '',
              '- Invii con punteggio: **%d**; con una previsione registrata: **%d**. Senza alcuna previsione: %s. '
              'Registrati senza previsione numerica: %s. Queste assenze restano assenze.'
              % (summary['submissions_scored'], summary['with_a_registered_prediction'],
                 ', '.join(summary['scored_without_any_registered_prediction']) or 'nessuno',
                 ', '.join(summary['registered_without_numeric_forecast']) or 'nessuno'),
              '- Bande del punteggio: **%d su %d** contengono l\'esito; fuori: %s. Bande del delta: **%d su %d**.'
              % (sb['inside'], sb['read'], ', '.join(sb['outside']) or 'nessuna', db['inside'], db['read']),
              '- Delta ufficiali contro il riferimento registrato: %d letti, **%d sotto la soglia di %s**: su quelli il '
              'verso ufficiale non si distingue e non conta né giusto né sbagliato.'
              % (summary['official_deltas_read'], summary['official_deltas_below_threshold'], num(ledger['indistinct_threshold'], 3)),
              '- Previsioni con un verso (centro di lavoro o delta atteso): %s.'
              % ('; '.join('%s %d' % (k, v) for k, v in sorted(summary['signed_forecasts_direction'].items())) or 'nessuna'),
              '- Previsioni puntuali di un banco su un delta, con esito: %s.' % (
                  '; '.join('%s (%s) previsto %s, ufficiale %s' % (f['label'], f['bench'], num(f['amplitude']['predicted'], 4, True),
                                                                  num(f['amplitude']['official'], 4, True))
                            for s in subs.values() for f in s['bench_forecasts']
                            if f['official'] and f['kind'] in ('delta', 'delta_of_two')) or 'nessuna'),
              '- Membri con il verso giusto, dove il banco aveva un membro: %s.' % (
                  '; '.join('%s %d su %d' % (f['label'], sum(e['direction'] == 'giusta' for e in f['member_errors']['members'].values()),
                                             sum(e['direction'] in ('giusta', 'sbagliata') for e in f['member_errors']['members'].values()))
                            for s in subs.values() for f in s['bench_forecasts']
                            if f['official'] and (f.get('member_errors') or {}).get('members')) or 'nessuno'), '',
              '| Banco | Previsioni con esito | Di cui delta con segno | Direzione | Taratura numerica |', '|---|---:|---:|---|---|']
    for key, row in sorted(summary['by_bench'].items()):
        lines.append('| %s — %s | %d (%s) | %d | %s | %s |' % (
            key, row['name'], row['forecasts'], ', '.join(row['labels']), row['signed_delta_forecasts'],
            '; '.join('%s %d' % (k, v) for k, v in sorted(row['direction'].items())) or '—', row['calibration']))
    lines += ['', '## 6. In attesa', '']
    waiting = [s for s in subs.values() if s['pending'] and not s['official']]
    if not waiting:
        lines.append('Nessun invio in attesa di punteggio.')
    for s in waiting:
        pred = s['prediction'] or {}
        lines.append('- **%s** (`%s`): stato `%s` nel file `%s`. Previsione registrata: banda %s, delta atteso %s contro %s, '
                     'soglia ±%s. Si legge con la regola scritta nel suo file quando lo stato è `published`.'
                     % (s['label'], s['pending']['entry_id'], s['pending']['status'], s['pending']['status_file'],
                        '—' if not pred.get('score_band') else '%s … %s' % (num(pred['score_band'][0], 3), num(pred['score_band'][1], 3)),
                        num(pred.get('expected_delta'), 3, True), pred.get('reference') or '—',
                        num(pred.get('decision_threshold'), 3)))
        for f in s['bench_forecasts']:
            lines.append('  - banco %s, prima dell\'invio: «%s» (`%s`).' % (f['bench'], f.get('statement') or f['kind'], f['path']))
    return '\n'.join(lines) + '\n'


def after_submission(ledger: dict, label: str) -> str:
    s = ledger['submissions'].get(label)
    if s is None:
        return 'nessun invio %s nel registro' % label
    if not s['official']:
        return '%s: nessun punteggio pubblicato (%s)' % (label, (s['pending'] or {}).get('status', 'nessuno stato salvato'))
    out = ['%s: ufficiale %s' % (label, num(s['official']['score_avg'], 6, True))]
    err = s['errors'] or {}
    if err.get('score_band'):
        out.append('  banda del punteggio: %s' % ('dentro' if err['score_band']['inside'] else 'FUORI di %s' % num(err['score_band']['distance_outside'], 4, True)))
    d = err.get('delta')
    if d:
        out.append('  delta contro %s: %s%s' % (d['reference'], num(d['official_delta'], 4, True),
                                                ' (sotto la soglia: indistinto)' if d['official_is_indistinct'] else ''))
        if d.get('direction'):
            out.append('  direzione della previsione con segno: %s; ufficiale − previsto %s'
                       % (d['direction'], num(d['amplitude']['official_minus_predicted'], 4, True)))
        moved = sorted(((m, v) for m, v in d['members_official_delta'].items() if v is not None), key=lambda kv: -abs(kv[1]))
        out.append('  membri che si muovono di più: ' + ', '.join('%s %s' % (m.upper(), num(v, 3, True)) for m, v in moved[:3]))
    for f in s['bench_forecasts']:
        a = f.get('amplitude') or {}
        out.append('  banco %s: previsto %s, ufficiale %s, direzione %s, rapporto %s; incertezza %s' % (
            f['bench'], num(a.get('predicted'), 4, True), num(a.get('official'), 4, True), f.get('direction') or '—',
            num(a.get('official_over_predicted'), 2),
            '; '.join('%s: %s' % (UNCERTAINTY_TEXT[k], 'sì' if v else 'no') for k, v in (f.get('uncertainty') or {}).items()) or '—'))
        me = (f.get('member_errors') or {}).get('members')
        if me:
            wrong = [m.upper() for m in MEMBERS if me[m]['direction'] == 'sbagliata']
            out.append('    membri con verso sbagliato: ' + (', '.join(wrong) or 'nessuno'))
    if not s['prediction']:
        out.append('  nessuna previsione registrata: niente da confrontare')
    return '\n'.join(out)


def fetch_status(entry: str, out_dir: Path) -> Path:
    """One read-only status request with the project's vcc wrapper; the answer is saved as it is, in a new file."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = out_dir / ('status_%s_%s.json' % (entry, stamp))
    run = subprocess.run(['cmd', '/c', str(REPO / 'scripts' / 'vcc.cmd'), '--json', 'status', entry],
                         capture_output=True, text=True, timeout=120)
    if run.returncode:
        raise SystemExit('vcc status failed: ' + (run.stdout + run.stderr)[-500:])
    body = json.loads(run.stdout)
    with out.open('x', encoding='utf-8') as fh:
        json.dump(body, fh, indent=2)
        fh.write('\n')
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('costruisci')
    p.add_argument('out')
    p.add_argument('--stati', action='append', default=[])
    p = sub.add_parser('rapporto')
    p.add_argument('ledger')
    p.add_argument('out')
    p = sub.add_parser('dopo-invio')
    p.add_argument('ledger')
    p.add_argument('label')
    p = sub.add_parser('leggi-stato')
    p.add_argument('entry')
    p.add_argument('out_dir')
    args = parser.parse_args()
    if args.command == 'costruisci':
        ledger = build(REPO, [Path(d) for d in args.stati])
        with Path(args.out).open('x', encoding='utf-8') as fh:
            json.dump(ledger, fh, indent=1, ensure_ascii=False)
            fh.write('\n')
        print(json.dumps(ledger['summary'], indent=1, ensure_ascii=False))
    elif args.command == 'rapporto':
        text = report(read(args.ledger))
        with Path(args.out).open('x', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('scritto', args.out)
    elif args.command == 'dopo-invio':
        sys.stdout.reconfigure(encoding='utf-8')
        print(after_submission(read(args.ledger), args.label))
    else:
        path = fetch_status(args.entry, Path(args.out_dir))
        body = read(path)
        print(json.dumps({'file': str(path), **{k: body.get(k) for k in ('entry_id', 'status', 'score_avg', 'error_info')}}))


if __name__ == '__main__':
    main()
