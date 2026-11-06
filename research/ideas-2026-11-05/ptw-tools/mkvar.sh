#!/bin/bash
# mkvar.sh NAME windows seats ledger [after_nearest] (PATCH=script.py run on the copy's src before building) : copy oc-proteus-dev to bots/variants/NAME with knobs set, and build it
set -e
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
n=$1
./copybot -f variants/oc-proteus-dev variants/$n > /dev/null
rm -f bots/variants/$n/READY
p=bots/variants/$n/src/params.h
sed -i "s/^inline constexpr bool windows = .*;/inline constexpr bool windows = $2;/; s/^inline constexpr bool seats = .*;/inline constexpr bool seats = $3;/; s/^inline constexpr bool ledger = .*;/inline constexpr bool ledger = $4;/; s/^inline constexpr bool after_nearest = .*;/inline constexpr bool after_nearest = ${5:-false};/" $p
grep "^inline constexpr bool" $p | tail -n 4 | tr '\n' ' '; echo
[ -n "$PATCH" ] && (cd bots/variants/$n/src && python3 $PATCH)
(cd bots/variants/$n && cambc build . > build.log 2>&1) || { tail -30 bots/variants/$n/build.log; exit 1; }
rm -f bots/variants/$n/build.log
echo built $n
