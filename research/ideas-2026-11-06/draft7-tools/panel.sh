#!/bin/bash
# panel.sh BOT TAG: BOT against the panel (PANEL.md) on panel-check-514510, real fuel, plus d7-p2 for astraeus and proteus.
cd /home/ubuntu/cambc-autumn; bot=$1; tag=$2; T=research/ideas-2026-11-06/draft7-tools/ab.sh
S=maps/suites/merged/panel-check-514510
for m in astraeus-now-1106 panel-proteus panel-demeter panel-ocean-td; do REF=variants/$m $T $bot d7pchk-$tag-vs-$m $S; done
REF=baselines/v67 $T $bot d7pchk-$tag-vs-v67 $S
for m in astraeus-now-1106 panel-proteus; do REF=variants/$m $T $bot d7p2-$tag-vs-$m maps/suites/merged/d7-p2; done
echo PANEL-DONE $tag >> /home/ubuntu/tmp-offload/draft7/panel-$tag.done
