"""Record the original human consent independently read through read_thread."""
from percorso import HERE, read, sha, write_new

plan = HERE/'cross_account_access_plan_r1.json'
document = read(plan)
write_new(HERE/'multi_account_authorization_r3.json', dict(
    verified_utc='2026-10-08T21:35:17Z',
    evidence_method='read_thread: original human userMessage, not an agent summary',
    thread_id='01a11c35-6e02-7d20-bd83-d8685a490980',
    human_message_id='01a11d70-7683-7c73-b020-068d2c2d141a',
    question_call='call_d00b2526c23e4a11b662023128fe9811',
    human_answer='Sì, autorizzo anche questi trasferimenti privati',
    extends='multi_account_authorization_r2.json',
    plan_sha256=sha(plan),
    authorized_folds={f:{k:v[k] for k in ('destination','additional_chunks','additional_bytes')}
                      for f,v in document['folds'].items()},
    source_owner='davideferrante11',
    handling=dict(private_jobs_only=True, temporary_locators_outside_git_and_logs=True,
        no_local_rna_download=True, no_publication=True, no_acl_changes=True),
    compute='No new compute requested here. MODELLI-ESTERNI owns previously authorized fit jobs.'))
