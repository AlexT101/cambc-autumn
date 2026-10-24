#!/usr/bin/env python3
"""Independent scenario model for next-round ABBA ordering.

This models roster sorting and alternation only. It does not execute or validate the
candidate's production rank/slot helper or its admission predicates.
"""


def schedule(a, b, a_first):
    teams = [sorted(a, key=lambda u: (-u[1], u[0])), sorted(b, key=lambda u: (-u[1], u[0]))]
    cursor = 0 if a_first else 1
    pos = {}
    while teams[0] or teams[1]:
        if teams[cursor]:
            ident, _priority, label = teams[cursor].pop(0)
            pos[label] = len(pos)
        cursor ^= 1
    return pos


def make_team(n, vals, prefix, dead_ids=()):
    # Dead champions keep their roster IDs, priorities, and alternating slots.
    out = []
    for i in range(n):
        ident = prefix + i
        label = f"dead:{ident}" if ident in dead_ids else f"{prefix}:{i}"
        priority = 13 if ident in dead_ids else vals[i]
        out.append((ident, priority, label))
    return out


def check_case(a_n, b_n, a_first, a_vals, b_vals, self_index, enemy_index):
    # Ties and negative priorities exercise ID ordering; dead roster slots remain in the schedule.
    a = make_team(a_n, a_vals, 0, dead_ids={a_n - 1})
    b = make_team(b_n, b_vals, 20, dead_ids={20 + b_n - 1})
    self_label = f"0:{self_index}"
    enemy_label = f"20:{enemy_index}"
    old = schedule(a, b, a_first)
    self_item = next(x for x in a if x[2] == self_label)
    fallback = self_item[1]
    raised_a = [(i, (13 if label == self_label else p), label) for i, p, label in a]
    new = schedule(raised_a, b, a_first)
    crossing_benefit = new[self_label] < new[enemy_label] and old[self_label] >= old[enemy_label]
    return {
        "counts": f"{a_n}v{b_n}", "a_first": a_first, "fallback": fallback,
        "self": self_label, "enemy": enemy_label,
        "old_slots": [old[self_label], old[enemy_label]],
        "new_slots": [new[self_label], new[enemy_label]],
        "crossing_benefit": crossing_benefit,
    }


def main():
    cases = []
    # Five-v-six and six-v-five, both opening teams. These include equal priorities
    # and one dead champion on each roster, still occupying its normal ID/turn slot.
    matrices = [
        (5, 6, True,  [-29, 13, 9, 0, -32], [14, 13, 13, 0, -29, -32], 0, 1),
        (5, 6, False, [-29, 13, 9, 0, -32], [14, 13, 13, 0, -29, -32], 0, 1),
        (6, 5, True,  [-32, 12, 13, 9, 0, -29], [14, 13, 13, 0, -29], 0, 1),
        (6, 5, False, [-32, 12, 13, 9, 0, -29], [14, 13, 13, 0, -29], 0, 1),
    ]
    for args in matrices:
        cases.append(check_case(*args))
    expected = [
        ([8, 3], [0, 3], True),
        ([9, 2], [1, 2], True),
        ([10, 3], [0, 3], True),
        ([10, 2], [1, 2], True),
    ]
    actual = [(c["old_slots"], c["new_slots"], c["crossing_benefit"]) for c in cases]
    assert actual == expected, f"independent ABBA scenarios changed: {actual!r}"
    print("Independent ABBA simulation passed:")
    for c in cases:
        print(c)
    print("Dead roster IDs and tied priorities are retained in sorting; 5v6 and 6v5 both tested.")


if __name__ == "__main__":
    main()
