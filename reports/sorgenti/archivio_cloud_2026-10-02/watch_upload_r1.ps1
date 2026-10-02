# Watcher of upload run r1: when the runner process has exited and the runner log shows at least
# $FinishedAtLeast lines "runner finished" (each clean stop for a parameter change adds one: 23:14 and 00:11 on
# 2-3 October), build manifest A from the copy receipts and the local hashes, copy it with its sidecar into the
# Drive setup folder of job 131, then write the marker UPLOAD_COMPLETE_r1.json last. Never overwrites: refuses if
# the marker or the manifest already exists.
param(
    [Parameter(Mandatory = $true)][int]$RunnerPid,
    [Parameter(Mandatory = $true)][int]$FinishedAtLeast,
    [string]$Py = 'C:\Users\ferra\vcc2026-data\.venv\Scripts\python.exe',
    [string]$Run = 'C:\Users\ferra\vcc2026-data\processed\archivio_cloud_2026-10-02\r1',
    [string]$Setup = 'G:\Il mio Drive\vcc2026\runs\archivio_verify_2026-10-02_r1'
)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$log = "$Run\watcher.log"
function Say($m) { "$(Get-Date -Format o) $m" | Add-Content $log }
Say "watcher started for runner pid $RunnerPid"
while ($true) {
    $alive = Get-Process -Id $RunnerPid -ErrorAction SilentlyContinue
    $finished = @(Select-String -Path "$Run\runner.log" -Pattern 'runner finished' -SimpleMatch).Count
    if (-not $alive -and $finished -ge $FinishedAtLeast) { break }
    Start-Sleep -Seconds 300
}
Say "runner ended; waiting for the local hashes"
while (-not (Test-Path "$Run\local_hashes.tsv")) { Start-Sleep -Seconds 300 }
$manifest = "$Run\manifests\a_specchio_r1.json"
$sidecar = "$Run\manifests\a_specchio_r1.sha256"
if (Test-Path $manifest) { Say "refusing: $manifest exists"; exit 1 }
& $Py "$here\archivio.py" manifest --plan "$Run\plan_r1.json" --receipts "$Run\copy_receipts.jsonl" `
    --hashes "$Run\local_hashes.tsv" --out $manifest *>> "$Run\watcher_manifest.log"
if (-not (Test-Path $sidecar)) { Say "manifest not written, see watcher_manifest.log"; exit 1 }
$sha = (Get-FileHash -Algorithm SHA256 $manifest).Hash.ToLower()
if ((Test-Path "$Setup\UPLOAD_COMPLETE_r1.json") -or (Test-Path "$Setup\manifests_a\a_specchio_r1.json")) { Say "refusing: marker or manifest exists on Drive"; exit 1 }
Copy-Item $manifest "$Setup\manifests_a\a_specchio_r1.json"
Copy-Item $sidecar "$Setup\manifests_a\a_specchio_r1.sha256"
$counts = Get-Content "$Run\copy_receipts.jsonl" | ForEach-Object { ($_ | ConvertFrom-Json).status } | Group-Object | ForEach-Object { @{ $_.Name = $_.Count } }
$marker = [ordered]@{
    manifest = 'a_specchio_r1.json'; manifest_sha256 = $sha; sidecar = 'a_specchio_r1.sha256'
    written_local = (Get-Date -Format o); receipts_status_counts = $counts
    note = 'written by watch_upload_r1.ps1 after the runner ended; a file on the laptop mount is not proof of upload: job 131 reads it from Colab'
}
[System.IO.File]::WriteAllText("$Setup\UPLOAD_COMPLETE_r1.json", ($marker | ConvertTo-Json -Depth 4), [System.Text.UTF8Encoding]::new($false))
Say "marker written, manifest sha256 $sha"
