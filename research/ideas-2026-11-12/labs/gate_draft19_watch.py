#!/usr/bin/env python3
"""Draft-failure watch for gate_draft19.sh: gate_draft19_watch.py PGID SINCE_EPOCH.

Every minute it reads the summaries of runs finished since SINCE by either bot and logs, per run, the games lost by
round 5, broken draft handoffs (DRAFT-UNFINISHED / PLAN-CHECK) and capped drafts (DRAFT-CAPPED) to watch.log.
It stops the gate (kills process group PGID, writes STOP) when the candidate has any broken handoff, or more capped
drafts than the base on the same run cell: a draft failure on unseen maps ends the gate rather than being averaged in.
"""
import json, os, signal, sys, time, glob
from pathlib import Path

R = Path('/home/ubuntu/cambc-autumn'); G = Path('/home/ubuntu/tmp-offload/labs/gate-draft19')
CAND, REF = 'lab-draft19-lab-emb6-c520-ps', 'lab-emb6-c520-ps'
pgid, since = int(sys.argv[1]), float(sys.argv[2])
seen = {}
log = open(G / 'watch.log', 'a')


def alive():
    try: os.killpg(pgid, 0); return True
    except OSError: return False


while True:
    for f in glob.glob(str(R / 'replays/ab/fb*/summary.json')):
        if os.path.getmtime(f) < since or f in seen: continue
        try: x = json.load(open(f))
        except (OSError, ValueError): continue
        bot = os.path.basename(x['cand']['path'].rstrip('/'))
        if bot not in (CAND, REF): continue
        n = os.path.basename(os.path.dirname(f)); c = 'cand'
        row = {'bot': bot, 'games': x['games'], 'errors': x['errors'], 'early': x['early_losses'][c],
               'handoff': (x.get('handoff_failures') or {}).get(c, 0), 'capped': (x.get('capped_drafts') or {}).get(c, 0)}
        seen[f] = row
        log.write(f'{time.strftime("%H:%M:%S")} {n} {json.dumps(row)}\n'); log.flush()
    bad = [f'{os.path.basename(os.path.dirname(f))} handoff {r["handoff"]}' for f, r in seen.items() if r['bot'] == CAND and r['handoff']]
    for f, r in seen.items():
        if r['bot'] != CAND: continue
        twin = f.replace(CAND, REF, 1)
        if twin in seen and r['capped'] > seen[twin]['capped']:
            bad.append(f'{os.path.basename(os.path.dirname(f))} capped {r["capped"]} vs base {seen[twin]["capped"]}')
    if bad:
        (G / 'STOP').write_text('\n'.join(bad) + '\n')
        try: os.killpg(pgid, signal.SIGTERM)
        except OSError: pass
        log.write(f'{time.strftime("%H:%M:%S")} STOPPED: {bad}\n'); log.flush()
        break
    if not alive(): break
    time.sleep(60)
