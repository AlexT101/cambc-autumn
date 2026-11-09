#!/bin/bash
# mkseg.sh SRC DST: an instrumented (gap census + probes, quiet) copy of variant SRC as variant DST.
set -e
cd /home/ubuntu/cambc-autumn
./copybot -f variants/$1 variants/$2 > /dev/null
D=bots/variants/$2/src; T=/home/ubuntu/tmp-offload/nooof/tools
cp $T/gap.h $D/
python3 $T/${GAPINST:-gapinst3.py} $D
[ -n "$NOPROBE" ] || python3 $T/probes.py $D > /dev/null
sed -i 's/constexpr bool debug_search = true;/constexpr bool debug_search = false;/' $D/combat/plan.cc
for pat in '"RF%s ' '"D %d %u %c' '"FIXC-BUSHT' '"RFKEEP' '"RFDROP' '"CREW ' '"RFCHOOSE'; do
  grep -rl --include=*.cc -e "$pat" $D | while read f; do
    python3 - "$f" "$pat" <<'PY'
import sys,re
f,pat=sys.argv[1],sys.argv[2]; L=open(f).read().split('\n')
for i,l in enumerate(L):
    if pat in l:
        for j in range(i, max(i-3,-1), -1):
            if 'debug_block({' in L[j] and 'if (false)' not in L[j]:
                L[j]=L[j].replace('debug_block({','if (false) debug_block({',1); break
open(f,'w').write('\n'.join(L))
PY
  done
done
