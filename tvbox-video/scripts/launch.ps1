$exe = "$env:USERPROFILE\AppData\Local\Programs\zyfun\zyfun.exe"
Start-Process "explorer.exe" -ArgumentList "`"$exe`""
Start-Sleep -Seconds 12
$p = Get-Process zyfun -ErrorAction SilentlyContinue
if ($p) {
  $p | Select-Object Id, ProcessName, MainWindowTitle, Responding | Format-Table -AutoSize
} else {
  Write-Output "zyfun NOT running"
}
$port = Test-NetConnection -ComputerName 127.0.0.1 -Port 9978 -WarningAction SilentlyContinue -InformationLevel Quiet
Write-Output "port9978=$port"
