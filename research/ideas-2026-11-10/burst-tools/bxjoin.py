"""Join the BX trace (the bot's burst belief at its turn end) with bl.py's truth rows for local batches.
Usage: bxjoin.py BATCH ANA OUT.pkl"""
import sys, os, zipfile, pickle, glob, json
sys.path.insert(0, os.path.dirname(__file__))
import bl
from multiprocessing import Pool
def one(m, B=None):
    B = os.environ['BATCH']
    mm = json.load(open(m)); base = os.path.basename(mm['source']).split('.')[0]
    us = 0 if base.endswith('-12') else 1
    g = {'dir': os.path.dirname(m), 'us': us, 'mid': base, 'win': mm['result']['winner'] == us}
    res = bl.analyse(g)
    z = zipfile.ZipFile(f'{B}/{base}.repl26a')
    txt = z.read('team-a.stdout' if us == 0 else 'team-b.stdout').decode(errors='replace')
    bx = {}
    for l in txt.split('\n'):
        if not l.startswith('BX '): continue
        f = l.split()
        try:
            r, h = int(f[1]), int(f[2])
            bx[(r, h)] = (int(f[3]), int(f[4]), int(f[5]), int(f[6]), int(f[7]), int(f[8]), int(f[9]), f[10], int(f[11]), int(f[12]), int(f[13]), int(f[14]), int(f[15]), int(f[16]), int(f[17]), int(f[18]), f[19:])
        except (ValueError, IndexError): pass
    res['bx'] = bx
    return res
if __name__ == '__main__':
  B, A, OUT = sys.argv[1:4]; os.environ["BATCH"] = B
  G = sorted(glob.glob(f'{A}/*/meta.json'))
  with Pool(12) as p: R = list(p.imap_unordered(one, G, chunksize=2))
  pickle.dump(R, open(OUT, 'wb')); print(len(R), 'games')
