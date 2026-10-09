"""Record direct user delegation and the Lead's concrete CPU input request."""
from percorso import HERE, now, pin, read, write_new

prepared=HERE/'neural_inputs_cloud_prepared_r4.json'
write_new(HERE/'neural_inputs_launch_authorization_r1.json',dict(
    recorded_utc=now(),human_source='current DATI-TRANSFER chat',
    human_text='puoi avviare altre attività se richiesto da altre chat o istanze di codex',
    request_source_thread='01a11c05-970e-7af2-a07e-3860bd74acbd',
    request_text="Richiesta operativa del Lead: riprendi l'estrazione reale degli input NTC e delle ancore AMMI già preparate, con preflight fresco e job CPU entro i consensi esistenti.",
    interpretation='The direct human delegation permits the requested private CPU input extraction; no paid quota, publication or Git push.',
    prepared=pin(prepared),jobs=[j['slug'] for j in read(prepared)['jobs']],
    scientific_scope='30 NTC bank parts, 47 contexts; 17 AMMI panel anchors and 2 exact T0 parity checks',
    paid_services=False,public_outputs=False,git_push=False,fast_jobs=False,
    source_visibility_changed=False,raw_RNA_download_to_laptop=False,
    previous_prepared_consent_false='historical pre-delegation state; retained unchanged',
    separately_authorizes_private_cross_account_transfers=False))
print('Recorded 3 private CPU jobs; no paid services or publication.')
