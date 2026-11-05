export PATH=/home/ubuntu/venv/bin:$HOME/.cargo/bin:$PATH CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
cd /home/ubuntu/cambc-autumn/.claude/worktrees/agent-a7617aa5334d83490
# usage: ab NAME CAND FIRST LAST
ab() {
    local name=$1 cand=$2 first=$3 last=$4
    local s=$(seq -s, -f "maps/fresh-%g" $first $last)
    python tools/ab.py $cand variants/astraeus-5b66bde --no-test-draft --suites $s --name $name > rsvscratch/$name.log 2>&1
}
