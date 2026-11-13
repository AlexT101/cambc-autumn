"""Combine the ladder seeding sim (P(top-4 order) per book setting) with the bracket sim (P(title) per order).

Usage: python3 combine.py SEEDSIM.json DROPS_DIR OUT_DIR
Writes OUT_DIR/seed_orders.json (per setting: P(order), P(seed 1), half partner shares) and
OUT_DIR/event_win.json (per drop rule: P(title | order) for every team; per setting: expected P(title) per team).
"""
import glob, json, os, sys

seed = json.load(open(sys.argv[1]))
drops = {}
for f in sorted(glob.glob(os.path.join(sys.argv[2], 'br_*.json'))):
    drops[os.path.basename(f)[3:-5]] = json.load(open(f))['event_win']
out = sys.argv[3]

json.dump({k: dict(normal=v['normal'], book=v['book'], window=v['interp'], book_live_from=v['book_at'],
                   us_seed1=v['us_seed1'], partner_in_our_half=v['partner'], mean_final_rating=v['mean_rating'],
                   fish_below_mite=v['fish_below_mite'], fish_below_cats=v['fish_below_cats'],
                   mite_below_cats=v['mite_below_cats'], orders=v['orders']) for k, v in seed.items()},
          open(os.path.join(out, 'seed_orders.json'), 'w'), indent=1)

combined = {}
for rule, ew in drops.items():
    for k, v in seed.items():
        teams = next(iter(ew.values())).keys()
        exp = {t: sum(p * ew[o][t] for o, p in v['orders'].items()) for t in teams}
        combined.setdefault(rule, {})[k] = exp
json.dump(dict(by_order={r: {o: {t: round(x, 4) for t, x in v.items()} for o, v in d.items()} for r, d in drops.items()},
               by_setting={r: {k: {t: round(x, 4) for t, x in v.items()} for k, v in d.items()} for r, d in combined.items()}),
          open(os.path.join(out, 'event_win.json'), 'w'))

rule = 'reversed_crossed_reset'
print(f'P(title) for us under {rule} (and no reset), by setting')
for k, v in seed.items():
    print(f"{k:50s} seed1 {v['us_seed1']:.3f}  title {combined[rule][k]['US']:.4f}  "
          f"(no reset {combined['reversed_crossed_noreset'][k]['US']:.4f})  Fish {combined[rule][k]['FISH']:.3f} Mite {combined[rule][k]['MITE']:.3f}")

# Compact summary for a page: base window (lock), book live from 12:00Z, default drop rule with and without reset.
def r4(x):
    return {k: r4(v) for k, v in x.items()} if isinstance(x, dict) else round(x, 4)


summary = dict(
    method=dict(
        rating='Elo, scale 400, K = 32 per 5-game group (score = wins/5); one group per team every 10 minutes',
        matchmaking='each top-4 pair meets in ~15% of ticks; otherwise an opponent ranked 5-11',
        window='now (00:40Z 11-13) to the 23:59Z lock; lock+6h gives the same answer',
        bracket='16-team double elimination, standard seeding (1-16, 8-9, 5-12, 4-13 | 6-11, 3-14, 7-10, 2-15), bo21',
        priors='per-event logit shift ~ t(4), bulk SD 0.32 for top-4 pairs and 0.40 vs the rest; series odds binomial',
        drop_rules='LB drops straight / reversed / half-swapped x straight / crossed: no effect (<= 0.2 points)'),
    title_by_order={rule: r4({o: v for o, v in drops[rule].items()}) for rule in ('reversed_crossed_reset', 'reversed_crossed_noreset')},
    settings={})
for k, v in seed.items():
    sc, interp, book_at, f, m = k.split('|')
    if interp != 'lock' or book_at != 'book 12:00Z':
        continue
    summary['settings'][f'{sc}|{f}|{m}'] = r4(dict(
        normal_rates=v['normal'], book_rates=v['book'], p_us_seed1=v['us_seed1'], partner_in_our_half=v['partner'],
        p_fish_below_cats=v['fish_below_cats'], p_mite_below_cats=v['mite_below_cats'],
        top_orders={o: p for o, p in v['orders'].items() if p >= 0.01},
        title_reset={t: combined['reversed_crossed_reset'][k][t] for t in ('US', 'FISH', 'MITE', 'CATS')},
        title_noreset={t: combined['reversed_crossed_noreset'][k][t] for t in ('US', 'FISH', 'MITE', 'CATS')}))
json.dump(summary, open(os.path.join(out, 'summary.json'), 'w'), indent=1)
