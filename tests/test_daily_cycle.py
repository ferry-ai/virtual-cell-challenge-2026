"""Tests for the daily chain orchestrator (scripts/32_daily_cycle.py).

The agents are replaced by two small Python programs that honour the same command
line, so the whole chain -- seal, review, sheet check, worktree, commit, markers --
runs for real inside a temporary git repository.
"""
import datetime as dt
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses look their module up while decorating
    spec.loader.exec_module(module)
    return module


cycle_mod = load("daily_cycle", "32_daily_cycle.py")

DATE = dt.date(2026, 9, 17)

SHEET_OK = textwrap.dedent("""\
    # Foglio per Claude

    ## Obiettivo
    Implementare lo strumento delle ancore (I-1).

    ## Contesto
    La stima di oggi sta in reports/leaderboard_2026-09-16/snapshot.md.

    ## Passi
    1. Scrivere lo script.
    2. Scrivere i test.

    ## Regola di accettazione
    Riproduce le righe della fotografia entro 0,002.

    ## Vincoli
    Solo libreria standard.

    ## Consegna
    Script, test e esito.
    """)

FAKE_CODEX = textwrap.dedent("""\
    import json, os, sys
    from pathlib import Path
    args = sys.argv[1:]
    if args[:1] == ["--version"]:
        print("codex-cli fake")
        sys.exit(0)
    prompt = sys.stdin.read()
    cycle = Path(args[args.index("-C") + 1])
    reply_path = Path(args[args.index("-o") + 1])
    (cycle / "02_revisione.md").write_text("# Revisione\\n\\nprompt di " + str(len(prompt)) + " caratteri\\n", encoding="utf-8")
    sheet = os.environ.get("FAKE_SHEET")
    if sheet:
        (cycle / "03_prompt_claude.md").write_text(Path(sheet).read_text(encoding="utf-8"), encoding="utf-8")
    reply = {"data": "2026-09-17", "esito": "prompt_pronto", "motivo": "passo scelto",
             "piano_verificato": True,
             "passo": {"id": "I-1", "titolo": "Ancore", "perche": "serve alla scala",
                       "metriche": ["tutte"]},
             "critiche_bloccanti": [], "domande_per_il_lead": []}
    reply_path.write_text(json.dumps(reply), encoding="utf-8")
    """)

FAKE_CLAUDE = textwrap.dedent("""\
    import json, os, sys
    from pathlib import Path
    args = sys.argv[1:]
    if args[:1] == ["--version"]:
        print("2.1.0 (Claude Code fake)")
        sys.exit(0)
    if args[:2] == ["auth", "status"]:
        logged = os.environ.get("FAKE_CLAUDE_LOGGED", "1") == "1"
        print(json.dumps({"loggedIn": logged, "authMethod": "fake" if logged else "none"}))
        sys.exit(0)
    assert "-p" in args, args
    prompt = sys.stdin.read()
    Path("src").mkdir(exist_ok=True)
    Path("src/new_step.py").write_text("VALUE = 1\\n", encoding="utf-8")
    Path(".ciclo/04_esito_claude.md").write_text("# Esito\\n\\nfatto\\n", encoding="utf-8")
    reply = {"esito": "completato", "passo_id": "I-1", "sintesi": "script scritto",
             "file_toccati": ["src/new_step.py"], "verifiche": "ok", "blocchi": []}
    print(json.dumps({"type": "result", "result": "fatto", "session_id": "s-1",
                      "structured_output": reply}))
    """)

GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
}


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout.strip()


