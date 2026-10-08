"""Locate existing local T1 tables by their exact frozen hashes; metadata only."""
import argparse
import os
from pathlib import Path
import json
from percorso import DATA,HERE,read,sha,write_new,now


def main(output='local_t1_sources_r1.json',all_local=False):
    release=read(HERE/'release_t1_r1.json');found={};wanted=set(release['voted']);candidates=0
    sizes={entry['bytes']:name for name,entry in release['voted'].items()}
    for root,dirs,files in os.walk(DATA if all_local else DATA/'processed'):
        dirs[:]=[d for d in dirs if d not in {'.venv','orch-venv','orchestrator','.git'}]
        for filename in files:
            name=filename.removesuffix('.bin').removesuffix('.npz')
            if all_local:
                path=Path(root)/filename
                try:name=sizes.get(path.stat().st_size)
                except OSError:continue
            if name not in wanted or name in found:continue
            path=Path(root)/filename;expected=release['voted'][name]
            if path.stat().st_size!=expected['bytes']:continue
            candidates+=1
            if sha(path)==expected['sha256']:found[name]=str(path)
    result=dict(utc=now(),found=found,missing=sorted(wanted-set(found)),size_candidates_hashed=candidates)
    write_new(HERE/output,result)
    print(json.dumps(dict(found=len(found),missing=result['missing'])))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--output',default='local_t1_sources_r1.json');p.add_argument('--all-local',action='store_true')
    a=p.parse_args();main(a.output,a.all_local)
