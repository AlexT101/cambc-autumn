#!/bin/bash
# h2h.sh ARM [SUITES]: bots/variants/ARM against bots/variants/r8s-base (charybdis 524), own drafts, 100k fuel, release
# builds, on this programme's fresh ladder-v4 suites (~/tmp-offload/r8-scale/suites/h2h-m0..3: seeds 8840000-8840059,
# 20,400 maps, both sides). Log in ~/tmp-offload/r8-scale/gates/ARM-h2h.log.
R=/home/ubuntu/wt/r8-scale; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
ARM=$1; S=/home/ubuntu/tmp-offload/r8-scale/suites; SU=${2:-$S/h2h-m0,$S/h2h-m1,$S/h2h-m2,$S/h2h-m3}
python3 -u tools/ab.py variants/$ARM variants/r8s-base --no-test-draft --suites $SU --name h2h-$ARM --keep-replays 1 > /home/ubuntu/tmp-offload/r8-scale/gates/$ARM-h2h.log 2>&1
touch /home/ubuntu/tmp-offload/r8-scale/gates/$ARM-h2h.done
