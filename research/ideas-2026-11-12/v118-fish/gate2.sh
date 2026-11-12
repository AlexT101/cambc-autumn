#!/bin/bash
# gate2.sh ARM...: as gate.sh, one arm after another (REF's halves are cached by the first gates): for each ARM the
# std read (Flp4 / Mt3q) and the fr8 read (fr8-g25 / Mt3q), pool v3 batches 16-17, 100k fuel.
R=/home/ubuntu/cambc-autumn; G=/home/ubuntu/tmp-offload/v118-fish/gates; mkdir -p $G; cd $R; source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=$R/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
REF=variants/lab-emb6-c520-ps
for ARM in "$@"; do
  python3 tools/fgate.py variants/$ARM $REF --pool v3 --first-batch 16 --max-batches 2 --ci 0 --jobs 4 > $G/$ARM-std.log 2>&1; touch $G/$ARM-std.done
  python3 tools/fgate.py variants/$ARM $REF --pool v3 --first-batch 16 --max-batches 2 --ci 0 --fish-body fr8-g25 --jobs 4 > $G/$ARM-fr8.log 2>&1; touch $G/$ARM-fr8.done
done
