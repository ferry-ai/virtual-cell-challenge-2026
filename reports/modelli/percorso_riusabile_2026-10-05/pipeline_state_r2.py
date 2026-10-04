"""Isolate Kaggle SDK authentication per account; preserve the original supervisor."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pipeline_state as original


def isolated_receipts(owner, job, out):
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--fetch', owner, job, str(out)],
                            env={**os.environ, 'KAGGLE_CONFIG_DIR': str(Path.home()/original.CONFIG[owner])},
                            capture_output=True, encoding='utf-8', errors='replace', timeout=180)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return json.loads(result.stdout)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--fetch':
        print(json.dumps(original.complete_receipts(sys.argv[2], sys.argv[3], Path(sys.argv[4]))))
    else:
        original.complete_receipts = isolated_receipts
        original.main()
