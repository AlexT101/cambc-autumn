"""Which of the host version's own live wins does a new host build still play the same way? rbuild leaves the cells the
host version won live to the host, which is only safe while the host plays exactly as that version did; a fuel patch
or the book's own overhead changes play on some maps (real fuel). Each won game is replayed between BOT (no book entry
for the cell) and a puppet of the opponent's recorded turns; a game that matches the live one round for round is a win
the host repeats unaided. The others need a book entry (rbuild --host-repro OUT).

    py hostcheck.py --bot variants/rbook-525f-m --host-version 119 [--opp "Intercontinental Fish" --refset r8] --out CELLS
BOT must play like the live upload (masked if it was: priorities are part of the replay). Prints one line per cell
and writes the reproduced cells ("MAP SIDE OPP") to --out."""
import argparse, json
from pathlib import Path

import rbuild


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bot', required=True, help='bot dir under bots/')
    ap.add_argument('--host-version', type=int, required=True)
    ap.add_argument('--opp', default='Intercontinental Fish')
    ap.add_argument('--refset', default='r8')
    ap.add_argument('--work', default=str(Path.home() / 'tmp-offload/rbook/hostcheck'))
    ap.add_argument('--jobs', type=int, default=32)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    work = Path(a.work).expanduser()
    work.mkdir(parents=True, exist_ok=True)
    sel = argparse.Namespace(versions=str(a.host_version), host_version=None, extra=None, opp=None, refset=a.refset)
    tag = a.opp.split()[-1].lower()
    cs = rbuild.extract_all(rbuild.select(sel, a.opp, a.refset, tag), work, min(a.jobs, 16))
    bot = rbuild.ROOT / 'bots' / a.bot
    book = (bot / 'src/book/book_data.h').read_text() if (bot / 'src/book/book_data.h').exists() else ''
    booked = [c for c in cs if f"// {c['map']}-{c['side']}-v" in book]
    cs = [c for c in cs if c not in booked]
    print(f'{len(booked)} of these cells are in {a.bot}\'s book (not checked), {len(cs)} left to the host')
    rbuild.build(bot)
    res = dict(rbuild.verify_one(cs, a, work, bot, tag))
    same = [c for c in cs if not res[c['key']]]
    for c in cs:
        print(c['map'], c['side'], 'same' if not res[c['key']] else res[c['key']])
    Path(a.out).write_text(''.join(f"{c['map']} {c['side']} {tag}\n" for c in same))
    print(f"{a.bot}: {len(same)}/{len(cs)} of v{a.host_version}'s live wins against {a.opp} {a.refset} replayed exactly")


if __name__ == '__main__':
    main()
