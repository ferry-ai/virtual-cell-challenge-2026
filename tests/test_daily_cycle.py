"""Tests for the chain of cycles (scripts/32_daily_cycle.py).

The agents are replaced by small Python programs that honour the same command lines:
Codex writes the review, the sheet and an acceptance test; Claude writes the module the
test imports; Grok answers with structured JSON and may ask for campaigns; the
orchestrator prints what the real console prints. The whole chain -- seal, review,
worktree, acceptance tests, commit, campaigns, report, signals -- runs for real inside a
temporary git repository.
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
MORNING = dt.datetime(2026, 9, 17, 10, 0)

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
    Il test di collaudo passa.

    ## Vincoli
    Solo libreria standard.

    ## Consegna
    Script, test e esito.
    """)


def acceptance_test(module):
    """A test that fails until Claude writes `module` with VALUE = 1."""
    return textwrap.dedent(f"""\
        import unittest


        class StepTest(unittest.TestCase):
            def test_value(self):
                import {module}
                self.assertEqual({module}.VALUE, 1)
        """)


ALWAYS_PASSES = "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        pass\n"

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
    (cycle / "03_prompt_claude.md").write_text(Path(os.environ["FAKE_SHEET"]).read_text(encoding="utf-8"), encoding="utf-8")
    (cycle / "collaudo").mkdir(exist_ok=True)
    (cycle / "collaudo" / "test_step.py").write_text(Path(os.environ["FAKE_TEST"]).read_text(encoding="utf-8"), encoding="utf-8")
    reply = {"data": "2026-09-17", "esito": "prompt_pronto", "motivo": "passo scelto",
             "piano_verificato": True,
             "passo": {"id": "I-1", "titolo": "Ancore", "perche": "serve alla scala",
                       "metriche": ["tutte"]},
             "critiche_bloccanti": [], "domande_per_il_lead": []}
    reply_path.write_text(json.dumps(reply), encoding="utf-8")
    """)

FAKE_CLAUDE = textwrap.dedent("""\
    import json, os, re, sys
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
    number = re.search(r"del ciclo (\\d+)", prompt).group(1)
    Path("src").mkdir(exist_ok=True)
    if os.environ.get("FAKE_CLAUDE_SKIP_CODE") != "1":
        Path(f"src/step_{number}.py").write_text("VALUE = 1\\n", encoding="utf-8")
    if os.environ.get("FAKE_CLAUDE_TAMPER") == "1":
        for test in Path(".ciclo/collaudo").glob("test_*.py"):
            test.write_text("import unittest\\n\\n\\nclass T(unittest.TestCase):\\n    def test_ok(self):\\n        pass\\n", encoding="utf-8")
    Path(".ciclo/04_esito_claude.md").write_text("# Esito\\n\\nfatto\\n", encoding="utf-8")
    reply = {"esito": "completato", "passo_id": "I-1", "sintesi": "script scritto",
             "file_toccati": [f"src/step_{number}.py"], "verifiche": "ok", "blocchi": []}
    print(json.dumps({"type": "result", "result": "fatto", "session_id": "s-1",
                      "structured_output": reply}))
    """)

FAKE_GROK = textwrap.dedent("""\
    import json, os, sys
    from pathlib import Path
    args = sys.argv[1:]
    if args[:1] == ["--version"]:
        print("grok fake")
        sys.exit(0)
    prompt = Path(args[args.index("--prompt-file") + 1]).read_text(encoding="utf-8")
    first = "fase 4, seguito" not in prompt
    counter = Path(os.environ["FAKE_GROK_COUNTER"])
    made = int(counter.read_text()) if counter.exists() else 0
    want = int(os.environ.get("FAKE_GROK_CAMPAIGNS", "0"))
    request = None
    if made < want:
        request = {"titolo": f"Campagna {made + 1}", "domanda": "Il collaudo regge?",
                   "contesto": "ciclo di prova", "risultato_atteso": "rischi",
                   "criteri": ["elenca i rischi"],
                   "materiali": ["diff.patch", "analisi_grok.md", "segreto.txt"]}
        counter.write_text(str(made + 1))
    reply = {"esito": "ok",
             "analisi_md": "# Analisi\\n\\nil passo regge\\n" if first else "",
             "sintesi_md": f"sintesi dopo {made} campagne",
             "richiesta": request, "domande_per_l_utente": ["integrare il branch?"]}
    print(json.dumps({"text": json.dumps(reply), "sessionId": "g-1",
                      "modelUsage": {"grok-fake": {}}, "total_cost_usd": 0,
                      "structuredOutput": reply}))
    """)

FAKE_ORCH = textwrap.dedent("""\
    import json, os, sys
    from pathlib import Path
    args = sys.argv[1:]
    log = Path(os.environ["FAKE_ORCH_LOG"])
    with log.open("a", encoding="utf-8") as handle:
        handle.write(" ".join(args[:1]) + "\\n")
    if args[0] == "brief":
        brief = Path(args[1])
        document = json.loads(brief.read_text(encoding="utf-8"))
        missing = [m["path"] for m in document["materials"] if not (brief.parent / m["path"]).is_file()]
        if missing or os.environ.get("FAKE_ORCH_INVALID") == "1":
            print("incarico non valido: " + ", ".join(missing))
            sys.exit(1)
        print("id: " + document["id"])
        sys.exit(0)
    label = args[args.index("--label") + 1]
    report = Path(os.environ["FAKE_ORCH_OUT"]) / f"report-{label}.md"
    report.write_text("# Rapporto\\n\\nnessun rischio nuovo\\n", encoding="utf-8")
    print(f"run creato: run-{label}")
    print("[stato finale] finished")
    print(f"[rapporto] {report}")
    """)

GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
}
TEMPLATES = ("prompt_codex.md", "preambolo_claude.md", "prompt_grok.md",
             "prompt_grok_seguito.md", "codex_output.schema.json",
             "claude_output.schema.json", "grok_output.schema.json")


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout.strip()


def no_agent(*args, **kwargs):
    raise AssertionError(f"no agent should run: {args[:1]}")


class ChainFixture(unittest.TestCase):
    """A throwaway repository shaped like this one, with fake agents."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        fakes = self.tmp / "fakes"
        fakes.mkdir()
        (self.tmp / "orch_out").mkdir()
        env = patch.dict(os.environ, {
            **GIT_IDENTITY, "FAKE_CLAUDE_LOGGED": "1",
            "VCC2026_DATA_ROOT": str(self.tmp / "data"),
            "FAKE_GROK_COUNTER": str(self.tmp / "grok_counter"),
            "FAKE_GROK_CAMPAIGNS": "0",
            "FAKE_ORCH_LOG": str(self.tmp / "orch.log"),
            "FAKE_ORCH_OUT": str(self.tmp / "orch_out"),
        })
        env.start()
        self.addCleanup(env.stop)
        for key in ("VCC2026_CODEX_EXE", "VCC2026_CLAUDE_EXE", "VCC2026_GROK_EXE",
                    "FAKE_CLAUDE_TAMPER", "FAKE_CLAUDE_SKIP_CODE", "FAKE_ORCH_INVALID"):
            os.environ.pop(key, None)

        self.root = self.tmp / "repo"
        config_dir = self.root / "configs" / "ciclo_giornaliero"
        config_dir.mkdir(parents=True)
        for name in TEMPLATES:
            shutil.copy2(ROOT / "configs" / "ciclo_giornaliero" / name, config_dir / name)
        for name, text in (("codex.py", FAKE_CODEX), ("claude.py", FAKE_CLAUDE),
                           ("grok.py", FAKE_GROK), ("orch.py", FAKE_ORCH)):
            (fakes / name).write_text(text, encoding="utf-8")
        self.settings = {
            "seal_deadline": "00:00",
            "worktree_root": str(self.tmp / "worktrees"),
            "log_root": str(self.tmp / "logs"),
            "codex": {"exe": [sys.executable, str(fakes / "codex.py")]},
            "claude": {"exe": [sys.executable, str(fakes / "claude.py")], "extra_args": []},
            "grok": {"exe": [sys.executable, str(fakes / "grok.py")]},
            "orchestratore": {"exe": [sys.executable, str(fakes / "orch.py")]},
            "verify": [{"name": "checker", "argv": ["{python}", "-c", "print('ok')"]}],
        }
        self.write_settings()
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
        self.test_file = self.tmp / "test_step.py"
        self.test_file.write_text(acceptance_test("step_01"), encoding="utf-8")
        os.environ["FAKE_SHEET"] = str(self.sheet_file)
        os.environ["FAKE_TEST"] = str(self.test_file)

    def write_settings(self):
        path = self.root / "configs" / "ciclo_giornaliero" / "ciclo.json"
        path.write_text(json.dumps(self.settings), encoding="utf-8")

    def chain(self):
        return cycle_mod.Chain(root=self.root, settings=cycle_mod.load_settings(self.root),
                               data_root=cycle_mod.resolve_data_root(self.root))

    def morning(self):
        return self.chain().cycle(DATE, 1)

    def seal(self):
        return cycle_mod.cmd_seal(
            self.chain(), DATE, plans=[p.relative_to(self.root).as_posix() for p in self.plans],
            snapshot=None, checker="ok", tests="ok", page_url=None, by="test")

    def guard(self, **kwargs):
        with patch("builtins.print"):
            return cycle_mod.cmd_guardiano(self.chain(), once=True, **kwargs)

    def draft(self, module="step_02", sheet=SHEET_OK, test=None, step=None):
        chain = self.chain()
        draft = cycle_mod.cmd_bozza(chain, clock=lambda: MORNING)
        (draft / "03_prompt_claude.md").write_text(sheet, encoding="utf-8")
        (draft / "02_dialogo.md").write_text("# Dialogo\n\nabbiamo deciso il passo\n",
                                             encoding="utf-8")
        (draft / "passo.json").write_text(json.dumps(step or {
            "id": "NUOVO", "titolo": "Secondo passo", "perche": "deciso nel dialogo"}),
            encoding="utf-8")
        (draft / "collaudo" / "test_second.py").write_text(
            test if test is not None else acceptance_test(module), encoding="utf-8")
        return draft

    def start(self, draft):
        return cycle_mod.cmd_avvia(self.chain(), draft=draft, clock=lambda: MORNING)

    def orch_starts(self):
        log = self.tmp / "orch.log"
        lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
        return lines.count("start")


