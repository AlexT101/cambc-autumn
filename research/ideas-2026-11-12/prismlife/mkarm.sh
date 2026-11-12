#!/bin/bash
# mkarm.sh NAME KNOB=VALUE...: a copy of variants/pl-base as variants/NAME with params::pl knobs set.
NAME=$1; shift
cd /home/ubuntu/cambc-autumn
./copybot -f variants/${BASE:-pl-base} variants/$NAME > /dev/null
for kv in "$@"; do
  k=${kv%%=*}; v=${kv#*=}
  grep -q "$k = " bots/variants/$NAME/src/params.h || { echo "no knob $k"; exit 1; }
  sed -i -E "s|($k = )[^;,]+([;,])|\1$v\2|" bots/variants/$NAME/src/params.h
done
grep -n -A12 "^namespace pl" bots/variants/$NAME/src/params.h | grep "constexpr" | sed 's|//.*||'
