#!/bin/bash
# mkvar.sh NAME knob=value ... : bots/variants/oc-gemfight-NAME from oc-gemfight-dev with params::gemfight knobs set.
set -e
cd /home/ubuntu/cambc-autumn
name=$1; shift
./copybot -f variants/${GF_DEV:-oc-gemfight-dev} variants/${GF_PREFIX:-oc-gemfight}-$name > /dev/null
p=bots/variants/${GF_PREFIX:-oc-gemfight}-$name/src/params.h
for kv in "$@"; do
  k=${kv%%=*}; v=${kv#*=}
  grep -q "inline constexpr [a-z]* $k = " $p || { echo "no knob $k"; exit 1; }
  sed -i "/^namespace gemfight {/,/^} \/\/ namespace gemfight/ s/^\(inline constexpr [a-z]* $k = \).*;/\1$v;/" $p
done
sed -n '/^namespace gemfight {/,/^} \/\/ namespace gemfight/p' $p | grep "inline constexpr" | tr '\n' ' '; echo
