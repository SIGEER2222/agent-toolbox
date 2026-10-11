$f = Get-ChildItem "$env:USERPROFILE\Downloads" -Filter "*195*.mp4" | Where-Object { $_.Length -gt 2GB } | Select-Object -First 1
if (-not $f) { Write-Host "no ep195 file >2GB"; exit 1 }
Write-Host "playing: $($f.FullName)  [$([math]::Round($f.Length/1GB,2)) GB]"
Start-Process "C:\Program Files\MPV Player\mpv.exe" -ArgumentList "--osd-level=2", "`"$($f.FullName)`""
