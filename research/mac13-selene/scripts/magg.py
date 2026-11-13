import os, sys, json
sys.path.insert(0, '/home/ubuntu/wt/mac13-selene/tools/replay')
os.environ['CAMBC_ANALYSIS'] = os.path.abspath(sys.argv[1])
from concurrent.futures import ProcessPoolExecutor
def one(d):
    try:
        from analysis import macro
        from analysis import Game
        g = Game(d); o = macro.extract(g)
        return [(int(g.winner == t), o['sides'][t]) for t in (0, 1)]
    except Exception as e:
        return None
def main():
    root = sys.argv[1]
    dirs = [x for x in os.listdir(root) if os.path.isdir(os.path.join(root, x)) and x != 'maps']
    rows = []
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(one, dirs, chunksize=4):
            if r: rows += r
    print(len(rows))
    keys = [k for k, v in rows[0][1].items() if isinstance(v, (int, float))]
    for k in keys:
        w = [s[k] for win, s in rows if win and isinstance(s.get(k), (int, float))]
        l = [s[k] for win, s in rows if not win and isinstance(s.get(k), (int, float))]
        if w and l: print(f'{k:16s} win {sum(w)/len(w):9.3f} lose {sum(l)/len(l):9.3f}')
    json.dump(rows, open('/tmp/selene/magg-' + os.path.basename(root.rstrip('/')) + '.json', 'w'))
if __name__ == '__main__': main()
