"""Per-turn fuel delta of bot B over bot A on the same games (bench.py game dirs, games that play
identically, by same_play.mjs): every turn of the side each game dir names (draft turns included),
paired turn by turn.
    python3 tools/antire/fuel_delta.py GAMES_A GAMES_B [MAP-SIDE ...]
Prints mean, p50, p99, max and min of B - A over all paired turns."""
import struct, sys, zipfile
from pathlib import Path

HEADER = 77


def turns(bundle, side):
    with zipfile.ZipFile(bundle) as z:
        data = z.read(f"team-{side}.fuel")
    return [struct.unpack_from("<Q", data, i)[0] for i in range(HEADER, len(data) - 7, 8)]


def main():
    a, b, *only = sys.argv[1:]
    deltas = []
    for d in sorted(Path(a).iterdir()):
        if only and d.name not in only:
            continue
        side = d.name.rsplit("-", 1)[1]
        fa, fb = next(d.glob("*.repl26a"), None), next((Path(b) / d.name).glob("*.repl26a"), None)
        if not fa or not fb:
            continue
        ta, tb = turns(fa, side), turns(fb, side)
        if len(ta) != len(tb):
            print(f"{d.name}: turn counts differ ({len(ta)} vs {len(tb)}), skipped")
            continue
        deltas += [y - x for x, y in zip(ta, tb)]
    deltas.sort()
    n = len(deltas)
    print(f"turns {n}: mean {sum(deltas) / n:+.1f}, p50 {deltas[n // 2]:+d}, p99 {deltas[int(n * 0.99)]:+d}, "
          f"max {deltas[-1]:+d}, min {deltas[0]:+d}")


main()
