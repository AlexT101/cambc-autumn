#!/bin/bash
# bodypicks.sh BODY J: chy-525 copy against BODY on fgate batch J (pool v4, 200k), all replays kept, for the drafts.
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-rt/release/libfastrunner.so
B=$1; J=$(printf %03d $2); P=$HOME/tmp-offload/gatebatch/suites-v4/m2560/b$J.parts
SU=$(ls -d $P/p* | paste -sd,),ladder
python tools/ab.py variants/draft-drop-our-vesper-ref0 variants/$B --no-test-draft --suites $SU --name ddov-bp-$B-b$J --keep-replays 0 \
  --experiment-config $HOME/tmp-offload/gatebatch/suites-v4/m2560/b$J.json --game-timeout 600 --fuel 200000 > $HOME/tmp-offload/ddov/bp-$B-b$J.log 2>&1
echo $? > $HOME/tmp-offload/ddov/bp-$B-b$J.done
