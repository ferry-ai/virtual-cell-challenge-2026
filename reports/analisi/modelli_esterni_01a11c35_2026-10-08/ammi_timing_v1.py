"""Measure completed phases without changing model inputs, outputs or exceptions."""
from datetime import datetime, timezone
import json
from pathlib import Path
import time


def measured(folder, phase, function, *args, **kwargs):
    path = Path(folder)/('timing_'+phase+'.json')
    if path.exists():
        raise FileExistsError(path)
    started = time.perf_counter()
    report = dict(phase=phase, started_utc=datetime.now(timezone.utc).isoformat())
    try:
        result = function(*args, **kwargs)
        report['status'] = 'COMPLETE'
        return result
    except Exception as error:
        report.update(status='ERROR', error_type=type(error).__name__)
        raise
    finally:
        report.update(seconds=time.perf_counter()-started,
                      finished_utc=datetime.now(timezone.utc).isoformat())
        with path.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
        print(json.dumps(dict(event='ammi_phase_timing', **report)), flush=True)
