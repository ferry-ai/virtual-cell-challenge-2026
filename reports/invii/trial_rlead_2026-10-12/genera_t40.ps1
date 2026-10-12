# Stage 45 (t28 emission on the centred-network effects) then stage 48 (package + official validator) for t40.
# Logs go next to this script; the manifests are copied here after the run.
$ErrorActionPreference = 'Stop'
$D = 'C:\Users\39346\vcc2026-data'
$R = Split-Path (Split-Path (Split-Path $PSScriptRoot))
$dir = $PSScriptRoot
$E = Join-Path $D 'processed\effects_rete_centrata_2026-10-12'
$env:VCC2026_DATA_ROOT = $D
$py = Join-Path $R 'scripts\py.cmd'
& $py (Join-Path $R 'scripts\45_generate_prediction.py') --run-id t40gen --trial trial-ext-profile `
    --effects "A=$E\effects_A.npz" --effects "B=$E\effects_B.npz" --effects "C=$E\effects_C.npz" `
    --effects-scale 1.5 --gene-dispersion --gene-dispersion-scale 1.0 `
    1> (Join-Path $dir 't40_stage45.log') 2> (Join-Path $dir 't40_stage45.log.err')
if ($LASTEXITCODE -ne 0) { throw "stage 45 exit $LASTEXITCODE" }
& $py (Join-Path $R 'scripts\48_package_prediction.py') --run-id t40pack --prediction (Join-Path $D 'artifacts\t40gen\prediction.h5ad') `
    1> (Join-Path $dir 't40_stage48.log') 2> (Join-Path $dir 't40_stage48.log.err')
if ($LASTEXITCODE -ne 0) { throw "stage 48 exit $LASTEXITCODE" }
