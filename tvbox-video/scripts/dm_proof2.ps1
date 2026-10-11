$ff = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
$v = Get-ChildItem "$env:USERPROFILE\Downloads" -Filter "*195*.mp4" | Select-Object -First 1
$a = [System.IO.Path]::ChangeExtension($v.FullName, ".ass")
$aesc = ($a -replace '\\', '/' -replace ':', '\:')
& $ff -y -v error -ss 00:03:10 -copyts -i "$($v.FullName)" -vf "ass='$aesc'" -frames:v 1 -update 1 "C:\Code\TVbox\dm_top.png"
Write-Host "done"
