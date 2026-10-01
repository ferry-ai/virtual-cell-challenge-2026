"""Check snapshot preservation and documentation-only scope against the recorded base."""

import hashlib
import json
import posixpath
import re
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def main():
    manifest = json.loads((HERE / "snapshot_manifest.json").read_text(encoding="utf-8"))
    mapping = {row["source"]: row["snapshot"] for row in manifest["files"]}
    checks = []
    for row in manifest["files"]:
        name = row["source"]
        original = subprocess.check_output(["git", "show", f"{manifest['base_commit']}:{name}"], cwd=ROOT)
        old = original.decode("utf-8-sig").replace("\r\n", "\n")

        def rebase(match):
            url = match.group(2)
            if not url or url.startswith(("#", "/")) or re.match(r"[a-zA-Z][\w+.-]*:", url):
                return match.group(0)
            file, sep, anchor = url.partition("#")
            source = posixpath.normpath(posixpath.join(posixpath.dirname(name), file))
            relative = posixpath.relpath(mapping.get(source, source), posixpath.dirname(row["snapshot"]))
            return match.group(1) + relative + sep + anchor + match.group(3)

        expected = re.sub(r"(\]\()([^\s)]+)(\))", rebase, old)
        actual = (ROOT / row["snapshot"]).read_bytes()
        checks.append({"source": name,
                       "prose_and_links_preserved": actual.decode("utf-8") == expected,
                       "snapshot_hash_unchanged": hashlib.sha256(actual).hexdigest() == row["snapshot_sha256"]})
    changed = subprocess.check_output(["git", "-c", "core.safecrlf=false", "diff", "--name-only", manifest["base_commit"]], cwd=ROOT, text=True).splitlines()
    unexpected = [name for name in changed if not (
        name.startswith("docs/") and not name.startswith("docs/checkpoints/0")
        or name in {"README.md", "CLAUDE.md", ".gitignore", "scripts/CLAUDE.md",
                    "configs/CLAUDE.md", "scripts/84_predict_official.py"}
        or name.startswith("reports/") and name.endswith("/README.md")
        or name.startswith("reports/analisi/rinnovo_repo_2026-10-01/")
    )]
    stage = (ROOT / "scripts/84_predict_official.py").read_text(encoding="utf-8")
    old_stage = subprocess.check_output(["git", "show", f"{manifest['base_commit']}:scripts/84_predict_official.py"], cwd=ROOT, text=True)
    body_unchanged = stage[stage.index("from __future__"):].replace("\r\n", "\n") == old_stage[old_stage.index("from __future__"):].replace("\r\n", "\n")
    extra_names = ["docs/PROMPT_CLAUDE.md", "docs/PROMPT_CLAUDE_TEAMMATE.md",
                   "docs/CONSEGNA_TEAMMATE.md", "docs/storico/rinnovo_2026-10-01/INDICE.md",
                   "reports/analisi/rinnovo_repo_2026-10-01/README.md",
                   "reports/analisi/rinnovo_repo_2026-10-01/VERIFICHE.md"]
    broken_links = []
    link_count = 0
    for name in extra_names:
        file = ROOT / name
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", file.read_text(encoding="utf-8")):
            if re.match(r"[a-zA-Z][\w+.-]*:", target):
                continue
            link_count += 1
            destination, _, anchor = target.partition("#")
            other = (file.parent / destination).resolve() if destination else file
            if not other.exists():
                broken_links.append({"file": name, "target": target, "reason": "missing"})
            elif anchor and other.is_file():
                headings = [line.lstrip("#").strip().lower() for line in other.read_text(encoding="utf-8").splitlines() if line.startswith("#")]
                anchors = {"".join(ch for ch in heading if ch.isalnum() or ch in " _-").replace(" ", "-") for heading in headings}
                if anchor not in anchors:
                    broken_links.append({"file": name, "target": target, "reason": "anchor"})
    ok = all(row["prose_and_links_preserved"] and row["snapshot_hash_unchanged"] for row in checks) and not unexpected and body_unchanged and not broken_links
    result = {"checked_at": datetime.now().astimezone().isoformat(), "base_commit": manifest["base_commit"],
              "snapshots": checks, "changed_tracked_files": changed,
              "unexpected_tracked_changes": unexpected, "stage84_runtime_unchanged": body_unchanged,
              "additional_local_links_checked": link_count, "broken_additional_links": broken_links,
              "passed": ok}
    (HERE / "verification.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Snapshot preservation: {len(checks)}; runtime unchanged: {body_unchanged}; passed: {ok}")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
