"""paired.py A B: per-map paired difference of CAND's score between replays/ab/A and replays/ab/B (same suites, same ref)."""
import collections, glob, math, os, re, sys

ROOT = '/home/ubuntu/cambc-autumn/.claude/worktrees/agent-a257b2d79d7ff4d76/replays/ab'
line = re.compile(r'\] (\S+\.map26a) A=(\d) B=(\d): (bot (\d) wins|draw)')


def scores(run):
    s = collections.defaultdict(list)
    for log in glob.glob(f'{ROOT}/{run}/fresh-*.log'):
        suite = os.path.basename(log)[:-4]
        for l in open(log):
            m = line.search(l)
            if m:
                s[(suite, m[1])].append(1.0 if m[5] == '1' else 0.0 if m[5] == '2' else 0.5)
    return {k: sum(v) / len(v) for k, v in s.items() if len(v) == 2}


a, b = scores(sys.argv[1]), scores(sys.argv[2])
keys = sorted(a.keys() & b.keys())
d = [a[k] - b[k] for k in keys]
n = len(d)
mean = sum(d) / n
sd = math.sqrt(sum((x - mean) ** 2 for x in d) / (n - 1))
se = sd / math.sqrt(n)
same = sum(1 for x in d if x == 0)
print(f'{sys.argv[1]} - {sys.argv[2]}: {n} maps, diff {100 * mean:+.2f} pts (95% CI {100 * (mean - 1.96 * se):+.2f} to '
      f'{100 * (mean + 1.96 * se):+.2f}), maps with equal score {same / n:.0%}')
