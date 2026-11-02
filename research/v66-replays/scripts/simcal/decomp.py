# Which sim inputs differ from what happened: per-fighter damage, hit rates, focus, heals, arrivals, outsiders.
# Engaged stand+chase sims (both sides dealt damage among participants within K rounds), ladder (r<=260) vs self-play (r<=260).
# usage: decomp.py [stand|chase|all] [notlost|all]
import sys, json, gzip
from collections import defaultdict
kind = sys.argv[1] if len(sys.argv) > 1 else 'all'; pred = sys.argv[2] if len(sys.argv) > 2 else 'notlost'
K = 5


def load(src):
    rs = [json.loads(l) for l in gzip.open(f'replays/v66-analysis/simcal/l2_{src}.jsonl.gz', 'rt')]
    rs = [x for x in rs if x['r'] <= 260 and (kind == 'all' or x['kind'] == kind) and (pred == 'all' or not x['lost'])]
    return [x for x in rs if sum(sum(f['a_part'][:K]) for f in x['us']) > 0 and sum(sum(f['a_part'][:K]) for f in x['them']) > 0]


def stats(rs):
    S = defaultdict(float)
    bytype = defaultdict(lambda: [0.0, 0.0, 0, 0])  # (side,type) -> pred sum, actual sum, rounds expected, rounds hit
    for x in rs:
        S['n'] += 1
        for side in ('us', 'them'):
            for f in x[side]:
                exp_rounds = [k for k in range(K) if k >= f['arr'] and (f['death'] is None or f['death'] > k)]
                hit = sum(1 for k in exp_rounds if f['a_hits'][k] > 0)
                hitany = sum(1 for k in range(K) if f['a_hits'][k] > 0)
                S[side + '_exp'] += len(exp_rounds); S[side + '_hit'] += hit; S[side + '_hitany'] += hitany
                S[side + '_pdmg'] += f['pd'] * len(exp_rounds)
                S[side + '_admg'] += sum(f['a_part'][:K]); S[side + '_aany'] += sum(f['a_any'][:K])
                S[side + '_heal'] += sum(f['healed'][:K]); S[side + '_camp'] += sum(f['camp'][:K])
                S[side + '_hp'] += f['hp']
                # damage per hitting round vs predicted per turn
                if hitany: S[side + '_perhit_a'] += sum(f['a_any'][:K]); S[side + '_perhit_p'] += f['pd'] * hitany
                b = bytype[(side, f['typ'])]
                b[0] += f['pd'] * len(exp_rounds); b[1] += sum(f['a_any'][:K]); b[2] += len(exp_rounds); b[3] += hit
                # arrivals: predicted arriving now but no hit in the first 2 rounds; predicted late but hit in round 0
                if f['arr'] == 0: S[side + '_arr0'] += 1; S[side + '_arr0_nohit2'] += f['a_hits'][0] == 0 and f['a_hits'][1] == 0
                else: S[side + '_late'] += 1; S[side + '_late_early'] += any(f['a_hits'][k] > 0 for k in range(min(K, f['arr'])))
        # focus: share of their damage on our participants that lands on the sim's first target
        tot = sum(sum(f['a_part'][:K]) for f in x['them'])
        tgt = next((f for f in x['us'] if f['h'] == x['sim_target']), None)
        took_t = sum(f2 for f2 in tgt['took'][:K]) if tgt else 0
        took_all = sum(sum(f['took'][:K]) for f in x['us'])
        S['them_focus_num'] += took_t; S['them_focus_den'] += took_all
        # our focus on their weakest at start
        w = min(x['them'], key=lambda f: f['hp'] + f['sh'])
        S['us_focus_num'] += sum(w['took'][:K]); S['us_focus_den'] += sum(sum(f['took'][:K]) for f in x['them'])
        S['extra'] += sum(sum(e['dmg'][:K]) for e in x['extra']); S['extra_n'] += len(x['extra']) > 0
        S['stuns'] += x['stuns_on_us']
        S['self_death10'] += x['self_death'] is not None and x['self_death'] <= 10
        S['us_died10'] += sum(f['death'] is not None and f['death'] <= 10 for f in x['us'])
        S['them_died10'] += sum(f['death'] is not None and f['death'] <= 10 for f in x['them'])
    return S, bytype


def show(name, S, bytype):
    n = S['n']
    print('\n## %s  engaged sims n=%d' % (name, n))
    for side in ('us', 'them'):
        print('  %-4s hit rate (rounds with a champion hit / rounds the sim has it hitting) %.2f; any-round hits/K %.2f; '
              'actual/pred dmg on participants %.2f, on anyone %.2f; dmg per hitting round / pred per turn %.2f' % (
                  side, S[side + '_hit'] / max(1, S[side + '_exp']), S[side + '_hitany'] / max(1, n * K) * 0 + S[side + '_hitany'] / max(1, S[side + '_exp']),
                  S[side + '_admg'] / S[side + '_pdmg'], S[side + '_aany'] / S[side + '_pdmg'], S[side + '_perhit_a'] / max(1, S[side + '_perhit_p'])))
        print('       heal received per sim %.1f /K rounds (hp %.0f); camp dmg %.1f; arrivals: arr=0 but no hit in 2 rounds %.2f; late but hit earlier %.2f' % (
            S[side + '_heal'] / n, S[side + '_hp'] / n, S[side + '_camp'] / n, S[side + '_arr0_nohit2'] / max(1, S[side + '_arr0']),
            S[side + '_late_early'] / max(1, S[side + '_late'])))
    print('  focus: their dmg on the sim target %.2f of our participants\' damage taken; ours on their weakest %.2f' % (
        S['them_focus_num'] / max(1, S['them_focus_den']), S['us_focus_num'] / max(1, S['us_focus_den'])))
    print('  outsiders: share of sims %.2f, dmg %.1f per sim over K (= %.2f of predicted their dmg); stuns on us per sim %.2f' % (
        S['extra_n'] / n, S['extra'] / n, S['extra'] / S['them_pdmg'], S['stuns'] / n))
    print('  deaths within 10: self %.3f; ours per sim %.3f; theirs per sim %.3f' % (S['self_death10'] / n, S['us_died10'] / n, S['them_died10'] / n))
    print('  by type: side type  pred/turn-of-expected  actual/pred  hit-rate  n_rounds')
    for (side, t), b in sorted(bytype.items()):
        if b[2] >= 40: print('     %-4s %-9s %6.1f %6.2f %6.2f %6d' % (side, t, b[0] / b[2], b[1] / max(1, b[0]), b[3] / b[2], b[2]))


if __name__ == '__main__':
    sp = load('selfplay'); ld = load('ladder')
    show('self-play', *stats(sp))
    show('ladder all', *stats(ld))
    for o in ('Fish', 'Mite', 'UoS', 'PBG'):
        show('ladder ' + o, *stats([x for x in ld if x['opp'] == o]))
