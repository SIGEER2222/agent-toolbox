$f = Get-ChildItem "$env:USERPROFILE\Downloads" -Filter *.mp4 | Where-Object { $_.Length -gt 2GB } | Select-Object -First 1
if ($f) { Invoke-Item $f.FullName }
