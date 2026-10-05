"""Launch disjoint sample partitions from the three verified non-CD4 banks."""
import argparse
import ast
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from launch_samples import call
from launch_samples_r2 import preflight
from pipeline_state import sha

HERE = Path(__file__).resolve().parent
CONFIG = [('kolf', 'kolf_pan_genome', 3), ('hct116', 'HCT116', 4), ('hek293t', 'HEK293T', 6)]


def prepare(state_path):
    state = json.loads(state_path.read_text())
    stages = []
    for alias, _, parts in CONFIG:
        producer = HERE/(alias+'_bank_stage_r1')
        frozen = json.loads((producer/'prepared.json').read_text())
        unit = frozen['spec']['name']
        info = state['units'][unit]
        source = (producer/'run.py').read_text(encoding='utf-8')
        if hashlib.sha256(source.encode()).hexdigest() != frozen['code_sha256']:
            raise ValueError('producer code changed')
        if info['state'] != 'remote_complete_manifest_checked' or sha(Path(info['receipt'])) != info['receipt_sha256']:
            raise ValueError('bank not verified')
        node = next(n for n in ast.parse(source).body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'P' for t in n.targets))
        old = ast.literal_eval(node.value)
        producer_meta = json.loads((producer/'kernel-metadata.json').read_text())
        for part in range(parts):
            slug = f'vcc-samples-{alias}-p{part}of{parts}-r1'
            stage = HERE/'other_sample_stages'/slug
            params = dict(unit=unit, spec=frozen['spec'], bank_receipt_sha256=info['receipt_sha256'],
                          bank_saved_version=info['saved_version'], part=part, parts=parts,
                          max_output_bytes=18 << 30)
            payload = {n: old[n] for n in ('bank.py', 'preparation.py')}
            files = {n:(HERE/n).read_bytes() for n in ('materialize_samples.py','materialize_partition.py')}
            files['params.json'] = json.dumps(params).encode()
            for name, b in files.items():
                payload[name] = {'data':base64.b64encode(b).decode(), 'sha256':hashlib.sha256(b).hexdigest()}
            code = 'import base64,hashlib,os,runpy,sys\nfrom pathlib import Path\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\nP='+repr(payload)+'\n'
            code += 'for n,v in P.items():\n b=base64.b64decode(v["data"]);assert hashlib.sha256(b).hexdigest()==v["sha256"];Path(n).write_bytes(b)\n'
            code += 'runpy.run_path("materialize_partition.py",run_name="__main__")\n'
            compile(code, 'run.py', 'exec')
            meta = {**producer_meta, 'id':info['kernel'].split('/')[0]+'/'+slug, 'title':slug,
                    'kernel_sources':[info['kernel'], *producer_meta['kernel_sources']]}
            frozen_part = dict(parameters=params, metadata=meta, code_sha256=hashlib.sha256(code.encode()).hexdigest(),
                               state_sha256=sha(state_path), producer_sha256=frozen['code_sha256'])
            if stage.exists():
                if json.loads((stage/'prepared.json').read_text()) != frozen_part or (stage/'run.py').read_text(encoding='utf-8') != code:
                    raise ValueError('existing stage differs; create new revision')
            else:
                stage.mkdir(parents=True)
                (stage/'run.py').write_text(code, encoding='utf-8')
                (stage/'kernel-metadata.json').write_text(json.dumps(meta, indent=1))
                (stage/'prepared.json').write_text(json.dumps(frozen_part, indent=1))
            stages.append((part, alias, stage, frozen_part))
    return sorted(stages, key=lambda x:(x[0], x[1]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--launch', action='store_true')
    p.add_argument('--preflight-out', type=Path)
    a = p.parse_args()
    stages = prepare(a.state)
    if not a.launch:
        print(json.dumps({'prepared':len(stages)})); return
    if a.preflight_out is None or a.preflight_out.exists():
        raise ValueError('new preflight receipt required')
    active = preflight(a.preflight_out)
    observed = {r['job'] for r in json.loads(a.preflight_out.read_text())['observed']}
    log = HERE/'other_sample_launches.jsonl'
    prior = [json.loads(s) for s in log.read_text().splitlines()] if log.exists() else []
    attempted = {r['slug'] for r in prior}
    for _, _, stage, frozen in stages:
        slug = frozen['metadata']['id']; owner = slug.split('/')[0]
        if slug in attempted: continue
        if slug in observed: raise ValueError('unreconciled remote job: '+slug)
        if active[owner] >= 5: continue
        rc, answer = call(owner, ['kernels','push','-p',str(stage)])
        ok = rc == 0 and 'successfully pushed' in answer and 'not valid' not in answer
        record = {**frozen,'utc':datetime.now(timezone.utc).isoformat(),'slug':slug,'stage':str(stage),
                  'accepted':ok,'answer':answer}
        with log.open('a', encoding='utf-8') as f: f.write(json.dumps(record)+'\n')
        print(json.dumps({'slug':slug,'accepted':ok}), flush=True)
        if not ok: raise RuntimeError(answer)
        active[owner] += 1


if __name__ == '__main__': main()
