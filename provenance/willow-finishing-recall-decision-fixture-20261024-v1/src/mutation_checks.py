#!/usr/bin/env python3
"""Verify selected fixture cases fail under test-only removal of their production guards."""
from pathlib import Path
import difflib, hashlib, json, subprocess, sys
root=Path(__file__).resolve().parents[1]
base=(root/'generated/fixture.cpp').read_text()
mutations={
 'scalar_init_removed':('if (payout_relaxed_pack) *payout_relaxed_pack = false;','/* guard removed for sensitivity check */'),
 'contextual_keep_removed':('if (!*home && payout_relaxed_pack) {','if (false) {'),
 'winning_topup_guard_removed':('&& capture_share(world, g) < gems_short(world)','&& capture_share(world, g) <= gems_short(world)'),
 'early_arrival_guard_removed':('if (world.round + my_channel_time() < world.camps[g].payout_round()\n                && capture_share(world, g) < gems_short(world)', 'if (true\n                && capture_share(world, g) < gems_short(world)'),
 'game_ender_precedence_removed':('if (game_ender(world)) {','if (game_ender(world) && false) {'),
}
out=root/'generated/mutations-v4'; out.mkdir(parents=True,exist_ok=True)
records=[]
for name,(old,new) in mutations.items():
 if base.count(old)!=1: raise SystemExit(f'{name}: expected one mutation anchor, found {base.count(old)}')
 mutant=base.replace(old,new,1)
 cpp=out/f'{name}.cpp'; cpp.write_text(mutant)
 patch=''.join(difflib.unified_diff(base.splitlines(True),mutant.splitlines(True),fromfile='production-extracted-fixture.cpp',tofile=f'{name}.cpp'))
 (root/'receipts'/'mutations-v4'/f'{name}.patch').write_text(patch)
 binary=out/name
 c=subprocess.run(['clang++','-std=c++20','-O0',str(cpp),'-o',str(binary)],capture_output=True,text=True)
 if c.returncode: raise SystemExit(f'{name}: mutation compile failed: {c.stderr}')
 r=subprocess.run([str(binary)],capture_output=True,text=True)
 if r.returncode==0: raise SystemExit(f'{name}: fixture failed to detect removed guard')
 (root/'logs'/f'mutation-v4-{name}.stdout.log').write_text(r.stdout)
 (root/'logs'/f'mutation-v4-{name}.stderr.log').write_text(r.stderr)
 records.append({'mutation':name,'mutation_patch':f'receipts/mutations-v4/{name}.patch','patch_sha256':hashlib.sha256(patch.encode()).hexdigest(),'mutated_source_sha256':hashlib.sha256(mutant.encode()).hexdigest(),'compile_exit':c.returncode,'test_exit':r.returncode,'detected':True,'first_failure':r.stderr.splitlines()[0] if r.stderr else None})
(root/'receipts/mutation-checks-v4.json').write_text(json.dumps({'schema':'production-branch-guard-mutation-checks/v1','base_generated_cpp_sha256':hashlib.sha256(base.encode()).hexdigest(),'checks':records},indent=2)+'\n')
print(f'PASS all {len(records)} guard-removal mutations detected')
for rec in records: print('PASS '+rec['mutation']+' -> '+str(rec['first_failure']))
