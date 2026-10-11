$f = Get-ChildItem "$env:USERPROFILE\Downloads" -Filter *.mp4 | Where-Object { $_.Length -gt 2GB } | Select-Object -First 1
Start-Process "C:\Program Files (x86)\Windows Media Player\wmplayer.exe" -ArgumentList "`"$($f.FullName)`""
