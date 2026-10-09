"""Resume before the first push from verified packages after local packaging recovery."""
import argparse
import json
import os
from pathlib import Path
from continue_ammi_cells_once_v1 import Continuation, check_pins, read, sha, validate_jobs, write_new, now
from ammi_inputs_v3 import checked

HERE = Path(__file__).resolve().parent


def no_prior_push(here):
    for fold in ('c-k562', 'c-ipsc'):
        for suffix in ('.json', '.json.intent.json', '.json.lock'):
            if (here/('ammi_'+fold+'_cells_auto_launch_r1'+suffix)).exists():
                raise ValueError('prior launch evidence exists; inspect remote state, never retry')


def configure():
    old = read(HERE/'ammi_cells_continuation_config_r1.json')
    check_pins(old)
    result = read(HERE/'ammi_cells_continuation_result_r1.json')
    if result['status'] != 'NEEDS_ATTENTION':
        raise ValueError('requires inspected failed preparation')
    no_prior_push(HERE)
    jobs = []
    dependencies = [Path(__file__), HERE/'compact_ammi_package_v2.py']
    for fold in ('c-k562', 'c-ipsc'):
        receipt = HERE/('ammi_'+fold+'_cells_prepared_r2.json')
        job = read(receipt)
        for key in ('code', 'metadata', 'template', 'original_prepared', 'mount_plan'):
            dependencies.append(checked(job[key]))
        if not job['lossless_repack']['extracted_bytes_identical']:
            raise ValueError('lossless parity missing')
        dependencies.append(receipt)
        jobs.append(job)
    validate_jobs(jobs)
    combined = HERE/'ammi_cells_prepared_r1.json'
    write_new(combined, dict(jobs=jobs, private=True, launch_pending=True))
    dependencies.append(combined)
    old['code_pins'].update({str(p): sha(p) for p in dependencies})
    old['state_directory'] = str(Path(old['state_directory']).with_name('ammi_cells_continuation_r2'))
    old['recovery'] = 'Local packaging only; first dispatch of unchanged two logical fits; no prior push receipts.'
    write_new(HERE/'ammi_cells_continuation_config_r2.json', old)
    print(json.dumps(dict(status='CONFIGURED_NOT_STARTED', packages=2, no_prior_push=True)))


class Recovery(Continuation):
    def __init__(self, config_path):
        self.config_path = Path(config_path)
        self.config = read(config_path)
        check_pins(self.config)
        self.here = Path(self.config['own'])
        self.dati = Path(self.config['dati'])
        no_prior_push(self.here)
        self.work = Path(self.config['state_directory'])
        self.work.mkdir(parents=True, exist_ok=False)
        write_new(self.work/'claim.json', dict(pid=os.getpid(), utc=now(), config_sha256=sha(config_path)))
        write_new(self.here/'ammi_cells_continuation_started_r2.json',
                  dict(utc=now(), pid=os.getpid(), config_path=str(config_path),
                       config_sha256=sha(config_path), state_directory=str(self.work),
                       scope='initial two cells launches after local lossless packaging recovery'))
        self.event('RECOVERED_PACKAGES_READY_FOR_FIRST_DISPATCH')

    def run(self):
        try:
            jobs = read(self.here/'ammi_cells_prepared_r1.json')['jobs']
            validate_jobs(jobs)
            self.dispatch(jobs)
            self.collect(jobs)
            result = dict(status=self.status, utc=now(), refit_performed=False)
        except Exception as error:
            self.event('NEEDS_ATTENTION', error_type=type(error).__name__)
            result = dict(status=self.status, utc=now(), error_type=type(error).__name__,
                          automatic_retry=False, remote_jobs_not_cancelled=True)
        write_new(self.here/'ammi_cells_continuation_result_r2.json', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--configure', action='store_true')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.configure == args.run:
        parser.error('select configure or run')
    if args.configure:
        configure()
    else:
        Recovery(HERE/'ammi_cells_continuation_config_r2.json').run()
