#!/bin/bash
# gate.sh ARM FIRST N [fr8|std|both] [REF]: bots/variants/ARM against bots/variants/r8s-base (charybdis 524) at 100k fuel,
# fixed fgate reads of N batches from pool v4 batch FIRST: fr8 = fr8-g25 + Mt3q bodies, std = Flp4 + Mt3q
# (the candidate's Mite half is shared, so std runs after fr8). Logs in ~/tmp-offload/r8-scale/gates/.
R=/home/ubuntu/wt/r8-scale; G=/home/ubuntu/tmp-offload/r8-scale/gates; mkdir -p $G; cd $R; source /home/ubuntu/venv/bin/activate
export FGATE_RUNNER_LIB=/home/ubuntu/cambc-autumn/tools/fastengine/runner/target-rt/release/libfastrunner.so CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
ARM=$1; FIRST=$2; N=$3; WHAT=${4:-both}; REF=${5:-variants/r8s-base}
T=b$FIRST-n$N; rm -f $G/$ARM-*-$T.done
if [ $WHAT != std ]; then
  python3 -u tools/fgate.py variants/$ARM $REF --pool v4 --first-batch $FIRST --max-batches $N --ci 0 --fish-body fr8-g25 > $G/$ARM-fr8-$T.log 2>&1; touch $G/$ARM-fr8-$T.done
fi
if [ $WHAT != fr8 ]; then
  python3 -u tools/fgate.py variants/$ARM $REF --pool v4 --first-batch $FIRST --max-batches $N --ci 0 > $G/$ARM-std-$T.log 2>&1; touch $G/$ARM-std-$T.done
fi
