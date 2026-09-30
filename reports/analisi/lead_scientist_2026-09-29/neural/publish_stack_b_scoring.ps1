param([Parameter(Mandatory=$true)][string]$Setup)
$ErrorActionPreference = 'Stop'
$plan = Get-Content -LiteralPath (Join-Path $Setup 'publish_plan.json') -Raw | ConvertFrom-Json
$allowedRoot = [IO.Path]::GetFullPath('G:\Il mio Drive\vcc2026\runs\')
foreach ($item in $plan.transfers) {
    $destinationPath = [IO.Path]::GetFullPath($item.destination)
    if (-not $destinationPath.StartsWith($allowedRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected destination outside project runs' }
    if (Test-Path -LiteralPath $destinationPath) { throw "Refuse existing destination: $destinationPath" }
    if ((Get-Item -LiteralPath $item.source).Length -ne $item.bytes -or (Get-FileHash -LiteralPath $item.source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256) { throw "Source differs from frozen transfer plan: $($item.source)" }
}
foreach ($item in $plan.transfers) {
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($item.destination)) | Out-Null
    [IO.File]::Copy($item.source,$item.destination,$false)
    if ((Get-FileHash -LiteralPath $item.destination -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256) { throw 'Drive readback hash differs' }
}
$guardEntries = @($plan.transfers | Where-Object { [IO.Path]::GetFileName($_.destination) -eq 'preflight.py' })
$contractEntries = @($plan.transfers | Where-Object { [IO.Path]::GetFileName($_.destination) -eq 'job_contract.json' })
if ($guardEntries.Count -ne 1 -or $contractEntries.Count -ne 1) { throw 'Ambiguous frozen guard/contract' }
$guardPath = $guardEntries[0].destination
$contractPath = $contractEntries[0].destination
$receiptPath = Join-Path $Setup 'preflight_local_receipt.json'
& (Join-Path (Get-Location) 'scripts\py.cmd') $guardPath validate --manifest $contractPath --site local --receipt $receiptPath
if ($LASTEXITCODE -ne 0) { throw 'Preflight failed; no queue publication' }
$receipt = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
if ($receipt.status -ne 'PASS' -or $receipt.validator_sha256 -ne $guardEntries[0].sha256 -or $receipt.manifest_sha256 -ne $contractEntries[0].sha256 -or (Get-FileHash -LiteralPath $plan.launcher -Algorithm SHA256).Hash.ToLowerInvariant() -ne $plan.launcher_sha256) { throw 'Preflight/launcher contract differs' }
$queuePath = [IO.Path]::GetFullPath($plan.queue)
if (-not $queuePath.StartsWith((Join-Path $allowedRoot 'queue\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected queue destination' }
if (Test-Path -LiteralPath $queuePath) { throw 'Queue file already exists' }
[IO.File]::Copy($plan.launcher,$queuePath,$false)
Write-Output '084 queued only after full local preflight PASS; runtime preflight remains mandatory before scoring.'
