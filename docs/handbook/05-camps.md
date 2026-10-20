# Camps & capture

*The main way to obtain resources is to defeat camps or monsters, on the map. They can spawn alone or in a group (any monsters that are cardinally connected).*

The main way to obtain resources is to defeat camps or monsters, on the map. They can spawn alone or in a group (any monsters that are cardinally connected).

## Pick your target

| Monster | Health | Strength | Range | Gold | Gems | Respawn |
| --- | --- | --- | --- | --- | --- | --- |
| Wolf | 1,350 | 20 | 3 | 40 | 4 | 40 rounds |
| Elk | 2,400 | 60 | 4 | 90 | 15 | 60 rounds |
| Golem | 5,000 | 120 | 4 | 160 | 36 | 80 rounds |
| Gem cluster | 120 | 0 | 0 | 0 | 7 | 50 rounds |
| Gold cluster | 120 | 0 | 0 | 20 | 0 | 50 rounds |
| Monolith | 20,000 | 200 | 5 | 300 | 200 | 150 rounds |

The map is populated with a variety of monsters. They vary in health, strength (damage dealt per turn) and the rewards they drop.

The monsters are friendly until they are hit! When a champion strikes a monster, it will awaken attacking the nearest champion every turn, until it either dies or does not take damage for 2 turns.

## After defeating a camp, make sure to capture!

> **Diagram: capture.** After every monster in a group dies, occupy at least one of its spawn tiles uncontested. At a capture phase your team starts a five-round timer; later capture phases count it down. Leaving the region empty or admitting an enemy resets progress. More allies do not speed it up. Rewards are shared among allies present when it finishes; the lowest ID receives any integer remainder. The group respawns together after rewards are claimed, using the longest cooldown of its members. Any occupied spawn tile delays the entire group.

<details>
<summary>Interactive diagram text</summary>

- Clear
- Clear the camp
- Defeat every monster in the group. Only then can the camp be captured.
- Start
- Capture starts · 5 rounds left
- Your team is alone in the camp’s capture area, so its five-round timer starts.
- 4 rounds left
- 3 rounds left
- If an enemy champion steps in, or your team leaves, the timer resets.
- 2 rounds left
- Captures resolve early in the round, before camps attack and before champions act.
- 1 round left
- One more round in the area finishes the capture.
- Captured
- Gems and gold are split between your champions in the area. This single-wolf camp pays 4 gems and 40 gold.
- Capture a wolf camp
- Illustrated example
- N. N
- Capture area
- Capture timer
- Not started
- Done
- N left
- Pause
- Replay
- Play
- N: N
- N (N of N)
- Capture progress

</details>

After defeating an entire group (cardinally connected monsters), you can then capture the rewards by standing on one of the tiles a monster was underneath, and wait 5 turns (the capture timer). This will award the waiting champion the gold and gems from the camp. If there are multiple champions, the reward is split evenly among them.

## What happens next?

After a camp reward is captured, its respawn timer begins. After the timer has finished (ticking down by 1 each round), the camp will respawn in the same location as before, full health, ready to drop rewards again.

### Capture and monster details

- Rewards combine every monster in the group.
- Allies on the region split the reward; the lowest ID gets the remainder.
- Extra allies do not speed capture. Empty or contested regions reset it.
- Wolf attacks at range 3, Elk and Golem at range 4, and Monolith at range 5. Monsters have vision 8, see through bushes and do not chase.
- Damage wakes the group; two rounds without an in-range champion let it sleep.

---

**See also:** [Gems & altars](./06-gems-and-scoring.md) · [Items & gold](./08-items.md) · [Vision & wards](./09-vision.md)

<sub>Engine sources cited by the handbook: `game/Engine/include/private_cpp/Engine/Balance/Camps.h`, `game/Engine/include/private_cpp/Engine/Balance/GameSettings.h`, `game/Engine/src/Game/Scheduler.cpp`, `game/Engine/src/Game/World.cpp`</sub>
