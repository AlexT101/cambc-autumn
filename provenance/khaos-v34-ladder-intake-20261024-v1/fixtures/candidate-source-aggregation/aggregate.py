#!/usr/bin/env python3
"""Aggregate native winners by explicit source identity, never by row order."""
from collections import Counter


def candidate_win_counts(rows, candidate_source):
    wins = Counter()
    for row in rows:
        a, b = row.get('A_source'), row.get('B_source')
        if not isinstance(a, str) or not isinstance(b, str) or not a or not b:
            raise ValueError('missing/invalid A_source or B_source')
        if a == b:
            raise ValueError('ambiguous duplicate source roles')
        if (a == candidate_source) == (b == candidate_source):
            raise ValueError('candidate source must occupy exactly one physical side')
        side = row.get('winner_side')
        if side not in ('A', 'B'):
            raise ValueError('winner_side must be A or B')
        candidate_side = 'A' if a == candidate_source else 'B'
        wins[candidate_side] += side == candidate_side
    return {'candidate_wins': sum(wins.values()), 'candidate_games': len(rows),
            'candidate_wins_by_candidate_side': {'A': wins['A'], 'B': wins['B']}}


def _self_test():
    def row(a, b, winner):
        return {'A_source': a, 'B_source': b, 'winner_side': winner}
    cases = [
        ([row('candidate', 'control', 'A'), row('control', 'candidate', 'A')], 1),
        ([row('candidate', 'control', 'B'), row('control', 'candidate', 'B')], 1),
        ([row('candidate', 'control', 'A'), row('control', 'candidate', 'B')], 2),
        ([row('candidate', 'control', 'B'), row('control', 'candidate', 'A')], 0),
    ]
    for rows, expected in cases:
        got = candidate_win_counts(rows, 'candidate')
        assert got['candidate_wins'] == expected, (rows, got, expected)
        assert got['candidate_games'] == 2
    for invalid in [
        [{'A_source': 'candidate', 'winner_side': 'A'}],
        [row('candidate', 'candidate', 'A')],
        [row('control', 'other', 'A')],
        [row('candidate', 'control', 'X')],
    ]:
        try:
            candidate_win_counts(invalid, 'candidate')
        except ValueError:
            continue
        raise AssertionError(f'accepted invalid row: {invalid}')
    print('PASS: swapped A/B outcome, win/loss, and source-role rejection cases')


if __name__ == '__main__':
    _self_test()
