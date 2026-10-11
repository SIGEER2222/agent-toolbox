#!/bin/bash
FP="${WINHOME:-$(cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r' | sed 's|^\(.\):|/mnt/\L\1|;s|\\|/|g')}/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin/ffprobe.exe"
declare -A U
U[jsm3u8]="https://vv.jisuzyv.com/play/b680rlVe/index.m3u8"
U[dbm3u8]="https://b3.bdzybf22.com/videos/202610/10/6ac9b10413f8cfc0dd5a/index.m3u8"
U[bfzym3u8]="https://fengbao13.com/video/fanrenxiuxianchuan/4e4fd90d6c6d/playlist.m3u8"
U[ukm3u8]="https://ukzy.ukubf3.com/20261010/KEnLNtrO/index.m3u8"
U[lzm3u8]="https://v.lzfile26.com/20250907/29035_af9df9a1/index.m3u8"
U[dyttm3u8]="https://vip.dytt-hot.com/20250705/95867_8d419525/index.m3u8"
U[ffm3u8]="https://vip.ffzy-plays.com/20240810/31235_d70f195e/index.m3u8"
for k in "${!U[@]}"; do
  url="${U[$k]}"
  pl=$(curl -skL --connect-timeout 8 --max-time 15 -A "Mozilla/5.0" "$url")
  seg=$(echo "$pl" | grep -v "^#" | grep -m1 .)
  case "$seg" in http*) ;; *) seg="$(dirname "$url")/$seg";; esac
  curl -skL --connect-timeout 8 --max-time 20 -A "Mozilla/5.0" -r 0-800000 -o "/tmp/seg_$k.ts" "$seg"
  res=$("$FP" -hide_banner -show_entries stream=width,height -of csv=p=0 "/tmp/seg_$k.ts" 2>/dev/null | grep -E "^[0-9]+," | head -1)
  echo "$k res=[$res] segsize=$(stat -c%s /tmp/seg_$k.ts 2>/dev/null) url=$seg"
done
