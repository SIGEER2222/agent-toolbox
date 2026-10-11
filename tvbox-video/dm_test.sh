#!/bin/bash
for cid in 42361818541 42607054789; do
  curl -s --compressed --connect-timeout 10 --max-time 30 -A "Mozilla/5.0" \
    -H "Referer: https://www.bilibili.com/" \
    "https://comment.bilibili.com/$cid.xml" -o "/tmp/dm_$cid.xml"
  cnt=$(grep -c "<d p=" "/tmp/dm_$cid.xml")
  sz=$(stat -c%s "/tmp/dm_$cid.xml")
  echo "$cid: ${cnt} danmaku, size=${sz}"
  head -c 150 "/tmp/dm_$cid.xml"; echo; echo "---"
done
