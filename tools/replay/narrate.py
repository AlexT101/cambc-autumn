"""Turn-level narratives of replays for LLM analysts: per-game timelines, fight transcripts, map legends and
cross-game episode files. See README.md (Narratives) and the README.txt it writes into the output folder."""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analysis.data import ROOT, _norm, load_index  # noqa: E402

DEFAULT_OUT = ROOT / 'replays' / '.narrative'
_maps = {}


def label_of(source):
    p = Path(source)
    parent = p.parent.name
    m = re.search(r'-([0-9a-f]{8})$', parent)
    tag = m.group(1) if m else parent[-6:]
    return re.sub(r'[^A-Za-z0-9._-]+', '-', f'{tag}-{p.stem}')


def safe(s):
    return re.sub(r'[^A-Za-z0-9._-]+', '-', s).strip('-')


def _mapinfo(h):
    from analysis.data import load_map
    from narrative.mapinfo import MapInfo
    if h not in _maps:
        _maps[h] = MapInfo(load_map(h).raw)
    return _maps[h]


def work(row, out, force):
    from narrative import episodes
    from narrative.report import VERSION, Narrator
    out = Path(out)
    d = row['dir']
    teams = row['teams']
    label = label_of(row['source'])
    base = f'{safe(teams[0])}_vs_{safe(teams[1])}__{label}'
    cache = out / 'cache' / f'{d}-{label}.json'
    if not force and cache.exists():
        c = json.loads(cache.read_text(encoding='utf-8'))
        if c.get('v') == VERSION and (out / 'games' / f'{base}.txt').exists():
            return c
    t0 = time.time()
    M = _mapinfo(row['mapHash'])
    n = Narrator(d, M, teams, label)
    v = n.v
    legend = out / 'legends' / f'{safe(n.map_name)}-{row["mapHash"][:8]}.txt'
    if not legend.exists():
        tmp = legend.with_suffix(f'.{os.getpid()}.tmp')
        tmp.write_text('\n'.join(M.legend(n.map_name)) + '\n', encoding='utf-8')
        try:
            os.replace(tmp, legend)
        except OSError:
            tmp.unlink(missing_ok=True)
    meta = v.meta
    res = meta['result']
    head = [f'GAME {label}  map {n.map_name}  rounds {res["rounds"]}  winner [{v.team_name[res["winner"]]}]  '
            f'tributed A {res["gems"][0]} B {res["gems"][1]}',
            f'source {row["source"]}  analysis {d}  legend ../legends/{legend.name}  fights {base}.fights.txt']
    for t in (0, 1):
        ids = [c for c in v.ids if v.team[c] == t]
        builds = []
        for c in ids:
            st = meta['champions'][v.g.idx[c]]
            builds.append(f'{v.type[c]} (k{st["kills"]} d{st["deaths"]})')
        rating = meta['teams'][t].get('ratingBefore')
        head.append(f'TEAM {"AB"[t]} [{v.team_name[t]}]{f" rating {rating:.0f}" if rating else ""} spawn {M.box(M.spawn[t])}: {", ".join(builds)}')
    ep = episodes.build(n)
    for c, k in sorted(n.tr.feints.items()):
        if k >= 20:
            head.append(f'HABIT {v.tn(c)}: started a recall and cancelled it at its next turn {k} times (omitted below)')
    body = n.timeline() + ['', check(n)]
    games = out / 'games'
    (games / f'{base}.txt').write_text('\n'.join(head + ['', 'TIMELINE'] + body) + '\n', encoding='utf-8')
    fl = []
    for f in n.fights:
        fl += n.transcript(f) + ['']
    (games / f'{base}.fights.txt').write_text('\n'.join(fl) + '\n', encoding='utf-8')
    c = {'v': VERSION, 'dir': d, 'label': label, 'file': f'games/{base}.txt', 'teams': teams, 'map': n.map_name,
         'winner': res['winner'], 'rounds': res['rounds'], 'gems': res['gems'], 'lines': len(body),
         'fights': len(n.fights), 'ms': round((time.time() - t0) * 1000), 'episodes': ep}
    cache.write_text(json.dumps(c), encoding='utf-8')
    return c


