@echo off
"%USERPROFILE%\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffprobe.exe" -hide_banner -show_entries stream=codec_name,width,height,r_frame_rate,duration -of default=nw=1 "%USERPROFILE%\Downloads\[Doomdos] - 凡人修仙传 - 第195话 - [4K BILIBILI COM WEB-DL].mp4"
