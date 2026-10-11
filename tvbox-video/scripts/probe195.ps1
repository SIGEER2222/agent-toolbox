$f = Get-ChildItem "$env:USERPROFILE\Downloads" -Filter *.mp4 | Where-Object { $_.Length -gt 2GB } | Select-Object -First 1
if ($f) {
  Write-Output "FILE: $($f.FullName) $($f.Length)"
  & "$env:USERPROFILE\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffprobe.exe" -hide_banner -show_entries stream=codec_name,width,height,r_frame_rate,duration -of default=nw=1 "$($f.FullName)" 2>&1 | Select-String "codec|width|height|duration|Stream|frame"
} else { Write-Output "NOT FOUND" }
