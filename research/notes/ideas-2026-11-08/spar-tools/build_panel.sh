#!/bin/bash
# Rebuild the spar panel's bodies (bots/variants is gitignored): spar-oc29-{F,M} from oc-base29 (or SRC), the 12
# jittered copies spar-j1..j12-{F,M} (seeds 1200001-1200012), and the two knob bodies o29s and o29gs.
#   research/notes/ideas-2026-11-08/spar-tools/build_panel.sh [SRC]    e.g. SRC=variants/oc-base29
cd /home/ubuntu/cambc-autumn; T=research/notes/ideas-2026-11-08/spar-tools; SRC=${1:-variants/oc-base29}
$T/makespar.sh $SRC oc29
for o in F M; do
  for i in $(seq 1 12); do python3 $T/jitter.py variants/spar-oc29-$o variants/spar-j$i-$o $((1200000+i)); done
  ./tools/copybot -f variants/spar-oc29-$o variants/spar-o29s-$o >/dev/null
  sed -i 's/^inline constexpr float life_value = [0-9.]*f;/inline constexpr float life_value = 443.0f;/; s/^inline constexpr float hurt_health_fraction = [0-9.]*f;/inline constexpr float hurt_health_fraction = 0.55f;/' bots/variants/spar-o29s-$o/src/params.h
  ./tools/copybot -f variants/spar-o29s-$o variants/spar-o29gs-$o >/dev/null
  sed -i 's/^inline float gold_price_scale = [0-9.]*f;/inline float gold_price_scale = 2.0f;/' bots/variants/spar-o29gs-$o/src/params.h
done
