"""One-shot identity and retry barriers; no actual cloud calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from continue_ammi_cells_once_v1 import Continuation,validate_jobs,write_new


def jobs():
    return [dict(slug='davidmaisterx/ammi-'+fold.lower()+'-cells-17-01a11c35-r5',
        fold=fold,mode='cells',seed=17,private=True) for fold in ('C-K562','C-iPSC')]


class ContinuationTests(unittest.TestCase):
    def test_exact_jobs_only(self):
        validate_jobs(jobs())
        for wrong in [jobs()[:1],jobs()+jobs()[:1],[dict(jobs()[0],mode='none'),jobs()[1]],
            [dict(jobs()[0],slug='another-account/job'),jobs()[1]]]:
            with self.assertRaises(ValueError):validate_jobs(wrong)

    def test_duplicate_local_claim_fails_without_cloud(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'config.json'
            write_new(config,dict(code_pins={},own=str(root),dati=str(root),state_directory=str(root/'state')))
            with patch('continue_ammi_cells_once_v1.subprocess.run') as run:
                first=Continuation(config)
                with self.assertRaises(FileExistsError):Continuation(config)
                (first.work/'STOP').touch()
                with self.assertRaises(InterruptedError):first.pause()
                run.assert_not_called()

    def test_unknown_push_stops_before_second_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            worker=Continuation.__new__(Continuation);worker.here=Path(tmp);worker.dati=Path(tmp)
            worker.event=Mock();calls=[]
            def call(script,*args):
                calls.append(Path(script).name)
                if Path(script).name=='launch_ammi_cloud_v4.py':
                    write_new(args[args.index('--out')+1],dict(accepted='unknown'))
            worker.call=call
            with self.assertRaises(ValueError):worker.dispatch(jobs())
            self.assertEqual(calls.count('launch_ammi_cloud_v4.py'),1)


if __name__=='__main__':unittest.main()
