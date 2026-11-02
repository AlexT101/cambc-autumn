"""Out-of-fuel turns of one bot across A/B batches, by round bucket, phase, decision branch and map; all and first-in-streak.

    py tools/fuel/census/batch_oof.py [--bot 1|2] replays/batch-A replays/batch-B ...

A turn is first-in-streak when the same champion's turn the round before did not run out (since CHANGES 217 a
streak's later `OOF r phase` lines name the last phase reached, not where fuel ran out). The branch is the turn's
`D` line (Branch in bot_parts.h).
"""
import argparse, collections, json, re, zipfile
from pathlib import Path


def bucket(r):
    return "1" if r == 1 else "2-10" if r <= 10 else "11-60" if r <= 60 else "61-300" if r <= 300 else "300+"


def mapclass(name):
    n = re.sub(r"-\d{6,}$", "", name)
    return re.sub(r"^(gen|mut)-", "", n)


def games(d, botno):
    for b in sorted(Path(d).glob("*.repl26a")):
        order = b.stem.rsplit("-", 1)[1]
        name = b.stem.split("-", 1)[1].rsplit("-", 1)[0]
        team = "a" if (order == "12") == (botno == 1) else "b"
        with zipfile.ZipFile(b) as z:
            out = z.read(f"team-{team}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
        yield b, name, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bot", type=int, default=1)
    ap.add_argument("--skip", default="shared-gems", help="skip maps whose name contains this ('' for none)")
    ap.add_argument("dirs", nargs="+")
    a = ap.parse_args()
    rows = []
    for d in a.dirs:
        for path, name, out in games(d, a.bot):
            if a.skip and a.skip in name:
                continue
            lines = out.splitlines()
            branch = {}
            for l in lines:
                if l.startswith("D ") and len(l.split()) > 3 and l.split()[1].isdigit() and l.split()[2].isdigit():
                    p = l.split()
                    branch[(int(p[1]), int(p[2]))] = p[3]
            oof = []
            for i, l in enumerate(lines):
                m = re.match(r"OOF (\d+) (.+)$", l)
                if not m or m[2].startswith("draft"):
                    continue
                champ = None
                for k in range(i + 1, min(i + 3, len(lines))):
                    s = re.match(r"SHORTCUT \d+ (\d+) out-of-fuel", lines[k])
                    if s:
                        champ = int(s[1])
                        break
                oof.append((int(m[1]), champ, m[2].strip()))
            keys = {(r, c) for r, c, _ in oof}
            for r, c, ph in oof:
                rows.append(dict(game=str(path), map=name, cls=mapclass(name), round=r, champ=c, phase=ph,
                                 first=(r - 1, c) not in keys, branch=branch.get((r, c), "?"), game_oof=len(oof)))
    first = [x for x in rows if x["first"]]
    print(f"OOF turns {len(rows)}, first-in-streak {len(first)}")

    def tab(title, key, rs, n=14):
        c = collections.Counter(key(x) for x in rs)
        print(f"  {title}: " + ", ".join(f"{k} {v} ({100 * v / max(1, len(rs)):.0f}%)" for k, v in c.most_common(n)))

    for t, rs in (("all", rows), ("first-in-streak", first)):
        print(f"\n=== {t}")
        tab("bucket", lambda x: bucket(x["round"]), rs)
        tab("phase", lambda x: x["phase"], rs)
        tab("branch", lambda x: x["branch"], rs)
        tab("map class", lambda x: x["cls"], rs, 20)
        tab("game OOF count", lambda x: "<10" if x["game_oof"] < 10 else "10-49" if x["game_oof"] < 50 else "50+", rs)
    print("\n=== first-in-streak, bucket x branch")
    c = collections.Counter((bucket(x["round"]), x["branch"]) for x in first)
    for b in ("1", "2-10", "11-60", "61-300", "300+"):
        print(" ", b, dict(sorted(((k[1], v) for k, v in c.items() if k[0] == b), key=lambda kv: -kv[1])))
    print("\n=== maps by first-in-streak OOF")
    c = collections.Counter(x["map"] for x in first)
    print(" ", ", ".join(f"{k} {v}" for k, v in c.most_common(25)))


if __name__ == "__main__":
    main()
