#!/bin/bash
# mk.sh NAME knob=value [knob=value ...]: bots/variants/oc-ap-NAME = oc-astport-dev with params::astport knobs set.
cd /home/ubuntu/cambc-autumn
n=$1; shift
./copybot -f variants/oc-astport-dev variants/oc-ap-$n > /dev/null || exit 1
P=bots/variants/oc-ap-$n/src/params.h
for kv in "$@"; do
  k=${kv%%=*} v=${kv#*=}
  grep -q "inline constexpr [a-z]* $k = " $P || { echo "no knob $k"; exit 1; }
  sed -i "s/\(inline constexpr [a-z]* $k = \)[^;]*;/\1$v;/" $P
done
grep -A40 "namespace astport" $P | grep "= true" | sed "s/^/  oc-ap-$n: /"
