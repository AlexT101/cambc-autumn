"""Release100M vehicle/export identity and overhead, using the standard bench map sets."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

R = Path('/home/ubuntu/cambc-autumn')
D = Path('/home/ubuntu/tmp-offload/localq/rounds/tune8')
spec = importlib.util.spec_from_file_location('tune8_bench', R / 'tools/fuel/bench.py')
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


def command(argv):
    subprocess.run([str(x) for x in argv], cwd=R, check=True)


def play(bot, opponent, maps, out):
    out.mkdir(parents=True)
    manifest = out / 'manifest.txt'
    cells = [(m, side) for m in maps for side in 'ab']
    rows = []
    for j, (m, side) in enumerate(cells):
        a, b = (bot, opponent) if side == 'a' else (opponent, bot)
        rows.append(f"{R / 'bots' / a} {R / 'bots' / b} {bench.map_file(m)} {out / (str(j) + '.repl26a')} --statistics {out / (str(j) + '.camstat')}\n")
    manifest.write_text(''.join(rows))
    command([R / 'tools/fastengine/runner/fastrunner', 'run-batch', manifest, '--release', '--jobs', '8',
             '--fuel-quantum', '100000000', '--slot-dir', bench.cpu_slots.DIR, '--slots', str(bench.cpu_slots.SIZE)])
    results = []
    held = bench.cpu_slots.acquire(1)
    try:
        for j, (m, side) in enumerate(cells):
            raw = subprocess.check_output(['cambc', 'summary', str(out / (str(j) + '.camstat')), '-o', '-'], cwd=R, text=True)
            s = json.loads(raw)
            draft = [p['champion'] for p in s['roster']['draft'] if p['team'] == 'team' + side.upper()]
            outcome = s['match'].get('outcome')
            assert outcome in ('teamA', 'teamB'), ('Invalid outcome', outcome)
            results.append(bench.read_game(m, side, out / (str(j) + '.repl26a'), draft, outcome[-1]))
    finally:
        bench.cpu_slots.release(held)
    return results


def compare(left, right, count):
    key = lambda x: (x['map'], x['side'])
    a, b = {key(x): x for x in left}, {key(x): x for x in right}
    assert len(left) == len(right) == len(a) == len(b) == count and a.keys() == b.keys()
    assert all(not x['handoff'] and not x['capped'] for x in left + right), 'Draft validity failure'
    different = [k for k in a if a[k]['replay'] != b[k]['replay']]
    fa = sum(sum(bench.after_round1(x)) for x in left)
    fb = sum(sum(bench.after_round1(x)) for x in right)
    return {'games': count, 'different': different, 'identical': count - len(different), 'left_play_fuel': fa,
            'right_play_fuel': fb, 'right_over_left_fraction': fb / fa - 1,
            'note': 'Release100M identity; does not establish identical100k behavior.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('tag', choices=['defaults', 'export'])
    ap.add_argument('left')
    ap.add_argument('right')
    a = ap.parse_args()
    opponent = 'variants/oc-emb5-504'
    for bot in dict.fromkeys([a.left, a.right, opponent]):
        command([sys.executable, R / 'tools/pooled.py', '1', '--', 'cambc', 'build', R / 'bots' / bot, '--release'])
    records = {}
    for tag, maps in [('def', bench.DEFAULT_MAPS), ('wide', bench.MAP_SETS['wide'])]:
        rows = []
        dirs = []
        for label, bot in [('left', a.left), ('right', a.right)]:
            out = D / 'identity' / (a.tag + '-' + tag + '-' + label)
            dirs.append(out)
            data = play(bot, opponent, maps, out)
            (D / 'identity' / (a.tag + '-' + tag + '-' + label + '.json')).write_text(json.dumps({'bot':bot,'opponent':opponent,'release':True,'fuel':100000000,'games':data},indent=1)+'\n')
            rows.append(data)
        result = compare(*rows, 2 * len(maps))
        records[tag] = result
        (D / (a.tag + '-identity.json')).write_text(json.dumps(records,indent=2)+'\n')
        assert not result['different'], 'Vehicle/plain replay identity failed; review required'
        if a.tag == 'defaults':
            assert result['right_over_left_fraction'] <= .01, 'Vehicle overhead exceeds1%; review before training'
        for out in dirs:
            shutil.rmtree(out)  # JSON retains complete identity/fuel records; no strength evidence is discarded.


if __name__ == '__main__':
    main()
