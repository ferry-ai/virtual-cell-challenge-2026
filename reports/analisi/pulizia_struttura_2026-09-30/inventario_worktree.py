"""Read-only inventory of the worktrees, branches and stash of the vcc2026 repository.

For every worktree other than main: HEAD, branch, whether HEAD is in main, unique commits,
uncommitted files (tracked changes and untracked), and for each such file whether the same
content (blob id) is reachable from main, and whether the file at the same path, or at the
same path one category level down (reports/<categoria>/...), is identical in main today.
Ignored files other than __pycache__ are counted with their bytes. For agent-hub worktrees
the hub's saved diff.patch is compared blob by blob with the files now on disk.
Nothing is written anywhere except to stdout (git hash-object is run without -w).
"""
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

MAIN = Path(r"C:/Users/ferra/OneDrive/Desktop/vcc2026")


def git(cwd, *args, check=False):
    r = subprocess.run(["git", "-C", str(cwd), "--no-optional-locks", *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 or not check else ""


def lines(s):
    return [l for l in s.split("\n") if l]


main_objects = set(l.split()[0] for l in lines(git(MAIN, "rev-list", "--objects", "main")))
main_files = set(lines(git(MAIN, "ls-tree", "-r", "--name-only", "main")))


def main_path_for(f):
    if f in main_files:
        return f
    if f.startswith("reports/"):
        rest = f[len("reports/"):]
        for m in main_files:
            if m.startswith("reports/") and m.count("/") == f.count("/") + 1 and m.endswith("/" + rest):
                return m
    return None


def mtime(p):
    return dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


def patch_post_images(patch: Path):
    out, cur = {}, None
    for line in patch.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^diff --git a/(.*) b/(.*)$", line)
        if m:
            cur = m.group(2)
            out[cur] = None
            continue
        m = re.match(r"^index ([0-9a-f]+)\.\.([0-9a-f]+)", line)
        if m and cur:
            out[cur] = m.group(2)
    return out


report = {"written": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
          "main_head": git(MAIN, "rev-parse", "main").strip(), "worktrees": []}
porcelain = git(MAIN, "worktree", "list", "--porcelain")
for block in porcelain.strip().split("\n\n"):
    kv = dict((l.split(" ", 1) + [""])[:2] for l in block.split("\n"))
    wt = Path(kv["worktree"])
    if wt == MAIN:
        continue
    head = kv["HEAD"]
    branch = kv.get("branch", "").replace("refs/heads/", "") or None
    in_main = subprocess.run(["git", "-C", str(MAIN), "merge-base", "--is-ancestor", head, "main"]).returncode == 0
    unique = lines(git(MAIN, "log", "--format=%h %ci %s", f"main..{head}"))
    tracked = lines(git(wt, "diff", "--name-only", "HEAD"))
    staged_new = lines(git(wt, "diff", "--cached", "--name-only", "--diff-filter=A", "HEAD"))
    untracked = lines(git(wt, "ls-files", "--others", "--exclude-standard"))
    ignored = [f for f in lines(git(wt, "ls-files", "--others", "--ignored", "--exclude-standard"))
               if "__pycache__" not in f]
    files = []
    for f in sorted(set(tracked) | set(untracked) | set(staged_new)):
        p = wt / f
        if not p.is_file():
            files.append({"path": f, "state": "deleted in worktree"})
            continue
        h = git(wt, "hash-object", f).strip()
        mp = main_path_for(f)
        files.append({
            "path": f, "bytes": p.stat().st_size, "mtime": mtime(p),
            "untracked": f in untracked,
            "content_in_main_history": h in main_objects,
            "main_path": mp,
            "identical_to_main_today": bool(mp) and git(MAIN, "rev-parse", f"main:{mp}").strip() == h,
        })
    newest = max((mtime(p) for p in wt.rglob("*") if p.is_file() and ".git" not in p.parts
                  and "__pycache__" not in p.parts), default=None)
    entry = {
        "worktree": str(wt), "head": head, "head_date": git(MAIN, "log", "-1", "--format=%ci", head).strip(),
        "branch": branch, "head_in_main": in_main, "unique_commits": unique,
        "uncommitted_files": files,
        "uncommitted_not_in_main_history": [x["path"] for x in files if not x.get("content_in_main_history")],
        "ignored_files": len(ignored),
        "ignored_bytes": sum((wt / f).stat().st_size for f in ignored if (wt / f).is_file()),
        "newest_file_mtime": newest,
    }
    adir = wt.parent
    if "agent-hub" in str(wt) and (adir / "diff.patch").exists():
        meta = json.loads((adir / "meta.json").read_text(encoding="utf-8"))
        post = patch_post_images(adir / "diff.patch")
        mism = [f for f, b in post.items()
                if not (wt / f).is_file() or not b or not git(wt, "hash-object", f).strip().startswith(b)]
        entry["hub"] = {
            "run": adir.parent.name, "agent": adir.name, "mode": meta.get("mode"),
            "state": meta.get("state"), "finished": meta.get("finished"),
            "diff_patch_bytes": (adir / "diff.patch").stat().st_size,
            "diff_patch_files": len(post),
            "worktree_matches_diff_patch": not mism and set(post) == {x["path"] for x in files},
        }
    report["worktrees"].append(entry)

stash = lines(git(MAIN, "stash", "list", "--format=%gd %H %ci %gs"))
report["stash"] = stash
report["branches"] = lines(git(MAIN, "branch", "-a", "--format=%(refname:short) %(objectname:short) %(committerdate:iso)"))
report["stale_worktree_metadata"] = sorted(
    d.name for d in (MAIN / ".git" / "worktrees").iterdir() if d.is_dir() and not (d / "gitdir").exists())
json.dump(report, sys.stdout, indent=1, ensure_ascii=False)
