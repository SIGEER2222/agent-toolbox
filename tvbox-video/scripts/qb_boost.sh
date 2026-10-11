#!/bin/bash
B="http://127.0.0.1:8080/api/v2"
curl -s -c /tmp/qbc "$B/auth/login" -d "username=admin&password=admintv" >/dev/null
curl -s -b /tmp/qbc "$B/app/setPreferences" --data-urlencode 'json={
  "connection_speed": 200,
  "max_connec": 2000,
  "max_connec_per_torrent": 500,
  "max_uploads": -1,
  "max_uploads_per_torrent": -1,
  "enable_multi_connections_from_same_ip": true,
  "announce_to_all_trackers": true,
  "announce_to_all_tiers": true
}'
echo "prefs set"
curl -s -b /tmp/qbc "$B/torrents/reannounce" -d "hashes="
echo "reannounced"
