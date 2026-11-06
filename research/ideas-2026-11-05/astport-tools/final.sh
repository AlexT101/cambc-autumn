#!/bin/bash
# final.sh: lr08's SPRT, then oc-astport on the combo and varied suites and the panel (plus the base's panel rates).
cd /home/ubuntu/cambc-autumn
T=research/ideas-2026-11-05/astport-tools
$T/sprt.sh lr08
$T/full.sh oc-astport ap-final-combo ap-combo
$T/full.sh oc-astport ap-final-varied ap-varied
S=panel-check-514510
for m in "variants/astraeus-now-1106 astraeus1106" "variants/panel-proteus proteus" "variants/panel-demeter demeter" "variants/panel-ocean-td ocean-td" "baselines/v67 v67"; do
  set -- $m
  REF=$1 $T/full.sh oc-astport pchk-astport-vs-$2 $S
done
for m in "variants/panel-proteus proteus" "variants/panel-demeter demeter" "variants/panel-ocean-td ocean-td" "baselines/v67 v67"; do
  set -- $m
  [ -f replays/ab/pchk-orc-vs-$2/summary.md ] && continue
  REF=$1 $T/full.sh oc-retest-clean pchk-orc-vs-$2 $S
done
