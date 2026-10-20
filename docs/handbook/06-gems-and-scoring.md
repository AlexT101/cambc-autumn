# Gems & altars

*The main objective of the game is to obtain gems by capturing camps, or stealing them from enemies. To actually progress towards winning the game however, the gems must first be tributed at altars.*

The main objective of the game is to obtain gems by capturing camps, or stealing them from enemies. To actually progress towards winning the game however, the gems must first be tributed at altars.

## Carried or tributed

> **Diagram: gems.** Carried gems can be stolen on death and do not count towards victory. Tributed gems are permanent team score.

<details>
<summary>Interactive diagram text</summary>

- In your bag
- Your killer takes them if you die
- Worth nothing until tributed
- Prism
- gains Focus from them
- Tribute at an altar
- Team score
- Safe for the rest of the match
- Count for your whole team
- 1,000 wins the match

</details>

## Tribute at an altar

Tributing requires a channel to secure the gems. The amount of time this takes scales with the number of gems you are carrying, namely the amount divided by 10, rounded up.

> **Diagram: tribute.** Stand within Chebyshev distance 1 of an altar with at least one gem and start a tribute. Duration is max(1, ceil(starting gems / 10)) champion turn ends: 1–10 gems take 1 countdown tick, 11–20 take 2. Timers decrement at turn end, including the starting turn, and complete at the owner's next turn start after reaching zero. Completion tributes the entire current bag. Damage does not interrupt it; stun, death or an altar lock does.

<details>
<summary>Interactive diagram text</summary>

- Stand next to an altar
- Any of the eight tiles around it, diagonals included.
- Start a tribute
- You need at least one carried gem.
- Stay for the channel
- Duration of channel is equal to number of gems / 10 turns.
- Step
- Actions that cancel your channel
- Taking Damage
- Stun
- Death
- Altar getting locked
- Continues
- Cancels

</details>

> **Diagram: delivery.** Tribute duration is max(1, ceil(carried gems / 10)) owner turn ends. The starting turn counts; completion waits until your next turn start after zero.

<details>
<summary>Interactive diagram text</summary>

- in your bag
- to tribute
- Try a different bag size
- Gems ÷ 10, rounded up, with a minimum of 1 turn end. Counts down at your turn end, including the starting turn. Resolves at your next turn start once zero.

</details>

### Timing details

- The channel ticks at the end of its champion’s turn, including the turn it starts. A timer that reaches zero stays pending until the start of that champion’s next turn. A one-tick tribute therefore completes at your next turn start, not at the end of the turn you start it.
- Its length uses your bag when you start. Completion tributes your whole bag, including gems gained since.
- Captures resolve before channels, so gems captured this round are included.

## Altar locks

Altar locks are a consumable you can purchase for 10g, and carry one at a time. You can place them on altars if you are within range, cancelling enemy channels, or simply delaying them by leaving them there. It takes 5 basic attacks to clear the lock, which is also triggered by the tributing action in the engine.

> **Diagram: lock.** An altar lock blocks opposing tributes but allows its owner's team to tribute. Placing it cancels existing tribute channels at that altar. Five basic attacks remove it.

<details>
<summary>Interactive diagram text</summary>

- Locked
- Enemy lock placed
- Your team cannot tribute at this altar. Placing the lock also cancelled any tributes already in progress here.
- 1 hit
- 1 of 5 hits
- Break it with basic attacks. A tribute attempt here becomes an attack on the lock.
- 2 hits
- 2 of 5 hits
- Three more successful basic attacks.
- 3 hits
- 3 of 5 hits
- Two more successful basic attacks.
- 4 hits
- 4 of 5 hits
- One more successful basic attack.
- Broken
- Lock broken
- The altar is open again. Start a new tribute.
- Break an enemy altar lock
- Illustrated example
- N. N
- Basic attacks
- N to break
- Open
- Pause
- Replay
- Play
- N: N
- N (N of N)
- Attacks on the lock
- Your own team’s lock does not stop you: you can tribute past it, and only the enemy is blocked.

</details>

### Tributing against a lock

Attempts to tribute against a locked altar are implicitly converted to auto attacks against the altar lock.

---

**See also:** [Camps & capture](./05-camps.md) · [Death, recall & recovery](./10-death-and-recall.md) · [A champion turn](./03-your-first-turn.md)

<sub>Engine sources cited by the handbook: `game/Engine/include/private_cpp/Engine/Balance/GameSettings.h`, `game/Engine/src/Game/Actions.cpp`, `game/Engine/src/Game/Scheduler.cpp`, `game/Engine/src/Game/Combat.cpp`, `game/Engine/src/Game/PlacedConsumables.cpp`</sub>
