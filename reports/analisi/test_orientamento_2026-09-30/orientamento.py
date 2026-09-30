"""Orientation tests: how fast a new agent gathers precise, current, consistent answers from CLAUDE.md.

The protocol is PROTOCOLLO.md beside this file; the questions, expected answers, sources, minimal
paths and perimeters are chiave.json, their one home. Tested agents never see this folder: they
work on a detached snapshot of the repository from which it is removed. Nothing here writes over
an earlier run: every output path is refused if it exists.

    python orientamento.py check                      # every source snippet sits at its line
    python orientamento.py render                     # the key as markdown, for PROTOCOLLO.md
    python orientamento.py snapshot --commit <sha> --dest <dir> --run runs/<id>
    python orientamento.py brief --task T3 --family claude --snapshot <dir> --run runs/<id>
    python orientamento.py collect --case runs/<id>/T3_claude --kind claude --transcript <jsonl> --result <file>
    python orientamento.py collect --case runs/<id>/T3_grok --hub-agent-dir <agent-hub/runs/<run>/grok>
    python orientamento.py score --case runs/<id>/T3_claude
    python orientamento.py summary --run runs/<id> --version economica|completa
    python orientamento.py cleanup --dest <dir>

Standard library only.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
KEY = HERE / "chiave.json"
FOLDER_GLOB = "reports/analisi/test_orientamento_*"
NUMBERED = re.compile(r"^\s*\d+(\t|→)")


def load_key() -> dict:
    return json.loads(KEY.read_text(encoding="utf-8"))


def refuse(path: Path) -> None:
    if path.exists():
        sys.exit(f"refusing: {path} exists (a run is never written over)")


def write_json(path: Path, data) -> None:
    refuse(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------------------------------ the key

def cmd_check(args) -> None:
    root = Path(args.root) if args.root else REPO
    key, problems = load_key(), []
    for task in key["compiti"]:
        qs = task["domande"]
        if not 4 <= len(qs) <= 6:
            problems.append(f"{task['id']}: {len(qs)} questions, expected 4-6")
        if not any(q["tipo"].startswith(("tranello", "attualità")) for q in qs):
            problems.append(f"{task['id']}: no trap or currency question")
        for q in qs:
            if not q["parole"] or not all(q["parole"]):
                problems.append(f"{q['id']}: empty keyword group")
            for src in q["fonti"]:
                path = root / src["file"]
                if not path.is_file():
                    problems.append(f"{q['id']}: {src['file']} missing")
                    continue
                lines = path.read_text(encoding="utf-8").splitlines()
                window = "\n".join(lines[src["riga"] - 1: src["riga"] + 2])
                if src["frammento"] not in window:
                    problems.append(f"{q['id']}: '{src['frammento']}' not at {src['file']}:{src['riga']}")
    protocol = HERE / "PROTOCOLLO.md"
    if protocol.exists():
        text = protocol.read_text(encoding="utf-8").replace("\r\n", "\n")
        found = re.search(r"<!-- chiave:inizio -->\n(.*?)<!-- chiave:fine -->", text, re.S)
        if not found or found.group(1).strip() != render().strip():
            problems.append("PROTOCOLLO.md: the key tables differ from chiave.json (paste `render` between the markers)")
    print("\n".join(problems) if problems else f"OK: {len(key['compiti'])} tasks, every source at its line")
    sys.exit(1 if problems else 0)


def cmd_render(args) -> None:
    print(render())


def render() -> str:
    key = load_key()
    out = []
    for task in key["compiti"]:
        budget = 2 * task["righe_minime"]
        out += [f"### {task['id']} — {task['riga_tabella']}", "",
                f"**Consegna all'agente:** {task['consegna']}", "",
                f"**Percorso minimo** (oltre alla lettura obbligatoria): {'; '.join(task['percorso_minimo'])}. "
                f"Circa {task['righe_minime']} righe in tutto; tetto {budget}.", "",
                f"**Fuori perimetro:** {', '.join('`' + p + '`' for p in task['fuori_perimetro'])}.", "",
                "| ID | Domanda | Risposta attesa | Tipo | Fonte |", "|---|---|---|---|---|"]
        for q in task["domande"]:
            src = "; ".join(f"`{s['file']}:{s['riga']}`" for s in q["fonti"])
            out.append(f"| {q['id']} | {q['domanda']} | {q['attesa']} | {q['tipo']} | {src} |")
        out.append("")
    return "\n".join(out)


# ------------------------------------------------------------------------------- the snapshot

def _writable(func, path, _exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _clear_readonly(root: Path) -> None:
    for p in [root, *root.rglob("*")]:
        try:
            os.chmod(p, os.stat(p).st_mode | stat.S_IWRITE)
        except OSError:
            pass


def cmd_snapshot(args) -> None:
    dest, run = Path(args.dest), Path(args.run)
    refuse(dest)
    refuse(run / "snapshot.json")
    subprocess.run(["git", "-C", str(REPO), "worktree", "add", "--detach", str(dest), args.commit], check=True)
    removed = sorted(str(p.relative_to(dest)) for p in dest.glob(FOLDER_GLOB))
    for p in dest.glob(FOLDER_GLOB):
        shutil.rmtree(p, onerror=_writable)
    write_json(run / "snapshot.json", {"commit": args.commit, "dest": str(dest), "removed": removed})
    print(f"snapshot at {dest}, without {removed}")


def cmd_cleanup(args) -> None:
    dest = Path(args.dest)
    _clear_readonly(dest)
    subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", str(dest)], check=False)
    subprocess.run(["git", "-C", str(REPO), "worktree", "prune"], check=False)
    print("removed" if not dest.exists() else f"still there: {dest}")


# ---------------------------------------------------------------------------------- the brief

BRIEF = """Sei un agente appena arrivato nel progetto vcc2026. La tua copia della repository è la
cartella `{snapshot}`: usa percorsi sotto questa cartella e non leggere altrove. Lavori in sola
lettura: non modifichi, non crei e non cancelli file, non lanci job, download, invii o altri agenti.
Un comando di sola lettura che la repo stessa indica (per esempio `python scripts/31_check_docs.py
--status <percorso>`) puoi eseguirlo, se il tuo ambiente lo permette; se non puoi, dillo.

