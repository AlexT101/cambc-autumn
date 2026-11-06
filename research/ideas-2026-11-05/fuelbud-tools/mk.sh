#!/bin/bash
# mk.sh NAME knob=value [...]: bots/variants/oc-fb-NAME = oc-fb-dev with params::fuelbud knobs set.
cd /home/ubuntu/cambc-autumn
n=$1; shift
./copybot -f variants/oc-fb-dev variants/oc-fb-$n > /dev/null || exit 1
P=bots/variants/oc-fb-$n/src/params.h
for kv in "$@"; do
  k=${kv%%=*} v=${kv#*=}
  grep -q "inline constexpr [a-z]* $k = " $P || { echo "no knob $k"; exit 1; }
  sed -i "s/\(inline constexpr [a-z]* $k = \)[^;]*;/\1$v;/" $P
done
grep -A30 "namespace fuelbud" $P | grep "inline constexpr" | sed "s/^/  oc-fb-$n: /"
