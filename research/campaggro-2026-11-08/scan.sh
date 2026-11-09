#!/bin/bash
# scan.sh BATCH OUTDIR: extract the games of BATCH whose stdout has a CAGG line, then outcome.py on them.
B=$1; O=$2; cd /home/ubuntu/cambc-autumn
python3 - "$B" > $O.list <<'PY'
import zipfile, glob, sys
for z in sorted(glob.glob(sys.argv[1] + '/*.repl26a')):
    try:
        Z = zipfile.ZipFile(z)
        if any(b'CAGG' in Z.read(n) for n in ('team-a.stdout', 'team-b.stdout')): print(z)
    except Exception: pass
PY
wc -l < $O.list
node tools/replay/extract.mjs $(cat $O.list) --out $O --threads 16 > $O.extract.log 2>&1
python3 research/campaggro-2026-11-08/outcome.py $O
