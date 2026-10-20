# Vision & wards

*Each champion sees its own patch of the map. Walls and bushes block the view.*

## How vision is calculated

Vision in the game is raycast, you can try it with the interactive vision tool below. To be more precise, the system uses symmetric shadow casting based on Albert Ford's algorithm.

[Albert Ford: Symmetric Shadowcasting — explanation and interactive example](https://www.albertford.com/shadowcasting/)

## What you can see

> **Diagram: sight.** Champions normally see up to 8 tiles using symmetric shadowcasting. Walls and bushes occlude vision; the connected bush cluster you stand in is transparent to your own vision. Your ward adds its vision; teammates' views are not shared.

<details>
<summary>Interactive diagram text</summary>

- Your champion sees 8 tilesN. Hover over any tile to trace its line of sight.
- , and your ward adds N more
- Your champion’s own tile.
- Visible: a clear line of sight from your champion.
- Visible through your ward.
- Walls themselves are never seen through or into.
- Out of range: more than 8 tiles away.
- Inside a bush. From outside it, you cannot see in.
- a bush
- a wall
- Hidden: N blocks the line of sight.
- Pieces cannot stand on walls.
- Wards are placed within two tiles of your champion.
- Line of sight
- Interactive · uses the game’s vision rules
- Piece to place
- Your champion
- Place a ward
- Remove ward
- Line of sight map. Click or use the arrow keys to move N.
- your champion
- your ward
- ..WWWW.......BBB...
- ..W..........BBB...
- ..W................
- ........WW.........
- ..BB......WWWWW....
- ..BB...............
- ......BB...........
- Your champion sees
- Your ward sees
- In range, out of sight
- Out of range
- Bush
- Vision is ray cast from the centre of your tile out to 8 tiles, including diagonals. Walls and bushes stop the rays, leaving shadows behind them. Move your champion into a bush to see across it, or place a ward to see around a corner.

</details>

- You see up to 8 tiles away in every direction, including diagonally, if nothing blocks the line of sight.
- Walls block sight. So do bushes: from outside, you cannot see into a bush or past it.
- Standing in a bush, you see across that whole bush and out of it, but not into other bushes.
- Holes cannot be stood on, but they do not block sight

## Wards

Each champion has a free ward, that can be placed to expand their personal vision. Its charge recharges over 10 owner turn ends. Placing a new ward replaces your existing ward, so you only ever have one active.

- **One active ward**: A new ward replaces the old one.
- **Permanent**: Wards do not expire or take damage.

## Vision is not shared among allies

Vision per champion is only their own, plus their own ward. You cannot see what your ally champions see, nor their wards. However, if you spot something of note, you can use the shared memory to try to communicate the information to your team.

---

**See also:** [Items & gold](./08-items.md) · [Shared memory](./12-shared-memory.md) · [Maps & movement](./04-maps-and-movement.md)

<sub>Engine sources cited by the handbook: `game/Engine/src/Game/World.cpp`, `game/Engine/src/Core/ShadowCast.cpp`, `game/Engine/include/private_cpp/Engine/Map.h`, `game/Engine/src/Game/PlacedConsumables.cpp`, `game/Engine/include/private_cpp/Engine/Balance/GameSettings.h`, `game/Engine/readme.md`</sub>
