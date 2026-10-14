import argparse
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path, PurePosixPath

from . import audits, camps, draft, economy, fights, gap, params, sensitivity, tempo
from .data import ANALYSIS, Game, load_index, load_map, resolve
from .util import BOOT, CAVEAT, Report

REPORTS = {
    'tempo': ('Tempo and economy', tempo),
    'fights': ('Fights and risk', fights),
    'audits': ('Decision audits', audits),
    'draft': ('Draft', draft),
    'economy': ('Economy and camp handling', economy),
    'camps': ('Camp values', camps),
    'gap': ('Gap report', gap),
    'sensitivity': ('Threshold sensitivity', sensitivity),
}
EXTRACTORS = ['tempo', 'fights', 'audits', 'draft', 'economy']
DEFAULT_REPORTS = 'tempo,fights,audits,draft,economy,camps,gap'


def cluster_of(meta):
    grp = meta.get('group') or {}
    if grp.get('id'):
        return grp['id']
    return f'{PurePosixPath(meta["source"]).parent}:{meta["map"]["name"]}'


def extract_game(d, P=None, only=None):
    P = P or params.DEFAULTS
    g = Game(d)
    grp = g.meta.get('group') or {}
    out = {'info': {'dir': d, 'map': g.map_name, 'hash': g.map.hash, 'names': g.names, 'winner': g.winner, 'rounds': g.n_rounds,
                    'gems': g.final_gems, 'kind': g.kind, 'ratings': g.ratings, 'ids': g.team_ids, 'cluster': cluster_of(g.meta),
                    'created': grp.get('createdAt')}}
    for name in only or EXTRACTORS:
        out[name] = REPORTS[name][1].extract(g, P)
    return out


def _extract_args(args):
    return extract_game(*args)


def extract_all(dirs, threads, P=None, only=None):
    with ProcessPoolExecutor(max_workers=threads) as ex:
        return dict(zip(dirs, ex.map(_extract_args, [(d, P, only) for d in dirs], chunksize=2)))


class Ctx:
    def __init__(self, games, vs_games, data, focus, top_teams, labels, map_filter, P, threads):
        self.games = games
        self.vs_games = vs_games
        self.data = data
        self.focus = focus
        self.top_teams = top_teams
        self.labels = labels
        self.map_filter = map_filter
        self.params = P
        self.threads = threads

    def describe(self, vs=False):
        gs = self.vs_games if vs else self.games
        s = f'{self.labels[1 if vs else 0]} ({len(gs)} games, {len({g["cluster"] for g in gs})} clusters'
        if self.map_filter:
            s += f', map {self.map_filter}'
        if self.focus and not vs:
            s += f', focus {self.focus}'
        return s + ')'

    def focus_teams(self, gi):
        if not self.focus:
            return [0, 1]
        return [t for t in (0, 1) if gi['names'][t].lower() == self.focus.lower()]

    def map_of(self, name):
        for gi in self.games + self.vs_games:
            if gi['map'] == name:
                return load_map(gi['hash'])
        raise KeyError(name)

    def side_entries(self, report, include_vs=False, vs=False):
        out = []
        if not vs:
            for gi in self.games:
                for t in self.focus_teams(gi):
                    out.append((gi, t, self.data[gi['dir']][report]['sides'][t]))
        if include_vs or vs:
            seen = {gi['dir'] for gi in self.games}
            for gi in self.vs_games:
                if gi['dir'] in seen and not vs:
                    continue
                for t in (0, 1):
                    out.append((gi, t, self.data[gi['dir']][report]['sides'][t]))
        return out

    def side_metrics(self, vs=False):
        out = []
        gs = self.vs_games if vs else self.games
        for gi in gs:
            for t in ((0, 1) if vs else self.focus_teams(gi)):
                m = {'dir': gi['dir'], 'map': gi['map'], 'team': t, 'name': gi['names'][t], 'opp': gi['names'][1 - t], 'kind': gi['kind'],
                     'rating': gi['ratings'][t], 'cluster': gi['cluster']}
                for r in EXTRACTORS:
                    if r in self.data[gi['dir']]:
                        m.update(self.data[gi['dir']][r]['sides'][t])
                m['won'] = int(gi['winner'] == t)
                out.append(m)
        return out

    def side_items(self, key, report='tempo'):
        out = []
        for gi in self.games:
            ts = self.focus_teams(gi)
            out += [dict(x, cluster=gi['cluster']) for x in self.data[gi['dir']][report][key] if x['team'] in ts]
        return out

    def game_data(self, gi, report):
        return self.data[gi['dir']][report][report]

    def pairs(self, key, map_name=None):
        out = []
        for gi in self.games:
            if map_name and map_name != '(all)' and gi['map'] != map_name:
                continue
            w = gi['winner']
            out.append((self.metric(gi, w, key), self.metric(gi, 1 - w, key), gi['cluster']))
        return out

    def metric(self, gi, t, key):
        for r in EXTRACTORS:
            s = self.data[gi['dir']].get(r, {}).get('sides', [{}, {}])[t]
            if key in s:
                return s[key]
        return None