class ChainFixture(unittest.TestCase):
    """A throwaway repository shaped like this one, with fake agents."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        env = patch.dict(os.environ, {**GIT_IDENTITY, "FAKE_CLAUDE_LOGGED": "1",
                                      "VCC2026_DATA_ROOT": str(self.tmp / "data")})
        env.start()
        self.addCleanup(env.stop)
        for key in ("VCC2026_CODEX_EXE", "VCC2026_CLAUDE_EXE"):
            os.environ.pop(key, None)

        self.root = self.tmp / "repo"
        config_dir = self.root / "configs" / "ciclo_giornaliero"
        config_dir.mkdir(parents=True)
        for name in ("prompt_codex.md", "preambolo_claude.md",
                     "codex_output.schema.json", "claude_output.schema.json"):
            shutil.copy2(ROOT / "configs" / "ciclo_giornaliero" / name, config_dir / name)
        fakes = self.tmp / "fakes"
        fakes.mkdir()
        (fakes / "codex.py").write_text(FAKE_CODEX, encoding="utf-8")
        (fakes / "claude.py").write_text(FAKE_CLAUDE, encoding="utf-8")
        settings = {
            "seal_deadline": "00:00",
            "worktree_root": str(self.tmp / "worktrees"),
            "log_root": str(self.tmp / "logs"),
            "codex": {"exe": [sys.executable, str(fakes / "codex.py")]},
            "claude": {"exe": [sys.executable, str(fakes / "claude.py")], "extra_args": []},
            "verify": [{"name": "checker", "argv": ["{python}", "-c", "print('ok')"]}],
        }
        (config_dir / "ciclo.json").write_text(json.dumps(settings), encoding="utf-8")
        (self.root / "configs" / "config.yaml").write_text(
            f'data_root: "{(self.tmp / "data").as_posix()}"\n', encoding="utf-8")
        docs = self.root / "docs"
        docs.mkdir()
        self.plans = [docs / f"PIANO_IMPLEMENTATIVO_{DATE}.md",
                      docs / f"PIANO_COMPRENSIONE_{DATE}.md"]
        for plan in self.plans:
            plan.write_text(f"# {plan.stem}\n\nI-1 ancore.\n", encoding="utf-8")
        (self.root / "README.md").write_text("repo di prova\n", encoding="utf-8")
        git("init", "-q", cwd=self.root)
        git("add", "-A", cwd=self.root)
        git("commit", "-q", "-m", "base", cwd=self.root)

        self.sheet_file = self.tmp / "sheet.md"
        self.sheet_file.write_text(SHEET_OK, encoding="utf-8")
        os.environ["FAKE_SHEET"] = str(self.sheet_file)

    def cycle(self):
        return cycle_mod.Cycle(root=self.root, date=DATE,
                               settings=cycle_mod.load_settings(self.root),
                               data_root=cycle_mod.resolve_data_root(self.root))

    def seal(self, cycle=None):
        cycle = cycle or self.cycle()
        return cycle_mod.cmd_seal(
            cycle, plans=[p.relative_to(self.root).as_posix() for p in self.plans],
            snapshot=None, checker="ok", tests="ok", page_url=None, by="test")

    def marker(self, name):
        return cycle_mod.read_json(self.cycle().path(name))


class SealTests(ChainFixture):
    def test_seal_records_hashes_and_refuses_to_overwrite(self):
        payload = self.seal()
        self.assertEqual(payload["esito"], "sigillato")
        self.assertEqual([e["sha256"] for e in payload["plans"]],
                         [cycle_mod.sha256(p) for p in self.plans])
        with self.assertRaises(FileExistsError):
            self.seal()

    def test_seal_rejects_a_plan_of_another_day(self):
        other = self.root / "docs" / "PIANO_IMPLEMENTATIVO_2026-09-16.md"
        other.write_text("ieri\n", encoding="utf-8")
        with self.assertRaises(cycle_mod.CycleError):
            cycle_mod.cmd_seal(self.cycle(), plans=["docs/PIANO_IMPLEMENTATIVO_2026-09-16.md"],
                               snapshot=None, checker="ok", tests="ok", page_url=None, by="test")

    def test_an_edit_after_the_seal_is_detected(self):
        self.seal()
        self.plans[0].write_text("riscritto dopo il sigillo\n", encoding="utf-8")
        ok, reason, _ = cycle_mod.verify_seal(self.cycle())
        self.assertFalse(ok)
        self.assertIn("modificato dopo il sigillo", reason)


class WaitTests(ChainFixture):
    def test_gives_up_at_the_deadline_without_a_seal(self):
        cycle = self.cycle()
        cycle.settings["seal_deadline"] = "10:00"
        times = iter([dt.datetime(2026, 9, 17, 9, 55), dt.datetime(2026, 9, 17, 10, 1)])
        slept = []
        ok, reason = cycle_mod.wait_for_seal(cycle, sleep=slept.append,
                                             clock=lambda: next(times))
        self.assertFalse(ok)
        self.assertIn("alle 10:00", reason)
        self.assertEqual(slept, [300.0])  # never sleeps past the deadline

    def test_a_broken_seal_stops_the_wait_at_once(self):
        self.seal()
        self.plans[1].write_text("cambiato\n", encoding="utf-8")
        cycle = self.cycle()
        cycle.settings["seal_deadline"] = "23:59"
        ok, reason = cycle_mod.wait_for_seal(
            cycle, sleep=lambda s: self.fail("should not wait"),
            clock=lambda: dt.datetime(2026, 9, 17, 9, 0))
        self.assertFalse(ok)


class SheetTests(unittest.TestCase):
    def test_a_complete_sheet_passes(self):
        self.assertEqual(cycle_mod.validate_sheet(SHEET_OK), [])

    def test_missing_section_forbidden_command_and_size_are_reported(self):
        without = SHEET_OK.replace("## Vincoli\n", "")
        self.assertIn("sezione mancante: ## Vincoli", cycle_mod.validate_sheet(without))
        pushing = SHEET_OK + "\nPoi esegui git push origin main.\n"
        self.assertTrue(any("vietata" in p for p in cycle_mod.validate_sheet(pushing)))
        # a prohibition is still a mention: the preamble, not the sheet, forbids things
        forbidding = SHEET_OK + "\nNon usare vcc submit.\n"
        self.assertTrue(any("vietata" in p for p in cycle_mod.validate_sheet(forbidding)))
        huge = SHEET_OK + "x" * cycle_mod.MAX_SHEET_BYTES
        self.assertTrue(any("oltre il limite" in p for p in cycle_mod.validate_sheet(huge)))
        self.assertEqual(cycle_mod.validate_sheet("  \n"), ["foglio vuoto"])


class HelperTests(unittest.TestCase):
    def test_render_fills_known_placeholders_and_rejects_unknown_ones(self):
        self.assertEqual(cycle_mod.render("a {{date}} b", {"date": "x"}), "a x b")
        with self.assertRaises(cycle_mod.CycleError):
            cycle_mod.render("{{missing}}", {})

    def test_repo_templates_use_only_the_placeholders_the_script_fills(self):
        cycle_mod.render((ROOT / "configs/ciclo_giornaliero/prompt_codex.md").read_text(encoding="utf-8"),
                         dict.fromkeys(["date", "cycle_dir", "repo_root", "plan_impl",
                                        "plan_comp", "seal", "skill"], "x"))
        cycle_mod.render((ROOT / "configs/ciclo_giornaliero/preambolo_claude.md").read_text(encoding="utf-8"),
                         dict.fromkeys(["date", "worktree", "branch", "inputs", "outcome",
                                        "step_id"], "x"))

    def test_output_schemas_are_strict(self):
        # Strict structured outputs need every property required and nothing extra.
        for name in ("codex_output.schema.json", "claude_output.schema.json"):
            schema = json.loads((ROOT / "configs/ciclo_giornaliero" / name).read_text(encoding="utf-8"))
            self.assertIs(schema["additionalProperties"], False, name)
            self.assertEqual(set(schema["required"]), set(schema["properties"]), name)

    def test_codex_reply_needs_a_step_when_the_prompt_is_ready(self):
        reply = {"data": "2026-09-17", "esito": "prompt_pronto", "motivo": "m",
                 "piano_verificato": True, "passo": None,
                 "critiche_bloccanti": [], "domande_per_il_lead": []}
        self.assertIn("esito prompt_pronto senza passo", cycle_mod.check_codex_reply(reply))
        reply.update(esito="nessun_passo")
        self.assertEqual(cycle_mod.check_codex_reply(reply), [])
        self.assertTrue(cycle_mod.check_codex_reply(None))

    def test_claude_output_structured_part_or_json_result(self):
        reply = {"esito": "completato"}
        _, structured = cycle_mod.parse_claude_output(
            json.dumps({"result": "x", "structured_output": reply}))
        self.assertEqual(structured, reply)
        _, structured = cycle_mod.parse_claude_output(
            "log line\n" + json.dumps({"result": json.dumps(reply)}))
        self.assertEqual(structured, reply)
        self.assertEqual(cycle_mod.parse_claude_output("not json"), (None, None))

    def test_environment_override_wins_for_both_agents(self):
        settings = cycle_mod.merge(cycle_mod.DEFAULTS, {"codex": {"exe": "a.exe"},
                                                        "claude": {"exe": "b.exe"}})
        with patch.dict(os.environ, {"VCC2026_CODEX_EXE": "env-codex",
                                     "VCC2026_CLAUDE_EXE": "env-claude"}):
            self.assertEqual(cycle_mod.resolve_codex(settings), ["env-codex"])
            self.assertEqual(cycle_mod.resolve_claude(settings), ["env-claude"])
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("VCC2026_CODEX_EXE", None)
            os.environ.pop("VCC2026_CLAUDE_EXE", None)
            self.assertEqual(cycle_mod.resolve_codex(settings), ["a.exe"])
            self.assertEqual(cycle_mod.resolve_claude(settings), ["b.exe"])

    def test_comment_keys_are_ignored_when_merging_settings(self):
        merged = cycle_mod.merge({"a": {"b": 1}}, {"_comment": "x", "a": {"_c": "y", "b": 2}})
        self.assertEqual(merged, {"a": {"b": 2}})

    def test_lock_blocks_a_second_run_and_breaks_a_stale_one(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        path = tmp / ".lock"
        with cycle_mod.Lock(path, stale_hours=8):
            with self.assertRaises(cycle_mod.LockBusy):
                with cycle_mod.Lock(path, stale_hours=8):
                    pass
        self.assertFalse(path.exists())
        path.write_text("{}", encoding="utf-8")
        old = path.stat().st_mtime - 9 * 3600
        os.utime(path, (old, old))
        with cycle_mod.Lock(path, stale_hours=8) as lock:
            self.assertTrue(lock.broke_stale)


class ChainTests(ChainFixture):
    def test_without_a_seal_the_day_closes_with_markers_and_no_agent(self):
        cycle = self.cycle()
        review = cycle_mod.stage_review(cycle, runner=lambda *a, **k: self.fail("no agent"))
        self.assertEqual(review["esito"], "saltato")
        implement = cycle_mod.stage_implement(cycle)
        self.assertEqual(implement["esito"], "non_avviato")
        self.assertIsNotNone(self.marker(cycle_mod.CODEX_MARKER))
        self.assertIsNotNone(self.marker(cycle_mod.CLAUDE_MARKER))

    def test_full_chain_commits_on_the_day_branch_once(self):
        self.seal()
        cycle = self.cycle()
        main_branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=self.root)
        with patch("builtins.print"):
            code = cycle_mod.cmd_run(cycle, dry_run=False, wait=False)
        self.assertEqual(code, 0)

        review = self.marker(cycle_mod.CODEX_MARKER)
        self.assertEqual(review["esito"], "prompt_pronto")
        self.assertEqual(review["foglio"]["sha256"],
                         cycle_mod.sha256(cycle.path(cycle_mod.SHEET)))
        implement = self.marker(cycle_mod.CLAUDE_MARKER)
        self.assertEqual(implement["esito"], "completato")
        self.assertEqual(implement["verifiche"], {"checker": "ok"})
        self.assertEqual(implement["file_modificati"], ["src/new_step.py"])
        self.assertTrue(cycle.path(cycle_mod.OUTCOME).is_file())

        worktree = cycle.worktree
        self.assertEqual(git("rev-parse", "--abbrev-ref", "HEAD", cwd=worktree),
                         f"ciclo/{DATE}")
        self.assertEqual(git("rev-parse", "HEAD", cwd=worktree), implement["commit"])
        committed = git("show", "--name-only", "--format=", "HEAD", cwd=worktree)
        self.assertNotIn(".ciclo", committed)  # the day's inputs are never committed
        self.assertIn("I-1", git("log", "-1", "--format=%s", cwd=worktree))
        # the main checkout stays on its branch and never sees the new file
        self.assertEqual(git("rev-parse", "--abbrev-ref", "HEAD", cwd=self.root), main_branch)
        self.assertFalse((self.root / "src" / "new_step.py").exists())

        before = cycle.path(cycle_mod.CLAUDE_MARKER).read_bytes()
        with patch("builtins.print"):
            self.assertEqual(cycle_mod.cmd_run(cycle, dry_run=False, wait=False), 0)
        self.assertEqual(cycle.path(cycle_mod.CLAUDE_MARKER).read_bytes(), before)

    def test_an_invalid_sheet_never_reaches_claude(self):
        self.sheet_file.write_text(SHEET_OK + "\nAlla fine esegui git push.\n", encoding="utf-8")
        self.seal()
        cycle = self.cycle()
        with patch("builtins.print"):
            self.assertEqual(cycle_mod.cmd_run(cycle, dry_run=False, wait=False), 2)
        self.assertEqual(self.marker(cycle_mod.CODEX_MARKER)["esito"], "foglio_non_valido")
        self.assertEqual(self.marker(cycle_mod.CLAUDE_MARKER)["esito"], "non_avviato")
        self.assertFalse(cycle.worktree.exists())

    def test_an_unauthenticated_claude_blocks_stage_three(self):
        os.environ["FAKE_CLAUDE_LOGGED"] = "0"
        self.seal()
        cycle = self.cycle()
        with patch("builtins.print"):
            self.assertEqual(cycle_mod.cmd_run(cycle, dry_run=False, wait=False), 3)
        implement = self.marker(cycle_mod.CLAUDE_MARKER)
        self.assertEqual(implement["esito"], "bloccato")
        self.assertIn("claude auth login", implement["motivo"])
        self.assertFalse(cycle.worktree.exists())

    def test_a_sheet_edited_after_review_is_refused(self):
        self.seal()
        cycle = self.cycle()
        cycle_mod.stage_review(cycle)
        cycle.path(cycle_mod.SHEET).write_text(SHEET_OK + "\nAggiunta.\n", encoding="utf-8")
        implement = cycle_mod.stage_implement(cycle)
        self.assertEqual(implement["esito"], "non_avviato")
        self.assertIn("modificato", implement["motivo"])

    def test_dry_run_writes_nothing(self):
        self.seal()
        cycle = self.cycle()
        before = sorted(p.name for p in cycle.dir.iterdir())
        with patch("builtins.print"):
            self.assertEqual(cycle_mod.cmd_run(cycle, dry_run=True, wait=False), 0)
        self.assertEqual(sorted(p.name for p in cycle.dir.iterdir()), before)
        self.assertFalse(cycle.worktree.exists())

    def test_status_prints_every_stage(self):
        self.seal()
        with patch("builtins.print") as shown:
            cycle_mod.cmd_status(self.cycle())
        text = "\n".join(str(call.args[0]) for call in shown.call_args_list)
        self.assertIn("fase 1, piano: sigillato", text)
        self.assertIn("fase 2, revisione: assente", text)


if __name__ == "__main__":
    unittest.main()
