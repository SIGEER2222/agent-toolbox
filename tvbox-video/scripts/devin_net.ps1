$pids = (Get-Process Devin -ErrorAction SilentlyContinue).Id
$conns = Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue | Where-Object { $pids -contains $_.OwningProcess }
$conns | Select-Object LocalAddress,RemoteAddress,RemotePort,OwningProcess | Sort-Object RemoteAddress -Unique | Format-Table -AutoSize
