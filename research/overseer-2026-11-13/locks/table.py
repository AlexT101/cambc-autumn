"""Markdown table of the lock-policy A/Bs from split.py's JSON (python3 split.py ... --json splits.json)."""
import json, sys

RULES = {
    "overseer-nolock-100k": "never buy (chy-nolock)",
    "ov-lock-cancel": "cancels only, no pre-emptive locks",
    "ov-lock-preempt": "pre-emptive only, no cancels, not a hard stop",
    "ov-lock-win": "cancel only game-ending tributes, no pre-emptive",
    "ov-lock-nohard": "full policy, lock never a hard stop",
    "ov-lock-alt2": "buy only on <= 2 altars",
    "ov-lock-alt3": "buy only on <= 3 altars",
    "ov-lock-eopt1": "buy only when the enemy has <= 1 altar option",
    "ov-lock-alt2-else-cancel": "full on <= 2 altars, cancel-only elsewhere",
    "ov-lock-end500": "buy once enemy score >= 500",
    "ov-lock-end700": "buy once enemy score + largest seen bag >= 700",
    "ov-lock-contest": "full + on <= 3 altars also the enemy's side pre-emptively",
    "ov-lock-precontest": "pre-emptive only on contested (and guarded) altars",
    "ov-lock-rich": "buy once this body spent 300+ gold on shards",
    "ov-lock-bag20": "cancel only bags of 20+ (winning always), no pre-emptive",
    "ov-lock-cancel-nohard": "cancels only, not a hard stop",
    "ov-lock-win-nohard": "cancel only game-ending, not a hard stop",
    "ov-lock-safe": "full; non-winning cancels only where we can't be killed in tribute_window",
    "ov-lock-safe-cancel": "safe cancels only, no pre-emptive",
    "ov-lock-inert": "buy and carry, never place, not a hard stop",
}
d = json.load(open(sys.argv[1]))
f = lambda v: f"{v[0]:.1f}" if v else "-"
print("| variant | rule | win % (95% CI) | OOF turns cand / ref | altars 1 / 2 / 3-4 / 5+ | rounds <600 / 600-899 / 900-1499 / 1500+ |")
print("|---|---|---|---|---|---|")
for name, r in d.items():
    s = r["splits"]
    alt = " / ".join(f(s["altars"].get(k)) for k in ["1", "2", "3-4", "5+"])
    rd = " / ".join(f(s["rounds"].get(k)) for k in ["<600", "600-899", "900-1499", "1500+"])
    oof = f"{r['oof']['cand'][0]:,} / {r['oof']['ref'][0]:,}"
    print(f"| {name.replace('ov-lock-', '').replace('overseer-', '')} | {RULES.get(name, '')} | {r['win']:.1f} ({r['ci95'][0]:.1f}-{r['ci95'][1]:.1f}) | {oof} | {alt} | {rd} |")
