"""Exhaust the turn-count inputs behind the new at-most-one-turn fast path."""
import itertools

checked = 0
for visible, acted, enemy, stunned, teleport, unseen_now, next_before in itertools.product((False, True), repeat=7):
    for channel_offset in range(-2, 4):
        lost = enemy and visible and stunned
        now = not acted if visible else unseen_now
        starts = channel_offset if teleport else 0
        turns = max(0, int(now and starts <= 0) + int(starts <= 1 and next_before) - int(lost))
        at_most_one = (visible and acted) or lost or (teleport and channel_offset > 0)
        if at_most_one:
            assert turns < 2
        if (visible and acted and lost) or (teleport and channel_offset > 1):
            assert turns == 0
        checked += 1
print(f"{checked} turn-count states: exact zero and at-most-one bounds hold")
