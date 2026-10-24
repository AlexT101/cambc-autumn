#!/usr/bin/env python3
"""Create a selective, hash-pinned provenance inventory and review-only stage list."""
from __future__ import annotations
import hashlib, json, os, pathlib, time

ROOT = pathlib.Path(__file__).resolve().parents[3]
BASE = pathlib.Path(__file__).resolve().parent
ALLOWED = {'.md','.json','.py','.mjs','.js','.sh','.patch','.apply','.cpp','.h','.txt','.csv','.tsv','.yaml','.yml','.sha256','.manifest','.exit'}
MAX_STAGE_BYTES = 1_000_000
STAMP = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
INV_PATH = BASE / f'PRESERVATION-INVENTORY-{STAMP}.json'
LIST_PATH = BASE / f'STAGING-CANDIDATES-{STAMP}.txt'


def sha(path: pathlib.Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def rel(p: pathlib.Path) -> str:
    return p.relative_to(ROOT).as_posix()

def excluded_reason(p: pathlib.Path, size: int) -> str | None:
    parts={x.lower() for x in p.relative_to(BASE).parts}
    name=p.name.lower()
    if any(any(key in x for key in ('auth','login','credential','cookie','token','secret')) for x in parts): return 'excluded-sensitive-or-auth-path'
    if 'raw' in parts: return 'local-raw-input-or-dump'
    if p.suffix.lower() in {'.repl26a','.wasm','.zip','.gz','.fuel','.debug','.stdout','.stderr','.log'}: return 'local-large-or-binary-run-artifact'
    if name.endswith('.statistics.json') or 'fullstats' in name: return 'local-full-match-statistics'
    if size > MAX_STAGE_BYTES: return 'local-large-file'
    if p.suffix.lower() not in ALLOWED: return 'local-unclassified-file'
    if p == INV_PATH or p == LIST_PATH: return 'snapshot-output-self-reference'
    if name.startswith('preservation-inventory-') or name.startswith('staging-candidates-'): return 'older-snapshot-superseded'
    return None

files=[]
for p in sorted(BASE.rglob('*')):
    if not p.is_file() or p in (INV_PATH,LIST_PATH): continue
    size=p.stat().st_size
    reason=excluded_reason(p,size)
    row={'path':rel(p),'bytes':size,'sha256':sha(p)}
    if reason is None:
        row['disposition']='staging-candidate'; files.append(row)
    else:
        row['disposition']='local-only'; row['reason']=reason
        # full content hashes allow local raw assets to be checked later without staging them.
        files.append(row)

candidates=[x for x in files if x['disposition']=='staging-candidate']
local=[x for x in files if x['disposition']=='local-only']
summary={}
for x in files:
    key=x.get('reason','staging-candidate')
    summary[key]=summary.get(key,0)+1
snapshot={
 'schema':'selective-provenance-inventory-v1',
 'created_utc':STAMP,
 'root':rel(BASE),
 'snapshot_scope':'As-of snapshot only; runtime support work may still be active.',
 'status':{
  'overall_intake':'pending further runtime support panels; this inventory does not claim global completion.',
  'newest18_support':'18 candidate-v33 output cells are pending root row review; all 18 outputs are absent.',
  'newest18_plan':'generalist-support-18-v1/PLAN.pending.json',
  'newest18_rows':'generalist-support-18-v1/ROWS.pending.tsv',
  'newest18_baseline_reuse':'generalist-support-18-v1/BASELINE-REUSE.json',
  'newest18_arms':{'support-P':{'new_cells_pending':6,'baseline_reused':6,'missing_baselines':['Gem Fields A','Fracture B']},'support-S':{'new_cells_pending':6,'baseline_reused':6,'missing_baselines':[]},'support-C':{'new_cells_pending':6,'baseline_reused':6,'missing_baselines':[]}},
  'known_open_panels':['newest18 generalist-support outputs pending root row review','support-P missing baseline refs for Gem Fields A and Fracture B'],
  'runtime_owner':'/root/contact_priority_lowcpu_runtime',
 },
 'stage_policy':{'candidates':len(candidates),'local_only':len(local),'counts':summary,'max_candidate_bytes':MAX_STAGE_BYTES,'raw_replays_wasm_zip_fullstats_and_logs':'local only; SHA-256 listed'},
 'files':files,
 'candidate_list':rel(LIST_PATH),
 'candidate_list_is_review_helper':'Its contents are not listed in its own hash inventory to avoid a self-referential checksum; stage after reviewing the explicit path list.',
}
INV_PATH.write_text(json.dumps(snapshot,indent=2)+'\n')
lines=[f'# Review-only staging candidates generated {STAMP}', '# Root should review this explicit list before staging.', '# Raw replays, WASM, ZIPs, full statistics, large logs, and raw dumps remain local; their hashes are in the preservation inventory.', '']
for x in candidates: lines.append(f"{x['path']}\t{x['bytes']}\t{x['sha256']}")
lines.append(f"{rel(INV_PATH)}\t{INV_PATH.stat().st_size if INV_PATH.exists() else 0}\tGENERATED-INVENTORY-SELF-PIN-OMITTED")
lines.append(f"{rel(LIST_PATH)}\t0\tGENERATED-LIST-SELF-PIN-OMITTED")
LIST_PATH.write_text('\n'.join(lines)+'\n')
print(f'{INV_PATH}\n{LIST_PATH}\nstaging candidates={len(candidates)} local-only={len(local)}')
