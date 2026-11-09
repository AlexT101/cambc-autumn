#!/bin/bash
# newbodies.sh TAG : bots/variants/spar-TAG-F/-M -> spar-TAG-Fl (Fish's locks) and spar-TAG-Mt3 (Mite's tribute habit,
# no locks). Idempotent. TAG: o25, oc29, dvnK.
cd /home/ubuntu/cambc-autumn; T=research/ideas-2026-11-09/oppfidelity-tools; t=$1
[ -d bots/variants/spar-$t-Fl ] || { ./copybot -f variants/spar-$t-F variants/spar-$t-Fl >/dev/null && python3 $T/patch_locks.py bots/variants/spar-$t-Fl fish; } || exit 1
[ -d bots/variants/spar-$t-Mt3 ] || { ./copybot -f variants/spar-$t-M variants/spar-$t-Mt3 >/dev/null && python3 $T/patch_mite.py bots/variants/spar-$t-Mt3 --v3 && python3 $T/patch_locks.py bots/variants/spar-$t-Mt3 none; } || exit 1
