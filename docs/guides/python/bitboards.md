# Bitboards

*Bitboards are a core aspect of how bots interact with the game. They represent groups of map tiles, letting your bot combine terrain, filter what it can see and choose where to move using a few simple operations.*

## Basics

A bit is a single binary value: either 0 or 1. In a bitboard, each bit corresponds to a tile on a two-dimensional grid. A 1 means the tile is selected; a 0 means it is not. Think of it as a map of yes/no answers laid over the game board, rather than a list of individual coordinates.

What those answers mean depends on the board. A walls bitboard marks wall tiles with 1; a visibility bitboard marks tiles your bot can see. A tile can be selected in several different boards. These boards store locations, not champion identities or the full contents of each tile.

- Plan movement: combine walls and holes into a set of blocked tiles, then exclude them from candidate destinations.
- Filter targets: keep only goal tiles that are also visible or reachable.
- Track exploration: remember visited tiles and find places you have not explored.
- Compare turns: find tiles whose membership changed between two snapshots.

Operations combine entire sets tile by tile, so you can narrow down useful locations before iterating over their coordinates. The examples below use an 8×8 board to keep things readable; game maps can be larger.

## Operations

Choose an operation, then select tiles in boards A and B to see how the result changes. Every result bit depends on the input bits at the same coordinate. Union and OR are two names for the same operation; intersection and AND are another pair.

> *Interactive bitboard demo on the website (https://2026a.battlecode.co.uk/game/docs).*

<details>
<summary>Demo text</summary>

- A OR B selects a tile if either input is 1, including when both are 1. Combine walls and holes into one blocked-tile mask.
- A AND B selects a tile only when both inputs are 1. Intersect candidate destinations with visible tiles to keep only visible candidates.
- A XOR B selects a tile when exactly one input is 1. Compare two snapshots to find tiles whose membership changed.
- A minus B keeps tiles selected in A but not in B. Remove blocked tiles from a set of candidate destinations.
- N tile (N, N)
- Operation
- Union / OR
- Intersection / AND
- Exclusive OR
- Difference: A minus B
- Result
- tiles selected in the result.
- Reset grids

</details>

**Python expressions: a and b are boards; p is a tile**

| Operation | Expression | Use |
| --- | --- | --- |
| Union / OR | `a \| b` | Tiles in either mask: walls OR holes. |
| Intersection / AND | `a & b` | Tiles in both: candidates AND visibility. |
| Exclusive OR | `a ^ b` | Tiles in exactly one mask: compare old and new state. |
| Complement / NOT | `~a` | Invert membership within map bounds. |
| Difference | `a & ~b` | Remove B from candidate set A. |
| Count | `a.count()` | Count selected tiles. |
| Membership | `a.is_set(p)` | Test one coordinate. |

Use `positions()` (`Bitboard.positions` in OCaml) to enumerate coordinates. Combine and filter masks before materialising large position lists to save memory and fuel.

## Build a pathfinding mask

**Terrain masks in Python**

```
from cambc import game_map
# Use bitwise operators, not boolean 'and'/'or'.
blocked = game_map.walls() | game_map.holes()
avoid = blocked | game_map.bushes()  # Optional routing preference.
open_bushes = game_map.bushes() & ~blocked
for tile in open_bushes.positions():
    pass  # Consider tile as a destination.
```

> **Bushes are walkable**
>
> Walls and holes block normal movement. Including bushes in an avoidance mask is a strategy choice, not a movement rule. Vision blockers and movement blockers are different sets.

This terrain example is not a complete movement validator. Also account for altars, enemy spawn tiles and known occupied tiles. The SDK pathfinding helper builds the full mask. Hidden occupants can still block a step, so check the movement action result.

To query a group of goals, set one bit per acceptable destination, then intersect with reachable or visible tiles. Camp group IDs are not bit indices: use their tile coordinates.

## Copies and snapshots

Map masks are cached objects. Use `copy()` before `set()`, `clear()` or `|=`. Assignment aliases the same object; ordinary `|`, `&` and `~` return new boards.

Refresh dynamic visibility and unit masks during play. They are snapshots, not live subscriptions, and cannot reveal information outside your permitted vision.

## Advanced: storage and bit layout

> *Interactive bitboard layout on the website (https://2026a.battlecode.co.uk/game/docs).*

<details>
<summary>Demo text</summary>

- Engine raw storage
- Linear export
- Each row is one 64-bit chunk. Grey cells are padding.
- Consecutive tiles in row-major order. Rows below show groups of 64 bits.
- Padding bit
- Raw
- Linear
- , tile (
- Map width
- 16 tiles (no padding)
- 24 tiles (padded chunk rows)
- Bitboard tiles
- Tile (
- Toggle selected bit
- ) → linear bit
- (byte
- , bit
- ). Chunk stride:
- words.

</details>

Internally, each 8 by 8 chunk occupies a 64-bit word. For tile `(x, y)`, chunk coordinates are `(x >> 3, y >> 3)`, and the bit within the word is `(y & 7) * 8 + (x & 7)`. Bit 0 is the first tile of the chunk; each next group of eight bits is the next local row.

**Logical tile to physical bit**

```
word_index = (y >> 3) * chunkStride + (x >> 3)
bit_index = (y & 7) * 8 + (x & 7)
mask = 1 << bit_index
```

Physical stride includes alignment padding; edge chunks also contain bits outside the map. Do not substitute `ceil(width / 8)` for `chunkStride` or interpret raw storage as a flat width-by-height bitmap. Native raw buffers require 16-byte alignment. Use SDK size and import/export helpers instead of guessing buffer sizes. Raw transfers include chunk padding; linear transfers are a separate interchange representation.

Prefer SDK operations to preserve map bounds and padding. Shifting a set is not pathfinding around obstacles. `reachable_tiles` computes reachability; `shadow_cast` computes visibility. See their language-specific signatures in the API.

---

**See also:** [Getting Started](./first-bot.md) · [Bot API reference](../../api/python.md)

<sub>Engine sources cited by the handbook: `game/Engine/include/private_cpp/Engine/Core/Bitboard.inl`, `game/cli/sdk/cpp/cambc.h`, `game/cli/sdk/python/_cambc.pyi`, `game/cli/sdk/rust/src/board.rs`, `game/cli/sdk/ocaml/cambc.mli`</sub>
