"""Compare completed teacher ablations on exactly the same maps and sides."""
import collections
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def read(name):
    summary = json.loads((ROOT / 'replays/ab' / name / 'summary.json').read_text())
    assert summary['games'] == 10000 and not summary['errors']
    matches = json.loads((ROOT / summary['suites'][0]['batch'] / 'results.json').read_text())['matches']
    return summary, {(m['map'], tuple(m['order'])): int(m['winner'] == 0) for m in matches}


def main():
    _, base = read('astraeus-teacher-v1-10k')
    rows = []
    for suffix in ('fuel-control', 'capped-search', 'visibility-fix', 'stock-plan-v2', 'stock-crew', 'stock-shop', 'warm-caches', 'crew-local', 'stock-crew-exact', 'crew-index-fix'):
        name = f'astraeus-teacher-{suffix}-10k'
        if not (ROOT / 'replays/ab' / name / 'summary.json').exists():
            continue
        summary, games = read(name)
        assert games.keys() == base.keys()
        diffs = collections.defaultdict(list)
        for (path, order), win in games.items():
            diffs[path].append(win - base[path, order])
        paired = [statistics.mean(v) for v in diffs.values()]
        delta = statistics.mean(paired) * 100
        se = statistics.stdev(paired) / len(paired)**.5 * 100
        rows.append(dict(name=name, wins=summary['cand_wins'], win_pct=summary['cand_win_pct'],
                         ci95=summary['ci95'], fuel=summary['teacher_fuel'], teacher_oof=summary['oof']['cand'],
                         gains=sum(games[k] > base[k] for k in base), losses=sum(games[k] < base[k] for k in base),
                         delta_pp=round(delta, 3), paired_map_ci95=[round(delta - 1.96*se, 3), round(delta + 1.96*se, 3)]))
    (OUT / 'ablations.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
