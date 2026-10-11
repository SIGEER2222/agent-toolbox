param([string]$action = "status")
$exe = "$env:USERPROFILE\AppData\Local\Programs\zyfun\zyfun.exe"
switch ($action) {
  "start" {
    Start-Process $exe
    Write-Output "launched"
  }
  "status" {
    $p = Get-Process zyfun -ErrorAction SilentlyContinue
    if ($p) { $p | Select-Object Id,ProcessName,StartTime | Format-Table -AutoSize } else { Write-Output "zyfun NOT running" }
    $c = Test-NetConnection -ComputerName 127.0.0.1 -Port 9978 -WarningAction SilentlyContinue -InformationLevel Quiet
    Write-Output "port9978=$c"
  }
  "kill" {
    Get-Process zyfun -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Output "killed"
  }
}
