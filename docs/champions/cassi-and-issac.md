# Cassi & Issac

*One draft choice creates a ranged spellcaster and a melee fighter. They act separately, but if either dies, both die.*

<img src="../images/champion-cassi-and-issac.webp" alt="Cassi & Issac" width="320">

## Two bodies, one linked fate

Cassi and Issac have separate positions, bags, abilities and bot instances. Each receives its own turn.

> **Shared passive**
>
> If either Cassi or Issac dies, the other dies too. Both lose their carried gems and together grant one kill reward.

## Cassi · ranged

**Cassi**

### Slot 0: Single-target damage

2 × Focus damage.

- **Target / range:** Enemy or camp · 4
- **Walking:** Excludes walking
- **Cooldown:** 8 owner turn ends

### Slot 1: Stun

One-round stun with no direct damage.

- **Target / range:** Enemy or camp · 4
- **Walking:** Compatible
- **Cooldown:** 8 owner turn ends

| Stat | Base | Growth per matching shard |
| --- | --- | --- |
| Health | 600 | 65 |
| Strength | 30 | 3 |
| Focus | 100 | 13 |

Attack type: Ranged. Basic attack range: 3 tiles.

## Issac · melee

**Issac**

### Slot 0: Attack reset

Resets your basic attack cooldown.

- **Target / range:** Self
- **Walking:** Compatible
- **Cooldown:** 8 owner turn ends

### Slot 1: Dash

Move up to 2 steps, including diagonals.

- **Target / range:** Ground · 2 tiles
- **Walking:** Compatible
- **Cooldown:** 8 owner turn ends

| Stat | Base | Growth per matching shard |
| --- | --- | --- |
| Health | 900 | 80 |
| Strength | 45 | 3 |
| Focus | 100 | 10 |

Attack type: Melee. Basic attack range: 1 tiles.

---

**See also:** [Champion roster](./README.md) · [Death, recall & recovery](../handbook/10-death-and-recall.md) · [Shared memory](../handbook/12-shared-memory.md)

<sub>Engine sources cited by the handbook: `game/Engine/include/private_cpp/Engine/Balance/Champions.h`, `game/Engine/include/private_cpp/Engine/Balance/ChampionPassives.h`, `game/Engine/include/private_cpp/Engine/Abilities/Designs.h`, `game/Engine/include/private_cpp/Engine/Passives/Designs.h`, `game/Engine/src/Game/Combat.cpp`</sub>
