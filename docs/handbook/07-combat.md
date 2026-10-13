# Combat & abilities

*Basic attacks use Strength. Spells use their own effects and Focus scaling.*

## Basic attacks

Every turn champions can attack using their basic attack, melees can hit targets within 1 tile, and ranged within 3. Depending on whether you are the melee or ranged class will determine whether you can move and attack on the same turn or not:

> **Diagram: reach.** Basic attacks deal Strength before modifiers and require a visible target. Ranges use Chebyshev distance, so diagonals count as one tile. Melee range is 1; ranged range is 3.

<details>
<summary>Interactive diagram text</summary>

- AND
- Walk and attack in one turn
- Ranged
- OR
- Walk or attack, not both
- N basic attacks reach N N in every direction, diagonals included.
- A basic attack deals your Strength as damage, before modifiers. Diagonals count as one tile, and the target must be visible.

</details>

## Abilities scale with focus

Abilities scale with focus by taking the champion's focus value, and multiplying by the ability multiplier.

For example, Stellar starts with 100 focus, and has an ability dealing 2x focus damage. Therefore she can cast the ability on her turn dealing a burst of 200 damage, starting its 8 turn cooldown. After 8 turns, she can cast the ability again.

> **Diagram: slots.** Each champion has two ability slots but only one successful cast per turn. Casting starts an 8-turn-end cooldown for that slot. Spell effects scale with Focus as specified in the champion's kit.

<details>
<summary>Interactive diagram text</summary>

- This turn
- Not this turn
- Afterwards
- Ready
- Slot

</details>

Ability details such as the range, targeting system, and whether you can cast and move are detailed on each champion's individual page

### Targets

- Unit spells need a valid visible target. Ground spells affect an area.
- Self-targeted spells use the self-cast action.

## Channels

Channels are actions that take several turns to complete, such as recall, tribute and teleport. Their timers tick down at your turn end, then execute at your next turn start when the timer is zero. The below table shows the channel actions in the game, and how and when they can be cancelled.

> **Diagram: channels.** Channels count down at owner turn ends and execute at the next owner turn start once zero. Recall takes 5 countdown ticks (3 with Home) and is interrupted by damage, stun or death. Tribute takes ceil(gems / 10) owner turn ends, at least 1: damage does not stop it, but stun, death or a new altar lock does. Teleport crystals channel for 3 owner turn ends: damage does not stop them; enemy stuns and death do. Recall and tribute can be cancelled manually; teleport cannot.

<details>
<summary>Interactive diagram text</summary>

- 5 turn ends · 3 with Home
- Gems ÷ 10 turn ends, rounded up (minimum 1)
- 3 turn ends
- Damage
- Stun
- Continues
- Cancels
- Channels are cancelled by...
- What interrupts each channel
- Cancel yourself
- Yes
- No

</details>

---

**See also:** [Champion roster](../champions/README.md) · [Items & gold](./08-items.md) · [Bot API reference](../api/cpp.md)

<sub>Engine sources cited by the handbook: `game/Engine/src/Game/Actions.cpp`, `game/Engine/src/Game/Combat.cpp`, `game/Engine/src/Game/Abilities.cpp`, `game/Engine/include/private_cpp/Engine/Balance/Champions.h`, `game/cli/sdk/cpp/cambc.h`</sub>
