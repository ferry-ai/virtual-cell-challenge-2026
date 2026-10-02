# Metadata-only listing of the project folder on the Drive mount (no file content is read).
# Writes path<TAB>bytes<TAB>lastwrite_utc for every file, plus a summary per top-level subfolder.
param(
    [string]$Root = 'G:\Il mio Drive\vcc2026',
    [string]$Out = "$PSScriptRoot\inv\drive_listing.tsv"
)
$ErrorActionPreference = 'Continue'
New-Item -ItemType Directory -Force (Split-Path $Out) | Out-Null
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$w = New-Object System.IO.StreamWriter($Out, $false, [System.Text.UTF8Encoding]::new($false))
$n = 0
$stack = New-Object System.Collections.Stack
$stack.Push((New-Object System.IO.DirectoryInfo($Root)))
while ($stack.Count -gt 0) {
    $d = $stack.Pop()
    try {
        foreach ($e in $d.EnumerateFileSystemInfos()) {
            if ($e -is [System.IO.DirectoryInfo]) { $stack.Push($e) }
            else {
                $line = "{0}`t{1}`t{2}" -f $e.FullName.Substring($Root.Length + 1), $e.Length, $e.LastWriteTimeUtc.ToString('s')
                $w.WriteLine($line)
                $n++
            }
        }
    } catch { $w.WriteLine("ERROR`t$($d.FullName)`t$($_.Exception.Message)") }
}
$w.Close()
"files=$n seconds=$([math]::Round($sw.Elapsed.TotalSeconds,1)) out=$Out"
