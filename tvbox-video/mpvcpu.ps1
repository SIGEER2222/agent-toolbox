$p1 = (Get-Process mpv -ErrorAction SilentlyContinue).CPU
Start-Sleep -Seconds 8
$p2 = (Get-Process mpv -ErrorAction SilentlyContinue).CPU
Write-Output "cpu1=$p1 cpu2=$p2 delta=$([math]::Round($p2-$p1,1))"
