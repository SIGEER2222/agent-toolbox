$f = Get-ChildItem "$env:USERPROFILE\Downloads" -Filter "*190*.mp4" | Select-Object -First 1
if (-not $f) { Write-Host "no ep190 file"; exit 1 }
Write-Host "playing: $($f.FullName)  [$([math]::Round($f.Length/1GB,2)) GB]"
Start-Process "C:\Program Files\MPV Player\mpv.exe" -ArgumentList "--osd-level=2", "--video-sync=display-resample", "`"$($f.FullName)`""
