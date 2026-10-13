# Death, recall & recovery

*Recall to heal safely. Die, and you lose your carried gems and sit out 60 rounds.*

## When a champion dies

> **Diagram: death.** The killer receives all carried gems and 50 base gold; assists award no gold. Camp kills destroy carried gems. Dead champions retain shopping turns and respawn at their next turn start after 60 owner turn-end ticks, when a spawn tile is available, with full health and abilities reset.

<details>
<summary>Interactive diagram text</summary>

- Carrying
- Carrying 11 gems
- An enemy closes in while your bag is full.
- Killed
- The champion who lands the killing blow takes all 11 gems and 50 gold. You keep your own gold and equipment.
- Waiting
- 60 turn ends to respawn
- Your bot still gets a turn each round to shop. Its respawn timer counts down at the end of each of those turns.
- Respawn
- Respawned
- At your turn start after the timer reaches zero, return to a free spawn tile with full health and both abilities ready, but an empty bag.
- What a death costs
- Illustrated example
- N. N
- You
- 60 rounds · can shop
- On your spawn
- Enemy
- +50 gold
- Pause
- Replay
- Play
- N: N
- N (N of N)
- After the kill

</details>

When a champion dies they respawn on their spawn tiles after 60 rounds, awarding their killer all the gems they were carrying in addition to 50 gold.

If a camp kills you, the carried gems are lost.

Cassi and Issac die together, awarding the killer 50 gold, and all the gems that both of them were carrying.

## Recalling

Recalling is a channeled action taking 5 turns, that returns your champion to the spawn from anywhere on the map. Spawn tiles allow you to shop, and also will heal you to full health so recalling when you are low, or have a lot of gold is usually a good idea.

> **Diagram: recall.** Recall takes 5 owner turn ends, or 3 with Home; the starting turn counts. Completion happens at the next owner turn start after zero. Damage or stun interrupts it. You retain carried gems. After arriving at turn start, remain on spawn until that turn ends to heal fully.

<details>
<summary>Interactive diagram text</summary>

- Start
- Start a recall
- Low on health and far from home, with 11 gems in your bag. Without Home, recall takes five of your turn ends.
- This turn ends · 4 left
- The first tick happens now, on the turn you started. Any damage cancels the recall.
- Next turn ends · 3 left
- Each of your turn ends counts down once. A stun would cancel the channel too.
- 2 turn ends left
- You cannot act during the channel unless you cancel it first.
- 1 turn end left
- Your next turn end reduces the timer to zero. Recall completes at the start of your following turn.
- Back on your spawn
- After your fifth turn-end tick reaches zero, recall completes at the start of your next turn. Your 11 gems are still carried, not tributed.
- Healed
- Healed to full
- Recall arrives at turn start. Stay on spawn until that turn ends to heal.
- Recall home
- Illustrated example
- N. N
- Your spawn
- 11 gems
- Out on the map
- Done
- N left
- Pause
- Replay
- Play
- N: N
- N (N of N)
- Recall progress

</details>

- Recall arrives at turn start. Stay on spawn until the end of that turn to heal to full.
- Any damage cancels it, and so does a stun. Start it somewhere safe.
- You keep your carried gems.

---

**See also:** [Gems & altars](./06-gems-and-scoring.md) · [Combat & abilities](./07-combat.md) · [Items & gold](./08-items.md) · [Cassi & Issac](../champions/cassi-and-issac.md)

<sub>Engine sources cited by the handbook: `game/Engine/src/Game/Combat.cpp`, `game/Engine/src/Game/Actions.cpp`, `game/Engine/src/Game/Scheduler.cpp`, `game/Engine/include/private_cpp/Engine/Balance/GameSettings.h`, `game/Engine/include/private_cpp/Engine/Balance/ItemPassives.h`</sub>
