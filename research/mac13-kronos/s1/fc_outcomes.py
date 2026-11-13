"""s1: match charybdis's farm choices (FC trace lines) to what they yielded.

    python research/mac13-kronos/s1/fc_outcomes.py BATCH_DIR [--out choices.jsonl] [--threads N]

BATCH_DIR must be extracted first (node tools/replay/extract.mjs BATCH_DIR). The traced side is the one
whose stdout holds FC lines. One output row per choice: a run of FC lines on one group, cut at each
payout of that group and ended by a switch to another group, the champion's death or the game's end.
"""
import argparse
import json
import re
import sys
import zipfile
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools' / 'replay'))
from analysis.data import ROOT as DATA_ROOT, Game, load_index  # noqa: E402

MELEE = {'Ryth', 'Vendetta', 'Marcella', 'Ren', 'Varg', 'Heart of Ruin', 'Issac'}
NUM = r'(-?[\d.]+|-?nan|-?inf)'
FC_RE = re.compile(
    r'FC (\d+) (\d+) (.) (.) g(-?\d+) h(\d+) st(\d+) v' + NUM + r' w' + NUM + r' R' + NUM + r' t' + NUM + r' c' + NUM + r' k' + NUM
    + r' H' + NUM + r' x' + NUM + r' p' + NUM + r' y' + NUM + r' pg' + NUM + r' bk' + NUM + r' wt' + NUM + r' vi(\d) s(-?\d+)'
    + r' a(-?\d+):(\d+):' + NUM + r' b(-?\d+):(\d+):' + NUM + r' at(-?\d+),(-?\d+) bag(\d+) hp' + NUM + r'/' + NUM
    + r' f(\d)(\d)(\d) cr(\d) tr(-?\d+) gap(-?\d+)')
FIELDS = ['round', 'id', 'why', 'mode', 'g', 'h', 'st', 'v', 'w', 'R', 't', 'c', 'k', 'H', 'x', 'p', 'y', 'pg', 'bk', 'wt', 'via',
          'steps', 'a_g', 'a_h', 'a_v', 'b_g', 'b_h', 'b_v', 'x0', 'y0', 'bag', 'hp', 'maxhp', 'opening', 'banking', 'repricing', 'crew',
          'trips', 'gap']
INTS = {'round', 'id', 'g', 'h', 'st', 'via', 'steps', 'a_g', 'a_h', 'b_g', 'b_h', 'x0', 'y0', 'bag', 'opening', 'banking',
        'repricing', 'crew', 'trips', 'gap'}


def parse_fc(text):
    out = []
    for line in text.splitlines():
        if not line.startswith('FC '):
            continue
        m = FC_RE.match(line)
        if not m:
            continue
        d = {}
        for k, v in zip(FIELDS, m.groups()):
            d[k] = int(v) if k in INTS else v if k in ('why', 'mode') else float(v)
        out.append(d)
    return out


