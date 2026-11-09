#!/bin/bash
# SPSA87 opponents: oc-base25 noise bodies (diverse-panel.md: the 26 tuned knobs redrawn x exp(0.2 N) every 100
# rounds) with member seeds 1360001-4, which the dpanel gate (seeds 1310001-32) never plays.
#   s87-n1, n2 -> spar-s87n{1,2}-{F,M}: Fish's / Mite's live picks on ladder maps, own draft elsewhere.
#   s87-n3, n4 -> s87-n{3,4}-td: ladder compositions (test_draft) on every map.
cd /home/ubuntu/cambc-autumn; T=research/ideas-2026-11-08
python3 - <<'PY'
import sys; sys.path.insert(0, 'research/ideas-2026-11-08/diverse-tools'); import bodies
for k in range(1, 5): bodies.noise(f'variants/s87-n{k}', 1360000 + k); print('noise', k)
PY
for k in 1 2; do $T/spar-tools/makespar.sh variants/s87-n$k s87n$k; done
for k in 3 4; do
  ./copybot -f variants/s87-n$k variants/s87-n$k-td >/dev/null
  sed -i 's/^constexpr bool test_draft = false;/constexpr bool test_draft = true;/' bots/variants/s87-n$k-td/src/params.h
  grep -q '^constexpr bool test_draft = true;' bots/variants/s87-n$k-td/src/params.h || echo FAIL td $k
done