def top_teams(index_dirs, data, n=5, min_games=20):
    ratings = defaultdict(list)
    for d in index_dirs:
        gi = data[d]['info']
        for t in (0, 1):
            if gi['ratings'][t] is not None:
                ratings[gi['names'][t]].append(gi['ratings'][t])
    ranked = sorted((sum(v) / len(v), k) for k, v in ratings.items() if len(v) >= min_games)
    return {k for _, k in ranked[-n:]}


def main(argv=None):
    ap = argparse.ArgumentParser(description='Offline replay analysis: Markdown reports and CSVs from replays/.analysis/.')
    ap.add_argument('sources', nargs='*', default=['replays/ladder'], help='replay dirs/files (default replays/ladder)')
    ap.add_argument('--vs', nargs='+', default=[], help='comparison set (replay dirs/files)')
    ap.add_argument('--team', help='focus on this team\'s side of each game')
    ap.add_argument('--map', help='only games on this map')
    ap.add_argument('--since', help='only ladder groups created at or after this ISO time (e.g. 2026-10-13T22:00); local games are kept')
    ap.add_argument('--out', help='output dir (default replays/.analysis/reports/<timestamp>/)')
    ap.add_argument('--reports', default=DEFAULT_REPORTS, help='comma-separated subset of ' + ','.join(REPORTS) + f' (default {DEFAULT_REPORTS}; sensitivity reruns extraction ~10 times)')
    ap.add_argument('--threads', type=int, default=min(16, os.cpu_count() or 4))
    args = ap.parse_args(argv)
    t0 = time.time()
    reports = [r.strip() for r in args.reports.split(',') if r.strip()]
    for r in reports:
        if r not in REPORTS:
            ap.error(f'unknown report {r}')
    P = params.make()
    BOOT['B'], BOOT['seed'] = P['boot'], P['seed']
    index = load_index()
    prim = resolve(args.sources or ['replays/ladder'], index)
    vs = resolve(args.vs, index) if args.vs else []
    dirs = list(dict.fromkeys(prim + vs))
    needs = {'economy': {'economy'}, 'camps': set(), 'gap': set(EXTRACTORS)}
    only = [r for r in EXTRACTORS if any(r in needs.get(rep, set(EXTRACTORS) - {'economy'}) for rep in reports)]
    data = extract_all(dirs, args.threads, P, only)
    t1 = time.time()

    def keep(gi):
        if args.map and gi['map'] != args.map:
            return False
        if args.since and gi['created'] and gi['created'] < args.since:
            return False
        return True

    games = [data[d]['info'] for d in prim if keep(data[d]['info'])]
    vs_games = [data[d]['info'] for d in vs if keep(data[d]['info'])]
    focus = None
    if args.team:
        names = {n for gi in games for n in gi['names']}
        match = [n for n in names if n.lower() == args.team.lower()]
        if not match:
            raise SystemExit(f'team {args.team!r} not in the source games ({", ".join(sorted(names))})')
        focus = match[0]
        games = [gi for gi in games if focus in gi['names']]
    if not games:
        raise SystemExit('no games selected')
    labels = (' '.join(args.sources), ' '.join(args.vs))
    ctx = Ctx(games, vs_games, data, focus, top_teams(dirs, data), labels, args.map, P, args.threads)
    rec = defaultdict(lambda: [0, 0])
    for gi in {g['dir']: g for g in games + vs_games}.values():
        for t in (0, 1):
            rec[gi['names'][t]][0] += gi['winner'] == t
            rec[gi['names'][t]][1] += 1
    ctx.team_winrates = {k: v[0] / v[1] for k, v in rec.items()}
    out = Path(args.out or ANALYSIS / 'reports' / datetime.now().strftime('%Y%m%d-%H%M%S'))
    out.mkdir(parents=True, exist_ok=True)
    done = []
    for r in reports:
        if r == 'gap' and not (focus and vs_games):
            continue
        title, mod = REPORTS[r]
        rep = Report(r, title, out)
        mod.render(ctx, rep)
        rep.save()
        done.append(rep)
    t2 = time.time()
    lines = ['# Summary', '', f'Set: {ctx.describe()}' + (f'; comparison: {ctx.describe(vs=True)}' if vs_games else '') + '.', '',
             f'Extraction {t1 - t0:.1f} s ({len(dirs)} games, {args.threads} processes), reports {t2 - t1:.1f} s. '
             'Highlights are generated from the reports and need a human check; every report cites game dirs and rounds.', '',
             CAVEAT, '', 'Bots change version over time and replays carry no version information (group.json `submissionId`/`version` are null); '
             'use `--since` to restrict to recent ladder groups.', '']
    for rep in done:
        lines += [f'## {rep.title} ([{rep.name}.md]({rep.name}.md))', '']
        lines += [f'- {h}' for h in rep.highlights] or ['- (no highlights)']
        lines += ['', 'CSVs: ' + (', '.join(f'`{c}`' for c in rep.csvs) or '-'), '']
    (out / 'summary.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f'{len(games)} games ({len(vs_games)} comparison) -> {out} in {t2 - t0:.1f} s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
