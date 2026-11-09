#!/bin/bash
# one.sh BOT MAP: both sides vs oc-base25 into scratch tf-MAP; prints BIG/r* lines of our side.
cd /home/ubuntu/cambc-autumn; source /home/ubuntu/venv/bin/activate
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
S=/tmp/claude-1000/-home-ubuntu-cambc-autumn/3650a530-f591-417e-a0c5-31524a1e3260/scratchpad; m=$(basename $2 .map26a)
rm -rf $S/tf-$m; timeout 900 python3 tools/fuel/bench.py run variants/$1 --fuel 0 --opp variants/oc-base25 --maps $2 --jobs 2 --games $S/tf-$m --out $S/tf-$m.json 2>&1 | grep 'out-of-fuel'
python3 - $S/tf-$m "$1" <<'PY'
import zipfile,glob,sys
for f in sorted(glob.glob(sys.argv[1]+'/*/*.repl26a')):
    z=zipfile.ZipFile(f); side='a' if f.split('/')[-1].startswith(sys.argv[2]) else 'b'
    s=z.read(f'team-{side}.stdout').decode(errors='replace'); n=0
    for l in s.splitlines():
        if l.startswith(('BIG','CUT ','NEED')) or (l.startswith('r') and 'ran out' in l):
            print(side, l.replace(f'/home/ubuntu/cambc-autumn/bots/variants/{sys.argv[2]}/src/','')); n+=1
        if n>60: break
PY
