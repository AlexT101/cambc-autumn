# The sim's verdict as a race: who among the participants dies first within 15 rounds, by verdict and margin,
# ladder vs self-play (r<=260), engaged sims; plus how damage converts into deaths.
import sys, json, gzip
from collections import defaultdict
K = 5
kind = sys.argv[1] if len(sys.argv) > 1 else 'stand'


def load(src):
    rs = [json.loads(l) for l in gzip.open(f'replays/v66-analysis/simcal/l2_{src}.jsonl.gz', 'rt')]
    rs = [x for x in rs if x['r'] <= 260 and (kind == 'all' or x['kind'] == kind)]
    return [x for x in rs if sum(sum(f['a_part'][:K]) for f in x['us']) > 0 and sum(sum(f['a_part'][:K]) for f in x['them']) > 0]


def first(x, h=15):
    u = min([f['death'] for f in x['us'] if f['death'] is not None and f['death'] <= h] or [99])
    t = min([f['death'] for f in x['them'] if f['death'] is not None and f['death'] <= h] or [99])
    if u == t == 99: return 'none'
    return 'ours' if u < t else 'theirs' if t < u else 'same'


def report(name, rs):
    print('\n## %s (n=%d)' % (name, len(rs)))
    for lab, sel in (('verdict ok', [x for x in rs if not x['lost']]), ('verdict lost', [x for x in rs if x['lost']]),
                     ('ok, margin>=0.3', [x for x in rs if not x['lost'] and x['margin'] >= 0.3]),
                     ('ok, margin<0.3', [x for x in rs if not x['lost'] and x['margin'] < 0.3])):
        if not sel: continue
        c = defaultdict(int)
        for x in sel: c[first(x)] += 1
        n = len(sel)
        selfp = [f for x in sel for f in x['us'] if f['h'] == x['c']]
        hpshare = sum(x['hp'] / x['mh'] for x in sel) / n
        took_self = sum(sum(f['took'][:K]) for f in selfp) / n
        took_us = sum(sum(sum(f['took'][:K]) for f in x['us']) for x in sel) / n
        dealt_us = sum(sum(sum(f['took'][:K]) for f in x['them']) for x in sel) / n
        dk = (c['theirs'] + c['same']) / max(1, c['theirs'] + c['ours'] + c['same'])
        print('  %-16s n=%5d first death: ours %.3f theirs %.3f same %.3f none %.3f | their share of decided %.2f | self hp %.2f, '
              'took(self) %.0f, took(us) %.0f, dealt to them %.0f in %d rounds' % (
                  lab, n, c['ours'] / n, c['theirs'] / n, c['same'] / n, c['none'] / n, dk, hpshare, took_self, took_us, dealt_us, K))


if __name__ == '__main__':
    sp = load('selfplay'); ld = load('ladder')
    report('self-play', sp); report('ladder', ld)
    for o in ('Fish', 'Mite', 'UoS', 'PBG'): report('ladder ' + o, [x for x in ld if x['opp'] == o])
