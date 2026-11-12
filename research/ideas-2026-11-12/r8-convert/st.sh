#!/bin/bash
# st.sh [pattern]: last batch line and result of each gate log
cd ~/tmp-offload/r8-convert/logs
for f in ${1:-rc-}*.log; do
  [ -f "$f" ] || continue
  b=$(grep -E "^batch" "$f" | tail -1 | sed -E 's/LLR.*\| ladder/| ladder/')
  r=$(grep -E "Against the bodies" "$f" | sed -E 's/.*Against the bodies: //')
  echo "${f%.log}: $b ${r:+|| $r}"
done
