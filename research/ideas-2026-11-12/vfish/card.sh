#!/bin/bash
# card.sh VARIANT [REF]: bots/variants/VARIANT against charybdis 525 (or bots/REF) on the card suite (seed 8860010, 340
# fresh ladder-v4 maps, both sides, own drafts, release, 100k fuel), then the Vesper scorecard of both sides.
# A mechanism check, not a gate: 680 games are +-3.7 points. Output: ~/tmp-offload/vfish/cards/VARIANT.txt
R=/home/ubuntu/cambc-autumn; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
V=$1; REF=${2:-variants/chy-bagfocus-525}; T=$HOME/tmp-offload/vfish; D=$R/research/ideas-2026-11-12/vfish; N=card-$V
mkdir -p $T/logs $T/cards $T/ext
python3 -u tools/ab.py variants/$V $REF --no-test-draft --suites $T/suites/card/fresh-8860010 --name $N --keep-replays 0 > $T/logs/$N.log 2>&1
B=$(ls -d replays/batch-*-ab-$N-fresh-8860010 | sort | tail -n 1); X=$T/ext/$N-$(date +%s)
node tools/replay/extract.mjs $B --threads 12 --out $X > $T/logs/$N-ext.log 2>&1
python3 $D/vcard.py $X $T/cards/$V.json > /dev/null
{ grep -E "^CAND|Out-of-fuel|Failed|Broken" $T/logs/$N.log; python3 $D/vread.py $T/cards/$V.json $V ref; } > $T/cards/$V.txt
rm -rf $B $X
cat $T/cards/$V.txt
