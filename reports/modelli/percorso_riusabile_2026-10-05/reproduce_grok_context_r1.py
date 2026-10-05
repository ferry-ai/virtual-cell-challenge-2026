"""Tiny independent counterexample: equal donor/condition must not merge contexts."""
import json,sys
from pathlib import Path
import numpy as np
import pandas as pd
from pipeline_state import HERE
sys.path.insert(0,str(HERE/'agenti/grok_transfer_esteso_r1'))
from linear_effects import estimate_source


def main():
    rows=pd.DataFrame([{'study':'study','context':context,'donor_or_clone':'D1',
        'condition':'Rest','modality':'CRISPRi','chemistry':'Flex','target':target,
        'n':20,'line_group':'line'} for context in ('c1','c2') for target in ('NTC','T')])
    counts=np.array([[1000,1000],[1800,200],[1000,1000],[200,1800]],float)
    out=estimate_source(rows,counts,np.ones_like(counts,dtype=bool),['g0','g1'],'source',modality='CRISPRi')
    receipt={'case':'same donor and condition, two distinct contexts with opposite responses',
        'expected_distinct_contexts':2,'returned_tables':len(out['tables']),
        'observed_raw':[t.raw.tolist() for t in out['tables']],
        'finding':'contexts collapsed by condition-only grouping; D-053 not met'}
    path=HERE/'grok_context_repro_r1.json';path.open('x').write(json.dumps(receipt,indent=1))
    print(json.dumps(receipt))


if __name__=='__main__':main()
