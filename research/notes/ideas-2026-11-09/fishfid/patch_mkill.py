"""Mt3k: Mite's kill flag at its 11-09 12:00 value. On a body already patched by patch_prio.py M, the kill band
(raw >= 2 * band_width) writes 21262 (real Mite: 21262 - 104k, k = co-committers) in place of 3099; protect stays 3095.
Usage: patch_mkill.py BOT_DIR"""
import sys, pathlib
p = pathlib.Path(sys.argv[1]) / 'src/model/turn_order.cc'; s = p.read_text()
old = 'return raw >= 2 * band_width ? 3099 : 3095;'
assert s.count(old) == 1, old
p.write_text(s.replace(old, 'return raw >= 2 * band_width ? 21262 : 3095;'))
