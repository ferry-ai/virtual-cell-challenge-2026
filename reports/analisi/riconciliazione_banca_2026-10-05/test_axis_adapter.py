"""Reproduce the low-control zero mismatch against the original AxisTable adapter."""
import json,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
R=Path(__file__).resolve().parents[3];sys.path.insert(0,str(R/'src'))
from vcc2026.multisource import AxisTable
def main():
    src=SimpleNamespace(genes=['G1','G2'],targets=['T'],control_mean=np.array([.9999999,.0000001]),
      shrunk=np.array([[.1,0]],np.float32),raw=np.array([[.25,0]],np.float32),
      se=np.array([[.2,np.nan]],np.float32),n_cells=np.array([100]),meta={})
    expected=AxisTable.from_source('x',src,['G1','extra','G2'])
    columns=np.array([0,2]);old={};corrected={}
    usable=src.control_mean>=1e-6
    for key in ('shrunk','raw','se'):
        old[key]=np.full((1,3),np.nan,np.float32);old[key][:,columns]=getattr(src,key)
        corrected[key]=np.full((1,3),np.nan,np.float32);corrected[key][:,columns[usable]]=getattr(src,key)[:,usable]
        assert np.allclose(corrected[key],getattr(expected,key),equal_nan=True)
    assert np.isfinite(old['shrunk'][0,2]) and np.isnan(expected.shrunk[0,2])
    proof={'original_adapter_equivalence':True,'r4_low_control_zero_mismatch_reproduced':True,
      'scope':'small exact adapter fixture, not biological validation','required_rule':'control_mean>=1e-6 before scatter, otherwise NaN',
      'no_formula_or_threshold_change':True,'no_SE_invented':True}
    Path(__file__).with_name('axis_adapter_repro.json').write_text(json.dumps(proof,indent=2))
    print('original AxisTable mask reproduced; corrected scatter equal on all three arrays')
if __name__=='__main__':main()
