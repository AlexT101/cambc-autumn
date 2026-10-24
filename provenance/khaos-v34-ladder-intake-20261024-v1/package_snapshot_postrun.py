#!/usr/bin/env python3
"""Create post-support-18 selective intake inventory and compact staging review."""
import hashlib,json,pathlib,time,collections
ROOT=pathlib.Path(__file__).resolve().parents[2]
BASE=pathlib.Path(__file__).resolve().parent
ALLOWED={'.md','.json','.py','.mjs','.js','.sh','.patch','.apply','.cpp','.h','.txt','.csv','.tsv','.yaml','.yml','.sha256','.manifest','.exit'}
MAX=100_000
STAMP=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())
INV=BASE/f'PRESERVATION-INVENTORY-{STAMP}.json'; LIST=BASE/f'STAGING-CANDIDATES-{STAMP}.txt'; REVIEW=BASE/f'PRESERVATION-REVIEW-{STAMP}.md'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def reason(p,size):
 parts={x.lower() for x in p.relative_to(BASE).parts}; name=p.name.lower()
 if any(any(k in x for k in ('auth','login','credential','cookie','token','secret')) for x in parts):return 'excluded-sensitive-or-auth-path'
 if 'raw' in parts:return 'local-raw-input-or-dump'
 if name == 'original-source-inputs.json':return 'local-raw-source-timeline'
 if any(x in parts for x in ('source-original','source-instrumented')):return 'local-reconstructible-source-copy'
 if name.endswith('.instrumented.cpp'):return 'local-reconstructible-instrumented-source-copy'
 if p.suffix.lower() in {'.repl26a','.wasm','.zip','.gz','.fuel','.debug','.stdout','.stderr','.log'}:return 'local-large-or-binary-run-artifact'
 if name.endswith('.statistics.json') or 'fullstats' in name:return 'local-full-match-statistics'
 if size>MAX:return 'local-large-file'
 if p.suffix.lower() not in ALLOWED:return 'local-unclassified-file'
 if name.startswith('preservation-inventory-') or name.startswith('staging-candidates-') or name.startswith('preservation-review-'):return 'older-snapshot-superseded'
 return None
files=[]
for p in sorted(BASE.rglob('*')):
 if not p.is_file() or p in {INV,LIST,REVIEW}:continue
 size=p.stat().st_size; why=reason(p,size); r={'path':rel(p),'bytes':size,'sha256':sha(p),'disposition':'staging-candidate' if why is None else 'local-only'}
 if why:r['reason']=why
 files.append(r)
candidates=[x for x in files if x['disposition']=='staging-candidate']; local=[x for x in files if x['disposition']=='local-only']
# Aggregate all files (including private/raw) by top-level child folder and extension class.
def typ(path):
 n=pathlib.Path(path).name.lower()
 if n.endswith('.statistics.json'):return 'full-statistics-json'
 return pathlib.Path(n).suffix.lower() or '[no extension]'
def agg(rows,keyfn):
 d=collections.defaultdict(lambda:[0,0])
 for r in rows:
  k=keyfn(r);d[k][0]+=1;d[k][1]+=r['bytes']
 return {k:{'files':v[0],'bytes':v[1]} for k,v in sorted(d.items())}
