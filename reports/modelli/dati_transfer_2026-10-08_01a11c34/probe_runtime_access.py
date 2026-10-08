"""Withdrawn local probe, retained as the record of a rejected proposal.

Never executed: owner approval covers only private davideferrante11 jobs.
Use runtime_view_resolver there; this local entry point is disabled.
"""
import argparse
from collections import Counter
import copy
from pathlib import Path
from percorso import DATA,HERE,now,pin,read,sha,write_new
from runtime_view_resolver import resolve


def main(revision,tag):
    raise RuntimeError('Local probe is not authorized; resolve inputs inside the approved private df11 job')
    # Unexecuted proposal retained below for provenance, not as an active workflow.
    stage=DATA/'processed/dati_transfer_2026-10-08_01a11c34/runtime_access'/revision
    inputs=read(stage/'runtime_inputs.json');view=read(inputs['view']['path'])
    locators=read(stage/'private_locators.json')['files'];selected={}
    for c in view['chunks']:
        if c['producer']+'/'+c['producer_file'] in locators:selected.setdefault(c['producer'],c)
    if len(selected)!=5:raise ValueError('expected exactly five authorised producer probes')
    probe=copy.deepcopy(view);probe['chunks']=list(selected.values())
    counts=Counter()
    for c in probe['chunks']:counts[c['context_id']]+=len(c['targets'])
    probe.update(probe_only=True,model_fit=False,expected_rows_by_context=dict(counts),
        response_shape=[sum(counts.values()),len(probe['genes'])],
        scope='five real authenticated chunks only; not a complete training view',parent_view=inputs['view'])
    folder=DATA/'processed/dati_transfer_2026-10-08_01a11c34/runtime_access_probes'/tag
    folder.mkdir(parents=True,exist_ok=False);path=folder/'probe.json';write_new(path,probe)
    result=resolve(path,sha(path),[],folder/'cache',folder/'resolved.json',stage/'private_locators.json')
    write_new(HERE/('runtime_access_probe_'+tag+'.json'),dict(utc=now(),scope=probe['scope'],
        execution_site='local host; Kaggle must repeat complete resolution before fit',
        source_view=inputs['view'],probe=pin(path),receipt=pin(folder/'resolved.receipt.json'),
        actual_chunks=len(selected),actual_bytes=result['bytes_verified'],all_probe_hashes_match=True,
        private_urls_in_report=False,complete_runtime_access_verified=False,model_fit=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('revision');p.add_argument('tag');a=p.parse_args();main(a.revision,a.tag)
