#!/bin/bash
declare -A C
C[185]=40480868938; C[186]=40698383030; C[187]=40920682135; C[188]=41140749663
C[189]=41804826860; C[190]=41805680522; C[191]=41806202889; C[192]=42011328801
C[193]=42426632174; C[194]=42360308036; C[195]=42607054789
for ep in "${!C[@]}"; do
  cid="${C[$ep]}"
  curl -s --compressed --connect-timeout 10 --max-time 40 -A "Mozilla/5.0" \
    -H "Referer: https://www.bilibili.com/" \
    "https://comment.bilibili.com/$cid.xml" -o "/tmp/dm_$ep.xml"
  echo "$ep cid=$cid size=$(stat -c%s /tmp/dm_$ep.xml)"
done