summary={'schema':'selective-provenance-inventory-v2','created_utc':STAMP,'root':rel(BASE),'snapshot_scope':'Post-run inventory as-of this timestamp; overall intake remains active.','status':{'overall_intake':'pending runtime-owned newer work; this is not global completion','generalist_support_18':'complete; 18 games saved, 0 failed, 0 errors; arm native audits and RESULT reports present','generalist_support_18_plan':'generalist-support-18-v1/PLAN.pending.json (historical original plan)','generalist_support_18_result':'generalist-support-18-v1/RESULT.json','baseline_reuse':'all 18 baseline references present, including support-P Gem Fields A and Fracture B','known_pending':'new edge-economy screen plan is prepared but not run; root review required','runtime_owner':'/root/contact_priority_lowcpu_runtime'},'stage_policy':{'staging_candidates':len(candidates),'staging_candidate_bytes':sum(x['bytes'] for x in candidates),'local_only':len(local),'local_only_bytes':sum(x['bytes'] for x in local),'max_candidate_bytes':MAX,'raw_replays_wasm_zip_fullstats_logs_raw_dumps':'local only; SHA-256 recorded'},'by_top_level_directory':agg(files,lambda r:pathlib.Path(r['path']).relative_to(rel(BASE)).parts[0] if len(pathlib.Path(r['path']).relative_to(rel(BASE)).parts)>1 else '[root]'),'by_file_type':agg(files,lambda r:typ(r['path'])),'files':files,'candidate_list':rel(LIST),'review_summary':rel(REVIEW)}
INV.write_text(json.dumps(summary,indent=2)+'\n')
with LIST.open('w') as f:
 f.write(f'# Review-only staging candidates generated {STAMP}\n# Root must inspect this complete selective list before staging.\n# Raw replays/WASM/ZIP/full statistics/logs/raw inputs remain local; hashes are recorded in inventory.\n')
 for x in candidates:f.write(f"{x['path']}\t{x['bytes']}\t{x['sha256']}\n")
 f.write(f'{rel(INV)}\t{INV.stat().st_size}\tGENERATED-INVENTORY-SELF-PIN-OMITTED\n')
 f.write(f'{rel(LIST)}\t0\tGENERATED-LIST-SELF-PIN-OMITTED\n')
 f.write(f'{rel(REVIEW)}\t0\tGENERATED-REVIEW-SELF-PIN-OMITTED\n')
# Candidate sensitive content/path flags, without printing any sensitive values.
name_flags=[x['path'] for x in candidates if any(t in x['path'].lower() for t in ('auth','login','credential','cookie','token','secret'))]
raw_flags=[x['path'] for x in candidates if pathlib.Path(x['path']).suffix.lower() in {'.repl26a','.wasm','.zip','.gz','.log'} or pathlib.Path(x['path']).name.lower().endswith('.statistics.json')]
review=['# Preservation staging review', '',f'Generated UTC: {STAMP}. This is a review aid only; no files were staged.', '',f"The current snapshot lists {len(candidates)} staging candidates ({sum(x['bytes'] for x in candidates):,} bytes) and {len(local)} local-only files ({sum(x['bytes'] for x in local):,} bytes). Raw replays, WASM, ZIPs, full match statistics, logs and raw inputs are excluded from staging and represented by hashes in the inventory.",'','## Coverage by top-level directory','', '| Directory | Files | Bytes |','|---|---:|---:|']
for k,v in summary['by_top_level_directory'].items():review.append(f"| `{k}` | {v['files']} | {v['bytes']:,} |")
review+=['','## Coverage by file type','','| Type | Files | Bytes |','|---|---:|---:|']
for k,v in summary['by_file_type'].items():review.append(f"| `{k}` | {v['files']} | {v['bytes']:,} |")
review+=['','## Review flags','',f'- Candidate paths containing sensitive/auth markers: {len(name_flags)}.']
review += [f'  - `{x}`' for x in name_flags]
review += [f'- Raw/binary/full-statistics candidate paths: {len(raw_flags)}. These should be zero; items belong in local-only.']
review += [f'  - `{x}`' for x in raw_flags]
review += ['', 'Raw and full-statistics items are explicitly local-only, with hashes only. Root should review the explicit candidate list before staging. The older 12:54 snapshot is retained as a historical pre-completion record.']
REVIEW.write_text('\n'.join(review)+'\n')
print(INV);print(LIST);print(REVIEW);print(f'candidates {len(candidates)} / {sum(x["bytes"] for x in candidates)} bytes; local-only {len(local)} / {sum(x["bytes"] for x in local)} bytes; sensitive candidate paths {len(name_flags)}; raw/full-stat candidate paths {len(raw_flags)}')
