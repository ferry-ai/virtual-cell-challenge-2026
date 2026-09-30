param(
    [string]$Source = 'G:\Il mio Drive\vcc2026\runs\lead_candidate_t28_2026-09-29_r2',
    [Parameter(Mandatory=$true)][string]$Out,
    [string]$ResumeEntry,
    [switch]$Execute
)
$ErrorActionPreference = 'Stop'
$python = 'C:\Users\ferra\vcc2026-data\.venv\Scripts\python.exe'
$runner = Join-Path $PSScriptRoot 'direct_t28_submission.py'
$sourcePath = [IO.Path]::GetFullPath($Source).TrimEnd('\','/')
$outputPath = [IO.Path]::GetFullPath($Out).TrimEnd('\','/')
foreach ($path in @($runner,$sourcePath,$outputPath)) {
    if ($path.Contains('"') -or $path.Contains("`n") -or $path.Contains("`r")) { throw 'Unsupported quoted/newline path' }
}
if ($ResumeEntry -and $ResumeEntry -notmatch '^[A-Za-z0-9_-]+$') { throw 'Invalid resume entry ID' }
if (Test-Path -LiteralPath $outputPath) { throw 'Choose a new attempt output directory' }
$arguments = @('-u',('"'+$runner+'"'),'--source',('"'+$sourcePath+'"'),'--out',('"'+$outputPath+'"'),'--submit')
if ($ResumeEntry) { $arguments += @('--resume-entry',$ResumeEntry) }
$review = [ordered]@{ source=$sourcePath; output=$outputPath; python=$python; runner=$runner;
    runner_sha256=(Get-FileHash -LiteralPath $runner -Algorithm SHA256).Hash.ToLowerInvariant();
    action='Full SHA validation in place, then official vcc submit'; hidden=$true; executed=$false }
if (-not $Execute) { $review | ConvertTo-Json; return }
$parent = [IO.Path]::GetDirectoryName($outputPath)
if (-not (Test-Path -LiteralPath $parent -PathType Container)) { throw 'Attempt parent must already exist' }
$stdout = $outputPath + '.worker_stdout.log'
$stderr = $outputPath + '.worker_stderr.log'
$started = $outputPath + '.worker_started.json'
foreach ($path in @($stdout,$stderr,$started)) {
    if (Test-Path -LiteralPath $path) { throw 'Worker evidence already exists; choose a new attempt' }
}
$process = Start-Process -FilePath $python -ArgumentList $arguments -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr
$review.executed = $true
$review['pid'] = $process.Id
$review['started_utc'] = [DateTime]::UtcNow.ToString('o')
$review | ConvertTo-Json | Set-Content -LiteralPath $started -Encoding UTF8
$review | ConvertTo-Json
