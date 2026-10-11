$f = Get-ChildItem "$env:USERPROFILE\Downloads" -Filter *.mp4 | Where-Object { $_.Name -like "*195*" } | Select-Object -First 1
$a = [IO.Path]::ChangeExtension($f.FullName, ".ass")
Write-Output "video: $($f.Name)"
Write-Output "ass: $a"
& "%USERPROFILE%\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe" -hide_banner -y -ss 320 -copyts -i "$($f.FullName)" -vf "ass='$($a -replace '\\','/' -replace ':','\:')',scale=1280:-1" -frames:v 1 -update 1 "C:\Code\TVbox\dm_proof.png" 2>&1 | Select-String "error|Error|frame=" | Select-Object -Last 3
