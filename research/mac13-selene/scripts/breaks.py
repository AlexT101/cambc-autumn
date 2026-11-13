import os, sys, json
sys.path.insert(0, '/home/ubuntu/wt/mac13-selene/tools/replay')
os.environ['CAMBC_ANALYSIS'] = os.path.abspath(sys.argv[1])
from concurrent.futures import ProcessPoolExecutor
from collections import Counter
def one(d):
    try:
        from analysis import macro, Game
        g = Game(d); o = macro.extract(g); G=o['game']
        return (G['break'], G['cause'], G['win_parts'], G['whole'])
    except Exception as e:
        return None
def main():
    root = sys.argv[1]
    dirs = [x for x in os.listdir(root) if os.path.isdir(os.path.join(root, x)) and x != 'maps']
    rows=[]
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(one, dirs, chunksize=4):
            if r: rows.append(r)
    print(len(rows))
    b=[r[0] for r in rows if r[0] is not None]
    import statistics as st
    print('break round quartiles', st.quantiles(b, n=4))
    bins=Counter(min(x//100,10) for x in b); print(sorted(bins.items()))
    print('cause', Counter(r[1] for r in rows))
    for k in rows[0][3]: print('whole', k, st.mean(r[3][k] for r in rows))
    for k in rows[0][2]: print('window', k, st.mean(r[2][k] for r in rows))
if __name__ == '__main__': main()
