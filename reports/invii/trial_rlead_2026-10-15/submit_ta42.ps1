# Upload of ta 42 (prepared 15/10, owner go in chat on 15/10), as a separate Windows process (PROCEDURE §2, rule 5): the registered name and description, the
# package of stage 48, the output of vcc saved as it is. No retry here: an interrupted upload is resumed by hand
# with `vcc submit --resume <entry>` after checking the sha256 of the .vcc against packaging.json.
$ErrorActionPreference = 'Continue'
$D = 'C:\Users\39346\vcc2026-data'
$dir = $PSScriptRoot
$vcc = Join-Path $D 'artifacts\ta42pack\prediction.vcc'
$name = 'ta 42 T3 x centred bridge network ensemble'
$desc = $name
$env:VCC2026_DATA_ROOT = $D
$env:PYTHONIOENCODING = 'utf-8'
@{started_utc = [DateTime]::UtcNow.ToString('o'); file = $vcc; bytes = (Get-Item -LiteralPath $vcc).Length; pid = $PID;
  model_name = $name; description_chars = $desc.Length} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dir 'submit_ta42_started.json') -Encoding UTF8
& (Join-Path $D '.venv\Scripts\vcc.exe') --json submit $vcc -m $name -d $desc 1> (Join-Path $dir 'submit_ta42_raw.json') 2> (Join-Path $dir 'submit_ta42_stderr.txt')
$code = $LASTEXITCODE
@{finished_utc = [DateTime]::UtcNow.ToString('o'); exit_code = $code} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dir 'submit_ta42_finished.json') -Encoding UTF8
