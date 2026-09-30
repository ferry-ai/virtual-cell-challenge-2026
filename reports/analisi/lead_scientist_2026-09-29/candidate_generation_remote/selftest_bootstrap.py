"""Exercise version guards without creating a venv or installing packages."""
import copy
import json
from pathlib import Path
from bootstrap_candidate_env import canonical, check_scientific

expected = json.loads((Path(__file__).resolve().parents[1] / "generator_development_r3/development_environment.json").read_text())
valid = {"python_major_minor": [3, 13], "versions": {canonical(k): v for k, v in expected["versions"].items()}}
check_scientific(expected, valid)
cases = []
different_scipy = copy.deepcopy(valid)
different_scipy["versions"]["scipy"] = "1.10.0"
cases.append(different_scipy)
missing_h5py = copy.deepcopy(valid)
del missing_h5py["versions"]["h5py"]
cases.append(missing_h5py)
wrong_python = copy.deepcopy(valid)
wrong_python["python_major_minor"] = [3, 12]
cases.append(wrong_python)
for case in cases:
    try:
        check_scientific(expected, case)
    except ValueError:
        pass
    else:
        raise AssertionError("Incompatible inherited environment accepted")
print("PASS: matching benchmark accepted; changed SciPy, missing h5py and wrong Python rejected")
