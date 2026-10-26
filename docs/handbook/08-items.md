# Items & gold

*Items in the game are purchased on the spawn tiles (or while dead) using gold. You can purchase shards, increasing permanent stats for your champion based on their internal growth values:*

## Shards and emblems

Items in the game are purchased on the spawn tiles (or while dead) using gold. You can purchase shards, increasing permanent stats for your champion based on their internal growth values:

- Strength, increasing your basic attack damage
- Health, increasing your maximum health
- Focus, increasing the power of your abilities

Shards cost 30 gold and after purchasing 5 (25 for Greed), combine into an emblem providing a unique bonus based on which shard type you purchased.

Try building an emblem below:

> **Diagram: items.** Shards cost 30 gold and add their champion's growth for the chosen stat. Five matching shards automatically combine into the corresponding emblem. Only the completed emblem grants its passive. Families have Strength, Health and Focus variants; use the family table for stat points and passives.

<details>
<summary>Interactive diagram text</summary>

- 15% more damage to camps
- No passive: counts as 6 shards instead of 5
- 10% less incoming damage
- 10% more gold gained
- 30% less damage from camps
- 50% shorter recall · 3 turn ends
- 33% shorter tribute, rounded up to at least one turn.
- 25% more gold and gems from your share of cluster rewards, rounded down.
- 50 extra gold per champion kill, before gold bonuses. Linked duo deaths grant one reward.
- 5% more damage to champions.
- No passive. Combines at 25 shards (750 gold) to give 35 shards worth of stats points.
- 1% bonus damage per unique completed emblem family owned, including Collectors itself. Shards and duplicate stat variants do not add families.
- N N
- N Emblem of N
- Build an emblem
- Interactive
- Emblem family
- Family
- Stat
- N of N shards bought
- Combined automatically
- N more N to combine
- Gold spent
- Counts as
- None yet
- Passive
- · needs the emblem
- Shards bought · drag to buy
- N shardsN
- : emblem
- Shards cost 30 gold. Each adds the champion’s growth in that stat, so Ryth gains +4.5 Strength per Strength shard. The fifth identical shard (25th for Greed) combines into the emblem, which adds the family passive.

</details>

> **Sharing Prospector rewards**
>
> The camp group's gem/gold cluster rewards are split among allied capturers. Each capturer who owns a Prospector emblem gets 25% of their own share as an additional reward, rounded down separately for gold and gems. Capturers without Prospector receive only their normal share. For example, 20 cluster gold shared by two allies gives each 10 base gold. A Prospector holder gets 2 extra gold; if both own it, both get 2 extra.

## Emblem families

**Every family has Strength, Health and Focus versions. 5 shards automatically combine to an emblem (150 gold total), except Greed: 25 shards (750 gold). Shards give stats; only the finished emblem gives the passive.**

| Family | Counts as | Passive |
| --- | --- | --- |
| Monster | 5 shards of the chosen stat | 15% more damage to camps. |
| Power | 6 shards of the chosen stat | None; one extra shard’s worth instead. |
| Durability | 5 shards of the chosen stat | 10% less incoming damage. |
| Treasure | 5 shards of the chosen stat | 10% more gold gained. |
| Jungle | 5 shards of the chosen stat | 30% less damage from camps. |
| Home | 5 shards of the chosen stat | 50% shorter recall: five turn ends become three, rounded up. |
| Bruiser | 5 of the chosen stat, 1 of each other | None; a spread of stats instead. |
| Tribute | 5 shards of the chosen stat | 33% shorter tribute, rounded up to at least one turn. |
| Capture | 5 shards of the chosen stat | Caps your team's remaining capture time at 3 turns, including when joining mid-capture. Never increases a shorter timer; the reduction remains if the holder leaves and an ally keeps capturing. |
| Prospector | 5 shards of the chosen stat | 25% more gold and gems from your share of cluster rewards, rounded down. |
| Hunter | 5 shards of the chosen stat | 50 extra gold per champion kill, before gold bonuses. Linked duo deaths grant one reward. |
| Skirmish | 5 shards of the chosen stat | 5% more damage to champions. |
| Greed | 35 shards of the chosen stat | No passive. Combines at 25 shards (750 gold) to give 35 shards worth of stats points. |
| Collectors | 5 shards of the chosen stat | 1% bonus damage per unique completed emblem family owned, including Collectors itself. Shards and duplicate stat variants do not add families. |

## Consumables

The shop also has some consumable items, each costing 10 gold. You may carry only one of each at the same time, with the same purchase rules as shards/emblems.

**10 gold each. Carry at most one of each. Buy them on your spawn or while dead.**

| Tool | Use |
| --- | --- |
| Altar lock | Place on an altar within two tiles. Blocks enemy tributes until removed by five basic attacks. |
| Teleport crystal | Teleport crystal allows you to access otherwise unreachable areas by teleporting you 3 tiles, ignoring terrain. However, the teleport only activates after a channel of 3 turns. |

### Extra item rules

- **Stats stack**: Every shard counts, including those inside duplicate emblems.
- **Emblem passives don’t**: A second emblem of a family adds no extra passive.
- **Gold bonuses add**: Treasure with Vesper Vale: 33% + 10% = 43%.
- **Spawn purchases heal**: Buying Health on your spawn heals the amount gained; Tavi’s field purchases do not.
- **Only Tavi can sell**: On spawn, for the full purchase value. Refunds are not earned gold.

---

**See also:** [Vision & wards](./09-vision.md) · [Champion roster](../champions/README.md) · [Tavi](../champions/tavi.md)

<sub>Engine sources cited by the handbook: `game/Engine/include/private_cpp/Engine/Balance/Items.h`, `game/Engine/include/private_cpp/Engine/Balance/ItemPassives.h`, `game/Engine/include/private_cpp/Engine/Balance/Consumables.h`, `game/Engine/include/private_cpp/Engine/Balance/GameSettings.h`, `game/Engine/src/Game/Actions.cpp`, `game/Engine/src/Game/Passives.cpp`, `game/Engine/src/Game/PlacedConsumables.cpp`, `game/Engine/src/Game/Scheduler.cpp`</sub>
