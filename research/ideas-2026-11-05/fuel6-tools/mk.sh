#!/bin/bash
# mk.sh NAME knob=value [knob=value ...]: bots/variants/oc-f6-NAME = oc-fuel6-dev with params::fuel6 knobs set.
cd /home/ubuntu/cambc-autumn
n=$1; shift
./copybot -f variants/oc-fuel6-dev variants/oc-f6-$n > /dev/null || exit 1
P=bots/variants/oc-f6-$n/src/params.h
for kv in "$@"; do
  k=${kv%%=*} v=${kv#*=}
  grep -q "inline constexpr [a-z]* $k = " $P || { echo "no knob $k"; exit 1; }
  sed -i "s/\(inline constexpr [a-z]* $k = \)[^;]*;/\1$v;/" $P
done
grep -A30 "namespace fuel6" $P | grep "inline constexpr" | sed "s/^/  oc-f6-$n: /"
