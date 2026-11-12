#!/bin/bash
# mkarm.sh NAME KNOB=VALUE...: a copy of variants/ff-base (BASE=) as variants/NAME with params::ff knobs set.
NAME=$1; shift
cd /home/ubuntu/cambc-autumn
./copybot -f variants/${BASE:-ff-base} variants/$NAME > /dev/null
for kv in "$@"; do
  k=${kv%%=*}; v=${kv#*=}
  grep -q "inline constexpr [a-z:_0-9 ]* $k = " bots/variants/$NAME/src/params.h || { echo "no knob $k"; exit 1; }
  sed -i -E "s|(inline constexpr [a-z:_0-9 ]* $k = )[^;,]+([;,])|\1$v\2|" bots/variants/$NAME/src/params.h
done
grep -n -A8 "^namespace ff" bots/variants/$NAME/src/params.h | grep "constexpr" | tr '\n' ' '; echo
