#!/usr/bin/env python3
"""Compact per-game cache for the s3 Prism-war study.

Reads each bel-study512 game's extracted analysis (rounds, events, map) and its replay zip's stdout (D lines, CV
lines, kr-beliefs' BD enemy records), and writes one gzip pickle a game to replays/.s3cache/<sha>.pkl.gz.
Usage: extract.py [--procs 16]
"""
import glob, gzip, json, os, pickle, re, sys, zipfile
from multiprocessing import Pool

ROOT = '/home/ubuntu/wt/mac13-kronos'
AN = os.path.join(ROOT, 'replays/.analysis')
OUT = os.path.join(ROOT, 'replays/.s3cache')
TAG = 'bel-study512'
KEEP_EV = {'attack', 'cast', 'death', 'recall_start', 'recall_cancel', 'recall_end', 'tribute_start', 'tribute_end',
           'tribute_cancel', 'capture', 'lock_place', 'respawn', 'shop'}
COLS = ['x', 'y', 'hp', 'maxHp', 'alive', 'gems', 'foc', 'str', 'chan', 'chanT', 'cd0', 'cd1', 'stun', 'turn', 'sees']

DIGITS = {c: i for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/")}
EFIELDS = ["id", "alive", "visible", "tracked", "x", "y", "pos_round", "source", "fixed_round", "at_round",
           "at_slot", "turns", "ready0", "ready1", "respawn_earliest", "respawn_latest", "count"]


def nums(text, n):
    out, i = [], 0
    for _ in range(n):
        v = shift = 0
        while True:
            d = DIGITS[text[i]]
            i += 1
            v |= (d & 31) << shift
            shift += 5
            if not d & 32:
                break
        out.append((v >> 1) ^ -(v & 1))
    return out


def parse_stdout(text, prism_ids_enemy):
    D, CV, BD = {}, [], []
    for line in text.split('\n'):
        line = line.strip('\x00 \r')
        if not line:
            continue
        if line.startswith('D '):
            p = line.split()
            if len(p) == 6:
                try:
                    D[(int(p[1]), int(p[2]))] = (p[3], int(p[4]), int(p[5]))
                except ValueError:
                    pass
        elif line.startswith('CV '):
            p = line.split()
            try:
                CV.append((p[1],) + tuple(float(x) if '.' in x else int(x) for x in p[2:]))
            except ValueError:
                pass
        elif line.startswith('BD ') and prism_ids_enemy:
            try:
                secs = line[3:].split('|')
                head = nums(secs[0], 8)
                for s in secs[1:]:
                    if s[0] != 'E':
                        continue
                    e = dict(zip(EFIELDS, nums(s[1:], len(EFIELDS))))
                    if e['id'] in prism_ids_enemy:
                        BD.append((head[0], head[1], e['id'], e['alive'], e['visible'], e['tracked'], e['x'], e['y'],
                                   e['pos_round'], e['source'], e['count']))
            except (KeyError, IndexError):
                pass
    return D, CV, BD


def one(d):
    m = json.load(open(os.path.join(d, 'meta.json')))
    sha = os.path.basename(d)
    out = os.path.join(OUT, sha + '.pkl.gz')
    if os.path.exists(out):
        return sha
    mp = json.load(open(os.path.normpath(os.path.join(AN, m['mapFile'].replace('../', '')))))
    o = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
    names = {c['id']: c['name'] for c in m['champions']}
    team = {c['id']: c['team'] for c in m['champions']}
    ch = {}
    for c in o['champions']:
        ch[c['id']] = {k: c[k] for k in COLS}
    ev = [e for e in (json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'))) if e['k'] in KEEP_EV]
    prisms = [i for i, n in names.items() if n == 'Prism']
    D, CV, BD = {}, [], []
    src = os.path.join(ROOT, m['source'])
    with zipfile.ZipFile(src) as z:
        for t, fn in ((0, 'team-a.stdout'), (1, 'team-b.stdout')):
            enemy_prisms = {i for i in prisms if team[i] != t}
            text = z.read(fn).decode('latin-1')
            a, b, c = parse_stdout(text, enemy_prisms)
            D.update(a)
            CV += [(t,) + x for x in b]
            BD += [(t,) + x for x in c]
    g = dict(sha=sha, source=m['source'], map=dict(w=mp['width'], h=mp['height'], spawn=mp['spawn'], altars=mp['altars'],
             groups=[dict(id=x['id'], tiles=x['tiles'], gems=x['gems'], side=x.get('side')) for x in mp['groups']],
             walls=mp['walls'], holes=mp['holes']),
             result=m['result'], teams=m['teams'], names=names, team=team, rounds=o['round'], ch=ch, D=D, CV=CV, BD=BD,
             ev=ev)
    tmp = out + '.tmp'
    with gzip.open(tmp, 'wb', compresslevel=3) as f:
        pickle.dump(g, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, out)
    return sha


def dirs():
    out = []
    for f in glob.glob(os.path.join(AN, '*/meta.json')):
        try:
            m = json.load(open(f))
        except Exception:
            continue
        if TAG in m.get('source', ''):
            out.append(os.path.dirname(f))
    return sorted(out)


if __name__ == '__main__':
    procs = int(sys.argv[sys.argv.index('--procs') + 1]) if '--procs' in sys.argv else 16
    os.makedirs(OUT, exist_ok=True)
    ds = dirs()
    print(len(ds), 'games', flush=True)
    with Pool(procs) as p:
        for i, _ in enumerate(p.imap_unordered(one, ds, chunksize=4)):
            if i % 100 == 0:
                print(i, flush=True)
    print('done')
