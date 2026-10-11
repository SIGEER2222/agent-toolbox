#!/bin/bash
FP="/mnt/c/Users/22448/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin/ffprobe.exe"
declare -A U
U[ukm3u8]="https://ukzy.ukubf3.com/20261010/KEnLNtrO/index.m3u8"
U[lzm3u8]="https://v.lzfile26.com/20250907/29035_af9df9a1/index.m3u8"
U[dyttm3u8]="https://vip.dytt-hot.com/20250705/95867_8d419525/index.m3u8"
U[bfzym3u8]="https://fengbao13.com/video/fanrenxiuxianchuan/4e4fd90d6c6d/index.m3u8"
for k in "${!U[@]}"; do
  url="${U[$k]}"
  for hop in 1 2 3; do
    pl=$(curl -skL --connect-timeout 8 --max-time 15 -A "Mozilla/5.0" "$url")
    # prefer highest-RESOLUTION variant if master playlist
    var=$(echo "$pl" | grep -i "RESOLUTION" | sort -t= -k2 -rn | head -1)
    if [ -n "$var" ]; then echo "$k master-variant: $var"; fi
    seg=$(echo "$pl" | grep -v "^#" | grep -m1 .)
    case "$seg" in
      http*) ;;
      /*) seg="$(echo "$url" | sed -E 's|(https?://[^/]+).*|\1|')$seg";;
      *) seg="$(dirname "$url")/$seg";;
    esac
    case "$seg" in *.m3u8*) url="$seg";; *) break;; esac
  done
  curl -skL --connect-timeout 8 --max-time 25 -A "Mozilla/5.0" -r 0-800000 -o "/tmp/seg_$k.ts" "$seg" 2>/dev/null
  res=$("$FP" -hide_banner -show_entries stream=width,height -of csv=p=0 "/tmp/seg_$k.ts" 2>/dev/null | grep -E "^[0-9]+," | head -1)
  echo "$k res=[$res] seg=$seg"
done
