"""Make a new immutable queued script using an already tested snapshot revision."""
import argparse
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument("--revision", type=int, required=True)
p.add_argument("--sha256", required=True)
a = p.parse_args()
assert a.revision > 2 and len(a.sha256) == 64
here = Path(__file__).resolve().parent
text = (here / "colab_generator_r2.sh").read_text(encoding="utf-8")
text = text.replace("_r2", f"_r{a.revision}")
text = text.replace("634f228e1c358a1f1d4474d59a0dcac2f3a501921d68795ca9acd4b371db1033", a.sha256)
with (here / f"colab_generator_r{a.revision}.sh").open("x", encoding="utf-8", newline="\n") as handle:
    handle.write(text)
