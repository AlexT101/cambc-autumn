#!/bin/bash
# card.sh VARIANT: like vfish/card.sh but keeps the extract in ~/tmp-offload/vfish/ext/surv-VARIANT and uses its own batch name.
R=/home/ubuntu/cambc-autumn; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
V=$1; REF=${2:-variants/chy-bagfocus-525}; T=$HOME/tmp-offload/vfish; D=$R/research/ideas-2026-11-12/vfish; N=scard-$V
mkdir -p $T/logs $T/cards $T/ext
python3 -u tools/ab.py variants/$V $REF --no-test-draft --suites $T/suites/card/fresh-8860010 --name $N --keep-replays 0 > $T/logs/$N.log 2>&1
B=$(ls -d replays/batch-*-ab-$N-fresh-8860010 | sort | tail -n 1); X=$T/ext/surv-$V
rm -rf $X
node tools/replay/extract.mjs $B --threads 12 --out $X > $T/logs/$N-ext.log 2>&1
python3 $D/vcard.py $X $T/cards/$V.json > /dev/null
{ grep -E "^CAND|Out-of-fuel|Failed|Broken" $T/logs/$N.log; python3 $D/vread.py $T/cards/$V.json $V ref; } > $T/cards/$V.txt
rm -rf $B
cat $T/cards/$V.txt
