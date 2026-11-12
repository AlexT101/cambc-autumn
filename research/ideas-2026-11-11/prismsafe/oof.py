"""Our bot's out-of-fuel turns in fgate runs: OOF turns and games, summed over both bodies and the given batches."""
import json, sys, glob
def oof(bot, batches, fuel):
    t = g = 0
    for b in batches:
        for o in ('Flp4', 'Mt3q'):
            for p in glob.glob(f'replays/ab/fbe501-{bot}-{o}-m2560b{b:03d}{fuel}/summary.json'):
                x = json.load(open(p))['oof']['cand']; t += x[0]; g += x[1]
    return t, g
if __name__ == '__main__':
    fuel = sys.argv[3] if len(sys.argv) > 3 else ''
    lo, hi = map(int, sys.argv[2].split('-'))
    for bot in sys.argv[1].split(','):
        print(bot, 'OOF turns, games:', oof(bot, range(lo, hi + 1), fuel))
