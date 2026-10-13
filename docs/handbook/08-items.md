# Items & gold

*Items in the game are purchased on the spawn tiles (or while dead) using gold. You can purchase shards, increasing permanent stats for your champion based on their internal growth values:*

## Shards and emblems

Items in the game are purchased on the spawn tiles (or while dead) using gold. You can purchase shards, increasing permanent stats for your champion based on their internal growth values:

- Strength, increasing your basic attack damage
- Health, increasing your maximum health
- Focus, increasing the power of your abilities

Shards cost 30 gold and after purchasing 5, combine into an emblem providing a unique bonus based on which shard type you purchased.

Try building an emblem below:

> **Diagram: items.** Shards cost 30 gold and add their champion's growth for the chosen stat. Five matching shards automatically combine into the corresponding emblem. Only the completed emblem grants its passive. Families have Strength, Health and Focus variants; use the family table for stat points and passives.

<details>
<summary>Interactive diagram text</summary>

- 10% more damage to camps
- No passive: counts as 6 shards instead of 5
- 10% less incoming damage
- 20% more gold gained
- 30% less damage from camps
- 50% shorter recall · 3 turn ends
- N N
- N Emblem of N
- Build an emblem
- Interactive
- Emblem family
- Family
- Stat
- N of 5 shards bought
- Combined automatically
- N more N to combine
- Gold spent
- Counts as
- None yet
- Passive
- · needs the emblem
- Pause
- Replay
- Play
- N: N
- N (N of N)
- Shards bought · drag to buy
- No shards
- 1 shard
- 2 shards
- 3 shards
- 4 shards
- 5 shards: emblem
- Shards cost 30 gold. Each adds the champion’s growth in that stat, so Ryth gains +5 Strength per Strength shard. The fifth identical shard combines into the emblem, which adds the family passive.

</details>

## Emblem families

**Every family has Strength, Health and Focus versions. 5 shards automatically combine to an emblem (150 gold total). Shards give stats; only the finished emblem gives the passive.**

| Family | Counts as | Passive |
| --- | --- | --- |
| Monster | 5 shards of the chosen stat | 10% more damage to camps. |
| Power | 6 shards of the chosen stat | None; one extra shard’s worth instead. |
| Durability | 5 shards of the chosen stat | 10% less incoming damage. |
| Treasure | 5 shards of the chosen stat | 20% more gold gained. |
| Jungle | 5 shards of the chosen stat | 30% less damage from camps. |
| Home | 5 shards of the chosen stat | 50% shorter recall: five turn ends become three, rounded up. |
| Bruiser | 5 of the chosen stat, 1 of each other | None; a spread of stats instead. |

## Consumables

The shop also has some consumable items, each costing 10 gold. You may carry only one of each at the same time, with the same purchase rules as shards/emblems.

**10 gold each. Carry at most one of each. Buy them on your spawn or while dead.**

| Tool | Use |
| --- | --- |
| Altar lock | Place on an altar within two tiles. Blocks enemy tributes until removed by three basic attacks. |
| Teleport crystal | Teleport crystal allows you to access otherwise unreachable areas by teleporting you 3 tiles, ignoring terrain. However, the teleport only activates after a channel of 3 turns. |

### Extra item rules

- **Stats stack**: Every shard counts, including those inside duplicate emblems.
- **Emblem passives don’t**: A second emblem of a family adds no extra passive.
- **Gold bonuses add**: Treasure with Vesper Vale: 20% + 20% = 40%.
- **Spawn purchases heal**: Buying Health on your spawn heals the amount gained; Tavi’s field purchases do not.
- **Only Tavi can sell**: On spawn, for the full purchase value. Refunds are not earned gold.

---

**See also:** [Vision & wards](./09-vision.md) · [Champion roster](../champions/README.md) · [Tavi](../champions/tavi.md)

<sub>Engine sources cited by the handbook: `game/Engine/include/private_cpp/Engine/Balance/Items.h`, `game/Engine/include/private_cpp/Engine/Balance/ItemPassives.h`, `game/Engine/include/private_cpp/Engine/Balance/Consumables.h`, `game/Engine/include/private_cpp/Engine/Balance/GameSettings.h`, `game/Engine/src/Game/Actions.cpp`, `game/Engine/src/Game/Passives.cpp`, `game/Engine/src/Game/PlacedConsumables.cpp`, `game/Engine/src/Game/Scheduler.cpp`</sub>
