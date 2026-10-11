$f = Get-ChildItem "$env:USERPROFILE\Downloads" -Filter *.mp4 | Where-Object { $_.Length -gt 2GB } | Select-Object -First 1
Start-Process "C:\Program Files\MPV Player\mpv.exe" -ArgumentList "--osd-level=2", "--video-sync=display-resample", "`"$($f.FullName)`""
