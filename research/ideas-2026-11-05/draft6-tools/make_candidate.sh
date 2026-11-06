#!/bin/bash
# make_candidate.sh LAB NAME [f92]: bots/variants/NAME = oc-base7 with LAB's draft_model.h (and its config "deploy"),
# lcb_patch.py's map_features.cc (kappa > 0), F92's map_features.{h,cc} (from oc-draftfeat2) when asked; then JS/C++ parity on
# the 128 ladder maps and fresh-548200.
set -e
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
lab=$1; name=$2; f92=$3
./copybot -f variants/oc-base7 variants/$name
rm -f bots/variants/$name/READY
if [ "$f92" = f92 ]; then cp bots/variants/oc-draftfeat2/src/draft/map_features.{h,cc} bots/variants/$name/src/draft/; fi
# lcb_patch.py only with a deploy kappa > 0: its code names the header's draw arrays, which kappa 0 leaves out.
if python3 -c "import json,sys; sys.exit(0 if (json.load(open('$lab/config.json')).get('deploy') or {}).get('kappa', 0) > 0 else 1)"; then
  python3 research/ideas-2026-11-05/draft6-tools/lcb_patch.py bots/variants/$name
fi
node tools/draftlab/model.mjs cpp --lab $lab --out bots/variants/$name/src/draft/draft_model.h
node tools/draftlab/native.mjs --lab $lab maps maps/suites/fresh/fresh-548200 --src bots/variants/$name/src/draft
cambc build bots/variants/$name | tail -1
echo "$name: oc-base7 with the draft6 model of $lab (research/ideas-2026-11-05/draft6.md)" > bots/variants/$name/NOTE
