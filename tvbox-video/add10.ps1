$magnets = @(
 "magnet:?xt=urn:btih:597c863b95c4264314f0eab3ced42ca91946411f",
 "magnet:?xt=urn:btih:dbf68e5e89de680d822229a355b57e9f75d77962",
 "magnet:?xt=urn:btih:334f61d1128c2a87285a7241ddd0384429e97af0",
 "magnet:?xt=urn:btih:a8489628fcaf244586c66ad2bd5e3322704aa061",
 "magnet:?xt=urn:btih:83967add46bdbdc08afc5f26d32543b18f52f7d9",
 "magnet:?xt=urn:btih:f9cf6d181c11422c6495d0abef8fde2af3a43c86",
 "magnet:?xt=urn:btih:6294b2ceb93061e2f1a68185e874774624e76786",
 "magnet:?xt=urn:btih:07f138dd7a1667f2018332cb12e6aa415078a3d5",
 "magnet:?xt=urn:btih:356db692320d2a160ff47795d73755df001bde1c",
 "magnet:?xt=urn:btih:f00a6b8547384b0ec4716997bf9ee1585230cea6"
)
$qb = "C:\Program Files\qBittorrent\qbittorrent.exe"
foreach ($m in $magnets) {
  Start-Process $qb -ArgumentList "--skip-dialog", "`"$m`""
  Start-Sleep -Seconds 3
}
