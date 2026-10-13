# Rules verification summary

We tested the cambc2026a engine against the docs with 22 probe bots (`probes/`) across ten topics:

- settings and item/champion/camp data
- turn order and memory
- fuel
- camps
- capture and gold
- action allowances
- stun, death and recall
- vision, wards and the teleport crystal
- the Monolith, altar locks and damage modifiers
- lingering spell effects and champion passives

The evidence for each result is in `findings.md`, and `../cambc-rules.yaml` records the tested behaviour.

All champion stats, item costs, camp HP/gold/gems and game settings match the docs exactly.

## Outright conflicts (the docs say one thing, the engine does another)

| # | Docs say | Engine does | Docs typo or engine bug? |
|---|---|---|---|
| 1 | Monolith attack range is 5 (camp table) | Range 3, both in the engine's data and in live play | Probably a typo in the table: the same page says "all monsters have range 3". It would be an engine bug only if 5 was intended. |
| 2 | An awake camp sleeps once it "does not take damage for 2 turns" | It sleeps after 2 camp phases with no champion within range 3. Taking damage does not keep it awake. | Docs typo; another line on the same page states the correct rule. |
| 3 | Teleport crystal "can reach walls" | It cannot land on a wall, though it can cross walls | Docs typo. |
| 4 | Ranged champions can't move and attack in one turn, and "the same rule applies for damaging abilities" | A damage spell never uses up the basic attack. Spells flagged "excludes walking" only stop you walking. | Docs wording. |
| 5 | Placing an altar lock "cancels enemy channels" | It cancels every tribute channel at that altar, including your own team's | **Possible engine bug.** Another line of the docs says "existing tribute channels at that altar", which does match the engine. |
| 6 | Capture means waiting "5 turns" on the camp | Stepping on during round R pays at round R+6 (six capture phases) | Off by one in the prose; the docs' diagram is consistent with the engine. |
| 7 | A respawned champion returns with abilities ready | On the respawn turn itself it cannot move, attack or cast | **Possible engine bug.** |
| 8 | Fuel page: a suspended bot "resumes next round" | A draft bot that runs out of fuel or yields before picking is never run again, and its remaining picks are random | Probably intended; the draft page's "remaining picks are random" agrees. |
| 9 | Gem and gold clusters have range 0 (camp table) | The engine's data says range 3 | No effect in play, since their strength is 0. |

## Clarifications and gaps (the docs were silent or vague; now settled)

- **Coordinates and symmetry:** (0,0) is the bottom-left, and north is +y. Each symmetry type maps tiles as horizontal (W-1-x, y), vertical (x, H-1-y), rotational (W-1-x, H-1-y).
- **Turn order:**
  - Team A starts odd rounds, team B even rounds, and the teams strictly alternate one champion at a time.
  - Priority ties go by pick order. Priority accepts any 32-bit integer.
  - Dead champions keep their turn slot.
- **Draft:**
  - A pick stays hidden until both teams have picked that round.
  - Re-picking your own champion is an error that doesn't use up the turn.
  - Each draft-memory write overwrites from byte 0.
  - A shared-memory write is visible straight away to teammates who act later.
- **Capture:**
  - Only the camp's own tiles count, not adjacent ones.
  - An enemy standing on any of them blocks the capture and resets progress.
  - Split shares are floored, and the lowest champion id gets the remainder.
  - Any occupied tile holds the camp's respawn indefinitely.
- **Gold:**
  - Gold starts at 0, there is no passive income, and killing camps gives none (only capturing does).
  - Bonuses apply to each champion's share and add together (Vesper + Treasure = +40%).
  - Gold is stored with fractions; the visible amount is rounded down.
- **Damage:** modifiers multiply and are never rounded, and health is fractional (Jungle + Durability: 20 → 12.6).
- **Camps:**
  - Each monster attacks the nearest champion of either team, measured as a square distance, with ties going to the lowest id.
  - Bushes don't hide you from camps.
  - Ren's retaliation hits camps too.
  - A stunned camp skips its next attack.
- **Allowances:**
  - Attack reset fails unless the attack is already used, and it restores only the attack. So a ranged champion can walk, reset, then attack.
  - A dash uses neither the walk nor the attack, and camps block dash paths.
- **Stun:** it removes exactly the target's next turn and blocks everything except setting priority. It cancels recall, tribute and teleport.
- **Vision and wards:**
  - Champion vision is a 17×17 square and ward vision 13×13, not circles.
  - Wards can be placed without seeing the tile, never expire, and survive the owner's death.
  - Units out of your vision, allies included, reveal only whether they are alive.
  - Bumping into a hidden unit reveals its tile only to you, only for that round. Attacking from a bush doesn't reveal you.
  - Bush clusters are edge-connected: diagonal bushes are separate clusters. Inside a bush your own cluster is see-through, but only within the normal 17×17 square.
  - `bitboard::shadow_cast` with walls and the other clusters' bushes as opaque reproduces engine vision exactly, and sight is symmetric.
- **Death and respawn:** a champion respawns in round D+61, or D+60 if it died before its own turn that round. Recall can't be restarted in the same turn after cancelling. Standing on spawn heals to full at every turn end, but enemies can still attack into it.
- **Altar locks:**
  - The team that placed a lock can still tribute at that altar.
  - Each team can have one lock per altar.
  - An enemy's tribute attempt becomes one of the three hits and uses up their basic attack.
  - Spells don't affect locks.
- **Fuel:**
  - About 21k of start-up cost comes out of each bot's first turn.
  - A bot that runs out resumes mid-code as the next round's turn, with fresh actions.
  - Reading the full camp-group list costs about 28k fuel (over a quarter of a turn).
  - Each team's printed output is capped at 1 MiB.
  - A host distance-field search costs a fixed part (about 0.25 fuel per map tile) plus about 100 per layer on an 80×80 map. It follows the number of layers, not tiles, so a route d steps long costs about 1.6k + 100d there.
- **SDK quirks:** `is_ready()` reports an attack reset as castable when it would fail. The header says the linear bitboard buffer uses one byte per tile; it is actually one bit per tile. `shadow_cast` from an opaque tile throws engine error 5.

## Still untested

The YAML follows the docs on these or leaves them out:

- walls between a camp and its target (no shipped map allows it)
- whether Varg's splash hits diagonal neighbours
- Durability emblem on its own, and the Monster bonus on spells
- the gem remainder in an uneven split
- gems gained during a tribute
- Treasure on kill gold
- Tavi selling
- whether shield-absorbed damage cancels a recall
- any inventory cap above 18 items
- whether wards block walking

## Probing tip

At the default 100k fuel per turn, heavy logging runs out of fuel and silently shifts timings into the next round. Always pass a large `--fuel` (for example `--fuel 50000000`) when probing.
