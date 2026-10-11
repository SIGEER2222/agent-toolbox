$paths = @(
  'C:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe',
  'C:\Program Files (x86)\DAUM\PotPlayer\PotPlayerMini.exe',
  'C:\Program Files (x86)\DAUM\PotPlayer\PotPlayerMini64.exe',
  'C:\Program Files\VideoLAN\VLC\vlc.exe',
  'C:\Program Files (x86)\VideoLAN\VLC\vlc.exe',
  'C:\Program Files\mpv\mpv.exe',
  'D:\Program Files\mpv\mpv.exe',
  "$env:LOCALAPPDATA\Programs\mpv\mpv.exe",
  "$env:ProgramFiles\mpv.net\mpvnet.exe",
  'C:\Program Files\MPC-HC\mpc-hc64.exe',
  'C:\Program Files (x86)\MPC-HC\mpc-hc.exe',
  'C:\Program Files\Kodi\kodi.exe'
)
foreach ($p in $paths) { if (Test-Path $p) { Write-Output "FOUND: $p" } }
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
  'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
  'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue |
  Where-Object { $_.DisplayName -match 'PotPlayer|VLC|mpv|MPC|Kodi|完美解码|Pot|迅雷影音|QQ影音|暴风影音' } |
  Select-Object DisplayName, InstallLocation | Format-Table -AutoSize
