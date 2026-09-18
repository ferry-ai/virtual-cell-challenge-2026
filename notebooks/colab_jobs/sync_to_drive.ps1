# Mirror the code a Colab job needs into the Drive for desktop folder.
# Usage: powershell -File notebooks\colab_jobs\sync_to_drive.ps1 [-DriveRoot "G:\Il mio Drive\vcc2026"]
param([string]$DriveRoot = "G:\Il mio Drive\vcc2026")
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$dest = Join-Path $DriveRoot "code"
foreach ($d in @("src", "scripts", "configs", "notebooks")) {
    robocopy (Join-Path $repo $d) (Join-Path $dest $d) /MIR /XD __pycache__ .pytest_cache /XF *.pyc /NP /NJH /NJS /NDL /NFL /R:2 /W:2 | Out-Null
}
Copy-Item (Join-Path $repo "requirements.txt") $dest -Force
$head = (git -C $repo rev-parse --short HEAD) 2>$null
$dirty = (git -C $repo status --porcelain | Measure-Object -Line).Lines
$stamp = "{0} head={1} dirty_files={2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"), $head, $dirty
Set-Content -Path (Join-Path $dest "SYNC_STAMP.txt") -Value $stamp -Encoding utf8
Write-Output "synced -> $dest : $stamp"
