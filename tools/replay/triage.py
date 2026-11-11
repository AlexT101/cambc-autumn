"""One game's turning points for one team: its most expensive loss episodes (analysis/losses.py) in round order, each
with what the champion was doing, how the wealth lead moved around it, the rule-checked alternative where the replay
shows one, and where the bot decides it.

    py tools/replay/triage.py GAME [GAME ...] --team NAME [--top 10] [--analysis DIR]

GAME is a replay file or dir (resolved through index.json; run extract.mjs first) or an analysis dir name. Without
--team the loser is triaged. --analysis reads an extract.mjs --out dir instead of replays/.analysis."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
for i, a in enumerate(sys.argv):
    if a == '--analysis' and i + 1 < len(sys.argv):
        os.environ['CAMBC_ANALYSIS'] = sys.argv[i + 1]

import argparse  # noqa: E402

from analysis import Game, load_index, resolve  # noqa: E402
from analysis import losses, macro  # noqa: E402
from analysis.data import ROOT  # noqa: E402
from analysis.util import fmt, pct  # noqa: E402

ABBR = {'walk': 'w', 'walk_bag': 'W', 'camp': 'c', 'hold': 'h', 'tribute': 'T', 'recall': 'R', 'teleport': 'P', 'fight': 'F',
        'wait_camp': '.', 'wait_altar': ':', 'idle': '_', 'spawn': 's', 'lost': 'x', 'dead': 'd', None: '?'}


def runs(classes):
    """Run-length string of a class list: 'W5 F2'."""
    out, prev, k = [], None, 0
    for c in classes:
        if c == prev:
            k += 1
            continue
        if prev is not None:
            out.append(f'{prev}{k}' if k > 1 else prev)
        prev, k = c, 1
    if prev is not None:
        out.append(f'{prev}{k}' if k > 1 else prev)
    return ' '.join(out)


def instead(e):
    """What the replay shows the side could have done, or ''."""
    t = e['tags']
    if e['kind'] == 'death':
        cf = e['cf']
        out = []
        if cf['altar']:
            a = cf['altar']
            out.append(f'tribute at r{a["r"]} (by an unlocked altar with {a["bag"]} gems, {a["dur"]} turn ends, no stun on it after, '
                       f'{a["enemies8"]} enemies within 8) would have banked them before the death')
        if cf['recall']:
            out.append(f'a recall from r{cf["recall"]["r"]} (killer in sight, no damage to it until r{e["r_hit"]}, closest enemy '
                       f'{cf["recall"]["closest"]}) would have landed first')
        if t['approach'] == 'walked toward them' and t['num'] != 'grouped, even+':
            out.append(f'it walked toward its killers while {t["num"]}' + (f' with {t["allies16"]} allies 9-16 away' if t['allies16'] else ''))
        elif t['allies16'] and t['num'] != 'grouped, even+':
            out.append(f'{t["allies16"]} allies were 9-16 away at the first hit')
        return '; '.join(out)
    if e['kind'] == 'camp_lost':
        sub = e['key'][1]
        if sub == 'stolen':
            return f'we did {pct(t["share"], 0)} of its damage; {e["key"][4]} ({t["near_doing"]})'
        if sub == 'invaded':
            return f'nearest of ours {t["near_dist"]} steps away ({t["near_doing"]}) while the enemy cleared and held it' if t.get('near_dist') is not None else 'all ours dead'
        return f'{e["key"][4]} ({t["near_doing"]})'
    if e['kind'] == 'stall':
        return f'{t["len"]} rounds still' + (f', {t["farmable"][1]} claimable or asleep {t["farmable"][0]} steps away' if t['farmable'] else '') \
            + (f', {t["escort"]} of them beside a tributing ally' if t['escort'] else '') \
            + (f', {t["standoff"]} of them with an enemy within 9' if t.get('standoff') else '')
    if e['kind'] == 'camp_death':
        return f'hp {pct(t["hp10"], 0)} ten rounds before' + (', also under champion fire' if t['third'] else '')
    return ''


def triage(d, team=None, top=10):
    g = Game(d)
    o = losses.extract(g)
    m = macro.extract(g)
    if team is None:
        t = 1 - g.winner
    else:
        match = [i for i, nm in enumerate(g.names) if nm.lower() == team.lower()]
        if not match:
            return f'{d}: team {team!r} not in {g.names}'
        t = match[0]
    u = 1 - t
    G = m['game']
    wealth, _, _ = macro._wealth(g)
    n = g.n_rounds

    def lead(r):
        i = max(0, min(n, r) - 1)
        return wealth[t][i] - wealth[u][i]

    src = g.meta.get('source', '')
    out = [f'{d}  {g.map_name}  {g.names[t]} ({"AB"[t]}) vs {g.names[u]}  {"WON" if g.winner == t else "LOST"} '
           f'{g.final_gems[t]}-{g.final_gems[u]} in {n} rounds',
           f'  picks: {", ".join(f"{g.name_of[c]}#{c}" for c in g.team_ids[t])} | vs {", ".join(f"{g.name_of[c]}#{c}" for c in g.team_ids[u])}',
           f'  replay: {src}   (cambc view {src}; turn-level: py tools/replay/narrate.py {src})',
           f'  earn rate {fmt(o["rate"], 3)} gems per alive champion-round (prices dead and still time)']
    lw = ' '.join(f'r{row["r"]}:{row["wealth"][t] - row["wealth"][u]:+d}' for row in G['timeline'][1::2])
    out.append(f'  wealth lead (tributed + carried, {g.names[t]} minus {g.names[u]}): {lw}')
    if g.winner != t:
        out.append(f'  break r{G["break"]} (last round level), next 100 rounds: cause {G["cause"]}, winner advantage '
                   + ', '.join(f'{k} {v:+d}' for k, v in G['win_parts'].items()))
    S = m['sides']
    keys = ['mt_work', 'mt_walk', 'mt_dead', 'mt_wait', 'control', 'isolated', 'fight_turnout', 'gem_latency']
    out.append('  macro: ' + ', '.join(f'{k} {macro._fm(k, S[t][k])}/{macro._fm(k, S[u][k])}' for k in keys) + '  (ours/theirs)')
    cls = macro.classify(g)
    mine = sorted((e for e in o['episodes'] if e['team'] == t), key=lambda e: -e['cost'])[:top]
    mine.sort(key=lambda e: e['r'])
    tot = sum(e['cost'] for e in o['episodes'] if e['team'] == t)
    tot_o = sum(e['cost'] for e in o['episodes'] if e['team'] == u)
    out += ['', f'  Turning points: {g.names[t]}\'s {len(mine)} most expensive episodes in round order (all episodes: {fmt(tot)} gems, '
                f'{g.names[u]}\'s {fmt(tot_o)}). lead = wealth lead 10 rounds before -> 30 after.']
    for e in mine:
        who = f'{g.name_of[e["cid"]]}#{e["cid"]}' if e.get('cid') is not None else e['tags'].get('group', '')
        r0 = e.get('r_hit', e['r'])
        out.append(f'  r{e["r"]:<5} {e["kind"]:10} {who:18} cost {fmt(e["cost"]):>6}  lead {lead(r0 - 10):+d} -> {lead(e["r"] + 30):+d}')
        out.append(f'         {losses._keystr(e["key"])}')
        if e.get('cid') is not None:
            prev = [cls[e['cid']][x] for x in range(max(1, r0 - 20), r0)]
            out.append(f'         before (20 rounds to r{r0}, {"/".join(f"{v}={k}" for k, v in ABBR.items() if k in set(prev))}): '
                       f'{runs([ABBR.get(c, "?") for c in prev])}')
        out.append(f'         {losses._tagstr(e)}')
        alt = instead(e)
        if alt:
            out.append(f'         instead: {alt}')
        out.append(f'         look at: {losses.code_for(losses.ckey(e))}')
    theirs = sorted((e for e in o['episodes'] if e['team'] == u), key=lambda e: -e['cost'])[:5]
    if theirs:
        out += ['', f'  {g.names[u]}\'s largest episodes (what {g.names[t]} won back):']
        for e in sorted(theirs, key=lambda e: e['r']):
            out.append(f'  r{e["r"]:<5} {losses._keystr(e["key"])}: {fmt(e["cost"])}')
    lf = sorted((f for f in o['fights'] if f['team'] == t and f['swing'] < 0), key=lambda f: f['swing'])[:3]
    if lf:
        out += ['', '  Worst fights (net swing):']
        for f in lf:
            out.append(f'  r{f["r"]}-{f["r1"]} swing {fmt(f["swing"])}: {f["present"]} v {f["opp_present"]} at the start, '
                       f'{"we" if f["init"] else "they"} started, kills {f["kills"]}-{f["deaths"]}, {f["half"]} half'
                       + (f', absent 9-16: {", ".join(f["absent_what"])}' if f['absent16'] else ''))
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('games', nargs='+')
    ap.add_argument('--team', help='the team to triage (default: the loser)')
    ap.add_argument('--top', type=int, default=10, help='episodes to list (default 10)')
    ap.add_argument('--analysis')
    args = ap.parse_args()
    index = load_index()
    dirs = []
    for x in args.games:
        dirs += resolve([x], index)
    for d in dirs:
        print(triage(d, args.team, args.top))
        print()


if __name__ == '__main__':
    main()
