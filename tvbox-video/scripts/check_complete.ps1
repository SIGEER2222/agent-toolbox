$probe = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffprobe.exe"
Get-ChildItem "$env:USERPROFILE\Downloads" -Filter "*Doomdos*.mp4" -ErrorAction SilentlyContinue |
  Sort-Object Name |
  ForEach-Object {
    $ep = if ($_.Name -match '(\d{3})') { $Matches[1] } else { '???' }
    $j = & $probe -v error -show_entries format=duration,size -of json "$($_.FullName)" 2>$null | ConvertFrom-Json
    if ($j.format) {
      $dur = [math]::Round([double]$j.format.duration/60,1)
      Write-Host ("ep{0}: OK  {1} GB  {2} min" -f $ep, [math]::Round($_.Length/1GB,2), $dur)
    } else {
      Write-Host ("ep{0}: BROKEN/INCOMPLETE  {1} GB" -f $ep, [math]::Round($_.Length/1GB,2))
    }
  }
