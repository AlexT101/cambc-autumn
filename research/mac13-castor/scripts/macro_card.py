"""One game's macro, both teams side by side: analysis/macro.py's metrics, a 50-round timeline of wealth and turn mix,
gem flow, and the break round with what happened after it.

    py tools/replay/macro_card.py GAME [GAME ...] [--analysis DIR]

GAME is a replay file or dir (resolved through index.json; run extract.mjs first) or an analysis dir name. --analysis
reads an extract.mjs --out dir instead of replays/.analysis."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
for i, a in enumerate(sys.argv):
    if a == '--analysis' and i + 1 < len(sys.argv):
        os.environ['CAMBC_ANALYSIS'] = sys.argv[i + 1]

import argparse  # noqa: E402

from analysis import Game, load_index, resolve  # noqa: E402
from analysis import macro  # noqa: E402
from analysis.util import fmt  # noqa: E402

SHOW = ['walk', 'walk_bag', 'camp', 'hold', 'tribute', 'fight', 'recall', 'wait_camp', 'idle', 'dead']


def card(d):
    g = Game(d)
    o = macro.extract(g)
    S, G = o['sides'], o['game']
    A, B = g.names
    w = g.winner
    out = [f'{d}  {g.map_name}  {A} (A) vs {B} (B)  winner {g.names[w]}  rounds {g.n_rounds}  tributed {g.final_gems[0]}-{g.final_gems[1]}',
           '  picks A: ' + ', '.join(g.name_of[c] for c in g.team_ids[0]) + ' | B: ' + ', '.join(g.name_of[c] for c in g.team_ids[1]), '']
    wd = max(len(k) for k in macro.METRICS)
    out.append(f'  {"metric":{wd}}  {"A":>8}  {"B":>8}')
    for k in macro.METRICS:
        out.append(f'  {k:{wd}}  {macro._fm(k, S[0][k]):>8}  {macro._fm(k, S[1][k]):>8}')
    out += ['', '  gems     ' + '  '.join(f'{k[2:]} {S[0][k]}/{S[1][k]}' for k in ('g_cap', 'g_kill', 'g_lost_champ', 'g_lost_camp', 'g_carried_end', 'g_tributed')), '']
    out.append('  rounds   wealth A-B (lead)    ' + ' '.join(f'{k[:6]:>6}' for k in SHOW) + '   (A over B, % of champion-rounds)')
    for row in G['timeline']:
        wa, wb = row['wealth']
        mix = []
        for k in SHOW:
            v = []
            for t in (0, 1):
                tot = sum(row['turns'][t].values())
                v.append(round(100 * row['turns'][t].get(k, 0) / tot) if tot else 0)
            mix.append(f'{v[0]:>2}/{v[1]:<2}'.rjust(6))
        mark = ' <- break' if G['break'] and row['r'] - 50 < G['break'] <= row['r'] else ''
        out.append(f'  {row["r"]:>6}   {wa:>5}-{wb:<5} ({wa - wb:+5d})   ' + ' '.join(mix) + mark)
    L = 1 - w
    out += ['', f'  break: r{G["break"]} (last round {g.names[L]} had at least {g.names[w]}\'s wealth); window r{G["window"][0]}-{G["window"][1]}: '
            f'cause {G["cause"]}, winner advantage ' + ', '.join(f'{k} {v:+d}' for k, v in G['win_parts'].items()) + f'; gap after {G["gap_after"]:+d}',
            '  whole game, winner advantage: ' + ', '.join(f'{k} {v:+d}' for k, v in G['whole'].items())]
    for t in (L, w):
        ds = G['deaths_win'][t]
        if ds:
            out.append(f'  {g.names[t]} deaths in the window: ' + '; '.join(f'r{x["r"]} {x["who"]} bag {x["bag"]} by {x["by"]}' for x in ds))
    det = o['detail']
    for t in (0, 1):
        ab = det[t]['absent']
        if ab:
            out.append(f'  {g.names[t]} absent from {det[t]["fights"].get("n", 0)} fights: ' + ', '.join(f'{k} {v}' for k, v in sorted(ab.items(), key=lambda kv: -kv[1])))
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('games', nargs='+')
    ap.add_argument('--analysis')
    args = ap.parse_args()
    index = load_index()
    dirs = []
    for x in args.games:
        dirs += resolve([x], index)
    for d in dirs:
        print(card(d))
        print()


if __name__ == '__main__':
    main()
