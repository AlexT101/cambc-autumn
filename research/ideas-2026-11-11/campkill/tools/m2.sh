#!/bin/bash
# Heavy-map read: base, ck-cast and ck-pass on 25 heavy maps x 16 noise seeds, 200k, then extract.
C=~/tmp-offload/campkill
for v in charybdis-cb9f86d ck-cast ck-pass; do $C/mech.sh variants/$v replays/campkill/hv16 hv16 & done
wait; touch $C/logs/m2.done
