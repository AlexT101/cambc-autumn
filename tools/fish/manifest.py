"""Select Fish games, deduplicate raw bytes, and split whole match groups."""
import argparse
import collections
import hashlib
import json
from pathlib import Path


def build(root, output):
    rows = {}
    copies = 0
    for p in sorted(Path(root).glob('*/group.json')):
        detail = json.loads(p.read_text())
        group = detail['group']
        for f in sorted(p.parent.glob('*.repl26a')):
            position = int(f.name.split('-')[0])
            match = next(m for m in detail['matches'] if m['position'] == position)
            sides = sorted(match.get('sides') or group['sides'], key=lambda s: s['side'])
            fish = [i for i,s in enumerate(sides) if s.get('teamName') == 'Intercontinental Fish']
            if len(fish) != 1:
                continue
            digest = hashlib.sha256(f.read_bytes()).hexdigest()
            copies += digest in rows
            rows.setdefault(digest, dict(sha256=digest, file=str(f), group=group['id'], date=group['createdAt'],
                match=match['id'], map=match['map'], side=fish[0], opponent=sides[1-fish[0]]['teamName'],
                version=sides[fish[0]].get('version'),
                split='test' if int(hashlib.sha256(group['id'].encode()).hexdigest(), 16) % 5 == 0 else 'train'))
    Path(output).write_text(json.dumps(list(rows.values()), indent=2)+'\n')
    print(len(rows), 'distinct games;', copies, 'duplicate copies;', dict(collections.Counter(r['split'] for r in rows.values())))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root')
    p.add_argument('output')
    a = p.parse_args()
    build(a.root, a.output)
