"""Read the official CLI's authenticated account and daily-limit endpoints."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from vcc import api, auth, config

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
if args.out.exists():
    raise FileExistsError(args.out)
profile = config.resolve_profile()
state = auth.read_profile_state(profile)
endpoint = config.resolve_endpoint(stored=state.get("endpoint"))
if endpoint.rstrip("/") != "https://virtualcellchallenge.org":
    raise ValueError("Only the installed official production endpoint is allowed")
credential = auth.resolve_token(profile)
identity = api.get_me(endpoint, credential.token)
limits = api.get_limits(endpoint, credential.token)
result = {"checked_utc": datetime.now(timezone.utc).isoformat(),
          "read_only": True, "can_submit": identity.get("can_submit"),
          "blockers": identity.get("blockers"), "daily_limits": limits}
with args.out.open("x", encoding="utf-8") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
print(json.dumps(result, indent=2))
