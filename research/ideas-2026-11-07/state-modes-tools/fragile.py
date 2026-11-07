"""Positions (every 50 rounds from 100) where our total gem lead >= 100: P(win) by spent-gold (item) lead and by
how much of the lead is carried. usage: fragile.py ANALYSIS_DIR SET"""
import sys
import numpy as np
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import power

def main():
    import os
    power.SET = sys.argv[2]
    dirs = [os.path.join(sys.argv[1], x) for x in os.listdir(sys.argv[1]) if os.path.exists(os.path.join(sys.argv[1], x, 'meta.json'))]
    with ProcessPoolExecutor(16) as p:
        games = [g for g in p.map(power.one, dirs, chunksize=4) if g and g['x']]
    print(f'## {sys.argv[2]}')
    for lo, hi in [(100, 200), (200, 10**9)]:
        for name, f in [('item lead < -150', lambda s: s[3] < -150), ('item lead -150..150', lambda s: -150 <= s[3] < 150), ('item lead >= 150', lambda s: s[3] >= 150),
                        ('mostly carried (trib < 1/3)', lambda s: s[1] < (s[1] + s[2]) / 3), ('mostly tributed', lambda s: s[1] >= (s[1] + s[2]) / 3)]:
            w, n, gs = 0.0, 0, 0
            for g in games:
                sel = [s for s in g['x'] if lo <= s[1] + s[2] < hi and f(s)]
                if sel:
                    w += g['win'] * len(sel); n += len(sel); gs += 1
            if n:
                print(f'  lead {lo}..{"" if hi > 10**8 else hi:5} {name:28} positions {n:5} (games {gs:4})  P(win) {100*w/n:5.1f}%')
main() if __name__ == '__main__' else None
