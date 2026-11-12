"""The Health-goal change (item 1) on the hoard losses, against Fish's recorded inputs.

    py research/ideas-2026-11-12/v118-fish-b/cf_php.py [--run php]
replays/v118b/runs/<run>/<key>/direct.repl26a is v118's masked source + the change (mktrace.py --lines d, then the
shop.cc edit), played against the puppet of that live game. Until the first purchase that differs the game is the
live game; after it Fish's side replays its recorded inputs without reacting, so this asks one thing only: with the
health the change buys, does the Prism survive the attack sequence that killed it live? An upper bound on the real effect.
Per game: the live hoard death (round, bag), the Prism's max health the round before in both games, the round the
re-run leaves the live game, and whether the re-run's Prism died within 5 rounds of the live death."""
import argparse, gzip, json, os, subprocess, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
ap = argparse.ArgumentParser(); ap.add_argument("--run", default="php"); a = ap.parse_args()
RUN = REPO / "replays/v118b/runs" / a.run
OUT = REPO / "replays/v118b" / f"cf-{a.run}-analysis"
keys = sorted(p.name for p in RUN.iterdir() if (p / "direct.repl26a").exists())
subprocess.run(["node", str(REPO / "tools/replay/extract.mjs"), *[str(RUN / k / "direct.repl26a") for k in keys], "--out", str(OUT), "--threads", "16"],
               cwd=REPO, stdout=subprocess.DEVNULL)
idx = {Path(r["source"]).parent.name: r["dir"] for r in json.load(open(OUT / "index.json"))["games"]}
F = {f["key"]: f for f in json.load(open(REPO / "replays/v118b/feat.json"))}
CL = {r["key"]: r for r in json.load(open(REPO / "replays/v118b/classes.json"))}


def load(root, d):
    meta = json.load(open(root / d / "meta.json")); rounds = json.load(gzip.open(root / d / "rounds.json.gz"))
    ev = [json.loads(l) for l in gzip.open(root / d / "events.jsonl.gz", "rt")]
    return meta, rounds, ev


rows = []
for k in keys:
    f = F[k]; us = 0 if f["side"] == "a" else 1
    big = [d for d in f["deaths"] if d["us"] and d["v"] == "Prism" and d["bag"] >= 100 and not d["camp"]]
    if not big or k not in idx:
        continue
    d0 = min(big, key=lambda d: d["r"])
    pid = d0["vid"]
    lm, lr, le = load(REPO / "replays/v118b/analysis", f["dir"])
    cm, cr, ce = load(OUT, idx[k])
    li = next(i for i, c in enumerate(lm["champions"]) if c["id"] == pid)
    r = d0["r"]
    n = min(len(lr["round"]), len(cr["round"]))
    div = next((i + 1 for i in range(n) if lr["champions"][li]["maxHp"][i] != cr["champions"][li]["maxHp"][i]), None)
    i = min(r - 2, n - 1)
    hp_live = lr["champions"][li]["maxHp"][i]; hp_cf = cr["champions"][li]["maxHp"][i]
    died_cf = [e for e in ce if e["k"] == "death" and e["v"] == pid and abs(e["r"] - r) <= 5]
    any_big = [e for e in ce if e["k"] == "death" and e["v"] == pid and e["gems"] >= 100 and "by" in e]
    tt = json.load(open(RUN / k / "direct.json")).get("ladder_trusted_through")
    kstr = d0.get("by_str")
    rows.append({"key": k, "class": CL[k]["class"], "r": r, "bag": d0["bag"], "by": d0["by"], "by_str": kstr, "hp_live": round(hp_live), "hp_cf": round(hp_cf),
                 "first_hp_diff": div, "left_live_at": tt, "died_same": bool(died_cf), "any_big_death": bool(any_big), "cf_result": cm["result"]["winner"] == us,
                 "cf_rounds": cm["result"]["rounds"], "cf_gems": cm["result"]["gems"][us]})
json.dump(rows, open(REPO / f"replays/v118b/cf-{a.run}.json", "w"))
ch = [x for x in rows if x["hp_cf"] != x["hp_live"]]
print(f"{len(rows)} hoard losses with a Prism death re-run; the change altered the Prism's max health before the live death in {len(ch)}")
import statistics as st
if ch:
    print(f"  in those: max health the round before the live death, live median {st.median(x['hp_live'] for x in ch):.0f} -> re-run {st.median(x['hp_cf'] for x in ch):.0f}; "
          f"hits for the killer live {st.median(x['hp_live'] / x['by_str'] for x in ch if x['by_str']):.1f} -> {st.median(x['hp_cf'] / x['by_str'] for x in ch if x['by_str']):.1f}")
    print(f"  the Prism died within 5 rounds of the live death in the re-run: {sum(x['died_same'] for x in ch)} of {len(ch)}; lost a 100+ bag to a champion at any time: {sum(x['any_big_death'] for x in ch)}; re-run won by us: {sum(x['cf_result'] for x in ch)}")
same = [x for x in rows if x["hp_cf"] == x["hp_live"]]
print(f"  unchanged health at the death in {len(same)}: died the same {sum(x['died_same'] for x in same)}")
for x in sorted(rows, key=lambda x: -x["bag"])[:70]:
    print(f"   {x['key']} {x['class'][:6]} live death r{x['r']} bag {x['bag']} by {x['by'][:6]} (Str {x['by_str']}): max hp {x['hp_live']} -> {x['hp_cf']}; first hp difference r{x['first_hp_diff']}; "
          f"re-run: {'died the same' if x['died_same'] else 'SURVIVED the live death'}{', lost a 100+ bag later' if (x['any_big_death'] and not x['died_same']) else ''}; ended r{x['cf_rounds']} with {x['cf_gems']} {'WON' if x['cf_result'] else ''}")
