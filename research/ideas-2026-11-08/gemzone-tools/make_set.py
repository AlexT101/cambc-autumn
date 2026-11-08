"""Copy the gem-zone maps of some suites into one set directory, by the bot's rule (economy/gem_zone.cc:
gem groups linked by box gap <= 5, the top cluster >= 75% of gems a round, <= 12 tiles across).

    python3 research/ideas-2026-11-08/gemzone-tools/make_set.py OUT_DIR SUITE_DIR...
"""
import json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
out, suites = sys.argv[1], sys.argv[2:]
os.makedirs(out, exist_ok=True)
rows = subprocess.run(['node', os.path.join(HERE, 'gemzone.mjs'), '5', '--box', *suites], capture_output=True, text=True, check=True).stdout
n = kept = 0
for line in rows.splitlines():
    r = json.loads(line)
    n += 1
    if not r['zones']:
        continue
    b = r['zones'][0]['bbox']
    if r['rtop'] >= 0.75 and max(b[2] - b[0], b[3] - b[1]) + 1 <= 12:
        src = r['file']
        name = src.replace('/', '_').removeprefix('maps_suites_fresh_')
        shutil.copy(src, os.path.join(out, name))
        kept += 1
print(f'{kept} of {n} maps -> {out}')
