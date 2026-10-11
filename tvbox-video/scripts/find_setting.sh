#!/bin/bash
for p in "setting/detail?key=player" "settings/detail/player" "setting/player" "setting/get/player" "system/setting/player" "setting/detail" "setting/list"; do
  echo "== $p"
  curl -s --connect-timeout 6 "http://127.0.0.1:9978/api/v1/$p" | head -c 300
  echo
done
