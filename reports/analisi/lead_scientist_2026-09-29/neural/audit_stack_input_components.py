"""Additive input audit: separate model-vocabulary loss from common-support loss.

Reuses the frozen first audit reader. Both source hashes are present in output;
does not alter that script, its r1 results, model inputs, or decision rules.
"""
import numpy as np
import scipy.sparse as sp
import audit_stack_input_axis as base


def population(x, genes, other, model, exact, upper, name):
    result,cells=original_population(x,genes,other,model,exact,upper,name)
    x=sp.csr_matrix(x); genes=np.asarray(genes,dtype=str)
    native=np.array([g in model for g in genes])
    common=np.array([g in exact for g in genes])
    native_counts=np.asarray(x[:,native].sum(axis=1,dtype=np.float64)).ravel()
    totals=cells.library_total.to_numpy(); retained=cells.retained_counts_exact.to_numpy()
    sums=np.asarray(x.sum(axis=0,dtype=np.float64)).ravel()
    extras=np.flatnonzero(native&~common)
    extras=extras[np.argsort(-sums[extras],kind='stable')]
    result['loss_components']={
        'genes_in_own_axis_and_model':int(native.sum()),
        'genes_removed_only_by_other_axis':int(len(extras)),
        'counts_in_own_axis_and_model':int(native_counts.sum()),
        'fraction_all_counts_outside_model':float(1-native_counts.sum()/totals.sum()),
        'fraction_all_counts_removed_only_by_other_axis':float((native_counts-retained).sum()/totals.sum()),
        'fraction_model_mappable_counts_removed_only_by_other_axis':float(1-retained.sum()/native_counts.sum()),
        'median_native_model_library_size':float(np.median(native_counts)),
        'top20_removed_only_by_other_axis':[
            {'gene':str(genes[i]),'counts':int(sums[i]),'fraction_of_all_counts':float(sums[i]/totals.sum())}
            for i in extras[:20]]}
    result['diagnostic_extension_sha256']=base.pilot.sha(__file__)
    cells['native_model_library_total']=native_counts
    cells['lost_fraction_outside_model']=(totals-native_counts)/totals
    cells['lost_fraction_additional_shared_axis']=(native_counts-retained)/totals
    np.testing.assert_allclose(cells.lost_fraction_outside_model+cells.lost_fraction_additional_shared_axis,
                               cells.lost_fraction_exact,rtol=0,atol=1e-15)
    return result,cells


original_population=base.population

if __name__=='__main__':
    base.population=population
    base.main()
