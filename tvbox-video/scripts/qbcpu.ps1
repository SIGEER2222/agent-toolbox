$p = Get-Process qbittorrent -ErrorAction SilentlyContinue
if ($p) {
  $p | Select-Object Id, CPU, @{N='MemMB';E={[math]::Round($_.WorkingSet64/1MB)}}, StartTime | Format-Table -AutoSize
  $c1 = $p.CPU; Start-Sleep -Seconds 5
  $p2 = Get-Process qbittorrent -ErrorAction SilentlyContinue
  Write-Host ("CPU delta in 5s: {0:N2}s ({1:N0}%)" -f ($p2.CPU-$c1), ($p2.CPU-$c1)/5*100)
} else { Write-Host "qbittorrent not running" }
