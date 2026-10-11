Get-ChildItem "$env:USERPROFILE\Downloads" -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match 'Doomdos|\.!qB$|\.parts$|\.mp4$' -and $_.Length -gt 200MB } |
  Select-Object Name, @{N='GB';E={[math]::Round($_.Length/1GB,2)}}, LastWriteTime |
  Sort-Object Name | Format-Table -AutoSize | Out-String -Width 200
