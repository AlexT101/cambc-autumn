"""Seal the prospectively approved pair without building bots or playing games."""
import json
import shutil
import subprocess
import sys
from pathlib import Path
from run import R,D,T,BASE,CAND,sha,write,source


def main():
    assert not any((D/arm/'first-heavy-start.json').exists() for arm in CAND), 'Never reseal started tests'
    shutil.copyfile(T/'protocol.json',D/'protocol.json')
    files={p for p in T.iterdir() if p.is_file() and p.suffix in ('.py','.md','.json')}
    files.update(D/x for x in ('protocol.json','port-proof.json','smoke-maps.json','chanM.patch','bagfF.patch'))
    files.add(Path('/home/ubuntu/tmp-offload/localq/reservations/exploit504/seeds.json'))
    files.add(Path('/home/ubuntu/tmp-offload/localq/reservations/exploit504-mirror/seeds.json'))
    files.add(R/'research/ideas-2026-11-10/opporder/patch_prio_ro.py')
    for d in ('tools/mapgen','research/ideas-2026-11-09/freshgate-tools','research/ideas-2026-11-08/diverse-tools','research/ideas-2026-11-08/spar-tools','research/ideas-2026-11-09/oppfidelity-tools'):
        files.update(p for p in (R/d).iterdir() if p.is_file() and p.suffix in ('.py','.sh','.mjs','.h'))
    files.update(R/p for p in ('copybot','tools/ab.py','tools/run_batched.py','tools/cambc_env.py','tools/cpu_slots.py','tools/pooled.py','sdk/cpp/cambc.h','sdk/cpp/cambc_local.h','tools/draftlab/features.mjs','tools/replay/drafts.mjs','tools/replay/engine.mjs','tools/replay/engine/version.json','tools/fastengine/runner/fastrunner','tools/fastengine/runner/target/release/libfastrunner.so','research/ideas-2026-11-08/spar-tools/hashes.json','research/ideas-2026-11-09/fishfid/patch_fish2.py','research/ideas-2026-11-09/fishfid/patch_prio.py','research/ideas-2026-11-09/fishfid/patch_coh.py'))
    files.update((R/'tools/replay/engine').glob('*.wasm'))
    files.update((R/'maps').glob('*.map26a'))
    files.update(Path('/home/ubuntu/tmp-offload/diverse/fresh')/x for x in ('feat-ladder.jsonl','feat-v2.jsonl'))
    files.add(Path('/home/ubuntu/tmp-offload/handoff/gate/mapclass.json'))
    engine=subprocess.check_output(['cambc','--version'],text=True).strip();assert engine.endswith('5.0.1')
    files.add(Path(shutil.which('cambc')).resolve())
    m={'jobs':['exploit504-'+arm+'-200k' for arm in CAND], 'argv':{arm:[sys.executable,str(T/'run.py'),arm] for arm in CAND},
       'files':{str(p):sha(p) for p in sorted(files)},'sources':{bot:source(bot) for bot in (BASE,*CAND.values(),'variants/oc-tune3')},
       'smoke_maps':{x['path']:x['sha256'] for x in json.loads((D/'smoke-maps.json').read_text())},'engine':engine,
       'body_generation':'Intermediate per-map spar header reads old live drafts, but the sealed feature-model patch replaces that table before use. Each generated body source is sealed before games and must match on reference reuse.'}
    write(D/'manifest.json',m)
    print(json.dumps({'manifest_sha256':sha(D/'manifest.json'),'files':len(files),'argv':m['argv']}))

if __name__=='__main__':main()
