"""Tables for measure.md from traced.py and replay_only.py pickles.

usage: python3 research/turn-order-2026-11-02/scripts/summarize.py TRACED.pkl OURS_REPLAY.pkl LADDER_REPLAY.pkl
"""
import pickle
import sys
from collections import Counter, defaultdict


def pct(a, b):
    return f'{100 * a / b:.1f}%' if b else '-'


def traced(path):
    res = [x for x in pickle.load(open(path, 'rb')) if 'error' not in x]
    print(f'## Traced games: {len(res)}, our champion-turns alive {sum(x["turns"] for x in res)}\n')
    # ---- metric 1
    bids = [b for x in res for b in x['bids']]
    print('### Bids by kind\n')
    print('| kind | bids | per game | assumed before | acted before | goal ok | ok if before | ok if not before |')
    print('|---|---|---|---|---|---|---|---|')
    by = defaultdict(list)
    for b in bids:
        by[b['kind']].append(b)
    for k in sorted(by, key=lambda k: -len(by[k])):
        L = by[k]
        ab = [b for b in L if b['assumed_before']]
        bf = [b for b in L if b['before']]
        nb = [b for b in L if b['before'] is False]
        print(f'| {k} | {len(L)} | {len(L) / len(res):.1f} | {pct(len(ab), len(L))} | {pct(len(bf), len(L))} | '
              f'{pct(sum(b["ok"] for b in L), len(L))} | {pct(sum(b["ok"] for b in bf), len(bf))} | '
              f'{pct(sum(b["ok"] for b in nb), len(nb))} |')
    print('\n### Failed "act before" (assumed before, acted after), by cause\n')
    fails = [b for b in bids if b['assumed_before'] and b['before'] is False]
    assumed = [b for b in bids if b['assumed_before']]
    print(f'{len(fails)} of {len(assumed)} bids that assumed acting first ({pct(len(fails), len(assumed))})\n')
    cause = Counter()
    cause_kind = defaultdict(Counter)
    detail = Counter()
    for b in fails:
        top = b['causes'][0][0]
        # one cause per bid: ally later > ally unseen > ally other > enemy > other
        kinds = [c[0] for c in b['causes']]
        for pref in ('ally_later', 'ally_unseen', 'ally_other', 'rank_other', 'enemy_reordered', 'other'):
            if pref in kinds:
                top = pref
                break
        cause[top] += 1
        cause_kind[b['kind']][top] += 1
        for c in b['causes']:
            if c[0] == top:
                detail[(top, c[1])] += 1
    print('| cause | bids | share | by bid kind |')
    print('|---|---|---|---|')
    for c, n in cause.most_common():
        kk = ', '.join(f'{k} {cause_kind[k][c]}' for k in cause_kind if cause_kind[k][c])
        print(f'| {c} | {n} | {pct(n, len(fails))} | {kk} |')
    print('\nCulprit detail (cause, culprit band or enemy sub-cause):', dict(detail.most_common(20)))
    ok_fail = sum(b['ok'] for b in fails)
    ok_held = [b for b in assumed if b['before']]
    print(f'\nGoal rate: assumed-first bids that did act first {pct(sum(b["ok"] for b in ok_held), len(ok_held))}, '
          f'that did not {pct(ok_fail, len(fails))}')
    # bid not assuming act-before (escape/heal/channel only)
    nab = [b for b in bids if b['assumed_before'] is False]
    print(f'Bids whose own assumption already had an enemy first: {len(nab)} ({Counter(b["kind"] for b in nab)})')
    # ---- TB
    tb = [t for x in res for t in x['tb']]
    print(f'\n### Safety turns_before_ours next-round term: {len(tb)} enemy-turn reads\n')
    print('| subset | reads | wrong | wrong: our rank (fix ours fixes it) | wrong: enemy rank | both |')
    print('|---|---|---|---|---|---|')
    for name, f in (('all within 8', lambda t: True), ('within 4', lambda t: t[3] <= 4),
                    ('within 4, enemy yet to act', lambda t: t[3] <= 4 and not t[10]),
                    ('within 4, enemy acted', lambda t: t[3] <= 4 and t[10])):
        S = [t for t in tb if f(t)]
        W = [t for t in S if t[4] != t[5]]
        ours = sum(1 for t in W if t[6] and not t[7])
        theirs = sum(1 for t in W if t[7] and not t[6])
        both = len(W) - ours - theirs
        print(f'| {name} | {len(S)} | {pct(len(W), len(S))} | {pct(ours, len(S))} | {pct(theirs, len(S))} | '
              f'{pct(both, len(S))} |')
    W = [t for t in tb if t[4] != t[5] and t[3] <= 4]
    print(f'\nWrong within 4: our own priority changed this round {pct(sum(t[8] for t in W), len(W))}, '
          f'the enemy changed {pct(sum(t[9] for t in W), len(W))}; predicted enemy first but it was after: '
          f'{pct(sum(1 for t in W if t[4] and not t[5]), len(W))}')
    print('\nEnemy hit us in r+1 before our turn (dist <= 4), by prediction / truth:')
    for pr in (False, True):
        for ac in (False, True):
            S = [t for t in tb if t[3] <= 4 and t[4] == pr and t[5] == ac]
            print(f'- predicted enemy first={pr}, actually first={ac}: {len(S)} reads, hit before our turn '
                  f'{pct(sum(t[11] for t in S), len(S))}')
    sup = [s for x in res for s in x['suppressed']]
    alw = [s for x in res for s in x['allowed']]
    print(f'\n### Kill bids the worst-case enemy rank suppresses: {len(sup)} ({len(sup) / len(res):.2f} a game) vs '
          f'{len(alw)} allowed\n')
    if sup:
        print(f'- suppressed: we acted first anyway {pct(sum(s["real_before"] for s in sup), len(sup))}, target died '
              f'next round {pct(sum(s["died"] for s in sup), len(sup))} (if we acted first '
              f'{pct(sum(s["died"] for s in sup if s["real_before"]), sum(s["real_before"] for s in sup))}, else '
              f'{pct(sum(s["died"] for s in sup if not s["real_before"]), sum(not s["real_before"] for s in sup))}); '
              f'target had acted already {pct(sum(s["acted"] for s in sup), len(sup))}; bid made instead '
              f'{dict(Counter(s["bid"] for s in sup))}')
        print(f'- allowed: we acted first {pct(sum(s["real_before"] for s in alw), len(alw))}, target died '
              f'{pct(sum(s["died"] for s in alw), len(alw))}')
    # ---- forks
    forks = [f for x in res for f in x['forks']]
    klt = sum(x['kl_turns'] for x in res)
    print(f'\n### Forks: {len(forks)} turns with 2+ killable enemies and no seat guarantee (of {klt} turns with an '
          f'enemy in our reach; {len(forks) / len(res):.2f} a game)\n')
    pg = [f for f in forks if f['pigeon']]
    print(f'- rank counting guarantees one acts after us: {len(pg)} ({len(pg) / len(res):.2f} a game)')
    for name, S in (('pigeon', pg), ('no guarantee', [f for f in forks if not f['pigeon']])):
        if S:
            print(f'- {name}: we acted before at least one {pct(sum(f["preceded"] > 0 for f in S), len(S))}, '
                  f'one of them died next round {pct(sum(f["killed"] > 0 for f in S), len(S))}, '
                  f'bid kinds {dict(Counter(f["bid"] for f in S))}, real slot == traced slot '
                  f'{pct(sum(f["real_slot"] == f["our_slot"] for f in S), len(S))}')
    # ---- metric 5
    pl = [p for x in res for p in x['pl']]
    legal = [p for p in pl if p['legal']]
    only = [o for p in pl for o in p['only']]
    turns_only = [p for p in pl if p['only']]
    print(f'\n### Ally blocking: {len(pl)} strike-search turns, {len(legal)} with a foe hittable from some tile\n')
    print(f'- turns where an ally held the only tile (walk or dash) from which we could hit a foe: {len(turns_only)} '
          f'({pct(len(turns_only), len(legal))} of turns with a hittable foe; {len(turns_only) / len(res):.2f} a game)')
    if only:
        print(f'- of those foes: ally vacated later the same round {pct(sum(o["vac_r"] for o in only), len(only))}, '
              f'by next round end {pct(sum(o["vac_n"] for o in only), len(only))}; holder found '
              f'{pct(sum(o["holder"] is not None for o in only), len(only))}; we hit someone that turn '
              f'{pct(sum(o["we_hit"] for o in only), len(only))}; the foe died that round or next '
              f'{pct(sum(o["died"] for o in only), len(only))}')
    mw = Counter()
    for x in res:
        mw.update(x['mw'])
    turns = sum(x['turns'] for x in res)
    print(f'- make_way: {dict(mw)} over {turns} champion-turns '
          f'({1000 * sum(mw.values()) / turns:.2f} per 1000 turns; y = declined, we carry more gems)')