class SealTests(ChainFixture):
    def test_seal_writes_cycle_01_and_refuses_to_overwrite(self):
        payload = self.seal()
        self.assertEqual(payload["esito"], "sigillato")
        self.assertTrue(self.morning().path(cycle_mod.SEAL).is_file())
        self.assertEqual(self.morning().dir.name, "ciclo-01")
        self.assertEqual([e["sha256"] for e in payload["plans"]],
                         [cycle_mod.sha256(p) for p in self.plans])
        with self.assertRaises(FileExistsError):
            self.seal()

    def test_seal_rejects_a_plan_of_another_day(self):
        other = self.root / "docs" / "PIANO_IMPLEMENTATIVO_2026-09-16.md"
        other.write_text("ieri\n", encoding="utf-8")
        with self.assertRaises(cycle_mod.CycleError):
            cycle_mod.cmd_seal(self.chain(), DATE,
                               plans=["docs/PIANO_IMPLEMENTATIVO_2026-09-16.md"],
                               snapshot=None, checker="ok", tests="ok", page_url=None,
                               by="test")

    def test_an_edit_after_the_seal_is_detected(self):
        self.seal()
        self.plans[0].write_text("riscritto dopo il sigillo\n", encoding="utf-8")
        ok, reason, _ = cycle_mod.verify_seal(self.morning())
        self.assertFalse(ok)
        self.assertIn("modificato dopo il sigillo", reason)


