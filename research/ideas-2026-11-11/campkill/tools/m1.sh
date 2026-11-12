#!/bin/bash
# Mechanism runs of the three arms on treasure-box (tb) and the fresh suite (f1), 200k.
C=~/tmp-offload/campkill
for v in ck-pass ck-cast ck-both; do
  $C/mech.sh variants/$v replays/campkill/tb tb &
done
wait
for v in ck-pass ck-cast ck-both; do
  $C/mech.sh variants/$v replays/campkill/f1 f1 &
done
wait
touch $C/logs/m1.done
