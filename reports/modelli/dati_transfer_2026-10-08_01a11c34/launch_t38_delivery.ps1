param([string]$Attempt = 'delivery_r1', [string]$Evidence = 'completion_r1', [switch]$WaitForGeneration, [string]$GenerationFolder = 'generation_recovery/r1')
$ErrorActionPreference = 'Stop'
if ($Attempt -notmatch '^[a-z0-9_]+$' -or $Evidence -notmatch '^[a-z0-9_]+$') { throw 'Invalid run label' }
if ($GenerationFolder -notmatch '^generation_recovery/r[0-9]+$') { throw 'Invalid generation folder' }
$taskFolder = $PSScriptRoot
$taskRoot = (Resolve-Path -LiteralPath (Join-Path $taskFolder '../../..')).Path
$taskData = 'C:\Users\ferra\vcc2026-data'
$taskPython = Join-Path $taskData '.venv\Scripts\python.exe'
$taskEvidence = Join-Path $taskFolder ($GenerationFolder + '/' + $Evidence)
$taskReceipt = Join-Path $taskEvidence 'verification.json'
if (-not $WaitForGeneration) {
    if (-not (Test-Path -LiteralPath $taskReceipt)) { throw 'Verified generation receipt required' }
    $taskVerified = Get-Content -Raw -LiteralPath $taskReceipt | ConvertFrom-Json
    if ($taskVerified.status -ne 'GENERATION_VERIFIED') { throw 'Generation verification incomplete' }
}
$taskLaunchReceipt = Join-Path $taskFolder ('launch_t38_' + $Attempt + '.json')
$taskPrivateLogs = Join-Path $taskData ('processed\dati_transfer_2026-10-08_01a11c34\submission_t38\process_' + $Attempt)
if ((Test-Path -LiteralPath $taskLaunchReceipt) -or (Test-Path -LiteralPath $taskPrivateLogs)) { throw 'Attempt already exists; inspect it first' }
New-Item -ItemType Directory -Path $taskPrivateLogs | Out-Null
$taskArguments = @('-u', ('"' + (Join-Path $taskFolder 't38_submission.py') + '"'), 'submit', '--evidence', ('"' + $taskEvidence + '"'), '--attempt', $Attempt)
if ($WaitForGeneration) {
    $taskArguments = @('-u', ('"' + (Join-Path $taskFolder 't38_delivery_pipeline.py') + '"'), '--completion', $Evidence, '--attempt', $Attempt, '--generation-folder', $GenerationFolder)
}
$taskProcess = Start-Process -FilePath $taskPython -ArgumentList $taskArguments -WorkingDirectory $taskRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskPrivateLogs 'stdout.txt') -RedirectStandardError (Join-Path $taskPrivateLogs 'stderr.txt') -PassThru
$taskRecord = [ordered]@{ utc = [DateTime]::UtcNow.ToString('o'); pid = $taskProcess.Id; attempt = $Attempt; evidence = $taskEvidence; logs = $taskPrivateLogs; hidden_persistent_process = $true; one_submission_only = $true; wait_for_generation = [bool]$WaitForGeneration }
$taskJson = $taskRecord | ConvertTo-Json
[IO.File]::WriteAllText($taskLaunchReceipt, $taskJson, [Text.UTF8Encoding]::new($false))
$taskJson
