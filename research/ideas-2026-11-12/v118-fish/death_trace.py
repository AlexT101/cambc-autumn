"""Every own death by a champion against the trace: what the victim's last turns decided.

    py research/ideas-2026-11-12/v118-fish/death_trace.py

Per death (trusted rounds only): the branch of the last turn and of the turn before the first hit, whether
want_home said yes on the last turn and for how many turns running, and the first want_home reason of that run.
Summed by phase, by result and by taxonomy class."""
import json, statistics as st, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tracelib as T  # noqa: E402

A = T.V / "analysis"


def main():
    deaths = [json.loads(l) for l in open(A / "deaths.jsonl")]
    cls = {}
    for l in open(A / "taxonomy.tsv").read().split("\n")[1:]:
        p = l.split("\t")
        if len(p) > 6:
            cls[p[0]] = p[6]
    ngames = Counter()
    for l in open(A / "games.jsonl"):
        g = json.loads(l)
        ngames[g["result"]] += 1
        ngames[(g["result"], cls[g["key"]])] += 1
    rows, skipped = [], 0
    cache = {}
    for d in deaths:
        if not d["us"] or d["kind"] != "death":
            continue
        tr = cache.get(d["key"]) or cache.setdefault(d["key"], T.load(d["key"]))
        if tr.trusted < d["r"] - 1:
            skipped += 1
            continue
        turns = []
        for r in range(max(1, d["r"] - 25), d["r"] + 1):
            t = tr.turn(r, d["vid"])
            if t and "TT" in t and t["TT"]["alive"]:
                turns.append((r, t))
        if not turns:
            skipped += 1
            continue
        run, reason = 0, 0
        for r, t in reversed(turns):
            codes = [w["code"] for w in t.get("WH", [])]
            if any(c > 0 for c in codes):
                run += 1
                reason = next(c for c in codes if c > 0)
            else:
                break
        hit = d.get("r_hit") or d["r"]
        before = next((t for r, t in reversed(turns) if r < hit), None)
        rows.append({**d, "last": turns[-1][1]["TT"]["branch"], "run": run, "reason": reason, "pre": before["TT"]["branch"] if before else "?",
                     "pre_home": bool(before) and any(w["code"] > 0 for w in before.get("WH", [])), "cls": cls[d["key"]],
                     "hp_last": turns[-1][1]["TT"]["hp"] / max(1, turns[-1][1]["TT"]["maxhp"])})
    print(f"{len(rows)} own deaths to champions traced to the death; {skipped} past the trusted rounds")

    def show(label, S, n):
        if not S:
            return
        last = Counter(r["last"] for r in S)
        pre = Counter(r["pre"] for r in S)
        runs = [r["run"] for r in S]
        reasons = Counter(T.WH_REASON[r["reason"]] for r in S if r["run"])
        print(f"  {label:34s} {len(S):5d} ({len(S) / max(1, n):5.2f}/game) | retreating on the last turn {100 * sum(r['run'] > 0 for r in S) / len(S):3.0f}%, run median {st.median(runs):.0f} "
              f"| wanted home before the first hit {100 * sum(r['pre_home'] for r in S) / len(S):3.0f}% | branch before the first hit: {' '.join(f'{k}:{v}' for k, v in pre.most_common(6))} "
              f"| reasons {dict(reasons.most_common(3))}")

    for lo, hi in ((1, 150), (151, 400), (401, 3000)):
        print(f"rounds {lo}-{hi}")
        for res in ("win", "loss"):
            show(f"our {res}s", [r for r in rows if lo <= r["r"] <= hi and r["result"] == res], ngames[res])
    print("losses by class")
    for c in ("hoard-killed", "hoard-camp", "unbanked", "overrun", "outfarmed"):
        show(c, [r for r in rows if r["result"] == "loss" and r["cls"] == c], ngames[("loss", c)])
    print("by victim, losses")
    for v, _ in Counter(r["victim"] for r in rows if r["result"] == "loss").most_common(8):
        show(v, [r for r in rows if r["result"] == "loss" and r["victim"] == v], ngames["loss"])
    json.dump(rows, open(A / "death_trace.json", "w"))


if __name__ == "__main__":
    main()
