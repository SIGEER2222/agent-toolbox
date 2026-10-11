Get-CimInstance Win32_Process -Filter "Name='quark.exe'" |
  Select-Object ProcessId, CommandLine |
  Format-List | Out-String -Width 500
