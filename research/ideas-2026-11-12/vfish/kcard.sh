#!/bin/bash
# kcard.sh VARIANT: card.sh, keeping the extract in ~/tmp-offload/vfish/ext-kill/VARIANT and adding prism.py / loss.py.
R=/home/ubuntu/cambc-autumn; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
V=$1; REF=${2:-variants/chy-bagfocus-525}; T=$HOME/tmp-offload/vfish; D=$R/research/ideas-2026-11-12/vfish; N=kcard-$V
mkdir -p $T/logs $T/cards $T/ext-kill
python3 -u tools/ab.py variants/$V $REF --no-test-draft --suites $T/suites/card/fresh-8860010 --name $N --keep-replays 0 > $T/logs/$N.log 2>&1
B=$(ls -d replays/batch-*-ab-$N-fresh-8860010 | sort | tail -n 1); X=$T/ext-kill/$V
rm -rf $X
node tools/replay/extract.mjs $B --threads 12 --out $X > $T/logs/$N-ext.log 2>&1
python3 $D/vcard.py $X $T/cards/$V.json > /dev/null
{ grep -E "^CAND|Out-of-fuel|Failed|Broken" $T/logs/$N.log; python3 $D/vread.py $T/cards/$V.json $V ref; echo; python3 $D/prism.py $X; python3 $D/loss.py $X; } > $T/cards/$V.txt
rm -rf $B
cat $T/cards/$V.txt
