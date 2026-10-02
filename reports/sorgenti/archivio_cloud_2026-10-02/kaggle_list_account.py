"""List the private datasets of one Kaggle account whose token file has a non-standard name.

The token is passed to the Kaggle CLI through its documented environment variables, in the child process only;
it is never printed or written anywhere.
"""
import json
import os
import subprocess
import sys

token_file, *args = sys.argv[1:]
with open(token_file, encoding="utf-8") as fh:
    tok = json.load(fh)
env = {k: v for k, v in os.environ.items() if k != "KAGGLE_CONFIG_DIR"}
env["KAGGLE_USERNAME"] = tok["username"]
env["KAGGLE_KEY"] = tok["key"]
p = subprocess.run([r"C:\Users\ferra\vcc2026-data\.venv\Scripts\kaggle.exe", *args], env=env, capture_output=True, text=True)
sys.stdout.write(p.stdout.replace(tok["key"], "***"))
sys.stderr.write(p.stderr.replace(tok["key"], "***"))
