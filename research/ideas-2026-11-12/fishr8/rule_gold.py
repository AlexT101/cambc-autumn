"""Rule layer: gold is worth FACTOR x more in the body's farm choices (shop.cc's per_gold, the one use of
gold_price_scale), so it takes the gold-rich groups (wolves, elk, golems) Fish r8 takes over gem clusters.
    py rule_gold.py BODY_DIR FACTOR"""
import sys, pathlib
p = pathlib.Path(sys.argv[1]) / 'src/economy/shop.cc'; k = float(sys.argv[2]); s = p.read_text()
old = 'kept.per_gold = params::gold_price_scale * share'
assert s.count(old) == 1, old
p.write_text(s.replace(old, f'kept.per_gold = params::gold_price_scale * {k}f /* fishr8 rule_gold */ * share')); print('rule_gold', k)
