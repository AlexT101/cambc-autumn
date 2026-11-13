"""Read captured third-party Mite wins and fetch a bounded set of cached ranked replays.

Does not spend platform API/scrim quota. Output is provisional until live validation
against the target pin; timestamps and matching drafts do not identify a bot version.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
NAMES = ['Ryth','Vesper Vale','Vendetta','Cassi & Issac','Stellar','Prism',
         'Marcella','Willow','Ren','Varg','Tavi','Heart of Ruin']
CAPTURE = '/home/ubuntu/cambc-autumn/.oarena/capture'


def fish_compatible(winner, mite, fish_entry):
    if fish_entry is None:
        return True
    ours, opponent = fish_entry['ours']['picks'], fish_entry['opp']['picks']
    if winner == ours:
        return True
    departure = next((i for i,(a,b) in enumerate(zip(winner,ours)) if a != b), 0)
    return mite[:departure] != opponent[:departure]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--since',default='2026-11-13T08:00')
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--refset',default='r10',help='Draft classification only; not proof of opponent identity')
    ap.add_argument('--limit',type=int,default=8)
    a=ap.parse_args()
    if a.limit < 0:
        ap.error('--limit must be nonnegative')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}',a.since):
        raise ValueError('Expected YYYY-MM-DDTHH:MM')
    a.work.mkdir(parents=True,exist_ok=True)
    sql=f"""select match_id,created_at,kind,map,team_a,team_b,name_a,name_b,picks_a,picks_b,replay
        from matches where created_at >= '{a.since}' and status='finished'
        and team_a not like '547efb5b%' and team_b not like '547efb5b%'
        and ((name_a='Mite' and result_a='loss') or (name_b='Mite' and result_b='loss'))
        order by created_at desc;"""
    response=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','big-arm',
        f'sqlite3 -readonly -json {CAPTURE}/capture.db'],input=sql,text=True,
        capture_output=True,check=True,timeout=120)
    rows=json.loads(response.stdout or '[]')
    (a.work/'rows.json').write_text(json.dumps(rows,indent=1)+'\n')
    drafts={}
    for line in (ROOT/'research/ladder-scrims-2026-11-06/data/games.jsonl').open():
        row=json.loads(line)
        if row.get('version')==119 and row.get('refset')==a.refset and row.get('opp_name')=='Mite':
            drafts[(row['map'],row['side'])]=[NAMES.index(n) for n in row['our_picks']]
    old=Path('/home/ubuntu/tmp-offload/rbook/x2')
    fish={}
    old_cells=json.loads((old/'book_cells.json').read_text())
    old_mite={(c['map'],c['side']) for c in old_cells if c['opp']=='mite'}
    for cell in old_cells:
        if cell['opp']=='fish':
            fish[(cell['map'],cell['side'])]=json.loads((old/'ent'/f"{cell['key']}.json").read_text())
    candidates=[]
    selected=set()
    fetched=0
    for row in rows:
        side='b' if row['name_a']=='Mite' else 'a'
        enemy='a' if side=='b' else 'b'
        cell=(row['map'],side)
        winner=json.loads(row[f'picks_{side}'])
        mite=json.loads(row[f'picks_{enemy}'])
        exact=winner==drafts.get(cell)
        compatible=fish_compatible(winner,mite,fish.get(cell))
        candidate=dict(row,side=side,winner=row[f'name_{side}'],winner_picks=winner,mite_picks=mite,
                       exact_host_draft=exact,fish_draft_compatible=compatible,
                       covered_by_old_mite_book=cell in old_mite,
                       opponent_version_verified=False,local_replay=None)
        path=row.get('replay') or ''
        if (compatible and cell not in selected and fetched<a.limit and row['kind']=='ranked'
                and re.fullmatch(r'replays/[0-9-]+/[0-9a-f-]+\.zip',path)):
            target=a.work/f"{row['match_id']}.zip"
            if not target.exists():
                subprocess.run(['scp','-q','-o','BatchMode=yes','-o','ConnectTimeout=10',
                                f'big-arm:{CAPTURE}/{path}',str(target)],check=True,timeout=120)
            candidate['local_replay']=str(target.resolve())
            selected.add(cell)
            fetched+=1
        candidates.append(candidate)
    (a.work/'candidates.json').write_text(json.dumps(candidates,indent=1)+'\n')
    provisional=[]
    for candidate in candidates:
        if candidate['local_replay']:
            team=re.sub(r'[^a-z0-9]','',candidate['winner'].lower())[:8]
            version=900 if candidate['exact_host_draft'] else 901
            key=f"{candidate['map']}-{candidate['side']}-v{version}-{team}-{candidate['match_id'][-12:]}"
            provisional.append(f"{candidate['local_replay']} {candidate['side']} {key} {candidate['map']} mite")
    (a.work/'provisional.tsv').write_text('\n'.join(provisional)+'\n')
    summary={'since':a.since,'foreign_wins':len(rows),'cells':len({(r['map'],r['side']) for r in candidates}),
             'ranked_cached':sum(r['kind']=='ranked' and bool(r.get('replay')) for r in rows),
             'fish_compatible_cells':len({(r['map'],r['side']) for r in candidates if r['fish_draft_compatible']}),
             'exact_host_cells':len({(r['map'],r['side']) for r in candidates if r['exact_host_draft']}),
             'fetched':fetched,'status':'provisional; requires target-pin live validation'}
    (a.work/'summary.json').write_text(json.dumps(summary,indent=1)+'\n')
    print(json.dumps(summary))


if __name__=='__main__':
    main()
