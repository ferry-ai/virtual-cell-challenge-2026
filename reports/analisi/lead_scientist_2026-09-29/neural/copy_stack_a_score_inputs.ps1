$ErrorActionPreference = 'Stop'
$predictionSource = 'C:\Users\ferra\vcc2026-data\interim\lead_stack_kaggle_A_r1'
$runRoot = 'G:\Il mio Drive\vcc2026\runs'
$predictionDest = Join-Path $runRoot 'lead_stack_kaggle_a_prediction_2026-09-29_r1'
if (Test-Path -LiteralPath $predictionDest) { throw 'Destination exists; refuse overwrite' }
$copySources = @(
    (Join-Path $predictionSource 'prediction_stack.h5ad'),
    (Join-Path $predictionSource 'prediction_transfer.h5ad'),
    (Join-Path $predictionSource 'reports\prediction\finished.json'),
    (Join-Path $predictionSource 'reports\prediction\inference_manifest.json')
)
$expected = @{
    'prediction_stack.h5ad' = '4baa9e71184fcf365a13860843a5700fdcfed245f5e7d51a212b850d6c2d1255'
    'prediction_transfer.h5ad' = '0210a9ffb131ee9f0412b89b70ea4e6d9aa0ea7c39d63b2276ab86e7dbd55828'
}
foreach ($sourceFile in $copySources) {
    $name = [IO.Path]::GetFileName($sourceFile)
    if ($expected.ContainsKey($name) -and (Get-FileHash -LiteralPath $sourceFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected[$name]) { throw "Source SHA differs: $name" }
}
[IO.Directory]::CreateDirectory($predictionDest) | Out-Null
$receipts = @()
foreach ($sourceFile in $copySources) {
    $name = [IO.Path]::GetFileName($sourceFile)
    $targetFile = Join-Path $predictionDest $name
    [IO.File]::Copy($sourceFile, $targetFile, $false)
    $sourceHash = (Get-FileHash -LiteralPath $sourceFile -Algorithm SHA256).Hash.ToLowerInvariant()
    $targetHash = (Get-FileHash -LiteralPath $targetFile -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($sourceHash -ne $targetHash) { throw "Drive copy changed: $name" }
    $receipts += [pscustomobject]@{name=$name;sha256=$targetHash;bytes=(Get-Item -LiteralPath $targetFile).Length}
}
$receipts | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'stack_a_drive_receipt.json') -Encoding utf8
$queueTarget = Join-Path $runRoot 'queue\081_lead_stack_score_kaggle_a_r1.sh'
if (Test-Path -LiteralPath $queueTarget) { throw 'Queue already exists' }
[IO.File]::Copy((Join-Path $PSScriptRoot '081_lead_stack_score_kaggle_a_r1.sh'), $queueTarget, $false)
$receipts | Format-Table
Write-Output 'Queued 081 scoring frozen Kaggle A predictions, no VCC submission'
