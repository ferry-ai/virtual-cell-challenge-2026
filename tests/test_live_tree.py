"""The maps agents navigate by must match the tree (D-043).

Each test is a way an agent gets lost, or the tree grows back what a cleanup removed:

* the stage table of `docs/LAVORO.md` §4 lists exactly the scripts in `scripts/`, and its
  next free number is the next number;
* the module table of `src/vcc2026/CLAUDE.md` lists exactly the modules, with the stages and
  the modules that import each one;
* every definition in `src/vcc2026` is reachable from a live stage, and no file imports a
  name it never uses;
* the repository map of `CLAUDE.md`, the index of `reports/CLAUDE.md` and the map of stages by
  role in `scripts/CLAUDE.md` name exactly what is there, and no stage hardcodes a data path.

Standard library only: it reads the code, it does not import it.
"""

from __future__ import annotations

import ast
import fnmatch
import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src" / "vcc2026"
SCRIPTS = REPO / "scripts"

# Kept although no stage calls them: tests of live code need them.
TEST_SUPPORT = {
    "reset_caches": "config: forgets the cached roots when a test changes the environment",
    "local_fetcher": "remote_csr: the offline fetcher of the byte-range tests",
    "assert_payloads_equivalent": "packaging: the parity oracle of D-019",
}


def stages() -> dict[int, Path]:
    return {int(p.name.split("_", 1)[0]): p for p in SCRIPTS.glob("[0-9]*_*.py")}


def modules() -> list[str]:
    return sorted(p.stem for p in SRC.glob("*.py") if p.stem != "__init__")


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_modules(tree: ast.Module, *, package_relative: bool) -> set[str]:
    """The vcc2026 modules a file imports, by any of the forms used in this repository."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "vcc2026":
                found.update(alias.name for alias in node.names)
            elif module.startswith("vcc2026."):
                found.add(module.split(".")[1])
            elif package_relative and node.level == 1 and module:
                found.add(module.split(".")[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("vcc2026."):
                    found.add(alias.name.split(".")[1])
    return found & set(modules())


def section(text: str, heading_start: str) -> str:
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(heading_start))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


class TestStageTable(unittest.TestCase):
    """docs/LAVORO.md §4 is where an agent learns which stages exist."""

    def setUp(self):
        self.text = (REPO / "docs" / "LAVORO.md").read_text(encoding="utf-8")
        self.table = section(self.text, "## 4.")

    def test_every_script_is_in_the_table_and_every_row_is_a_script(self):
        listed = {int(n) for n in re.findall(r"`scripts/(\d+)_[^`]*\.py`", self.table)}
        self.assertEqual(sorted(listed), sorted(stages()),
                         "add the missing rows to docs/LAVORO.md §4, or remove the rows of "
                         "scripts that left the tree")

    def test_the_next_free_number_is_the_next_number(self):
        match = re.search(r"prossimo numero libero è \*\*(\d+)\*\*", self.table)
        self.assertIsNotNone(match, "docs/LAVORO.md §4 no longer states the next free number")
        self.assertEqual(int(match.group(1)), max(stages()) + 1)


class TestModuleTable(unittest.TestCase):
    """src/vcc2026/CLAUDE.md says what changes when a module changes."""

    def setUp(self):
        self.rows = {}
        text = (SRC / "CLAUDE.md").read_text(encoding="utf-8")
        for line in text.splitlines():
            match = re.match(r"\| `(\w+)\.py` \|", line)
            if match:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                self.rows[match.group(1)] = cells

    def test_every_module_has_a_row_and_every_row_a_module(self):
        self.assertEqual(sorted(self.rows), modules())

    def test_the_importing_stages_are_the_real_ones(self):
        real = {m: set() for m in modules()}
        for number, path in stages().items():
            for module in imported_modules(parse(path), package_relative=False):
                real[module].add(number)
        for module, cells in self.rows.items():
            with self.subTest(module=module):
                self.assertEqual(sorted(int(n) for n in re.findall(r"\d+", cells[2])),
                                 sorted(real[module]))

    def test_the_importing_modules_are_the_real_ones(self):
        real = {m: set() for m in modules()}
        for module in modules():
            for used in imported_modules(parse(SRC / f"{module}.py"), package_relative=True):
                if used != module:
                    real[used].add(module)
        for module, cells in self.rows.items():
            with self.subTest(module=module):
                self.assertEqual(sorted(re.findall(r"`(\w+)`", cells[3])), sorted(real[module]))


def names_in(node: ast.AST) -> set[str]:
    """Every name a piece of code can reach: names, attributes, imported names, and
    identifier-like strings (a getattr, a registry key). Errs towards keeping code."""
    out = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            out.add(sub.id)
        elif isinstance(sub, ast.Attribute):
            out.add(sub.attr)
        elif isinstance(sub, ast.ImportFrom):
            out.update(alias.name for alias in sub.names)
        elif isinstance(sub, ast.Constant) and isinstance(sub.value, str) and sub.value.isidentifier():
            out.add(sub.value)
    return out


def is_dunder_all(node: ast.stmt) -> bool:
    return isinstance(node, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets)


class TestNoDeadCode(unittest.TestCase):
    """What no live stage reaches regrows unnoticed: D-040 and D-043 each removed hundreds of lines."""

    def test_every_definition_is_reached_from_a_live_stage(self):
        definitions: dict[tuple[str, str], ast.AST] = {}
        seeds: set[str] = set()
        for path in sorted(SRC.glob("*.py")):
            for node in parse(path).body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    definitions[(path.stem, node.name)] = node
                elif is_dunder_all(node):
                    continue
                elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        if isinstance(target, ast.Name):
                            definitions[(path.stem, target.id)] = node
                    if node.value is not None:
                        seeds |= names_in(node.value)  # evaluated at import
                else:
                    seeds |= names_in(node)  # module-level code runs at import
        for path in stages().values():
            seeds |= names_in(parse(path))

        reached, frontier = set(), set(seeds)
        while frontier:
            name = frontier.pop()
            for key, node in definitions.items():
                if key[1] == name and key not in reached:
                    reached.add(key)
                    frontier |= names_in(node)
        dead = sorted(f"{module}.{name}" for module, name in definitions
                      if (module, name) not in reached and name not in TEST_SUPPORT)
        self.assertEqual(dead, [], "no live stage reaches these: archive them (docs/LAVORO.md §5), "
                                   "or list a test helper in TEST_SUPPORT with its reason")

    def test_no_file_imports_a_name_it_never_uses(self):
        unused = []
        for path in sorted([*SRC.glob("*.py"), *SCRIPTS.glob("*.py"), *(REPO / "tests").glob("*.py")]):
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text)
            lines = text.splitlines()
            exported = set()
            for node in tree.body:
                if is_dunder_all(node) and isinstance(node.value, (ast.List, ast.Tuple)):
                    exported |= {e.value for e in node.value.elts if isinstance(e, ast.Constant)}
            used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                        continue
                    if "noqa: F401" in lines[node.lineno - 1]:
                        continue
                    for alias in node.names:
                        bound = (alias.asname or alias.name).split(".")[0]
                        if bound not in used and bound not in exported:
                            unused.append(f"{path.relative_to(REPO).as_posix()}:{node.lineno} {bound}")
        self.assertEqual(unused, [])

    def test_no_stage_hardcodes_a_data_path(self):
        """Paths come from config.paths() or from arguments; docstrings may show examples."""
        offenders = []
        for path in sorted(SCRIPTS.glob("*.py")):
            tree = parse(path)
            docstrings = {id(node.body[0].value) for node in ast.walk(tree)
                          if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef))
                          and node.body and isinstance(node.body[0], ast.Expr)
                          and isinstance(node.body[0].value, ast.Constant)}
            for node in ast.walk(tree):
                if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                        and id(node) not in docstrings
                        and ("C:/Users" in node.value or "C:\\Users" in node.value)):
                    offenders.append(f"{path.name}:{node.lineno}")
        self.assertEqual(offenders, [])


def tracked(prefix: str = "") -> list[str]:
    """Tracked paths, relative to the repository, under an optional prefix."""
    try:
        out = subprocess.run(["git", "-C", str(REPO), "ls-files", "--", prefix or "."],
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        raise unittest.SkipTest("git is not available")
    return out.splitlines()


def children(prefix: str) -> set[str]:
    """Entries directly under a folder: files by name, folders as 'name/'."""
    names = set()
    for path in tracked(prefix):
        rest = path[len(prefix):]
        head, sep, _ = rest.partition("/")
        names.add(head + "/" if sep else head)
    return names


def fenced_block_after(text: str, heading: str) -> str:
    """The first ``` block after a heading."""
    after = text[text.index(heading):]
    start = after.index("```") + 3
    return after[start:after.index("```", start)]