def check(n):
    """Self-check against the engine's end-of-game statistics."""
    v = n.v
    bad = []
    for c in v.ids:
        st = v.meta['champions'][v.g.idx[c]]
        deaths = sum(1 for r in v.deaths for e in v.deaths[r] if e['v'] == c)
        kills = sum(1 for r in v.deaths for e in v.deaths[r] if e.get('by') == c and 'linked' not in e)
        banked = sum(it.end['gems'] for it in n.tr.items[c] if it.kind == 'trib' and it.end)
        for name, got, want in (('deaths', deaths, st['deaths']), ('kills', kills, st['kills']),
                                ('tributed', banked, st['stats']['submittedGems'] if st.get('stats') else None)):
            if want is not None and got != want:
                bad.append(f'{v.tn(c)} {name} {got} vs engine {want}')
    return 'CHECK ' + ('ok: deaths, kills and tributed gems per champion match the engine' if not bad else 'MISMATCH ' + '; '.join(bad))


def rows_for(sources, index, team=None):
    out, seen = [], set()
    for src in sources:
        p = _norm(src)
        rows = [r for r in index if r['source'] == p or r['source'].startswith(p + '/')]
        if not rows:
            print(f'no extracted replays under {src}', file=sys.stderr)
        for r in rows:
            if not r['ok'] or r['dir'] in seen:
                continue
            if team and team not in r['teams']:
                continue
            seen.add(r['dir'])
            out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('sources', nargs='+', help='replay folders or .repl26a files (extracted first unless --no-extract)')
    ap.add_argument('--out', default=str(DEFAULT_OUT))
    ap.add_argument('--threads', type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument('--team', help='only games with this team')
    ap.add_argument('--no-extract', action='store_true')
    ap.add_argument('--force', action='store_true', help='rebuild cached games')
    a = ap.parse_args()
    out = Path(a.out)
    for sub in ('games', 'legends', 'episodes', 'cache'):
        (out / sub).mkdir(parents=True, exist_ok=True)
    if not a.no_extract:
        r = subprocess.run(['node', str(ROOT / 'tools' / 'replay' / 'extract.mjs'), *a.sources, '--threads', str(a.threads)],
                           cwd=ROOT)
        if r.returncode:
            print('extract.mjs reported failures; narrating the games that decoded', file=sys.stderr)
    rows = rows_for(a.sources, load_index(), a.team)
    t0 = time.time()
    results, failed = [], []
    with ProcessPoolExecutor(a.threads) as ex:
        futs = {ex.submit(work, r, str(out), a.force): r for r in rows}
        for i, fu in enumerate(as_completed(futs), 1):
            r = futs[fu]
            try:
                results.append(fu.result())
            except Exception as e:  # keep going: one odd replay should not stop a 2500-game run
                failed.append((r['source'], repr(e)))
            if i % 100 == 0:
                print(f'[{i}/{len(rows)}] {time.time() - t0:.0f} s', file=sys.stderr)
    results.sort(key=lambda c: c['file'])
    kinds = {}
    for c in results:
        for k, lines in c['episodes'].items():
            kinds.setdefault(k, []).extend(lines)
    for k, lines in kinds.items():
        (out / 'episodes' / f'{k}.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    idx = [f'{c["file"]}  {c["map"]}  [{c["teams"][0]}] vs [{c["teams"][1]}]  winner [{c["teams"][c["winner"]]}]  '
           f'r{c["rounds"]}  tributed {c["gems"][0]}-{c["gems"][1]}  {c["lines"]} lines  {c["fights"]} fights' for c in results]
    (out / 'index.txt').write_text('\n'.join(idx) + '\n', encoding='utf-8')
    from narrative.guide import GUIDE
    (out / 'README.txt').write_text(GUIDE, encoding='utf-8')
    print(f'{len(results)} games in {time.time() - t0:.0f} s -> {out}; episodes: '
          + ', '.join(f'{k} {len(v)}' for k, v in sorted(kinds.items())))
    for s, e in failed:
        print(f'FAILED {s}: {e}', file=sys.stderr)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
