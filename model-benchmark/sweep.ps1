# Runs a list of tune.py trials in order. Usage: pwsh sweep.ps1 <trials-file>
# Each line of the trials file: <name> <key=value> <key=value> ...
param([string]$TrialsFile)
Set-Location $PSScriptRoot
$log = Join-Path $PSScriptRoot ("runtime_" + [IO.Path]::GetFileNameWithoutExtension($TrialsFile) + ".log")
$p = Start-Process lms -ArgumentList "log","stream","-s","runtime" -RedirectStandardOutput $log -RedirectStandardError "$log.err" -WindowStyle Hidden -PassThru
Start-Sleep 2
foreach ($line in Get-Content $TrialsFile) {
  if (-not $line.Trim() -or $line.StartsWith("#")) { continue }
  $parts = $line.Trim() -split "\s+"
  Add-Content $log "=== TRIAL $($parts[0]) ==="
  python tune.py @parts 2>&1 | Select-Object -Last 1
}
Stop-Process -Id $p.Id -Force -Confirm:$false
lms unload --all | Out-Null
"SWEEP DONE"
