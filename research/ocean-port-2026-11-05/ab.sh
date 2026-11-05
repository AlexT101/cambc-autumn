#!/bin/bash
# The ocean port (CHANGES 402-404, 9cd456fb) plus beaten_near's fix (d0259a22) against astraeus a790c441:
# own drafts, real budget, fast runner, fresh ladder-mix suites 518000-518039 (20,480 games).
set -e
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
export PATH=$HOME/.cargo/bin:$PATH CAMBC_SLOTS=86 CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
L=replays/ocean-port; mkdir -p $L
[ -d maps/suites/fresh/fresh-518039 ] || node tools/mapgen/mapgen.mjs suite --seed 518000-518039 --out 'maps/suites/fresh/fresh-{seed}' > $L/mapgen.log 2>&1
suites=$(seq -f "maps/suites/fresh/fresh-%g" 518000 518039 | paste -sd,)
python tools/ab.py variants/astraeus-d0259a2 variants/astraeus-a790c44 --no-test-draft --suites "$suites" --name oport-fix > $L/ab.log 2>&1
echo done
