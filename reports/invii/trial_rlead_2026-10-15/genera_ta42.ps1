# Stage 45 (td 28 / td 38 emission) then stage 48 (package + official validator) for ta 42 (T3 0.7 + ta 40 0.3).
# Logs go next to this script; the manifests are copied here after the run.
$ErrorActionPreference = 'Stop'
$D = 'C:\Users\39346\vcc2026-data'
$R = Split-Path (Split-Path (Split-Path $PSScriptRoot))
$dir = $PSScriptRoot
$E = Join-Path $D 'processed\effects_ta42_ens07_2026-10-15'
$env:VCC2026_DATA_ROOT = $D
$py = Join-Path $R 'scripts\py.cmd'
& $py (Join-Path $R 'scripts\45_generate_prediction.py') --run-id ta42gen --trial trial-ext-profile `
    --effects "A=$E\effects_A.npz" --effects "B=$E\effects_B.npz" --effects "C=$E\effects_C.npz" `
    --effects-scale 1.5 --gene-dispersion --gene-dispersion-scale 1.0 `
    1> (Join-Path $dir 'ta42_stage45.log') 2> (Join-Path $dir 'ta42_stage45.log.err')
if ($LASTEXITCODE -ne 0) { throw "stage 45 exit $LASTEXITCODE" }
& $py (Join-Path $R 'scripts\48_package_prediction.py') --run-id ta42pack --prediction (Join-Path $D 'artifacts\ta42gen\prediction.h5ad') `
    1> (Join-Path $dir 'ta42_stage48.log') 2> (Join-Path $dir 'ta42_stage48.log.err')
if ($LASTEXITCODE -ne 0) { throw "stage 48 exit $LASTEXITCODE" }
