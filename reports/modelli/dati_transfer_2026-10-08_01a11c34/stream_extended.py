"""Read the provider live log stream; print only bounded sanitized progress."""
import argparse
import json
import re
from percorso import HERE,DATA,read
from quick_generation_cloud import api_for_owner

p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('label');a=p.parse_args()
proof=read(HERE/a.folder/'prepared.json')
dest=DATA/'processed/dati_transfer_2026-10-08_01a11c34'/a.folder/'streams';dest.mkdir(parents=True,exist_ok=True)
try:
    with (dest/(a.label+'.jsonl')).open('x',encoding='utf-8') as out:
        for event in api_for_owner(proof['owner']).kernels_logs_stream(proof['slug']):
            out.write(json.dumps(event)+'\n');out.flush()
            for line in str(event.get('data','')).splitlines():
                line=re.sub(r'https?://\S+','[URL REDACTED]',line)
                line=re.sub(r'[A-Za-z0-9+/=]{100,}','[ENCODED DATA OMITTED]',line)
                if len(line)>1000:line='[LONG LINE OMITTED]'
                print(line,flush=True)
except Exception as exc:
    print('Log stream ended: '+type(exc).__name__,flush=True)
