"""Build compact, auditable observations from per-input Fish perspectives."""
import argparse
import collections
import gzip
import json
from pathlib import Path


def distance(a, b):
    if 'x' not in a or 'x' not in b:
        return 999
    return max(abs(a['x'] - b['x']), abs(a['y'] - b['y']))


def shield(c):
    return sum(b['mag'] for b in c['buffs'] if b['type'] == 0)


def run(manifest, cache, split, output):
    rows = collections.defaultdict(list)
    games = []
    for entry in json.loads(Path(manifest).read_text()):
        if entry['split'] != split:
            continue
        key = entry['sha256'][:16]
        with gzip.open(Path(cache) / f'{key}.json.gz') as f:
            g = json.load(f)
        team = [c for c in g['roster'] if c['team'] == g['side']]
        names = {c['id']: c['name'] for c in team}
        first = {}
        for t in g['turns']:
            for a in t['actions']:
                if a['kind'] == 'Set priority':
                    first.setdefault(t['id'], a['value'])
        games.append({k: entry[k] for k in ['sha256', 'file', 'group', 'date', 'opponent', 'map']})
        for t in g['turns']:
            ident = dict(game=key, round=t['round'], actor=t['id'], type=names[t['id']])
            actions = t['actions']
            for a in actions:
                s = a.get('before')
                if s is None:
                    continue
                m = s['me']
                ref = dict(ident, step=a['step'])
                if a['kind'] == 'Set priority':
                    rows['priority'].append(dict(ref, value=a['value'], first=first[t['id']], n=len(team),
                        hp=m['hp'], maxhp=m['maxHp'], shield=shield(m), gems=m['gems'], alive=m['alive'],
                        start_enemies=len(t['start']['enemies']), enemies=len(s['enemies']),
                        nearest=min((distance(m, e) for e in s['enemies']), default=999),
                        rank_types=[c['type'] for c in team],
                        attacked_champion=any(x['kind'] in ('Attack', 'Cast ability') and any([e['x'], e['y']] == x['to'] for e in x['before']['enemies']) for x in actions),
                        stunned=any(b['type'] == 1 for b in m['buffs']),
                        actions=[x['kind'] for x in actions]))
                if a['kind'] == 'Cast ability' and a['ability'] == 5:
                    cs = [c for c in s['allies'] if distance(m, c) <= 4]
                    target = next((c for c in cs if [c['x'], c['y']] == a['to']), None)
                    if target is None:
                        raise ValueError(f'heal target not visible: {ref}')
                    rows['heal'].append(dict(ref, target=target['id'], focus=m['focus'], candidates=cs))
                if a['kind'] == 'Attack':
                    radius = 3 if m['type'] in (1, 3, 5, 6, 8, 11) else 1
                    cs = [c for c in s['enemies'] if distance(m, c) <= radius]
                    target = next((c for c in cs if [c['x'], c['y']] == a['to']), None)
                    if cs:
                        rows['attack'].append(dict(ref, target=target['id'] if target else None, candidates=cs, me=m))
                if a['kind'] == 'Submit gems':
                    rows['tribute_attempt'].append(dict(ref, gems=m['gems'], hp=m['hp'], maxhp=m['maxHp'],
                        enemies=len(s['enemies']), score=s['score'][g['side']], altar=a['to']))
            # A turn may move into range before deciding to tribute. Use its final position,
            # and exclude a channel already in progress rather than count it as a refusal.
            s = t.get('end')
            if not s:
                continue
            m = s['me']
            if not m['alive'] or 'gems' not in m or not m['gems']:
                continue
            if any(b['type'] == 1 for b in t['start']['me']['buffs']):
                continue
            if t['start']['me']['channelType'] and not any(a['kind'] == 'Cancel channel' for a in actions):
                continue
            if min((max(abs(m['x']-x), abs(m['y']-y)) for x,y in g['map']['altars']), default=999) <= 1:
                rows['altar_opportunity'].append(dict(ident, gems=m['gems'], hp=m['hp'], maxhp=m['maxHp'],
                    enemies=len(s['enemies']), attempted=any(a['kind']=='Submit gems' for a in actions),
                    nearest=min((distance(m,e) for e in s['enemies']), default=999),
                    actions=[a['kind'] for a in actions]))
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output, 'wt') as f:
        json.dump(dict(games=games, rows=rows), f, separators=(',', ':'))
    print(split, len(games), {k: len(v) for k, v in rows.items()})


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest')
    p.add_argument('cache')
    p.add_argument('split', choices=['train', 'test'])
    p.add_argument('output')
    a = p.parse_args()
    run(a.manifest, a.cache, a.split, a.output)
