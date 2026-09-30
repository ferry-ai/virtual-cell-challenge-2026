"""Read public VCC pages/assets without authentication; save only provenance and links.

Full downloaded assets remain only in memory. Keyword matches are printed for
inspection and are not copied into the repository.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.request
from urllib.parse import urljoin


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("urls", nargs="*")
parser.add_argument("--links-from", type=Path)
parser.add_argument("--out", type=Path, required=True)
parser.add_argument("--find", default="non.?commercial|pre.?train|Arc Virtual Cell Model|Model License")
args = parser.parse_args()
if args.links_from:
    records = json.loads(args.links_from.read_text(encoding="utf-8"))
    args.urls += sorted({url for record in records for url in record["public_links"]
                        if url.startswith("https://virtualcellchallenge.org/") and ".js" in url})
if not args.urls:
    parser.error("Provide URLs or --links-from")
args.out.parent.mkdir(parents=True, exist_ok=True)
records = []
for url in args.urls:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
        final_url = response.url
        headers = {key: response.headers.get(key) for key in ("Date", "Last-Modified", "ETag", "Content-Type")}
    content = raw.decode("utf-8", errors="replace")
    paths = re.findall(r'(?:src|href)=["\']([^"\']+)', content)
    paths += re.findall(r'["\']([^"\']+\.js(?:\?[^"\']*)?)["\']', content)
    links = sorted({urljoin(final_url, p) for p in paths if ".js" in p or "rules" in p or "faq" in p})
    records.append({"url": url, "final_url": final_url, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                    "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "headers": headers,
                    "public_links": links})
    modules = sorted(set(re.findall(r'\b[a-zA-Z_$]\w*\((\d+)\)', content)))
    print(json.dumps({"url": final_url, "bytes": len(raw), "links": links,
                      "module_references": modules}, ensure_ascii=False))
    for i, match in enumerate(re.finditer(args.find, content, flags=re.IGNORECASE)):
        if i >= 30:
            print("more matches omitted")
            break
        print(json.dumps({"offset": match.start(), "text": content[max(0, match.start()-100):match.end()+300]}, ensure_ascii=False))
with args.out.open("x", encoding="utf-8") as stream:
    json.dump(records, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
