# Generation (stage 45) and packaging (stage 48) of t30, as a separate Windows process (PROCEDURE §2, rule 5): the t25
# arguments unchanged (trial-ext-profile, seed and scale by default, official controls), only the effects files change
# (PROTOCOLLO.md §13-§14 of reports/modelli/ibrido_selettivo_2026-10-04). Logs and receipts next to this script.
$ErrorActionPreference = 'Continue'
$R = 'C:\Users\ferra\OneDrive\Desktop\vcc2026'
$D = 'C:\Users\ferra\vcc2026-data'
$dir = $PSScriptRoot
$E = Join-Path $D 'processed\ibrido_selettivo_2026-10-04\export_abc_r2'
$env:VCC2026_DATA_ROOT = $D
$env:PYTHONIOENCODING = 'utf-8'
Set-Location -LiteralPath $R
@{started_utc = [DateTime]::UtcNow.ToString('o'); pid = $PID; effects = $E} | ConvertTo-Json |
    Set-Content -LiteralPath (Join-Path $dir 't30_gen_started.json') -Encoding UTF8
& (Join-Path $R 'scripts\py.cmd') scripts\45_generate_prediction.py --run-id t30gen --trial trial-ext-profile `
    --effects "A=$E\effects_A.npz" --effects "B=$E\effects_B.npz" --effects "C=$E\effects_C.npz" *> (Join-Path $dir 't30_stage45.log')
$c45 = $LASTEXITCODE
$c48 = $null
if ($c45 -eq 0) {
    & (Join-Path $R 'scripts\py.cmd') scripts\48_package_prediction.py --run-id t30pack `
        --prediction (Join-Path $D 'artifacts\t30gen\prediction.h5ad') *> (Join-Path $dir 't30_stage48.log')
    $c48 = $LASTEXITCODE
}
@{finished_utc = [DateTime]::UtcNow.ToString('o'); stage45_exit = $c45; stage48_exit = $c48} | ConvertTo-Json |
    Set-Content -LiteralPath (Join-Path $dir 't30_gen_finished.json') -Encoding UTF8
