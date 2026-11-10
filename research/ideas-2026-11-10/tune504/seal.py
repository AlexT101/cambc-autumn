"""Seal proposed tune8 sources/tools/config, without builds or games."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

T = Path(__file__).resolve().parent
R = T.parents[2]
D = Path('/home/ubuntu/tmp-offload/localq/rounds/tune8')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def source(bot):
 d=R/'bots'/bot/'src'
 return {str(p.relative_to(d)):sha(p) for p in sorted(d.rglob('*')) if p.is_file()}

def main():
 assert not (D/'first-heavy-start.json').exists(), 'Never reseal a started run'
 p=json.loads((T/'protocol.json').read_text()); spec=json.loads((T/'parameters.json').read_text()); tr=p['training']
 cfg={k:tr[k] for k in ('maps_per_iter','pairs','weights','a','A','alpha','c','gamma','inflight','seed')}
 cfg.update(bot='bots/'+p['vehicle'],opps=[f'variants-spar-dvn{k}-{b}' for k in tr['opponent_noise'] for b in tr['opponent_bodies']],
            pool=[str(D/'selected')],params={x['name']:[*x['range'],'float'] for x in spec['parameters']})
 D.mkdir(exist_ok=True)
 write(D/'config.json',cfg)
 shutil.copyfile(T/'protocol.json',D/'protocol.json')
 paths=set(p for p in T.iterdir() if p.is_file() and p.suffix in ('.py','.json','.md'))
 paths.update([D/'config.json',D/'protocol.json'])
 for d in ['tools/tune','tools/mapgen','research/ideas-2026-11-09/freshgate-tools',
           'research/ideas-2026-11-08/diverse-tools','research/ideas-2026-11-08/spar-tools',
           'research/ideas-2026-11-09/oppfidelity-tools']:
  paths.update(x for x in (R/d).iterdir() if x.is_file() and x.suffix in ('.py','.sh','.mjs','.h'))
 paths.update(R/x for x in ['copybot','tools/ab.py','tools/run_batched.py','tools/cambc_env.py','tools/cpu_slots.py',
              'tools/pooled.py','tools/gate_compile_ahead.py','tools/fuel/bench.py','sdk/cpp/cambc.h','sdk/cpp/cambc_local.h',
              'research/ideas-2026-11-09/fishfid/patch_fish2.py','research/ideas-2026-11-09/fishfid/patch_prio.py',
              'research/ideas-2026-11-09/fishfid/patch_coh.py'])
 paths.update(Path('/home/ubuntu/tmp-offload/diverse/fresh')/x for x in ('feat-ladder.jsonl','feat-v2.jsonl'))
 paths.add(Path('/home/ubuntu/tmp-offload/handoff/gate/mapclass.json'))
 maps=list((R/'maps').glob('*.map26a'))+list(Path('/home/ubuntu/tmp-offload/diverse/fresh/pool').rglob('*.map26a'))
 # Standard identity suites are fixed inputs too.
 sys.path.insert(0,str(R/'tools/fuel'))
 import bench
 maps.extend(bench.map_file(m) for m in bench.MAP_SETS['wide'])
 maps=sorted(set(maps))
 assert all(x and x.is_file() for x in maps)
 # Training novelty checks use only gate/ladder map content, with bench maps conservatively included.
 m={'job':'tune8','argv':[str(Path(sys.executable)),str(T/'run.py')],
    'files':{str(x):sha(x) for x in sorted(paths)},
    'sources':{b:source(b) for b in (p['base'],p['vehicle'],'variants/oc-tune3')},
    'validation_maps':{str(x):sha(x) for x in maps},
    'engine':subprocess.check_output(['cambc','--version'],text=True).strip(),
    'source_generation_note':'Opponent spar per-map draft table is replaced by sealed feature-model body patches before use; generated source sealed before training.'}
 assert m['engine'].endswith('5.0.1')
 write(D/'manifest.json',m)
 print(json.dumps({'manifest_sha256':sha(D/'manifest.json'),'argv':m['argv'],'sealed_files':len(paths),'map_paths':len(maps)}))

if __name__=='__main__':main()
