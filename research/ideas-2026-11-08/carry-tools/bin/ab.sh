#!/bin/bash
# ab.sh NAME CAND REF SUITE [extra ab.py args]: one ab.py run (fast runner, slot pool, own drafts).
source /home/ubuntu/venv/bin/activate; cd /home/ubuntu/cambc-autumn
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
L=/home/ubuntu/tmp-offload/carry/logs; N=$1; C=$2; R=$3; S=$4; shift 4
python tools/ab.py variants/$C variants/$R --no-test-draft --suites $S --name $N --threads ${THR:-28} "$@" > $L/$N.log 2>&1
echo "exit $?" >> $L/$N.log
touch $L/$N.done
