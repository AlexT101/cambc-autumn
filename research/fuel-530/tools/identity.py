"""Compare bench replay hashes and fuel on identical turns only."""
import json,sys
from pathlib import Path
base=json.loads(Path(sys.argv[1]).read_text())
a={(g['map'],g['side']):g for g in base['games']}
rows=[]
for file in sys.argv[2:]:
 b=json.loads(Path(file).read_text());bg={(g['map'],g['side']):g for g in b['games'] if 'error' not in g}
 same=[k for k in a if k in bg and a[k]['replay']==bg[k]['replay']]
 totals=[0,0,0];savings=[0,0,0]
 for key in same:
  x,y=a[key],bg[key]
  assert len(x['play'])==len(y['play'])
  for v,w in zip(x['play'][x['bodies']:],y['play'][y['bodies']:]):
   for j,threshold in enumerate([0,95000,100000]):
    if v>=threshold: totals[j]+=1;savings[j]+=v-w
 rows.append(dict(file=file,identical=len(same),games=len(a),differ=[k for k in a if k not in same],
  turns=totals,saved_per_turn=[round(v/max(1,n),3) for v,n in zip(savings,totals)]))
print(json.dumps(rows,indent=2))
