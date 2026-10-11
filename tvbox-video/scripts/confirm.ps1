$wshell = New-Object -ComObject wscript.shell
$ok = $wshell.AppActivate("Doomdos")
if (-not $ok) { $ok = $wshell.AppActivate("Torrent") }
Start-Sleep -Milliseconds 600
$wshell.SendKeys("{ENTER}")
