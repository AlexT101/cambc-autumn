import glob, json, os, pickle, sys
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chokes import pockets


def one(path):
    mp = json.load(open(path))
    g, pk = pockets(mp)
    return os.path.basename(path)[:-5], [(set(s), set(b)) for s, b in pk]


if __name__ == '__main__':
    ana = sys.argv[1]
    paths = glob.glob(os.path.join(ana, 'maps', '*.json'))
    with Pool(6) as p:
        out = dict(p.map(one, paths))
    pickle.dump(out, open(os.path.join(ana, 'pockets.pkl'), 'wb'))
    print(len(out))
