$dl = "$env:USERPROFILE\Downloads"
$removed = @()
Get-ChildItem $dl -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match 'Doomdos' -and $_.Name -match '18[5-9]' } |
  ForEach-Object { $removed += $_.Name; Remove-Item $_.FullName -Force }
Write-Host "removed count: $($removed.Count)"
$removed | ForEach-Object { Write-Host " - $_" }
Write-Host "--- remaining Doomdos files:"
Get-ChildItem $dl -Filter "*Doomdos*" -File | Sort-Object Name | Select-Object Name,@{N='GB';E={[math]::Round($_.Length/1GB,2)}} | Format-Table -AutoSize | Out-String -Width 200
