#!/bin/bash
for d in WH3-modding model-studio wyccc-warhammer-mod-manager tool-hub mom.report.client MyMod decidebench JmAura.Net; do
  r=$(git -C "/mnt/e/Code/$d" remote get-url origin 2>/dev/null)
  [ -n "$r" ] && echo "$d -> $r"
done
echo "--- ssh test github.com:22 ---"
timeout 10 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=8 -T git@github.com 2>&1 | head -2
echo "--- ssh test ssh.github.com:443 ---"
timeout 10 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=8 -p 443 -T git@ssh.github.com 2>&1 | head -2
