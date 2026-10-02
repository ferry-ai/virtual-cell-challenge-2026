"""List every dataset of one Kaggle account with its privacy flag and size, as the Kaggle API reports them.

The token comes from a kaggle.json file and is passed to the API in this process only; it is never printed.
"""
import json
import os
import sys

token_file = sys.argv[1]
with open(token_file, encoding="utf-8") as fh:
    tok = json.load(fh)
os.environ.pop("KAGGLE_CONFIG_DIR", None)
os.environ["KAGGLE_USERNAME"], os.environ["KAGGLE_KEY"] = tok["username"], tok["key"]
from kaggle.api.kaggle_api_extended import KaggleApi  # noqa: E402

api = KaggleApi()
api.authenticate()
out, page = [], 1
while True:
    items = api.dataset_list(mine=True, page=page)
    if not items:
        break
    for d in items:
        get = (lambda k: getattr(d, k, None) if not isinstance(d, dict) else d.get(k))
        out.append({"ref": get("ref"), "is_private": get("is_private") if get("is_private") is not None else get("isPrivate"),
                    "bytes": get("total_bytes") if get("total_bytes") is not None else get("totalBytes"),
                    "updated": str(get("last_updated") or get("lastUpdated"))})
    page += 1
print(json.dumps({"account": tok["username"], "datasets": out}, indent=1))
