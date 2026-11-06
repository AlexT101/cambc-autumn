#!/bin/bash
# make_candidate.sh LAB NAME: bots/variants/NAME = oc-base10 with LAB's draft_model.h (oc-base10's map_features are
# already F92's); then JS/C++ parity on the 128 ladder maps and fresh-590200, and a build.
set -e
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
lab=$1; name=$2
./copybot -f variants/oc-base10 variants/$name
rm -f bots/variants/$name/READY
node tools/draftlab/model.mjs cpp --lab $lab --out bots/variants/$name/src/draft/draft_model.h
node tools/draftlab/native.mjs --lab $lab maps maps/suites/fresh/fresh-590200 --src bots/variants/$name/src/draft
cambc build bots/variants/$name | tail -n 1
echo "$name: oc-base10 with the draft7 model of $lab (research/ideas-2026-11-06/draft7.md)" > bots/variants/$name/NOTE
diff -r bots/variants/oc-base10/src bots/variants/$name/src --brief
