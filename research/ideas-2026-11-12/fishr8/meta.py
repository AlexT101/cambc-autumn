"""Loader for Fish match rows pulled from big-arm's capture.db (pull_rows_remote.sh -> ~/tmp-offload/fishr8/rows.tsv.gz)."""
import gzip, json, os
FISH = '1890540d-1ffc-4847-adbf-d0d08772f268'
CH = ["Ryth", "Vesper", "Vendetta", "C&I", "Stellar", "Prism", "Marcella", "Willow", "Ren", "Varg", "Tavi", "HoR"]
COLS = "match_id,created_at,kind,map,group_id,position,team_a,team_b,name_a,name_b,result_a,picks_a,picks_b,engine,rank_a,rank_b,rating_a,rating_b,replay,map_id".split(',')
RAW = os.path.expanduser('~/tmp-offload/fishr8/rows.tsv.gz')
CHANGES = ['2026-11-12T10:00', '2026-11-12T11:50']   # set from drafts (see draft_epochs in README)
def epoch(t): return sum(t >= c for c in CHANGES)
def rows(raw=RAW):
    out = {}
    for line in gzip.open(raw, 'rt'):
        f = line.rstrip('\n').split('\t')
        if len(f) != len(COLS): continue
        r = dict(zip(COLS, f)); s = 'a' if r['team_a'] == FISH else 'b'; o = 'b' if s == 'a' else 'a'
        try: r['f_picks'] = json.loads(r['picks_' + s]); r['op_picks'] = json.loads(r['picks_' + o])
        except Exception: continue
        if not r['f_picks'] or not r['op_picks']: continue
        r['f_side'] = s; r['opp'] = r['name_' + o]; r['opp_id'] = r['team_' + o]
        ra = r['result_a']; r['f_win'] = (ra == 'win') == (s == 'a') if ra in ('win', 'loss') else None
        r['ep'] = epoch(r['created_at']); out[r['match_id']] = r
    return sorted(out.values(), key=lambda r: r['created_at'])
def names(p): return [CH[i] for i in p]