def group_kind(types):
    s = set(types)
    if 'Monolith' in s:
        return 'monolith'
    if 'Golem' in s:
        return 'golem'
    if 'Elk' in s:
        return 'elk'
    if 'Wolf' in s:
        return 'wolf'
    return 'cluster'


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def game_choices(d):
    g = Game(d)
    src = ROOT / g.meta['source']
    try:
        z = zipfile.ZipFile(src)
    except Exception:
        return []
    names = z.namelist()
    team, fcs = None, []
    for t, f in ((0, 'team-a.stdout'), (1, 'team-b.stdout')):
        if f in names:
            lines = parse_fc(z.read(f).decode('utf-8', 'replace'))
            if lines:
                team, fcs = t, lines
    if team is None:
        return []
    m = g.map
    groups = {grp['id']: grp for grp in m.groups}
    ev = g.events
    captures = {}  # group -> [(round, team, {id: (gems, gold)})]
    clears = {}  # group -> [round]
    deaths = {}  # champion -> [(round, by_camp, gems)]
    holds = {}  # group -> [(round, team)]
    for e in ev:
        k = e['k']
        if k == 'capture':
            captures.setdefault(e['g'], []).append((e['r'], e['team'], {s[0]: (s[1], s[2]) for s in e['shares']}))
        elif k == 'group_clear':
            clears.setdefault(e['g'], []).append((e['r'], g.team_of.get(e.get('by'), 2)))
        elif k == 'death':
            deaths.setdefault(e['v'], []).append((e['r'], 'camp' in e, e.get('gems', 0)))
        elif k == 'capture_hold':
            holds.setdefault(e['g'], []).append((e['r'], e['team']))
    n_rounds = g.n_rounds
    rows = []
    by_champ = {}
    for f in fcs:
        by_champ.setdefault(f['id'], []).append(f)
    ally_spawn = m.spawn_center(team)
    enemy_spawn = m.spawn_center(1 - team)
    for cid, lines in by_champ.items():
        if cid not in g.idx:
            continue
        ctype = g.name_of[cid]
        rng = 1 if ctype in MELEE else 3
        ch = g.ch(cid)
        my_deaths = sorted(deaths.get(cid, []))
        # Choices: start at an FC line; a later line on the same group continues it unless a payout of
        # the group fell between them.
        i = 0
        while i < len(lines):
            first = lines[i]
            h = first['h']
            r0 = first['round']
            caps = [c for c in captures.get(h, []) if c[0] > r0]
            # The next line on another group.
            j = i + 1
            modes = first['mode']
            while j < len(lines) and lines[j]['h'] == h:
                j += 1
            switch_round = lines[j]['round'] if j < len(lines) else None
            death = next((dd for dd in my_deaths if dd[0] >= r0), None)
            end_round, outcome, share = None, None, (0, 0)
            cap = caps[0] if caps else None
            cands = []
            if cap is not None:
                cands.append((cap[0], 0, 'cap'))
            if death is not None:
                cands.append((death[0], 1, 'died'))
            if switch_round is not None:
                cands.append((switch_round, 2, 'switched'))
            cands.append((n_rounds + 1, 3, 'gameend'))
            # A payout at round R happens before the turns of R: it beats a death or switch in R.
            end_round, _, kind = min(cands)
            if kind == 'cap':
                ct, sh = cap[1], cap[2]
                if ct == team and cid in sh:
                    outcome, share = 'ours', sh[cid]
                elif ct == team:
                    outcome = 'ally'
                else:
                    outcome = 'enemy'
            else:
                outcome = kind
            # The lines of this choice: up to its end (a payout ends it; later lines on the group start the next).
            k2 = i + 1
            while k2 < j and (lines[k2]['round'] < end_round or (kind != 'cap' and lines[k2]['round'] == end_round)):
                modes += lines[k2]['mode']
                k2 += 1
            grp = groups.get(h)
            if grp is None:
                i = j
                continue
            tiles = [tuple(t) for t in grp['tiles']]
            # Realised parts: arrival (in attack range of a camp tile; on one for a cleared group), clear, hold.
            need = 0 if first['st'] == 1 else rng
            arrive = None
            for r in range(r0, min(end_round, n_rounds) + 1):
                idx = r - 1
                if idx >= len(ch['x']) or not ch['alive'][idx] or ch['x'][idx] is None:
                    continue
                p = (ch['x'][idx], ch['y'][idx])
                if min(cheb(p, t) for t in tiles) <= need:
                    arrive = r
                    break
            clear = next((c for c in clears.get(h, []) if r0 <= c[0] <= end_round), None)
            clear_r = clear[0] if clear else None
            # The group's first payout after the choice began, up to a hold's length past its end: a crew
            # member leaves a cleared group to its claimer, whose capture pays the team.
            post = next((c for c in captures.get(h, []) if r0 < c[0] <= end_round + 8), None)
            post_team = post[1] if post else 2
            post_gems = sum(v[0] for v in post[2].values()) if post else 0
            post_gold = sum(v[1] for v in post[2].values()) if post else 0
            post_mine = int(bool(post) and cid in post[2])
            on_tiles_end = None
            ei = min(end_round, n_rounds) - 2
            if 0 <= ei < len(ch['x']) and ch['alive'][ei] and ch['x'][ei] is not None:
                on_tiles_end = min(cheb((ch['x'][ei], ch['y'][ei]), t) for t in tiles)
            # A switch: how much of the abandoned walk went towards the new choice (Chebyshev, a bound).
            nxt_h, progress, moved = -1, None, None
            if kind == 'switched' and j < len(lines) and lines[j]['h'] in groups:
                nxt = lines[j]
                nxt_h = nxt['h']
                t2 = [tuple(t) for t in groups[nxt_h]['tiles']]
                p0, p1 = (first['x0'], first['y0']), (nxt['x0'], nxt['y0'])
                progress = min(cheb(p0, t) for t in t2) - min(cheb(p1, t) for t in t2)
                moved = cheb(p0, p1)
            gems_now = grp['gems']
            gold_now = grp['gold']
            side_d = cheb(grp['tiles'][0], ally_spawn) / max(1e-9, cheb(grp['tiles'][0], ally_spawn) + cheb(grp['tiles'][0], enemy_spawn))
            rows.append({
                'game': d, 'map': g.map_name, 'team': team, 'won': int(g.winner == team), 'cid': cid, 'ctype': ctype,
                'r0': r0, 'end': end_round, 'outcome': outcome, 'share_gems': share[0], 'share_gold': share[1],
                'kind': group_kind(grp['types']), 'types': ''.join(sorted(set(t[0] for t in grp['types']))),
                'g_gems': gems_now, 'g_gold': gold_now, 'side': grp['side'] if team == 0 else (1 - grp['side'] if grp['side'] >= 0 else -1),
                'side_frac': side_d, 'arrive': arrive, 'clear_r': clear_r, 'clear_team': (clear[1] if clear[1] == 2 else int(clear[1] != team)) if clear else -1,
                'post_r': post[0] if post else None, 'post_team': (post_team if post_team == 2 else int(post_team != team)), 'post_gems': post_gems,
                'post_gold': post_gold, 'post_mine': post_mine, 'next_h': nxt_h, 'progress': progress, 'moved': moved, 'end_dist': on_tiles_end, 'modes': modes,
                'n_lines': k2 - i, 'death_by_camp': int(death[1]) if kind == 'died' and death else 0,
                'death_gems': death[2] if kind == 'died' and death else 0,
                **{f'fc_{k}': v for k, v in first.items()},
            })
            # Next choice: the first line on this group after the payout, else the next group's.
            if kind == 'cap':
                i = k2 if k2 < j else j
            else:
                i = j
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('batch')
    ap.add_argument('--out', default=str(ROOT / 'replays' / 'mac13-kronos-s1-choices.jsonl'))
    ap.add_argument('--threads', type=int, default=16)
    a = ap.parse_args()
    batch = Path(a.batch).resolve().relative_to(DATA_ROOT).as_posix()
    dirs = sorted({r['dir'] for r in load_index() if r['source'].startswith(batch + '/') and r['ok']})
    print(f'{len(dirs)} games', file=sys.stderr)
    n = 0
    with Pool(a.threads) as pool, open(a.out, 'w') as f:
        for rows in pool.imap_unordered(game_choices, dirs, chunksize=4):
            for r in rows:
                f.write(json.dumps(r) + '\n')
                n += 1
    print(f'{n} choices -> {a.out}', file=sys.stderr)


if __name__ == '__main__':
    main()
