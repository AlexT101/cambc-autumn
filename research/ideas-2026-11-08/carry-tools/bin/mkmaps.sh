#!/bin/bash
# mkmaps.sh A B [extra mapgen args]: fresh-A..fresh-B in chunks of <=100 seeds.
source /home/ubuntu/venv/bin/activate; cd /home/ubuntu/cambc-autumn
L=/home/ubuntu/tmp-offload/carry/logs; A=$1; B=$2; shift 2
F=maps/suites/fresh/fresh-{seed}
for ((s=A; s<=B; s+=100)); do e=$((s+99)); [ $e -gt $B ] && e=$B
  python3 tools/pooled.py 16 -- nice node tools/mapgen/mapgen.mjs suite --seed $s-$e --jobs 16 "$@" --out $F > $L/mapgen-$s.log 2>&1 || exit 1
done
touch $L/mapgen-$A-$B.done
