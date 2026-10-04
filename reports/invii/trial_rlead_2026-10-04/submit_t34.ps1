# Upload of t34, as a separate Windows process (PROCEDURE §2, rule 5): the registered name and description, the
# package of stage 48, the output of vcc saved as it is. No retry here: an interrupted upload is resumed by hand
# with `vcc submit --resume <entry>` after checking the sha256 of the .vcc against packaging.json.
$ErrorActionPreference = 'Continue'
$D = 'C:\Users\39346\vcc2026-data'
$dir = $PSScriptRoot
$vcc = Join-Path $D 'artifacts\t34pack\prediction.vcc'
$name = 'trial-34 contrastive effect network on the trial-31 K562 transfer with the trial-22 generator'
$desc = (Get-Content -LiteralPath (Join-Path $dir 't34_description.txt') -Raw -Encoding UTF8).Trim()
$env:VCC2026_DATA_ROOT = $D
$env:PYTHONIOENCODING = 'utf-8'
@{started_utc = [DateTime]::UtcNow.ToString('o'); file = $vcc; bytes = (Get-Item -LiteralPath $vcc).Length; pid = $PID;
  model_name = $name; description_chars = $desc.Length} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dir 'submit_t34_started.json') -Encoding UTF8
& (Join-Path $D '.venv\Scripts\vcc.exe') --json submit $vcc -m $name -d $desc 1> (Join-Path $dir 'submit_t34_raw.json') 2> (Join-Path $dir 'submit_t34_stderr.txt')
$code = $LASTEXITCODE
@{finished_utc = [DateTime]::UtcNow.ToString('o'); exit_code = $code} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dir 'submit_t34_finished.json') -Encoding UTF8
