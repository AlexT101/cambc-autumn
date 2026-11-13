#!/bin/bash
# h2h.sh VARIANT SET [REF]: bots/variants/VARIANT against charybdis 525 (variants/chy-bagfocus-525, or bots/REF), own
# drafts, release, 100k fuel, on every suite of ~/tmp-offload/vfish/suites/SET (fresh ladder-v4, both sides).
# Log ~/tmp-offload/vfish/logs/VARIANT-SET.log, then VARIANT-SET.done.
R=/home/ubuntu/cambc-autumn; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
V=$1; SET=$2; REF=${3:-variants/chy-bagfocus-525}; T=$HOME/tmp-offload/vfish; TAG=$V-$SET$([ -n "$3" ] && echo "-vs-$(basename $3)")
SU=$(ls -d $T/suites/$SET/fresh-* | paste -sd,)
python3 -u tools/ab.py variants/$V $REF --no-test-draft --suites $SU --name vf-$TAG --keep-replays 200 > $T/logs/$TAG.log 2>&1
touch $T/logs/$TAG.done
