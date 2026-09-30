"""Two checks of the rename mechanism on the real repository, read-only.

1. Without the table "Nomi cambiati" the checker must fail on the immutable citations of
   docs/LAVORO.md (it is load-bearing), and with it must pass.
2. config.repo_file, old (HEAD) and new, gives the same path for every repository path the
   recipes name, and for a sample of moved report paths: stage 100's inputs do not change.
"""
import importlib.util
import json
import subprocess
import sys
import types
from pathlib import Path

REPO = Path(r"C:/Users/ferra/OneDrive/Desktop/vcc2026")
sys.path.insert(0, str(REPO / "src"))

spec = importlib.util.spec_from_file_location("check_docs", REPO / "scripts" / "31_check_docs.py")
cd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cd)
errors = []
cd.check_links(errors)
print("with the table:", len(errors), "link errors")
real = cd.archived_paths(cd.REPO_ROOT)  # already without the old name
cd.renamed_paths = lambda root: {}
cd.archived_paths = lambda root: real
errors = []
cd.check_links(errors)
print("without the table:", len(errors), "link errors")
for e in errors:
    print("  ", e)

from vcc2026 import config as new  # noqa: E402
old_src = subprocess.run(["git", "-C", str(REPO), "show", "HEAD:src/vcc2026/config.py"],
                         capture_output=True, text=True, encoding="utf-8").stdout
old = types.ModuleType("old_config")
old.__file__ = str(REPO / "src" / "vcc2026" / "config.py")
sys.modules["old_config"] = old
exec(compile(old_src, old.__file__, "exec"), old.__dict__)
named = []
for recipe in sorted((REPO / "configs" / "recipes").glob("*.json")):
    spec = json.loads(recipe.read_text(encoding="utf-8"))
    named += [spec.get("cis", {}).get("pairs"), spec.get("gene_share", {}).get("path")]
named = sorted(set(filter(None, named)))
named += ["reports/trial_2026-09-13/", "docs/SVD_E_RANGO.md", "configs/config.yaml", "reports/gone/x.csv"]
same = [(raw, old.repo_file(raw) == new.repo_file(raw)) for raw in named]
print(f"repo_file identical on {sum(s for _, s in same)}/{len(same)} paths")
for raw, s in same:
    if not s:
        print("  DIFFERS", raw, old.repo_file(raw), new.repo_file(raw))
print("docs/LAVORO.md ->", new.repo_file("docs/LAVORO.md"))
