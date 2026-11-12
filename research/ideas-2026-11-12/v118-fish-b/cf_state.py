"""The Prism's body at the round of its live hoard death, live game against a re-run of a changed bot on Fish's recorded
inputs (replays/v118b/runs/<run>): max health, unspent gold, hits for the live killer's Strength.

    py research/ideas-2026-11-12/v118-fish-b/cf_state.py --run phs
The re-run stops being the live game at its first different action, and Fish's side then replays its inputs blindly: only
the Prism's own state (what it bought, by when) is read from it, not the fight's outcome."""
import argparse, gzip, json, subprocess, statistics as st
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
ap = argparse.ArgumentParser(); ap.add_argument("--run", required=True); a = ap.parse_args()
RUN = REPO / "replays/v118b/runs" / a.run
OUT = REPO / "replays/v118b" / f"cf-{a.run}-analysis"
keys = sorted(p.name for p in RUN.iterdir() if (p / "direct.repl26a").exists())
subprocess.run(["node", str(REPO / "tools/replay/extract.mjs"), *[str(RUN / k / "direct.repl26a") for k in keys], "--out", str(OUT), "--threads", "16"], cwd=REPO, stdout=subprocess.DEVNULL)
idx = {Path(r["source"]).parent.name: r["dir"] for r in json.load(open(OUT / "index.json"))["games"]}
F = {f["key"]: f for f in json.load(open(REPO / "replays/v118b/feat.json"))}
rows = []
for k in keys:
    f = F[k]
    big = [d for d in f["deaths"] if d["us"] and d["v"] == "Prism" and d["bag"] >= 100 and not d["camp"]]
    if not big or k not in idx: continue
    d0 = min(big, key=lambda d: d["r"]); pid = d0["vid"]; r = d0["r"]
    lm = json.load(open(REPO / "replays/v118b/analysis" / f["dir"] / "meta.json")); lr = json.load(gzip.open(REPO / "replays/v118b/analysis" / f["dir"] / "rounds.json.gz"))
    cr = json.load(gzip.open(OUT / idx[k] / "rounds.json.gz"))
    li = next(i for i, c in enumerate(lm["champions"]) if c["id"] == pid)
    n = min(len(lr["round"]), len(cr["round"])); i = min(r - 2, n - 1)
    L, C = lr["champions"][li], cr["champions"][li]
    rows.append({"key": k, "r": r, "kstr": d0.get("by_str") or 0, "hp_live": L["maxHp"][i], "hp_cf": C["maxHp"][i], "gold_live": L["gold"][i], "gold_cf": C["gold"][i],
                 "alive_cf": C["alive"][i], "short": i < r - 2, "gems_cf": C["gems"][i], "gems_live": L["gems"][i]})
ok = [x for x in rows if not x["short"] and x["kstr"] > 100]
print(f"{len(rows)} hoard deaths re-run; {len(ok)} with the re-run still going at the live death round and a killer of 100+ Strength")
m = lambda xs: round(st.median(xs))
print(f"  Prism max health the round before the live death: live median {m([x['hp_live'] for x in ok])}, re-run {m([x['hp_cf'] for x in ok])}")
print(f"  hits for the live killer's Strength: live median {st.median(x['hp_live'] / x['kstr'] for x in ok):.1f}, re-run {st.median(x['hp_cf'] / x['kstr'] for x in ok):.1f}; "
      f"6+ hits: live {sum(x['hp_live'] >= 6 * x['kstr'] for x in ok)}, re-run {sum(x['hp_cf'] >= 6 * x['kstr'] for x in ok)} of {len(ok)}")
print(f"  unspent gold then: live median {m([x['gold_live'] for x in ok])}, re-run {m([x['gold_cf'] for x in ok])}")
print(f"  carried gems then: live median {m([x['gems_live'] for x in ok])}, re-run {m([x['gems_cf'] for x in ok])}")
print(f"  health raised by 300+ in {sum(x['hp_cf'] - x['hp_live'] >= 300 for x in ok)}, lowered by 300+ in {sum(x['hp_live'] - x['hp_cf'] >= 300 for x in ok)}, same in {sum(x['hp_cf'] == x['hp_live'] for x in ok)}")
json.dump(rows, open(REPO / f"replays/v118b/cf-state-{a.run}.json", "w"))