def replay(path, label, per_team=False, min_games=20):
    res = [x for x in pickle.load(open(path, 'rb')) if 'error' not in x]
    print(f'\n## Replay-only ({label}): {len(res)} games\n')
    team = defaultdict(lambda: {'churn': Counter(), 'dbl': Counter(), 'conv': Counter(), 'games': 0, 'wins': 0,
                                'rows': []})
    for x in res:
        for t in (0, 1):
            name = x['teams'][t]
            T = team[name]
            T['games'] += 1
            T['wins'] += x['winner'] == t
            T['churn'].update(x['churn'][t])
            T['dbl'].update(x['dbl'][t])
            T['conv'].update(x['conv'][t])
            T['rows'] += x['conv_rows'][t]
    names = sorted(team, key=lambda n: -team[n]['games'])
    names = [n for n in names if team[n]['games'] >= min_games]
    print('### Priority churn (metric 2)\n')
    print('| team | games | win | champ-rounds changed | in contact changed | team order changes | '
          'never-change games | contact top (mixed rounds) | contact share | contact jump to top | quiet jump | '
          'in-contact rank moves next round (up) |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for n in names:
        T = team[n]
        k = T['churn']
        print(f'| {n} | {T["games"]} | {pct(T["wins"], T["games"])} | {pct(k["cr_changed"], k["cr"])} | '
              f'{pct(k["cr_contact_changed"], k["cr_contact"])} | {pct(k["order_changed"], k["rounds"])} | '
              f'{pct(k["never_changes"], T["games"])} | {pct(k["mixed_top_contact"], k["mixed"])} | '
              f'{pct(k["mixed_share"], k["mixed"])} | {pct(k["contact_jump_top"], k["contact_not_top"])} | '
              f'{pct(k["quiet_jump_top"], k["quiet_not_top"])} | {pct(k["contact_rank_moved"], k["contact_n"])} '
              f'({pct(k["contact_rank_up"], k["contact_n"])}) |')
    print('\n### Round-boundary doubles (metric 3)\n')
    print('| team | boundaries | one champion both seats | in contact | same champ, in contact | hit (either seat) | '
          'kill | same-champ hit / kill / hit both | control: in-contact single turn hit / kill |')
    print('|---|---|---|---|---|---|---|---|---|')
    for n in names:
        k = team[n]['dbl']
        print(f'| {n} | {k["boundaries"]} | {pct(k["same"], k["boundaries"])} | {pct(k["contact"], k["boundaries"])} | '
              f'{pct(k["contact_same"], k["contact"])} | {pct(k["contact_hit"], k["contact"])} | '
              f'{pct(k["contact_kill"], k["contact"])} | {pct(k["same_contact_hit"], k["contact_same"])} / '
              f'{pct(k["same_contact_kill"], k["contact_same"])} / {pct(k["same_contact_hit2"], k["contact_same"])} | '
              f'{pct(k["turn_contact_hit"], k["turn_contact"])} / {pct(k["turn_contact_kill"], k["turn_contact"])} |')
    print('\n### Kill conversion (metric 6): enemy under 25% health, not on its spawn, one of ours within 4\n')
    print('| hunting team | episodes | killed by us | escaped | healed | recalled | reached spawn | other death | '
          'enemy first in escapes | enemy first in kills |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    for n in names:
        k = team[n]['conv']
        tot = sum(k[o] for o in ('killed', 'escaped', 'healed', 'recalled', 'spawn', 'camp', 'other'))
        esc = k['escaped'] + k['healed'] + k['recalled'] + k['spawn']
        efe = k['e_first_escaped'] + k['e_first_healed'] + k['e_first_recalled'] + k['e_first_spawn']
        print(f'| {n} | {tot} | {pct(k["killed"], tot)} | {pct(k["escaped"], tot)} | {pct(k["healed"], tot)} | '
              f'{pct(k["recalled"], tot)} | {pct(k["spawn"], tot)} | {pct(k["camp"] + k["other"], tot)} | '
              f'{pct(efe, esc)} | {pct(k["e_first_killed"], k["killed"])} |')
    return team


if __name__ == '__main__':
    traced(sys.argv[1])
    replay(sys.argv[2], 'traced games, both sides')
    if len(sys.argv) > 3:
        replay(sys.argv[3], 'ladder, 2026-10-29..31', min_games=40)
