#!/bin/bash
for d in AweSun Code Download "Program Files" "Program Files (x86)" Soft Temp Tools Users VS; do
  du -sh "/mnt/e/$d" 2>/dev/null
done
echo "--- recycle bin ---"
du -sh '/mnt/e/$RECYCLE.BIN' 2>/dev/null
