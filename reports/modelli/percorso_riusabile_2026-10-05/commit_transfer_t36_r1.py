"""Stage only this turn's static transfer evidence, excluding active process outputs and identity."""
import subprocess
from pathlib import Path
here=Path(__file__).resolve().parent;repo=here.parents[2]
files=[Path(p) for p in ('docs/PROGETTO.md','docs/REGISTRO.md','docs/piani/strategia-scientifica.md','reports/invii/README.md')]
for name in ('README.md','ESECUZIONE_r16.md','ESECUZIONE_r17.md','download_ranges_v1.py','download_submit_frozen_r1.py','download_submit_frozen_r2.py','download_submit_frozen_r3.py','download_only_frozen_r4.py','download_submit_t36_r5.py','prepare_stream_submit_r3.py','prepare_download_only_r4.py','prepare_t36_stream_r5.py','consolidate_t36_transfer_r1.py','commit_transfer_t36_r1.py'):
 files.append((here/name).relative_to(repo))
for folder in ('reports/invii/prediction_t31_2026-10-06','reports/invii/prediction_t36_2026-10-06'):
 files.extend(p.relative_to(repo) for p in (repo/folder).glob('*') if p.is_file())
for folder in ('completion_r1','records_r1'):
 files.extend(p.relative_to(repo) for p in (here/'generation_successors_r1'/folder).glob('*') if p.is_file() and p.stat().st_size<1_000_000)
for folder in ('upload_execution_r1','upload_execution_r2','upload_execution_r3','upload_execution_r5_t36'):
 for name in ('launch.json','started.json','producer_verified.json'):
  p=here/'generation_successors_r1'/folder/name
  if p.is_file():files.append(p.relative_to(repo))
for p in (repo/'reports/invii/trial_2026-10-06').glob('*'):
 if p.is_file() and p.name.startswith(('t31_','t36_','submission_texts')):files.append(p.relative_to(repo))
paths=here/'generation_successors_r1/stage_transfer_t36_r1.txt'
paths.write_text('\n'.join(sorted(set(p.as_posix() for p in files)))+'\n',encoding='utf-8')
subprocess.run(['git','add','--pathspec-from-file='+str(paths)],cwd=repo,check=True)
print(f'Staged {len(set(files))} owned static paths; no raw identity, signed URLs or active progress.')
