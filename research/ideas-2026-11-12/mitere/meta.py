"""Loader for Mite match rows pulled from big-arm's capture.db (tools/pull_rows_remote.sh -> raw/all.tsv.gz)."""
import gzip, json, os
MITE = 'ee83f5e5-bcad-4923-86b4-b79ea6083d2e'
US = 'stellar best girl'
CH = ["Ryth", "Vesper", "Vendetta", "C&I", "Stellar", "Prism", "Marcella", "Willow", "Ren", "Varg", "Tavi", "HoR"]
COLS = "match_id,created_at,kind,map,group_id,position,team_a,team_b,name_a,name_b,result_a,picks_a,picks_b,engine,rank_a,rank_b,rating_a,rating_b,replay,map_id".split(',')
RAW = os.path.expanduser('~/tmp-offload/mitere/raw/all.tsv.gz')
# behaviour-change times seen by the scheduler's hourly opp-check (UTC); 11-11 04:00 is the priority re-encoding
CHANGES = ['2026-11-11T04:00', '2026-11-11T07:05', '2026-11-11T10:58', '2026-11-11T12:53', '2026-11-11T20:02',
           '2026-11-11T21:02', '2026-11-11T22:10', '2026-11-11T23:09', '2026-11-12T03:08', '2026-11-12T03:32',
           '2026-11-12T04:21', '2026-11-12T07:06']
def epoch(t):
    return sum(t >= c for c in CHANGES)
def rows():
    out = {}
    for line in gzip.open(RAW, 'rt'):
        f = line.rstrip('\n').split('\t')
        if len(f) != len(COLS): continue
        r = dict(zip(COLS, f))
        s = 'a' if r['team_a'] == MITE else 'b'
        o = 'b' if s == 'a' else 'a'
        try:
            r['m_picks'] = json.loads(r['picks_' + s]); r['op_picks'] = json.loads(r['picks_' + o])
        except Exception: continue
        if not r['m_picks'] or not r['op_picks']: continue
        r['m_side'] = s; r['opp'] = r['name_' + o]; r['opp_id'] = r['team_' + o]
        ra = r['result_a']
        r['m_win'] = (ra == 'win') == (s == 'a') if ra in ('win', 'loss') else None
        r['ep'] = epoch(r['created_at'])
        out[r['match_id']] = r
    return sorted(out.values(), key=lambda r: r['created_at'])
def names(p): return [CH[i] for i in p]
