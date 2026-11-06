#!/bin/bash
# Phase 1 oracles: everything at --fuel 10M against the real-budget cap copy, on fuelbud-oracle (533300-533319).
T=/home/ubuntu/cambc-autumn/research/ideas-2026-11-05/fuelbud-tools
$T/ab.sh variants/oc-tuned4 variants/oc-fb-cap fb-ceil fuelbud-oracle --fuel 10000000 &
for f in base farm loop strike guard prey stand order queue; do
  $T/ab.sh variants/oc-fb-gv-$f variants/oc-fb-cap fb-gv-$f fuelbud-oracle --fuel 10000000 &
done
wait
