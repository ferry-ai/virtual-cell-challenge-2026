param(
    [Parameter(Mandatory=$true)][string]$PlanSha256,
    [Parameter(Mandatory=$true)][string]$ReceiptName,
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath('C:\Users\ferra\vcc2026-data')
$remoteRoot = [IO.Path]::GetFullPath('G:\Il mio Drive\vcc2026\data')
$planPath = Join-Path $PSScriptRoot 'plan.json'
if ([IO.Path]::GetFileName($ReceiptName) -ne $ReceiptName) { throw 'Receipt must be a plain filename' }
$receipt = Join-Path $PSScriptRoot $ReceiptName
if ((Test-Path -LiteralPath $receipt) -or (Test-Path -LiteralPath ($receipt + '.jsonl'))) { throw 'Receipt exists' }
if ((Get-FileHash -LiteralPath $planPath -Algorithm SHA256).Hash -ne $PlanSha256) { throw 'Plan hash mismatch' }
$plan = Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
if ([IO.Path]::GetFullPath($plan.root) -ne $root) { throw 'Unexpected root' }
$proofs = @{}
foreach ($proof in $plan.proof_files) {
    if ($proof.name -notin @('colab_a_r1.jsonl','colab_a_r2.jsonl')) { throw 'Unexpected proof file' }
    $proofPath = Join-Path $PSScriptRoot $proof.name
    if ((Get-FileHash -LiteralPath $proofPath -Algorithm SHA256).Hash -ne $proof.sha256) { throw 'Proof changed' }
    foreach ($line in [IO.File]::ReadLines($proofPath)) {
        $r = $line | ConvertFrom-Json
        if ($r.status -eq 'verified' -and $r.sha256 -eq $r.expected_sha256 -and $r.bytes -eq $r.expected_bytes) {
            $proofs[$r.rel] = $r
        }
    }
}
function Get-SafeLocalFile($row) {
    $path = [IO.Path]::GetFullPath((Join-Path $root $row.rel))
    if (-not $path.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase) -or $path -ne [IO.Path]::GetFullPath($row.path)) { throw 'Path escaped root' }
    $item = Get-Item -LiteralPath $path -Force
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Not an ordinary file' }
    $ancestor = $item.Directory
    while ($null -ne $ancestor) {
        if ($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse ancestor' }
        if ($ancestor.FullName -eq $root) { break }
        $ancestor = $ancestor.Parent
    }
    if ($null -eq $ancestor) { throw 'Root not found' }
    if ($item.Length -ne $row.bytes) { throw "Local size changed: $path" }
    return $item
}
# Validate the entire closed plan and remote evidence before any mutation.
$seen = @{}
foreach ($row in $plan.rows) {
    if ($seen.ContainsKey($row.rel)) { throw 'Repeated path' }
    $seen[$row.rel] = $true
    $null = Get-SafeLocalFile $row
    $remotePath = [IO.Path]::GetFullPath((Join-Path $remoteRoot $row.rel))
    if ($remotePath -ne [IO.Path]::GetFullPath($row.remote_path) -or -not $remotePath.StartsWith($remoteRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Remote path escaped root' }
    $remote = Get-Item -LiteralPath $remotePath
    $proof = $proofs[$row.rel]
    if ($null -eq $proof -or $proof.sha256 -ne $row.sha256 -or $proof.bytes -ne $row.bytes -or $remote.Length -ne $row.bytes) { throw "Remote proof mismatch: $($row.rel)" }
}
$before = [IO.DriveInfo]::new('C').AvailableFreeSpace
$started = (Get-Date).ToUniversalTime().ToString('o')
$removed = 0
$removedBytes = [long]0
$failure = $null
try {
    if ($Apply) {
        foreach ($row in $plan.rows) {
            $item = Get-SafeLocalFile $row
            # Hold a read lock denying writers during the fresh hash and deletion.
            $stream = [IO.File]::Open($item.FullName, [IO.FileMode]::Open, [IO.FileAccess]::Read, ([IO.FileShare]::Read -bor [IO.FileShare]::Delete))
            try {
                $hash = [Security.Cryptography.SHA256]::Create()
                try { $actual = [Convert]::ToHexString($hash.ComputeHash($stream)).ToLowerInvariant() } finally { $hash.Dispose() }
                if ($actual -ne $row.sha256) { throw "Fresh local hash mismatch: $($row.rel)" }
                Remove-Item -LiteralPath $item.FullName -ErrorAction Stop
                $removed++
                $removedBytes += [long]$row.bytes
                [ordered]@{rel=$row.rel;bytes=$row.bytes;sha256=$actual;remote_path=$row.remote_path;removed_utc=(Get-Date).ToUniversalTime().ToString('o')} | ConvertTo-Json -Compress | Add-Content -LiteralPath ($receipt + '.jsonl') -Encoding utf8
                if ($removed % 20 -eq 0 -or $row.bytes -gt 1GB) { Write-Output "Removed $removed/$($plan.rows.Count), $([math]::Round($removedBytes/1GB,2)) GiB by path; $($row.rel)" }
            } finally { $stream.Dispose() }
        }
    }
} catch {
    $failure = $_.Exception.Message
    throw
} finally {
    $after = [IO.DriveInfo]::new('C').AvailableFreeSpace
    [ordered]@{started_utc=$started;finished_utc=(Get-Date).ToUniversalTime().ToString('o');apply=[bool]$Apply;plan_sha256=$PlanSha256;validated_paths=$plan.rows.Count;removed_paths=$removed;removed_bytes_by_path=$removedBytes;expected_unique_bytes=$plan.unique_bytes;free_bytes_before=$before;free_bytes_after=$after;free_bytes_delta=($after-$before);error=$failure} | ConvertTo-Json | Set-Content -LiteralPath $receipt -Encoding utf8
}
Get-Content -LiteralPath $receipt
