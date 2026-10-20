# A champion turn

Each turn a champion has a few options.

Every turn a champion can move one tile, in any 8 directions

Make a basic attack, dealing damage equal to their strength to a target in range

And use one of their two champion abilities, to activate a more powerful effect

If you are a ranged champion, you may NOT move, and basic attack on the same turn. This same rule applies for damaging abilities that are ranged as well.

> **Diagram: turn.** Melee champions can walk and attack in the same turn. Ranged champions normally choose walking or a basic attack: either consumes the other allowance. Attack-reset abilities can restore the attack allowance.

<details>
<summary>Interactive diagram text</summary>

- AND
- Walk and make a basic attack in the same turn.
- OR
- A normal walk spends your attack, and attacking spends your walk.
- Walk
- The basic rule, before spells. An attack-reset spell can restore an attack.

</details>

In addition to the basic combat, a champion has a few other options to interact.

Each champion carries a ward, that grants them persistent vision of an area with a range of 6 tiles. They may leave this ward behind to keep watch of an area anywhere within 2 tiles of them, and can relocate it once its free ward charge has recharged over 10 owner turn ends.

When a champion is low on health, or simply needs to travel to their spawn tiles, they can activate a recall. This cancellable action takes 5 turns, and will teleport the champion straight to their spawn tiles.

On the spawn tiles, they may shop for items using gold an unlimited amount.

When carrying the all important gems, and are directly next to an altar, a feature of the map, a champion may tribute gems, a cancellable action that takes a number of turns, equal to the number of gems being tributed divided by 10

Additionally, you can use consumable items without limit (though you can only carry one of each at once).

### Everything you can do

> **Diagram: actions.** Each turn normally allows one ordinary move, one basic attack, and one successful ability cast across both slots. Melee attack range is 1 tile; ranged attack range is 3. Movement and attacks share an allowance for ranged champions. Abilities have an 8-turn-end cooldown per slot. Some abilities exclude walking or reset attacks. Wards require their trinket charge, which recharges over 10 owner turn ends; consumables require inventory. Shop on your spawn or while dead (subject to champion exceptions). Starting a channel prevents other actions until it finishes or is cancelled. Recall and tribute each have one start and one cancellation per turn. Priority changes affect the next round.

<details>
<summary>Interactive diagram text</summary>

- No actions
- Cancel only
- Shop only
- Your turn: everything you can do
- Three kinds of limit
- Once every turn
- Refills when your next turn starts
- One tile, in any of eight directions
- Not after an “excludes walking” spell
- One visible enemy, camp or altar lock in range
- Melee 1 tile · ranged 3
- Ranged: uses up your walk
- Slot 0 or slot 1, never both
- Some reset your basic attack
- Whenever you have one
- No per-turn limit
- 1 charge
- Recharges over 10 owner turn ends
- Crystal or altar lock
- 1 of each
- 10 gold each
- Used up when used
- Shards, emblems and consumables
- Any amount
- Only on your spawn…
- …or while you are dead
- Timers tick at the end of your turn
- Timers count down now, and those reaching zero resolve at the start of your next turn.
- Return to your spawn
- 5 turn ends
- 3 turn ends with a Home emblem
- Damage or a stun cancels it
- From a tile touching an altar
- Gems ÷ 10 / min 1
- Needs at least one carried gem
- Stun, death or a new lock cancels it
- Travel to a free tile within range three
- 3 turn ends
- You can’t cancel it yourself
- Can’t act?
- Mix actions from all three rows in one turn, then end it. You can walk or attack before starting a channel, but not once it has begun.

</details>

### The exact turn order

The game engine runs each round's actions through phases, see the below graphic to understand the order of operations:

> **Diagram: round.** At round start: camp respawns, existing spell/ward updates, camp captures, then camp actions. Champion turns follow, alternating teams; the starting team swaps each round. Each champion starts by resolving zero timers: respawn, ward recharge, buff/shield expiry, then channels. At turn end, timers decrement without triggering these effects; spawn recovery still happens at turn end. Recall arrives at turn start, so staying on spawn heals at that same turn's end.

<details>
<summary>Interactive diagram text</summary>

- Respawns
- Camp respawn timers
- After a camp reward has been claimed, its group's respawn timer ticks once per round. At zero, the group respawns only if all its spawn tiles are free.
- Captures
- Camp capture timers
- Camps
- Camp turns
- Each living camp ticks its ability cooldowns and buffs before its actions. Buffs applied to a camp this round do not tick again yet. Awake camps then perform their actions, followed by camp end-of-turn maintenance.
- Champions
- Champions act one at a time, alternating teams while both have turns left. Each champion's full turn-end sequence below finishes before the next champion acts. Dead champions still get a turn to shop.
- NN
- One round, in order
- World updates automatically
- Your bots act
- Phase
- Odd rounds
- Even rounds
- Pause
- Replay
- Play
- N: N
- N (N of N)
- Round phase
- At this champion’s turn start
- Resolve zero timers before the bot acts: respawn, ward recharge, buff and shield expiry, then channel completion. A channel at zero can still be interrupted before this point.
- At this champion’s turn end
- Respawn
- If dead, tick the champion's respawn timer. At the next turn start, a zero timer respawns the champion if a spawn tile is free.
- Recovery
- Cooldowns
- If alive, tick this champion's ability cooldowns, including an ability cast this turn.
- Buffs
- If alive, tick this champion's buff and shield durations. Zero-duration effects remain active until their owner's next turn starts.
- Channels
- Champion turn-end step

</details>

#### Who goes first?

- **Teams alternate**: The team that starts swaps every round.
- **Priority, then draft order**: Within a team, higher priority acts first.
- **set_priority**: Takes effect from the next round and persists.
- **Dead champions still act**: They get a turn to shop.

> **Order matters**
>
> A capture can add gems before a tribute completes. Camps attack before your next turn.

---

**See also:** [Combat & abilities](./07-combat.md)

<sub>Engine sources cited by the handbook: `game/Engine/src/Game/Scheduler.cpp`, `game/Engine/src/Game/Actions.cpp`, `game/Engine/src/Game/Combat.cpp`, `game/Engine/src/Game/Abilities.cpp`, `game/Engine/include/private_cpp/Engine/Balance/GameSettings.h`, `game/Engine/include/private_cpp/Engine/Balance/Consumables.h`, `game/cli/sdk/cpp/cambc.h`</sub>
