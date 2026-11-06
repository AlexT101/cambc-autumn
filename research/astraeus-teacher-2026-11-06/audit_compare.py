"""Compare teacher-vs-Astraeus runs paired by map and side, clustering both sides by map."""
import argparse
import collections
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]


def read(name):
    directory = ROOT / 'replays/ab' / name
    summary = json.loads((directory / 'summary.json').read_text())
    settings = json.loads((directory / 'teacher.json').read_text())
    assert summary['games'] == 20000 and not summary['errors'], name
    assert summary['teacher_fuel'] == 'unlimited' and summary['opponent_fuel'] == 100000
    assert summary['oof']['cand'][0] == 0, name
    games = {}
    for suite in summary['suites']:
        matches = json.loads((ROOT / suite['batch'] / 'results.json').read_text())['matches']
        for match in matches:
            key = (match['map'], tuple(match['order']))
            assert key not in games and match['winner'] in (0, 1)
            games[key] = int(match['winner'] == 0)
    assert len(games) == 20000
    return summary, settings, games


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline')
    parser.add_argument('candidate')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    baseline, bs, bg = read(args.baseline)
    candidate, cs, cg = read(args.candidate)
    assert bs['runner_sha256'] == cs['runner_sha256']
    assert bs['opponent'] == cs['opponent']
    assert bs['maps'] == cs['maps'] and bg.keys() == cg.keys()
    differences = collections.defaultdict(list)
    for key in bg:
        differences[key[0]].append(cg[key] - bg[key])
    assert all(len(values) == 2 for values in differences.values())
    paired = [statistics.mean(values) for values in differences.values()]
    delta = statistics.mean(paired) * 100
    se = statistics.stdev(paired) / len(paired)**0.5 * 100
    result = dict(baseline=args.baseline, candidate=args.candidate, games=20000,
                  baseline_wins=baseline['cand_wins'], candidate_wins=candidate['cand_wins'],
                  baseline_win_pct=100 * baseline['cand_wins'] / 20000,
                  candidate_win_pct=100 * candidate['cand_wins'] / 20000,
                  delta_pp=delta, paired_map_ci95=[delta - 1.96 * se, delta + 1.96 * se],
                  gained=sum(cg[key] > bg[key] for key in bg),
                  lost=sum(cg[key] < bg[key] for key in bg),
                  teacher_oof=candidate['oof']['cand'], opponent_oof=candidate['oof']['ref'])
    rendered = json.dumps(result, indent=2) + '\n'
    if args.out:
        args.out.write_text(rendered)
    print(rendered, end='')


if __name__ == '__main__':
    main()
