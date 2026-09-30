"""New operational scoring attempt; await cloud content hashes before starting."""
from pathlib import Path

root = Path(__file__).resolve().parent
source = (root / "081_lead_stack_score_kaggle_a_r1.sh").read_text(encoding="utf-8")
source = source.replace("lead_stack_score_kaggle_a_code_r1", "lead_stack_score_kaggle_a_code_r2")
source = source.replace("lead_stack_score_kaggle_a_2026-09-29_r1", "lead_stack_score_kaggle_a_2026-09-29_r2")
start = source.index('test -f "$PREDICTION/finished.json"')
end = source.index('mkdir -p "$CODE_DIR"')
source = source[:start] + '''test -x "$PY"
test ! -e "$OUT"
test ! -e "$CODE_DIR"
inputs_ready() {
  test -f "$PREDICTION/finished.json" || return 1
  test -f "$PREDICTION/inference_manifest.json" || return 1
  echo "4baa9e71184fcf365a13860843a5700fdcfed245f5e7d51a212b850d6c2d1255  $PREDICTION/prediction_stack.h5ad" | sha256sum -c - || return 1
  echo "0210a9ffb131ee9f0412b89b70ea4e6d9aa0ea7c39d63b2276ab86e7dbd55828  $PREDICTION/prediction_transfer.h5ad" | sha256sum -c - || return 1
  echo "9f89e6380704210adac7445199ca15117e85138193fd55c3cd6de8749a681f65  $SETUP/scoring_snapshot.tar.gz" | sha256sum -c - || return 1
}
for attempt in $(seq 1 45); do
  if inputs_ready; then break; fi
  echo "Waiting for complete Drive inputs, attempt $attempt/45"
  sleep 20
done
inputs_ready
''' + source[end:]
target = root / "082_lead_stack_score_kaggle_a_r2.sh"
with target.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(source)
print(target)
