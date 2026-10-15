# Resume of the ta 42 upload interrupted by the PC restart of 15/10 (~19:20 CEST): same entry wAUBxckeaH0Ab8bMXYaM, same
# .vcc (sha256 cf5aa84e... checked against ta42pack/packaging.json before resuming), receipts in new files.
$ErrorActionPreference = 'Continue'
$D = 'C:\Users\39346\vcc2026-data'
$dir = $PSScriptRoot
$vcc = Join-Path $D 'artifacts\ta42pack\prediction.vcc'
$name = 'ta 42 T3 x centred bridge network ensemble'
$desc = $name
$entry = 'wAUBxckeaH0Ab8bMXYaM'
$env:VCC2026_DATA_ROOT = $D
$env:PYTHONIOENCODING = 'utf-8'
@{started_utc = [DateTime]::UtcNow.ToString('o'); file = $vcc; entry = $entry; pid = $PID} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dir 'resume_ta42_started.json') -Encoding UTF8
& (Join-Path $D '.venv\Scripts\vcc.exe') --json submit $vcc -m $name -d $desc --resume $entry 1> (Join-Path $dir 'resume_ta42_raw.json') 2> (Join-Path $dir 'resume_ta42_stderr.txt')
$code = $LASTEXITCODE
@{finished_utc = [DateTime]::UtcNow.ToString('o'); exit_code = $code} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dir 'resume_ta42_finished.json') -Encoding UTF8
