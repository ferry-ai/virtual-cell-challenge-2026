"""Pin existing T3 effects and distinguish generated cells from a verified delivery."""
import hashlib
import numpy as np
from percorso import HERE, DATA, read, pin, sha, now, write_new

path=DATA/'processed/validazione_indipendente_8a8ca58a_2026-10-08/t3_effetti_r1/effects/effects_A.npz'
candidate=read(HERE/'candidate_t3_r1.json');expected=candidate['effects']['A']
if sha(path)!=expected['sha256'] or path.stat().st_size!=expected['bytes']:raise ValueError('T3 effect changed')
with np.load(path,allow_pickle=False) as z:
    mask=z['observed']
    if mask.dtype!=np.bool_ or mask.shape!=(300,18533):raise ValueError('T3 mask schema differs')
    mask_record=dict(npz_key='observed',shape=list(mask.shape),dtype=str(mask.dtype),
        observed_pairs=int(mask.sum()),array_sha256=hashlib.sha256(mask.tobytes(order='C')).hexdigest(),
        array_digest_definition='C-order bool bytes, no header')
inventory=read(HERE/'t3_preserved_inventory_r1.json')
diagnostics=read(HERE/'t3_preserved_metadata_r1/compact_diagnostics.json')
manifest=read(HERE/'t3_preserved_metadata_r1/generation_stage45_manifest.json')
if diagnostics['shape']['n_cells']!=360000 or 'recovery_prediction.h5ad' not in inventory['output_files']:
    raise ValueError('generation/recovery evidence incomplete')
out=dict(utc=now(),candidate='T3-CRISPRi-KO / t38',effects=pin(path),mask=mask_record,
    source_fit_job=candidate['source_job'],candidate_record=pin(HERE/'candidate_t3_r1.json'),
    fit_complete=True,fit_rerun=False,
    generation_job=inventory['slug'],generation_job_status=inventory['status'],
    preserved_cell_file='recovery_prediction.h5ad',generation_shape=diagnostics['shape'],
    stored_entries=diagnostics['storage']['stored_entries'],
    stage45_original_file_record=manifest['outputs']['prediction'],
    warning='Stage45 digest is head+tail sampled, not full SHA256 of preserved cloud file. Recovery cell file listed, not downloaded/rehashed.',
    remaining=['full hash and shape/CSR/provenance verification of preserved cell file in cloud',
               'stage48 packaging on a filesystem with measured sufficient space',
               'official container validation and bit-identical payload comparison',
               'new human/coordination authorization to resume actual delivery; current request is inspection only'],
    new_generation=False,new_packaging=False,new_submission=False,
    scientific_status='candidate only; no C/J validation or official score; T36 already scored and distinct',
    known_KO_only_pairs=6722,claims_complete_D053=False,
    evidence=[pin(HERE/'t3_preserved_inventory_r1.json'),pin(HERE/'t3_preserved_metadata_r1/compact_diagnostics.json'),
              pin(HERE/'t3_preserved_metadata_r1/failure.json')])
write_new(HERE/'t3_preserved_handoff_r1.json',out)
print('Existing T3 effects and observed mask pinned; recovery cells listed, not rehashed or packaged.')
