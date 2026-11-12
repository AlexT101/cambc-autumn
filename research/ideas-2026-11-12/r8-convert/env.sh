# source this: environment for every run of the r8-convert programme (worktree /home/ubuntu/wt/r8-convert)
cd /home/ubuntu/wt/r8-convert
source /home/ubuntu/venv/bin/activate
export CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH
export FGATE_RUNNER_LIB=/home/ubuntu/cambc-autumn/tools/fastengine/runner/target-rt/release/libfastrunner.so
L=$HOME/tmp-offload/r8-convert/logs
