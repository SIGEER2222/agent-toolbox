$pid_ = (Get-Process qbittorrent -ErrorAction SilentlyContinue).Id
if (-not $pid_) { Write-Host "qbittorrent not running"; exit }
$c = Get-NetTCPConnection -OwningProcess $pid_ -ErrorAction SilentlyContinue
$udp = (netstat -ano | Select-String "UDP").Count
Write-Host "TCP connections: $($c.Count)"
$c | Group-Object State | Select-Object Name, Count | Format-Table -AutoSize
$c | Select-Object -First 12 RemoteAddress, RemotePort, State | Format-Table -AutoSize
