#!/bin/bash
# dg_variant.sh NAME 'sed script' : bots/variants/dg-NAME from dg-dev with params.h edited by the sed script, its lab
# copy lab-dg-NAME, both built.
set -e
cd /home/ubuntu/cambc-autumn
n=$1; s=$2
rm -rf bots/variants/dg-$n bots/variants/lab-dg-$n
./copybot variants/dg-dev variants/dg-$n > /dev/null
[ -n "$s" ] && sed -i "$s" bots/variants/dg-$n/src/params.h
grep -n "^inline constexpr.*\(shadow\|shadow_sites\|force_mode\|trace\|s2_\) =" bots/variants/dg-$n/src/params.h | sed 's/^/  /'
py tools/combatlab/labify.py variants/dg-$n variants/lab-dg-$n > /dev/null
cambc build bots/variants/dg-$n 2>&1 | grep -E "error|built" | sed 's/^/  /'
cambc build bots/variants/lab-dg-$n 2>&1 | grep -E "error|built" | sed 's/^/  /'
