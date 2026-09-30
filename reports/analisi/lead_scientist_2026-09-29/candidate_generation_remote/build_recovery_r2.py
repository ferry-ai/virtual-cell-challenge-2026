"""Freeze a new t28 attempt with durable stage-45 output, no scientific edits."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
OUT = HERE / "recovery_r2"
OUT.mkdir(exist_ok=False)
original = HERE / "generate_candidate.py"
assert hashlib.sha256(original.read_bytes()).hexdigest() == "c73f518ee173566d6df851f79815bd11f2838ca6cb5af1e471368717d1dcccfb"
text = original.read_text(encoding="utf-8")
insertion = '''def publish_verified(source, destination):
    """Preserve a completed stage before the next stage can lose the runtime."""
    source, destination = Path(source), Path(destination)
    partial = destination.with_name(destination.name + ".partial")
    if destination.exists() or partial.exists():
        raise FileExistsError(destination)
    expected_sha, expected_bytes = sha256(source), source.stat().st_size
    with source.open("rb") as inp, partial.open("xb") as out:
        shutil.copyfileobj(inp, out, length=8 * 1024**2)
        out.flush()
    checked_file(partial, expected_sha, expected_bytes)
    partial.rename(destination)
    return {"sha256": expected_sha, "bytes": expected_bytes,
            "full_sha256_verified": True, "path": str(destination)}


'''
assert text.count("def safe_child(root, relative):") == 1
text = text.replace("def safe_child(root, relative):", insertion + "def safe_child(root, relative):")
old = '''        prediction_sha = sha256(scratch / "gen/prediction.h5ad")
        command48 += ["--expect-sha256", prediction_sha]'''
new = '''        prediction_sha = sha256(scratch / "gen/prediction.h5ad")
        checkpoint = destination / "stage45_checkpoint"
        checkpoint.mkdir()
        for source in sorted((scratch / "gen").iterdir()):
            if source.is_file() and source.suffix in {".json", ".log", ".txt"}:
                publish_verified(source, checkpoint / source.name)
        publish_verified(scratch / "stage45.log", checkpoint / "stage45.log")
        receipt = publish_verified(scratch / "gen/prediction.h5ad", checkpoint / "prediction.h5ad")
        if receipt["sha256"] != prediction_sha:
            raise ValueError("Generation changed during durable checkpoint copy")
        save(checkpoint / "complete.json", receipt | {"utc": datetime.now(timezone.utc).isoformat(),
             "scientific_recipe_unchanged": True, "stage48_not_yet_started": True})
        command48 += ["--expect-sha256", prediction_sha]'''
assert text.count(old) == 1
text = text.replace(old, new)
(OUT / "generate_candidate_r2.py").write_text(text, encoding="utf-8", newline="\n")
bootstrap = (HERE / "colab_candidate_environment_r2.sh").read_text(encoding="utf-8")
bootstrap = bootstrap.replace('OUT="$DRIVE/runs/lead_candidate_environment_2026-09-29_r2"',
                              'OUT="$DRIVE/runs/lead_candidate_environment_2026-09-29_r3"')
(OUT / "078_lead_candidate_environment_r3.sh").write_text(bootstrap, encoding="utf-8", newline="\n")
launcher = (HERE / "colab_t28_generate_r1.sh").read_text(encoding="utf-8")
launcher = launcher.replace("lead_candidate_t28_setup_2026-09-29_r1", "lead_candidate_t28_setup_2026-09-29_r2")
launcher = launcher.replace("lead_candidate_t28_2026-09-29_r1", "lead_candidate_t28_2026-09-29_r2")
launcher = launcher.replace("generate_candidate.py", "generate_candidate_r2.py")
launcher = launcher.replace("c73f518ee173566d6df851f79815bd11f2838ca6cb5af1e471368717d1dcccfb",
                            hashlib.sha256((OUT / "generate_candidate_r2.py").read_bytes()).hexdigest())
launcher = launcher.replace("--run-id t28 --phi-scale", "--run-id t28r2 --phi-scale")
launcher = launcher.replace('test -f "$ENVROOT/ready.json"', '''while ! test -f "$DRIVE/runs/queue/078_lead_candidate_environment_r3.sh.done"; do sleep 10; done
test -f "$ENVROOT/ready.json"''')
(OUT / "079_lead_t28_generate_r2.sh").write_text(launcher, encoding="utf-8", newline="\n")
manifest = {"reason": "Owner diagnostic 2026-09-29T19:58:07Z: Colab scratch, model venv and Drive mount absent; old processes gone",
            "science": "Identical frozen code archive, inputs, parameters and RNG; new run/output names only",
            "engineering": "Full SHA256-verified stage45 H5AD persisted on Drive before packaging",
            "old_attempt_preserved": True, "submission": False,
            "files": {p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p in OUT.iterdir() if p.is_file()}}
(OUT / "review.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps(manifest, indent=2))