Parti da `{snapshot}/CLAUDE.md` e segui la sua tabella dei compiti per il compito qui sotto: leggi
ciò che la riga del tuo compito indica e fermati dove dice. Quando hai le risposte, smetti di leggere.

**Il tuo compito.** {consegna}

**Le domande.** Per ciascuna: la risposta breve; la fonte, come percorso relativo alla repo e riga;
il tipo di affermazione (misurato, interpretazione, regola, contraddizione aperta, non documentato,
dato datato). Se la repo non lo dice, o dice cose in conflitto, scrivilo: non inventare e non
dedurre oltre ciò che leggi.

{domande}

**Che cosa restituisci.** Solo un blocco ```json, senza altro testo, con questa forma:

```json
{{"compito": "{task}", "risposte": [{{"id": "{task}.1", "risposta": "...", "fonte": "percorso:riga", "tipo": "..."}}],
 "letture_dichiarate": ["percorso", "..."], "dove_ti_sei_fermato": "una frase"}}
```
"""


def cmd_brief(args) -> None:
    key = load_key()
    task = next(t for t in key["compiti"] if t["id"] == args.task)
    case = Path(args.run) / f"{args.task}_{args.family}"
    prompt = case / "prompt.md"
    refuse(prompt)
    case.mkdir(parents=True, exist_ok=True)
    questions = "\n".join(f"{i}. ({q['id']}) {q['domanda']}" for i, q in enumerate(task["domande"], 1))
    text = BRIEF.format(snapshot=Path(args.snapshot).as_posix(), consegna=task["consegna"],
                        domande=questions, task=task["id"])
    prompt.write_text(text, encoding="utf-8")
    write_json(case / "case.json", {"task": task["id"], "family": args.family, "snapshot": args.snapshot})
    print(prompt)
    if args.family in ("grok", "claude2"):
        print(f"hub: py -3 hub.py start {args.family} --mode read --task-file {prompt} "
              f"--cwd {args.snapshot} --label orient-{task['id'].lower()}")


# -------------------------------------------------------------------------------- the transcript

def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_text(c.get("text") or c.get("content") or "") if isinstance(c, dict) else str(c)
                         for c in content)
    return str(content or "")


def _claude_calls(path: Path):
    calls, results, usage, stamps, seen = {}, {}, {"input": 0, "cache_read": 0, "cache_creation": 0, "output": 0}, [], set()
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        if entry.get("timestamp"):
            stamps.append(entry["timestamp"])
        msg = entry.get("message") or {}
        content = msg.get("content") if isinstance(msg, dict) else None
        if entry.get("type") == "assistant" and isinstance(msg, dict) and msg.get("id") not in seen:
            seen.add(msg.get("id"))
            u = msg.get("usage") or {}
            usage["input"] += u.get("input_tokens", 0)
            usage["cache_read"] += u.get("cache_read_input_tokens", 0)
            usage["cache_creation"] += u.get("cache_creation_input_tokens", 0)
            usage["output"] += u.get("output_tokens", 0)
        for c in content if isinstance(content, list) else []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                calls[c["id"]] = (c["name"], c.get("input") or {})
            elif c.get("type") == "tool_result":
                results[c.get("tool_use_id")] = _text(c.get("content"))
    return calls, results, usage, stamps


def _grok_calls(path: Path):
    calls, results = {}, {}
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        for call in entry.get("tool_calls") or []:
            try:
                arguments = json.loads(call.get("arguments") or "{}")
            except json.JSONDecodeError:
                arguments = {"raw": call.get("arguments")}
            calls[call["id"]] = (call["name"], arguments)
        if entry.get("type") == "tool_result":
            results[entry.get("tool_call_id")] = _text(entry.get("content"))
    stamps = []
    events = path.parent / "events.jsonl"
    if events.exists():
        for line in events.read_text(encoding="utf-8").splitlines():
            ts = json.loads(line).get("ts")
            if ts:
                stamps.append(ts)
    return calls, results, None, stamps


def _relative(raw: str, snapshot: str) -> tuple[str, bool]:
    p = raw.replace("\\", "/")
    s = snapshot.replace("\\", "/").rstrip("/")
    if p.lower().startswith(s.lower() + "/"):
        return p[len(s) + 1:], True
    return p, not re.match(r"^[A-Za-z]:/|^/", p)


def _hub_transcript(agent_dir: Path) -> tuple[str, Path, Path]:
    command = json.loads((agent_dir / "command.json").read_text(encoding="utf-8"))
    argv = command["argv"]
    session = argv[argv.index("--session-id") + 1]
    if "grok" in Path(argv[0]).name.lower():
        hits = list((Path.home() / ".grok" / "sessions").glob(f"*/{session}/chat_history.jsonl"))
        return "grok", hits[0], agent_dir / "result.md"
    hits = list((Path.home() / ".claude" / "projects").glob(f"*/{session}.jsonl"))
    return "claude", hits[0], agent_dir / "result.md"


def cmd_collect(args) -> None:
    case = Path(args.case)
    info = json.loads((case / "case.json").read_text(encoding="utf-8"))
    if args.hub_agent_dir:
        kind, transcript, result = _hub_transcript(Path(args.hub_agent_dir))
        meta_hub = json.loads((Path(args.hub_agent_dir) / "meta.json").read_text(encoding="utf-8"))
    else:
        kind, transcript, result, meta_hub = args.kind, Path(args.transcript), Path(args.result), None
    calls, results, usage, stamps = (_claude_calls if kind == "claude" else _grok_calls)(transcript)
    reads, searches, commands = [], [], []
    for cid, (name, inp) in calls.items():
        out = results.get(cid, "")
        lower = name.lower()
        if lower in ("read", "read_file"):
            raw = inp.get("file_path") or inp.get("target_file") or inp.get("path") or ""
            rel, inside = _relative(raw, info["snapshot"])
            reads.append({"file": rel, "inside_snapshot": inside, "offset": inp.get("offset"),
                          "limit": inp.get("limit"), "lines": sum(1 for l in out.splitlines() if NUMBERED.match(l))})
        elif lower in ("grep", "glob", "grep_search", "file_search", "list_dir", "codebase_search"):
            searches.append({"tool": name, "input": inp, "result_lines": len(out.splitlines())})
        elif lower in ("bash", "powershell", "run_terminal_cmd", "run_command"):
            commands.append({"tool": name, "command": inp.get("command"), "result_lines": len(out.splitlines())})
    answer_text = result.read_text(encoding="utf-8") if result.exists() else ""
    block = re.findall(r"```json\s*(\{.*?\})\s*```", answer_text, re.S)
    answers = json.loads(block[-1]) if block else {"parse_error": True, "raw": answer_text[-4000:]}
    write_json(case / "answers.json", answers)
    write_json(case / "reads.json", {"reads": reads, "searches": searches, "commands": commands})
    write_json(case / "meta.json", {
        "kind": kind, "transcript": str(transcript), "result": str(result),
        "first": min(stamps) if stamps else None, "last": max(stamps) if stamps else None,
        "usage": usage, "hub_meta": {k: meta_hub.get(k) for k in ("model", "duration_s", "extra", "state")} if meta_hub else None})
    print(f"{case}: {len(reads)} reads, {len(searches)} searches, {len(commands)} commands")


# ---------------------------------------------------------------------------------- the score

def _grade(q: dict, text: str) -> float:
    t = " ".join(text.lower().split())
    hits = sum(any(alt.lower() in t for alt in group) for group in q["parole"])
    if hits == len(q["parole"]):
        return 1.0
    if q["tipo"].startswith(("tranello", "attualità")):
        return 0.0
    return 0.5 if hits * 2 >= len(q["parole"]) else 0.0


def cmd_score(args) -> None:
    case = Path(args.case)
    out = case / (f"score_{args.tag}.json" if args.tag else "score.json")
    refuse(out)
    key = load_key()
    info = json.loads((case / "case.json").read_text(encoding="utf-8"))
    task = next(t for t in key["compiti"] if t["id"] == info["task"])
    answers = json.loads((case / "answers.json").read_text(encoding="utf-8"))
    reads = json.loads((case / "reads.json").read_text(encoding="utf-8"))
    manual_path = case / "grading.json"
    manual = json.loads(manual_path.read_text(encoding="utf-8")) if manual_path.exists() else {}
    given = {a.get("id"): a for a in answers.get("risposte", [])}
    rows, points, traps_ok, stale = [], 0.0, True, 0
    for q in task["domande"]:
        a = given.get(q["id"], {})
        auto = _grade(q, f"{a.get('risposta', '')} {a.get('tipo', '')}")
        m = manual.get(q["id"], {})
        got = m.get("punti", auto)
        cited = str(a.get("fonte", "")).replace("\\", "/")
        right_source = any(s["file"] in cited for s in q["fonti"])
        stale += bool(m.get("scaduta"))
        if q["tipo"].startswith(("tranello", "attualità")) and got < 1:
            traps_ok = False
        points += got
        rows.append({"id": q["id"], "auto": auto, "punti": got, "fonte_giusta": right_source,
                     "scaduta": bool(m.get("scaduta")), "nota": m.get("nota")})
    lines = sum(r["lines"] for r in reads["reads"])
    files = sorted({r["file"] for r in reads["reads"]})
    patterns = task["fuori_perimetro"]
    outside = sorted({f for f in files if any(fnmatch.fnmatch(f, p) for p in patterns)})
    outside_snapshot = sorted({r["file"] for r in reads["reads"] if not r["inside_snapshot"]})
    contaminated = any(fnmatch.fnmatch(f, FOLDER_GLOB + "*") or "test_orientamento" in f for f in files)
    budget = 2 * task["righe_minime"]
    n = len(task["domande"])
    passed = (points >= 0.8 * n and traps_ok and stale == 0 and len(outside) <= 1
              and lines <= budget and not contaminated and not outside_snapshot)
    write_json(out, {
        "task": task["id"], "family": info["family"], "questions": rows, "points": points, "of": n,
        "traps_ok": traps_ok, "stale": stale, "lines_read": lines, "budget": budget,
        "files_read": files, "outside_perimeter": outside, "outside_snapshot": outside_snapshot,
        "contaminated": contaminated, "graded_by_hand": sorted(manual), "passed": passed})
    print(f"{task['id']} {info['family']}: {points}/{n}, lines {lines}/{budget}, "
          f"outside {len(outside)}, {'PASS' if passed else 'FAIL'}")


def cmd_summary(args) -> None:
    run = Path(args.run)
    out = run / f"summary_{args.version}.md"
    refuse(out)
    scores = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(run.glob("T*_*/score.json"))]
    if not scores:
        sys.exit("no score.json under the run")
    lines = ["| Compito | Famiglia | Punti | Righe lette / tetto | Fuori perimetro | Tranelli | Esito |",
             "|---|---|---|---|---|---|---|"]
    for s in scores:
        lines.append(f"| {s['task']} | {s['family']} | {s['points']}/{s['of']} | {s['lines_read']}/{s['budget']} | "
                     f"{len(s['outside_perimeter'])} | {'ok' if s['traps_ok'] else 'no'} | "
                     f"{'passa' if s['passed'] else 'non passa'} |")
    passed = sum(s["passed"] for s in scores)
    failing = {}
    for s in scores:
        failing.setdefault(s["task"], []).append(s["passed"])
    both = sorted(t for t, v in failing.items() if len(v) > 1 and not any(v))
    if args.version == "economica":
        ok = passed >= 2 and len(scores) == 3
        rule = "almeno 2 esecuzioni su 3 passano"
    else:
        ok = passed >= 0.8 * len(scores) and not both
        rule = "almeno l'80 % delle esecuzioni passa, e nessun compito fallisce in entrambe le famiglie"
    lines += ["", f"Passano {passed} su {len(scores)}. Regola ({args.version}): {rule}. "
              f"Compiti falliti in entrambe le famiglie: {', '.join(both) or 'nessuno'}. "
              f"**Esito: {'successo' if ok else 'insuccesso'}.**"]
    refuse(out)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("--root"); c.set_defaults(fn=cmd_check)
    sub.add_parser("render").set_defaults(fn=cmd_render)
    c = sub.add_parser("snapshot"); c.add_argument("--commit", required=True); c.add_argument("--dest", required=True)
    c.add_argument("--run", required=True); c.set_defaults(fn=cmd_snapshot)
    c = sub.add_parser("cleanup"); c.add_argument("--dest", required=True); c.set_defaults(fn=cmd_cleanup)
    c = sub.add_parser("brief"); c.add_argument("--task", required=True)
    c.add_argument("--family", required=True, choices=["claude", "claude2", "grok"])
    c.add_argument("--snapshot", required=True); c.add_argument("--run", required=True); c.set_defaults(fn=cmd_brief)
    c = sub.add_parser("collect"); c.add_argument("--case", required=True); c.add_argument("--hub-agent-dir")
    c.add_argument("--kind", choices=["claude", "grok"]); c.add_argument("--transcript"); c.add_argument("--result")
    c.set_defaults(fn=cmd_collect)
    c = sub.add_parser("score"); c.add_argument("--case", required=True); c.add_argument("--tag"); c.set_defaults(fn=cmd_score)
    c = sub.add_parser("summary"); c.add_argument("--run", required=True)
    c.add_argument("--version", required=True, choices=["economica", "completa"]); c.set_defaults(fn=cmd_summary)
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args.fn(args)


if __name__ == "__main__":
    main()
