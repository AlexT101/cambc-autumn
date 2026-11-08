#!/bin/bash
# makespar.sh SRC TAG : bots/SRC -> bots/variants/spar-TAG-F and -M (forced live drafts of Fish / Mite)
cd /home/ubuntu/cambc-autumn; T=research/ideas-2026-11-08/spar-tools
for o in F M; do
  ./copybot -f $1 variants/spar-$2-$o >/dev/null && python3 $T/patch_spar.py bots/variants/spar-$2-$o >/dev/null && python3 $T/gen_table.py $o bots/variants/spar-$2-$o || echo FAIL $1 $o
done
