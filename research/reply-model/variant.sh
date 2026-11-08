#!/bin/bash
# variant.sh NAME DANGER_SCALE PRESS_WEIGHT [LEAN MIN_FUEL]: bots/variants/NAME from oc-reply with those params, and its
# lab copy lab-NAME.
set -e
cd /home/ubuntu/cambc-autumn
n=$1; ds=$2; pw=$3; lean=${4:-true}; mf=${5:-0}
rm -rf bots/variants/$n bots/variants/lab-$n
./copybot variants/oc-reply variants/$n > /dev/null
sed -i "s/inline constexpr float danger_scale = [0-9.]*f;/inline constexpr float danger_scale = ${ds}f;/; s/inline constexpr float press_weight = [0-9.]*f;/inline constexpr float press_weight = ${pw}f;/; s/inline constexpr bool lean = [a-z]*;/inline constexpr bool lean = ${lean};/; s/inline constexpr std::uint64_t min_fuel = [0-9]*;/inline constexpr std::uint64_t min_fuel = ${mf};/" bots/variants/$n/src/params.h
grep -n "danger_scale =\|press_weight =\|lean =\|min_fuel =" bots/variants/$n/src/params.h
python3 tools/combatlab/labify.py variants/$n variants/lab-$n > /dev/null
cambc build bots/variants/lab-$n 2>&1 | grep -E "error|built"
