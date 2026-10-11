$dirs = @("$env:LOCALAPPDATA\Programs", "C:\Program Files", "C:\Program Files (x86)", "$env:APPDATA", "$env:LOCALAPPDATA", "$env:APPDATA\..\LocalLow")
foreach ($d in $dirs) {
  Get-ChildItem $d -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match 'quark' } |
    ForEach-Object { Write-Host "DIR: $($_.FullName)" }
}
Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match 'quark' } | ForEach-Object { Write-Host "PROC: $($_.ProcessName) $($_.Id)" }
winget list --name quark 2>$null | Select-Object -First 5
