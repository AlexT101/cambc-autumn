#!/bin/bash
# panel.sh BOT TAG: BOT against the panel (PANEL.md) on panel-check-514510, real fuel, plus d6-p2 for astraeus and proteus.
cd /home/ubuntu/cambc-autumn; bot=$1; tag=$2; T=research/ideas-2026-11-05/draft6-tools/ab.sh
S=maps/suites/merged/panel-check-514510
for m in astraeus-now-1106 panel-proteus panel-demeter panel-ocean-td; do REF=variants/$m $T $bot pchk-$tag-vs-$m $S; done
REF=baselines/v67 $T $bot pchk-$tag-vs-v67 $S
for m in astraeus-now-1106 panel-proteus; do REF=variants/$m $T $bot p2-$tag-vs-$m maps/suites/merged/d6-p2; done
echo PANEL-DONE $tag >> /home/ubuntu/tmp-offload/draft6/panel-$tag.done
