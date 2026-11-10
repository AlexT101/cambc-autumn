"""Emblem lab round 5: the structural edits, flags read by evehicle.py's hooks in shop.cc (FLAGS, FLAG_PATCHES), and
two whole-table stat edits. Appended to the library after every table edit (edits.py build --structural)."""
import edits as ed


def add_edits(add, table, main):
    # Greed (25 shards for the stats of 40, no passive) as the stat sink from an ordinal on; 12: past the table.
    for k in (6, 8, 10, 12):
        add(f"greed-from-{k}", "structural", flags=[("greed_from", k)])
    # Collectors keyed to the distinct families owned, not to the ordinal.
    for n in (2, 3, 4, 5):
        add(f"collectors-at-{n}-families", "structural", flags=[("coll_at", n)])
    add("diversify-after-collectors", "structural", flags=[("diversify", 1)])
    # The stat of an ordinal bucket's emblems: Health, or the main stat.
    for b in range(4):
        for v, name in ((1, "hp"), (2, "main")):
            add(f"stat-{name}-k{3 * b}-{3 * b + 2}", "structural", flags=[(f"stat_b{b}", v)])
    # The current logic's prices (it decides the cells the table leaves, and everything past ordinal 11).
    for m in (0.5, 2, 4):
        add(f"fight-weight-x{m}", "structural", flags=[("fight_w", m)])
    for f in ("skirmish", "treasure", "prospector", "capture", "hunter", "tribute"):
        for m in (0.5, 2):
            add(f"price-{f}-x{m}", "structural", flags=[(f"m_{f}", m)])
    for m in (1, 2):
        add(f"collectors-priced-x{m}", "structural", flags=[("coll_priced", m)])
    # The stat mix of the whole table: every arm in Health, or in the type's usual stat.
    add("table-all-hp", "structural", ed.mapped(table, lambda p, t, k, a: a // 3 * 3 + 2 if a != ed.NONE else a))
    add("table-all-main", "structural", ed.mapped(table, lambda p, t, k, a: a // 3 * 3 + main[t] if a != ed.NONE else a))
