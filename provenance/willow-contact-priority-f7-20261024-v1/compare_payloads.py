#!/usr/bin/env python3
"""Compare extracted replay payloads, excluding ZIP/bundle wrapper bytes and source labels."""
from __future__ import annotations
import gzip, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROV = ROOT / 'provenance/willow-contact-priority-f7-20261024-v1'
EXTRACT = PROV / 'payloads/extracted'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def records():
    found = {}
    for meta_path in EXTRACT.glob('*/meta.json'):
        meta = json.loads(meta_path.read_text())
        src = Path(meta['source']).name
        key = src.replace('.repl26a', '')
        item = {'meta': meta, 'dir': meta_path.parent, 'events': gzip.decompress((meta_path.parent/'events.jsonl.gz').read_bytes()),
                'rounds': gzip.decompress((meta_path.parent/'rounds.json.gz').read_bytes())}
        found[key] = item
    return found


def compare(a, b):
    return {
        'events_payload_equal': a['events'] == b['events'],
        'rounds_payload_equal': a['rounds'] == b['rounds'],
        'events_uncompressed_sha256': sha(a['events']),
        'rounds_uncompressed_sha256': sha(a['rounds']),
        'map_hashes': [a['meta']['map']['hash'], b['meta']['map']['hash']],
        'result': [a['meta']['result'], b['meta']['result']],
    }


def alive_willow_contact(rows, key):
    item = rows[key]
    data = json.loads(item['rounds'])
    meta = item['meta']
    out = []
    for champ in meta['champions']:
        if champ['name'] != 'Willow':
            continue
        state = data['champions'][champ['id']]
        alive13 = [i for i, p in enumerate(state['prio']) if p == 13 and state['alive'][i]]
        recall13 = [i for i in alive13 if state['chan'][i] == 1]
        end_recall = [i for i, ch in enumerate(state['chan']) if ch == 1 and state['alive'][i]]
        out.append({'team': champ['team'], 'alive_priority13_rounds': [data['round'][i] for i in alive13],
                    'alive_recall_rounds': len(end_recall), 'alive_recall_priority13_rounds': [data['round'][i] for i in recall13]})
    return out


def main():
    r = records()
    pairs = {
        'Elkring candidate-B vs parent-B': ('candidate-elkring-B', 'parent-elkring-B'),
        'Pilgrimage candidate-A vs parent-A': ('candidate-pilgrimage-A', 'parent-pilgrimage-A'),
        'Gold Rush candidate-A vs existing parent-A control': ('candidate-gold-rush-A', 'f7-base-gold-rush-A-A'),
    }
    report = {'schema':'contact-priority-payload-comparison/v1','comparisons':{},'willow':{}}
    for label, (a,b) in pairs.items():
        report['comparisons'][label] = compare(r[a],r[b])
    for key in ['candidate-elkring-B','candidate-pilgrimage-A','parent-elkring-B','parent-pilgrimage-A']:
        report['willow'][key] = alive_willow_contact(r,key)
    out=PROV/'payload-comparison.json'
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
