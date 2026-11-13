"""Forced picks against an opponent that is not the entry's: does the draft return to the host's own cleanly?

    py forcecheck.py --host variants/BOT --opp variants/chy-525f --work WORK [--jobs 24]
Plays BOT on every forced cell (WORK/force.txt, entries in WORK/ent) against --opp, which drafts as it likes. Per game:
our picks must equal the entry's up to and including the round after which the opponent's picks first differ from the
entry's opponent's (that round's pick is made before the difference shows), no guard line (PLAN-CHECK, DRAFT-UNFINISHED,
DRAFT-CAPPED) may print, and the game must run its course. Prints one line a game and a summary."""
import argparse, json, os, re, subprocess, sys, zipfile
from pathlib import Path

import rbuild

ROOT, HERE = rbuild.ROOT, rbuild.HERE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', required=True)
    ap.add_argument('--opp', required=True)
    ap.add_argument('--work', required=True)
    ap.add_argument('--jobs', type=int, default=24)
    a = ap.parse_args()
    work = Path(a.work).expanduser()
    host, opp = ROOT / 'bots' / a.host, ROOT / 'bots' / a.opp
    keys = [l.split()[0] for l in open(work / 'force.txt') if l.strip()]
    ents = {k: json.loads((work / 'ent' / f'{k}.json').read_text()) for k in keys}
    out = work / 'forcecheck'
    out.mkdir(exist_ok=True)
    lines = []
    for k, e in ents.items():
        f = out / f'{k}.repl26a'
        f.unlink(missing_ok=True)
        A, B = (host, opp) if e['side'] == 'a' else (opp, host)
        lines.append(f"{A} {B} {rbuild.map_path(re.match(r'^(.+)-[ab]-v', k).group(1))} {f}")
    (out / 'manifest.txt').write_text('\n'.join(lines) + '\n')
    env = dict(os.environ, CAMBC_BIN=str(rbuild.FAST), FASTRUNNER_MODE='native')
    r = subprocess.run([str(rbuild.FAST), 'run-batch', str(out / 'manifest.txt'), '--jobs', str(a.jobs), '--slot-dir', str(rbuild.cpu_slots.DIR),
                        '--slots', str(rbuild.cpu_slots.SIZE), '--release', '--color', 'never'], capture_output=True, text=True, env=env, cwd=ROOT)
    (out / 'run.log').write_text(r.stdout + r.stderr)
    bad = wins = 0
    for k, e in ents.items():
        f = out / f'{k}.repl26a'
        tmp = out / f'{k}.json'
        tmp.unlink(missing_ok=True)
        if f.exists():
            subprocess.run(['node', str(HERE / 'extract.mjs'), str(tmp), f"{f}:{e['side']}:{k}"], capture_output=True)
        if not tmp.exists():
            print(k, 'NO GAME')
            bad += 1
            continue
        g = json.loads(tmp.read_text())
        fo, ft, go, gt = e['ours']['picks'], e['opp']['picks'], g['ours']['picks'], g['opp']['picks']
        left = next((i for i in range(len(ft)) if gt[i] != ft[i]), len(ft))  # the opponent's first pick off the entry
        need = min(len(fo), left + 1)
        with zipfile.ZipFile(f) as z:
            text = z.read(f"team-{e['side']}.stdout").replace(b'\0', b'').decode(errors='replace')
        guard = [w for w in ('PLAN-CHECK', 'DRAFT-UNFINISHED', 'DRAFT-CAPPED') if w in text]
        ok = go[:need] == fo[:need] and not guard and len(set(go)) == len(fo) and g['rounds'] > 100
        won = g['outcome'] == (1 if e['side'] == 'a' else 2)
        wins += bool(won)
        bad += not ok
        print(k, 'ok' if ok else 'BAD', f'opponent leaves at pick {left}; ours {go} forced {fo}; rounds {g["rounds"]}; won {won}', *guard)
    print(f'{len(ents)} forced cells, {bad} bad, {wins} won against {a.opp}')


if __name__ == '__main__':
    main()