class TestFolderMaps(unittest.TestCase):
    """The map in CLAUDE.md and the folder indexes are how an agent finds its way in."""

    def test_the_repository_map_names_every_top_level_entry(self):
        block = fenced_block_after((REPO / "CLAUDE.md").read_text(encoding="utf-8"), "## Repository map")
        drawn = [m.group(1) for m in re.finditer(r"[├└]── (\S+)", block)]
        patterns = [d.split("/")[0] + ("/" if "/" in d else "") for d in drawn]
        entries = {e for e in children("") if not e.startswith(".")}
        missing = sorted(e for e in entries if not any(fnmatch.fnmatch(e, p) for p in patterns))
        stale = sorted(p for p in patterns if not any(fnmatch.fnmatch(e, p) for e in entries))
        self.assertEqual(missing, [], "add these to the repository map in CLAUDE.md")
        self.assertEqual(stale, [], "the repository map in CLAUDE.md names what is not there")

    def test_the_reports_index_names_every_folder_once(self):
        text = (REPO / "reports" / "CLAUDE.md").read_text(encoding="utf-8")
        index = section(text, "## Index")
        listed = [t for t in re.findall(r"`([^`]+)`", index)
                  if "<" not in t and "/" not in t.rstrip("/")]
        entries = children("reports/") - {"CLAUDE.md"}
        self.assertEqual(sorted(t for t in set(listed) if listed.count(t) > 1), [],
                         "a folder is listed twice in reports/CLAUDE.md")
        self.assertEqual(sorted(entries - set(listed)), [],
                         "add these folders to the index in reports/CLAUDE.md")
        self.assertEqual(sorted(set(listed) - entries), [],
                         "the index in reports/CLAUDE.md names folders that are not there")

    def test_the_map_of_stages_by_role_names_every_stage_once(self):
        block = fenced_block_after((SCRIPTS / "CLAUDE.md").read_text(encoding="utf-8"), "# scripts")
        numbers = [int(n) for n in re.findall(r"(?<![\w.])(\d{2,3})(?![\w.])", block)]
        self.assertEqual(sorted(n for n in set(numbers) if numbers.count(n) > 1), [])
        self.assertEqual(sorted(numbers), sorted(stages()))


if __name__ == "__main__":
    unittest.main()