class WaitTests(ChainFixture):
    def test_gives_up_at_the_deadline_without_a_seal(self):
        cycle = self.morning()
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
        cycle = self.morning()
        cycle.settings["seal_deadline"] = "23:59"
        ok, _ = cycle_mod.wait_for_seal(
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

    def test_test_inventory_reports_missing_tests_and_forbidden_code(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "helper.py").write_text("import subprocess\n# git push origin\n",
                                       encoding="utf-8")
        (tmp / "data.bin").write_bytes(b"\x00")
        entries, problems = cycle_mod.test_inventory(tmp, 10_000)
        self.assertEqual(len(entries), 2)
        self.assertIn("nessun file test*.py nel collaudo", problems)
        self.assertTrue(any("vietata" in p for p in problems))
        self.assertTrue(any("non ammesso" in p for p in problems))
        self.assertEqual(cycle_mod.test_inventory(tmp / "assente", 10)[1],
                         ["cartella collaudo assente"])


class HelperTests(unittest.TestCase):
    def test_giornata_starts_at_day_start(self):
        self.assertEqual(cycle_mod.giornata_for(dt.datetime(2026, 9, 18, 7, 59), "08:00"),
                         dt.date(2026, 9, 17))
        self.assertEqual(cycle_mod.giornata_for(dt.datetime(2026, 9, 18, 8, 0), "08:00"),
                         dt.date(2026, 9, 18))

    def test_render_fills_known_placeholders_and_rejects_unknown_ones(self):
        self.assertEqual(cycle_mod.render("a {{date}} b", {"date": "x"}), "a x b")
        with self.assertRaises(cycle_mod.CycleError):
            cycle_mod.render("{{missing}}", {})

    def test_repo_templates_use_only_the_placeholders_the_script_fills(self):
        filled = {
            "prompt_codex.md": ["date", "cycle_dir", "tests_dir", "repo_root", "plan_impl",
                                "plan_comp", "seal", "skill"],
            "preambolo_claude.md": ["date", "cycle", "origin", "worktree", "branch",
                                    "inputs", "tests", "outcome", "step_id"],
            "prompt_grok.md": ["date", "cycle", "cycle_dir", "worktree", "branch",
                               "commit", "outcome", "materials", "budget"],
            "prompt_grok_seguito.md": ["date", "cycle", "index", "status", "report",
                                       "analysis", "remaining"],
        }
        for name, keys in filled.items():
            text = (ROOT / "configs/ciclo_giornaliero" / name).read_text(encoding="utf-8")
            cycle_mod.render(text, dict.fromkeys(keys, "x"))

    def test_output_schemas_are_strict(self):
        # Strict structured outputs need every property required and nothing extra.
        for name in ("codex_output.schema.json", "claude_output.schema.json",
                     "grok_output.schema.json"):
            schema = json.loads((ROOT / "configs/ciclo_giornaliero" / name).read_text(encoding="utf-8"))
            self.assertIs(schema["additionalProperties"], False, name)
            self.assertEqual(set(schema["required"]), set(schema["properties"]), name)

    def test_grok_materials_enum_matches_the_script(self):
        schema = json.loads((ROOT / "configs/ciclo_giornaliero/grok_output.schema.json")
                            .read_text(encoding="utf-8"))
        request = schema["properties"]["richiesta"]["anyOf"][0]
        self.assertEqual(tuple(request["properties"]["materiali"]["items"]["enum"]),
                         cycle_mod.MATERIALS)

    def test_codex_reply_needs_a_step_when_the_prompt_is_ready(self):
        reply = {"data": "2026-09-17", "esito": "prompt_pronto", "motivo": "m",
                 "piano_verificato": True, "passo": None,
                 "critiche_bloccanti": [], "domande_per_il_lead": []}
        self.assertIn("esito prompt_pronto senza passo", cycle_mod.check_codex_reply(reply))
        reply.update(esito="nessun_passo")
        self.assertEqual(cycle_mod.check_codex_reply(reply), [])
        self.assertTrue(cycle_mod.check_codex_reply(None))

    def test_grok_reply_needs_an_analysis_first_and_a_complete_request(self):
        reply = {"esito": "ok", "analisi_md": "", "sintesi_md": "s", "richiesta": None,
                 "domande_per_l_utente": []}
        self.assertIn("analisi indipendente vuota",
                      cycle_mod.check_grok_reply(reply, first=True))
        self.assertEqual(cycle_mod.check_grok_reply(reply, first=False), [])
        reply["richiesta"] = {"titolo": "t", "domanda": "", "contesto": "c",
                              "risultato_atteso": "r", "criteri": [], "materiali": []}
        problems = cycle_mod.check_grok_reply(reply, first=False)
        self.assertIn("richiesta.domanda assente", problems)
        self.assertIn("richiesta.criteri vuoto", problems)
        self.assertTrue(cycle_mod.check_grok_reply(None, first=True))

    def test_agent_outputs_are_parsed_from_their_json_shapes(self):
        reply = {"esito": "completato"}
        _, structured = cycle_mod.parse_claude_output(
            json.dumps({"result": "x", "structured_output": reply}))
        self.assertEqual(structured, reply)
        _, structured = cycle_mod.parse_claude_output(
            "log line\n" + json.dumps({"result": json.dumps(reply)}))
        self.assertEqual(structured, reply)
        self.assertEqual(cycle_mod.parse_claude_output("not json"), (None, None))
        _, structured = cycle_mod.parse_grok_output(json.dumps({"structuredOutput": reply}))
        self.assertEqual(structured, reply)
        _, structured = cycle_mod.parse_grok_output(json.dumps({"text": json.dumps(reply)}))
        self.assertEqual(structured, reply)

    def test_environment_override_wins_for_every_agent(self):
        settings = cycle_mod.merge(cycle_mod.DEFAULTS, {"codex": {"exe": "a.exe"},
                                                        "claude": {"exe": "b.exe"},
                                                        "grok": {"exe": "c.exe"}})
        with patch.dict(os.environ, {"VCC2026_CODEX_EXE": "env-codex",
                                     "VCC2026_CLAUDE_EXE": "env-claude",
                                     "VCC2026_GROK_EXE": "env-grok"}):
            self.assertEqual(cycle_mod.resolve_codex(settings), ["env-codex"])
            self.assertEqual(cycle_mod.resolve_claude(settings), ["env-claude"])
            self.assertEqual(cycle_mod.resolve_grok(settings), ["env-grok"])
        with patch.dict(os.environ, {}, clear=False):
            for key in ("VCC2026_CODEX_EXE", "VCC2026_CLAUDE_EXE", "VCC2026_GROK_EXE"):
                os.environ.pop(key, None)
            self.assertEqual(cycle_mod.resolve_codex(settings), ["a.exe"])
            self.assertEqual(cycle_mod.resolve_claude(settings), ["b.exe"])
            self.assertEqual(cycle_mod.resolve_grok(settings), ["c.exe"])

    def test_comment_keys_are_ignored_when_merging_settings(self):
        merged = cycle_mod.merge({"a": {"b": 1}}, {"_comment": "x", "a": {"_c": "y", "b": 2}})
        self.assertEqual(merged, {"a": {"b": 2}})

    def test_repo_settings_load_and_keep_the_campaign_cap(self):
        settings = cycle_mod.load_settings(ROOT)
        self.assertEqual(settings["orchestratore"]["max_campagne"], 3)
        self.assertEqual(settings["orchestratore"]["route"], "deep_kimi")
        self.assertEqual(settings["day_start"], "08:00")

    def test_lock_blocks_a_live_holder_and_replaces_a_dead_one(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        path = tmp / "guardiano.lock"
        with cycle_mod.RunnerLock(path, command="guardiano"):
            with self.assertRaises(cycle_mod.LockBusy):
                with cycle_mod.RunnerLock(path, command="run"):
                    pass
        self.assertFalse(path.exists())
        path.write_text(json.dumps({"pid": 12345, "command": "guardiano"}), encoding="utf-8")
        with cycle_mod.RunnerLock(path, command="run", alive=lambda pid: False) as lock:
            self.assertTrue(lock.broke_stale)
        self.assertFalse(cycle_mod.pid_alive(0))
        self.assertTrue(cycle_mod.pid_alive(os.getpid()))


class MorningCycleTests(ChainFixture):
    def test_the_morning_cycle_runs_end_to_end_once(self):
        os.environ["FAKE_GROK_CAMPAIGNS"] = "1"
        self.seal()
        main_branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=self.root)
        self.assertEqual(self.guard(), 0)
        cycle = self.morning()

        review = cycle.marker(cycle_mod.CODEX_MARKER)
        self.assertEqual(review["esito"], "prompt_pronto")
        self.assertEqual([f["path"] for f in review["collaudo"]["file"]], ["test_step.py"])

        implement = cycle.marker(cycle_mod.CLAUDE_MARKER)
        self.assertEqual(implement["esito"], "completato")
        self.assertEqual(implement["collaudo"]["prima"]["esito"], "fallito")
        self.assertEqual(implement["collaudo"]["dopo"]["esito"], "ok")
        self.assertEqual(implement["file_modificati"], ["src/step_01.py"])
        self.assertEqual(implement["branch"], f"ciclo/{DATE}-01")
        worktree = Path(implement["worktree"])
        self.assertEqual(git("rev-parse", "HEAD", cwd=worktree), implement["commit"])
        committed = git("show", "--name-only", "--format=", "HEAD", cwd=worktree)
        self.assertNotIn(".ciclo", committed)  # inputs and test copies are never committed
        # the main checkout stays on its branch and never sees the new file
        self.assertEqual(git("rev-parse", "--abbrev-ref", "HEAD", cwd=self.root), main_branch)
        self.assertFalse((self.root / "src" / "step_01.py").exists())

        control = cycle.marker(cycle_mod.GROK_MARKER)
        self.assertEqual(control["esito"], "ok")
        self.assertEqual(len(control["campagne"]), 1)
        campaign = control["campagne"][0]
        self.assertEqual(campaign["esito"], "finished")
        self.assertEqual(campaign["run_id"], f"run-ciclo-{DATE}-01-1")
        self.assertEqual(campaign["materiali_scartati"], ["segreto.txt"])
        self.assertTrue((self.root / campaign["rapporto"]).is_file())
        brief = json.loads((self.root / campaign["brief"]).read_text(encoding="utf-8"))
        self.assertEqual(brief["route"], "deep_kimi")
        self.assertEqual([m["path"] for m in brief["materials"]],
                         ["diff.patch", "analisi_grok.md"])
        self.assertTrue(cycle.path(cycle_mod.ANALYSIS).is_file())
        self.assertIn("dopo 1 campagne", cycle.path(cycle_mod.SYNTHESIS).read_text(encoding="utf-8"))
        report = cycle.path(cycle_mod.REPORT).read_text(encoding="utf-8")
        self.assertIn("Campagna 1", report)
        self.assertIn("integrare il branch?", report)
        self.assertEqual(self.orch_starts(), 1)

        before = {name: cycle.path(name).read_bytes() for name in
                  (cycle_mod.CODEX_MARKER, cycle_mod.CLAUDE_MARKER, cycle_mod.GROK_MARKER)}
        self.assertEqual(self.guard(), 0)
        for name, data in before.items():
            self.assertEqual(cycle.path(name).read_bytes(), data)
        self.assertEqual(self.orch_starts(), 1)

    def test_without_a_valid_seal_the_cycle_closes_without_agents(self):
        self.seal()
        self.plans[0].write_text("cambiato dopo il sigillo\n", encoding="utf-8")
        self.guard(runner=no_agent)
        cycle = self.morning()
        self.assertEqual(cycle.marker(cycle_mod.CODEX_MARKER)["esito"], "saltato")
        self.assertEqual(cycle.marker(cycle_mod.CLAUDE_MARKER)["esito"], "non_avviato")
        self.assertEqual(cycle.marker(cycle_mod.GROK_MARKER)["esito"], "non_eseguito")
        self.assertTrue(cycle.path(cycle_mod.REPORT).is_file())
        self.assertFalse(cycle.worktree.exists())

    def test_an_unauthenticated_claude_blocks_and_the_cycle_still_closes(self):
        os.environ["FAKE_CLAUDE_LOGGED"] = "0"
        os.environ["FAKE_GROK_CAMPAIGNS"] = "1"
        self.seal()
        self.guard()
        cycle = self.morning()
        implement = cycle.marker(cycle_mod.CLAUDE_MARKER)
        self.assertEqual(implement["esito"], "bloccato")
        self.assertIn("claude auth login", implement["motivo"])
        self.assertEqual(cycle.marker(cycle_mod.GROK_MARKER)["esito"], "non_eseguito")
        self.assertFalse(cycle.worktree.exists())
        self.assertFalse((self.tmp / "grok_counter").exists())  # Grok never ran
        self.assertEqual(self.orch_starts(), 0)

    def test_editing_the_tests_after_the_review_stops_the_cycle(self):
        self.seal()
        cycle = self.morning()
        cycle_mod.stage_review(cycle)
        (cycle.path(cycle_mod.TESTS) / "test_step.py").write_text(ALWAYS_PASSES,
                                                                   encoding="utf-8")
        implement = cycle_mod.stage_implement(cycle)
        self.assertEqual(implement["esito"], "non_avviato")
        self.assertIn("collaudo", implement["motivo"])

    def test_claude_cannot_pass_by_editing_its_copy_of_the_tests(self):
        os.environ["FAKE_CLAUDE_TAMPER"] = "1"
        os.environ["FAKE_CLAUDE_SKIP_CODE"] = "1"
        self.seal()
        self.guard()
        implement = self.morning().marker(cycle_mod.CLAUDE_MARKER)
        self.assertEqual(implement["collaudo"]["dopo"]["esito"], "fallito")
        self.assertEqual(implement["esito"], "parziale")
        self.assertIn("collaudo fallito", implement["motivo"])

    def test_tests_that_already_pass_are_not_informative(self):
        self.test_file.write_text(ALWAYS_PASSES, encoding="utf-8")
        self.seal()
        self.guard()
        implement = self.morning().marker(cycle_mod.CLAUDE_MARKER)
        self.assertEqual(implement["collaudo"]["prima"]["esito"], "ok")
        self.assertEqual(implement["esito"], "parziale")
        self.assertIn("non informativo", implement["motivo"])

    def test_an_invalid_sheet_never_reaches_claude(self):
        self.sheet_file.write_text(SHEET_OK + "\nAlla fine esegui git push.\n",
                                   encoding="utf-8")
        self.seal()
        self.guard()
        cycle = self.morning()
        self.assertEqual(cycle.marker(cycle_mod.CODEX_MARKER)["esito"], "foglio_non_valido")
        self.assertEqual(cycle.marker(cycle_mod.CLAUDE_MARKER)["esito"], "non_avviato")
        self.assertFalse(cycle.worktree.exists())

    def test_run_drains_the_queue_and_reports_the_first_cycle(self):
        self.seal()
        with patch("builtins.print"):
            code = cycle_mod.cmd_run(self.chain(), DATE, dry_run=False, wait=False)
        self.assertEqual(code, 0)
        self.assertTrue(self.morning().closed)

    def test_dry_run_writes_nothing(self):
        self.seal()
        cycle = self.morning()
        before = sorted(p.name for p in cycle.dir.iterdir())
        with patch("builtins.print"):
            self.assertEqual(cycle_mod.cmd_run(self.chain(), DATE, dry_run=True, wait=False), 0)
        self.assertEqual(sorted(p.name for p in cycle.dir.iterdir()), before)
        self.assertFalse(cycle.worktree.exists())

    def test_a_second_guardian_is_refused(self):
        lock = Path(self.settings["log_root"]) / cycle_mod.LOCK_NAME
        lock.parent.mkdir(parents=True)
        lock.write_text(json.dumps({"pid": os.getpid(), "command": "guardiano"}),
                        encoding="utf-8")
        with self.assertRaises(cycle_mod.LockBusy):
            self.guard()

    def test_a_flat_legacy_day_is_ignored(self):
        legacy = self.root / "reports" / "ciclo_giornaliero" / "2026-09-16"
        legacy.mkdir(parents=True)
        (legacy / "01_piano.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self.chain().cycles(), [])
        self.assertEqual(self.guard(runner=no_agent), 0)


class CampaignTests(ChainFixture):
    def test_grok_cannot_exceed_the_campaign_cap(self):
        os.environ["FAKE_GROK_CAMPAIGNS"] = "5"
        self.seal()
        self.guard()
        control = self.morning().marker(cycle_mod.GROK_MARKER)
        self.assertEqual(len(control["campagne"]), 3)
        self.assertIn("oltre il tetto", control["motivo"])
        self.assertEqual(self.orch_starts(), 3)

    def test_a_disabled_orchestrator_starts_nothing(self):
        self.settings["orchestratore"]["abilitato"] = False
        self.write_settings()
        os.environ["FAKE_GROK_CAMPAIGNS"] = "1"
        self.seal()
        self.guard()
        control = self.morning().marker(cycle_mod.GROK_MARKER)
        self.assertEqual(control["campagne"], [])
        self.assertIn("campagne 0 su 0", control["motivo"])
        self.assertEqual(self.orch_starts(), 0)

    def test_an_invalid_brief_is_recorded_and_not_started(self):
        os.environ["FAKE_GROK_CAMPAIGNS"] = "1"
        os.environ["FAKE_ORCH_INVALID"] = "1"
        self.seal()
        self.guard()
        control = self.morning().marker(cycle_mod.GROK_MARKER)
        self.assertEqual(control["campagne"][0]["esito"], "incarico_non_valido")
        self.assertEqual(self.orch_starts(), 0)

    def test_a_resumed_control_stage_repeats_no_campaign_and_no_call(self):
        os.environ["FAKE_GROK_CAMPAIGNS"] = "1"
        self.seal()
        cycle = self.morning()
        cycle_mod.stage_review(cycle)
        cycle_mod.stage_implement(cycle)

        def crash_on_second_call(argv, **kwargs):
            if any(str(arg).endswith("prompt-02.md") for arg in argv):
                raise KeyboardInterrupt
            return cycle_mod.run_process(argv, **kwargs)

        with self.assertRaises(KeyboardInterrupt):
            cycle_mod.stage_control(cycle, runner=crash_on_second_call)
        self.assertFalse(cycle.closed)
        self.assertEqual(self.orch_starts(), 1)
        control = cycle_mod.stage_control(cycle)
        self.assertEqual(len(control["campagne"]), 1)
        self.assertEqual(self.orch_starts(), 1)
        self.assertEqual(len(control["chiamate"]), 2)


class DialogueCycleTests(ChainFixture):
    def test_a_dialogue_cycle_waits_its_turn_and_continues_from_the_previous_branch(self):
        self.seal()
        cycle, payload = self.start(self.draft("step_02"))
        self.assertEqual(cycle.number, 2)
        self.assertEqual(payload["origine"], "dialogo")
        self.assertEqual(payload["avviato_da"], "codex")
        self.assertEqual([c.number for c in cycle_mod.open_queue(self.chain())], [1, 2])
        self.assertFalse(any(p.name.startswith("bozza-")
                             for p in cycle.dir.parent.iterdir()))

        self.guard()
        first = self.morning().marker(cycle_mod.CLAUDE_MARKER)
        second = cycle.marker(cycle_mod.CLAUDE_MARKER)
        self.assertEqual(second["esito"], "completato")
        self.assertEqual(second["base"], first["commit"])
        self.assertIn(f"continua da {DATE}-01", second["base_motivo"])
        worktree = Path(second["worktree"])
        self.assertTrue((worktree / "src" / "step_01.py").is_file())
        self.assertTrue((worktree / "src" / "step_02.py").is_file())
        self.assertEqual(git("rev-parse", "HEAD~1", cwd=worktree), first["commit"])
        self.assertTrue((worktree / ".ciclo" / cycle_mod.PREVIOUS_REPORT).is_file())
        self.assertTrue(cycle.closed)
        self.assertIn("dialogo con ChatGPT",
                      cycle.path(cycle_mod.REPORT).read_text(encoding="utf-8"))

    def test_a_cycle_started_first_runs_first(self):
        cycle, _ = self.start(self.draft("step_02"))
        self.guard()  # no plan yet: the dialogue cycle does not wait for one
        self.assertTrue(cycle.closed)
        self.assertEqual(cycle.marker(cycle_mod.CLAUDE_MARKER)["esito"], "completato")

    def test_integrated_work_is_not_used_as_a_base(self):
        self.seal()
        self.guard()
        first = self.morning().marker(cycle_mod.CLAUDE_MARKER)
        git("merge", "-q", "--no-edit", first["branch"], cwd=self.root)
        cycle, _ = self.start(self.draft("step_02"))
        self.guard()
        second = cycle.marker(cycle_mod.CLAUDE_MARKER)
        self.assertEqual(second["base"], git("rev-parse", "HEAD", cwd=self.root))
        self.assertIn("già integrato", second["base_motivo"])

    def test_cycle_numbers_skip_01_and_never_collide(self):
        first, _ = self.start(self.draft("step_02"))
        second, _ = self.start(self.draft("step_03"))
        self.assertEqual((first.number, second.number), (2, 3))

    def test_an_invalid_draft_is_refused_and_nothing_is_created(self):
        draft = self.draft(sheet=SHEET_OK + "\nPoi git push.\n", test="")
        (draft / "collaudo" / "test_second.py").unlink()
        with self.assertRaises(cycle_mod.CycleError) as caught:
            self.start(draft)
        self.assertIn("vietata", str(caught.exception))
        self.assertIn("nessun file test", str(caught.exception))
        self.assertTrue(draft.is_dir())
        self.assertFalse((draft.parent / "ciclo-02").exists())

    def test_a_draft_outside_the_cycle_folders_is_refused(self):
        outside = self.tmp / "altrove"
        outside.mkdir()
        with self.assertRaises(cycle_mod.CycleError):
            cycle_mod.cmd_avvia(self.chain(), draft=outside, clock=lambda: MORNING)

    def test_status_shows_the_queue(self):
        self.seal()
        self.start(self.draft("step_02"))
        with patch("builtins.print") as shown:
            cycle_mod.cmd_status(self.chain(), DATE)
        text = "\n".join(str(call.args[0]) for call in shown.call_args_list)
        self.assertIn(f"ciclo {DATE}-01 [piano] in corso", text)
        self.assertIn(f"ciclo {DATE}-02 [dialogo] in coda", text)
        self.assertIn("nessun guardiano attivo", text)


if __name__ == "__main__":
    unittest.main()
