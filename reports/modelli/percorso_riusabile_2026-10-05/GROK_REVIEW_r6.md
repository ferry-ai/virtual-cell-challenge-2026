# Parent review r6 — formula fixtures pass; aggregation equivalence open

Measured: parent reran8test_r6_refit fixtures PASS. r6 result/package preserved,
worker PID19956 terminated without pushes. CD4 retry alias corrected in final
dispatch. Source selection uses explicit C identity instead of max row count.

Not adopted as the requested IDENTICAL-model refit yet: mix_model.py one_vote
combines H1 train/val tables AFTER independent shrinkage (metadata explicitly
states 'not script-98 pooling before shrink'). collapse_fragment similarly
averages multiple already-shrunk BIO/condition tables. Original script98 extra
effects_from_pseudobulk(...,condition=None) pools compatible rows before
shrinkage. CD4 is its specified exception: joint per condition then gamma0.
Changing only bank does not authorize changing that statistic/aggregation.
Eight passing mix-formula fixtures do not test this end-to-end adapter equality.

H1 training_vote=false in r4 denotes subcontexts sharing one source weight,
NOT a prohibition against eligible H1train/val; H1test remains protected. Thus
do not hide issue by dropping H1 or giving two source votes. Produce the same
count_sum joint statistic from both banks, reuse outputs only where equivalent.
Audit only table counts/identities relevant to this equality, not general repo.

KOLF metabolic/strong original ERROR with no resources/scientific status,
empty saved logs, each SAMECODE retry1 accepted/RUNNING. kolf_startup_failure_r1.
CD4Stim8retry1 and panaccess1 were RUNNING at preflight_joint_progress_r4;
sourcefits_status_r7 and cd4_joint_status_r2 latest cached receipts. Keep aliases
and dedup supersedes_failed before mounting. No failed originals in kernel_sources.
