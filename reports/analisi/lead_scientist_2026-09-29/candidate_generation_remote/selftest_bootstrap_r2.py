"""No installs: reject base and escaped library/script destinations."""
from pathlib import Path
import tempfile
from bootstrap_candidate_env_r2 import check_install_destination

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    env = root / "venv"
    base = root / "base"
    valid = {"purelib": env / "lib/site-packages", "platlib": env / "lib/site-packages", "scripts": env / "bin"}
    check_install_destination(env, base, valid)
    cases = [(base, base, valid)]
    for name in valid:
        invalid = dict(valid)
        invalid[name] = base / name
        cases.append((env, base, invalid))
    for prefix, base_prefix, paths in cases:
        try:
            check_install_destination(prefix, base_prefix, paths)
        except ValueError:
            pass
        else:
            raise AssertionError("Installation outside the isolated venv was accepted")
print("PASS: venv paths accepted; base interpreter and three escaping destinations rejected")
