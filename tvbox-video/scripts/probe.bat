@echo off
"%USERPROFILE%\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffprobe.exe" -hide_banner -show_entries stream=codec_name,width,height,bit_rate -of default=nw=1 "https://vv.jisuzyv.com/play/b680rlVe/index.m3u8"
