"""Gold weight: farm prices gold at `x` times the body's per_gold. Real Fish takes the same captures and gems as the
body by r200 but ~25% more gold a share (Marcella 76 vs 53, Vendetta 76 vs 66, Vesper 133 vs 115): its camp choice
prices worth as 3 gems + gold (FISH_MODEL 7.2).
Usage: patch_gold.py BOT_DIR X"""
import sys, pathlib
p = pathlib.Path(sys.argv[1]) / 'src/economy/shop.cc'; x = float(sys.argv[2]); s = p.read_text()
old = '        kept.per_gold = params::gold_price_scale * share * kept.next.saved'
assert s.count(old) == 1
p.write_text(s.replace(old, f'        kept.per_gold = params::gold_price_scale * {x}f * share * kept.next.saved'))
