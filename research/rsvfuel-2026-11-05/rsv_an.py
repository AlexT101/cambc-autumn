"""Parse RSV lines from batch dirs into a pickle of records: python rsv_an.py OUT.pkl BATCHDIR..."""
import sys, re, json, zipfile, pickle
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

F = ("banks opening cut k n floor lr wr se travel tiles zoned g best apr cen gstate gsteps near foes6 foes10 "
     "canmove canattack cancast area shared help chunks").split()
ACC = "travel approach guard route zone order send queue tiles step_route see_revealed strike_enemy attack_camp cast_at_camp reset_attack home_stands ahead travel_dash heal shield ward lock strike_after cast_approach".split()


def one(p):
    order = Path(p).stem.rsplit("-", 1)[1]
    names = json.loads((Path(p).parent / "results.json").read_text())["bots"]
    recs = []
    with zipfile.ZipFile(p) as z:
        for t in "ab":
            bot = Path(names[0 if (t == "a") == (order == "12") else 1]).name
            s = z.read(f"team-{t}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
            for line in s.splitlines():
                if not line.startswith("RSV "):
                    continue
                if line.count("|") != 3 or len(line.split("|")[0].split()) != 4 + len(F):
                    continue
                head, marks, acc, cuts = line.split("|")
                h = head.split()
                r = dict(round=int(h[1]), handle=int(h[2]), late=int(h[3]), map=Path(p).stem, bot=bot)
                vals = list(map(int, h[4:]))
                r.update(zip(F, vals))
                ms = []
                for m in marks.split():
                    ms.append((m[0], int(m[1:])))
                r["marks"] = ms
                a = acc.split()
                r["oofacc"] = int(a[-1])
                for name, x in zip(ACC, a[:-1]):
                    f, c = x.split("/")
                    r["acc_" + name] = int(f)
                    r["n_" + name] = int(c)
                r["cuts"] = [c for c in cuts.strip().split(",") if c and c != "-"]
                recs.append(r)
    return recs


if __name__ == "__main__":
    files = [str(f) for d in sys.argv[2:] for f in Path(d).glob("*.repl26a")]
    out = []
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(one, files, chunksize=8):
            out += r
    pickle.dump(out, open(sys.argv[1], "wb"))
    print(len(out), "records")
