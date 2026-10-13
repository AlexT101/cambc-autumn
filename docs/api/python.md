# Bot API reference: Python

*Public Python SDK functions and methods.*

Start with [Getting Started](../guides/python/first-bot.md). Other languages: [C++](./cpp.md) · [Rust](./rust.md) · [OCaml](./ocaml.md).

## Contents

- [cambc](#cambc) (8)
- [cambc.Ability](#cambc-ability) (30)
- [cambc.AbilityKind](#cambc-abilitykind) (1)
- [cambc.AbilityTargetMask](#cambc-abilitytargetmask) (17)
- [cambc.AltarLock](#cambc-altarlock) (5)
- [cambc.Bitboard](#cambc-bitboard) (47)
- [cambc.BuffCollection](#cambc-buffcollection) (9)
- [cambc.BuffRestrictions](#cambc-buffrestrictions) (17)
- [cambc.BuffTypes](#cambc-bufftypes) (1)
- [cambc.Camp](#cambc-camp) (20)
- [cambc.CampType](#cambc-camptype) (1)
- [cambc.Champion](#cambc-champion) (59)
- [cambc.ChampionDraft](#cambc-championdraft) (1)
- [cambc.ChampionState](#cambc-championstate) (18)
- [cambc.ChampionType](#cambc-championtype) (1)
- [cambc.Consumable](#cambc-consumable) (7)
- [cambc.ConsumableType](#cambc-consumabletype) (6)
- [cambc.debug](#cambc-debug) (2)
- [cambc.DistanceField](#cambc-distancefield) (22)
- [cambc.draft](#cambc-draft) (3)
- [cambc.DraftMemoryBuffer](#cambc-draftmemorybuffer) (7)
- [cambc.Error](#cambc-error) (2)
- [cambc.ErrorCode](#cambc-errorcode) (1)
- [cambc.game_map](#cambc-game-map) (14)
- [cambc.game_map.CampGroup](#cambc-game-map-campgroup) (13)
- [cambc.ItemPassive](#cambc-itempassive) (1)
- [cambc.ItemType](#cambc-itemtype) (13)
- [cambc.PassiveType](#cambc-passivetype) (1)
- [cambc.SharedMemoryBuffer](#cambc-sharedmemorybuffer) (6)
- [cambc.Symmetry](#cambc-symmetry) (1)
- [cambc.Team](#cambc-team) (3)
- [cambc.Teleport](#cambc-teleport) (8)
- [cambc.Unit](#cambc-unit) (13)
- [cambc.Vec2](#cambc-vec2) (20)
- [cambc.vision](#cambc-vision) (28)
- [cambc.Ward](#cambc-ward) (9)

<a id="cambc"></a>

## cambc

### champions

```python
def champions(team: Optional[Team] = None) -> list[Champion]
```

Visible champions of a team, or of both teams (allies first). Args: team: Team to include, or None for both teams.

### end_turn

```python
def end_turn() -> None
```

End the current turn.

*Example: Stop optional planning when little fuel remains and yield the current turn.*

```python
if bc.fuel_remaining() < 1000:
    bc.end_turn()
```

### fuel_remaining

```python
def fuel_remaining() -> int
```

Return the fuel left in the current turn.

*Example: Stop optional planning when little fuel remains and yield the current turn.*

```python
if bc.fuel_remaining() < 1000:
    bc.end_turn()
```

### global_submitted_gems

```python
def global_submitted_gems(team: Team) -> int
```

Return the total gems a team has tributed. Args: team: Team to count.

### is_draft

```python
def is_draft() -> bool
```

Return whether this bot instance is running the draft rather than controlling a champion.

### me

```python
def me() -> Champion
```

This bot's champion; raises ValueError during the draft.

### resign

```python
def resign() -> None
```

### round_number

```python
def round_number() -> int
```

Return the current round number.

<a id="cambc-ability"></a>

## cambc.Ability

### __eq__

```python
def __eq__(self, other: object) -> bool
```

### __hash__

```python
def __hash__(self) -> int
```

### __init__

```python
def __init__(self) -> None
```

### __repr__

```python
def __repr__(self) -> str
```

### can_target_allies

```python
def can_target_allies(self) -> bool
```

Return whether the ability can target allied champions.

### can_target_camps

```python
def can_target_camps(self) -> bool
```

Return whether the ability can target camps.

### can_target_enemies

```python
def can_target_enemies(self) -> bool
```

Return whether the ability can target enemy champions.

### can_target_ground

```python
def can_target_ground(self) -> bool
```

Return whether the ability can target a tile.

### can_target_self

```python
def can_target_self(self) -> bool
```

Return whether the ability can target its caster.

### cooldown

```python
def cooldown(self) -> int
```

Return the remaining cooldown; 0 means ready.

### damage_amount

```python
def damage_amount(self, target: Optional[Champion] = None) -> float
```

Return the damage the ability would deal, after mitigation and shields if a target is given. Args: target: Optional visible champion that would be hit.

### get

```python
def get(self, kind: type[_A]) -> _A
```

Return the ability's payload of the requested kind; raises if the slot holds a different kind. Args: kind: Ability kind to extract.

### has

```python
def has(self, kind: Union[AbilityKind, type[AbilityInfo]]) -> bool
```

Return whether the slot holds an ability of a kind. Args: kind: Ability kind to test for.

### heal_amount

```python
def heal_amount(self, target: Optional[Champion] = None) -> float
```

Return the healing the ability would do, capped at the target's missing health if a target is given. Args: target: Optional visible champion that would be healed.

### info

```python
def info(self, kind: Optional[AbilityKind] = None) -> Optional[AbilityInfo]
```

Ability properties, or None for an empty slot; with kind, require that kind. Args: kind: Optional ability kind the slot must have; raises if it differs.

### is_aoe_damage

```python
def is_aoe_damage(self) -> bool
```

Check whether this is an area-damage ability.

### is_attack_reset

```python
def is_attack_reset(self) -> bool
```

Check whether this is an attack-reset ability.

### is_cc

```python
def is_cc(self) -> bool
```

Check whether this is a crowd-control ability.

### is_damage

```python
def is_damage(self) -> bool
```

Check whether this is a damage ability.

### is_dash

```python
def is_dash(self) -> bool
```

Check whether this is a dash ability.

### is_heal

```python
def is_heal(self) -> bool
```

Check whether this is a healing ability.

### is_on_cooldown

```python
def is_on_cooldown(self) -> bool
```

Return whether the cooldown is still running.

### is_ready

```python
def is_ready(self) -> bool
```

Check whether this ability is ready to cast.

### is_shield

```python
def is_shield(self) -> bool
```

Check whether this is a shield ability.

### mask_into

```python
def mask_into(self, out: Bitboard) -> None
```

Like valid_tiles, but writes into out. Args: out: Destination Bitboard; its previous contents are overwritten.

### shield_amount

```python
def shield_amount(self, target: Optional[Champion] = None) -> float
```

Return the shield the ability would grant. Args: target: Optional visible champion that would be shielded.

### slot

```python
def slot(self) -> int
```

Return the ability's slot index on its champion.

### use

```python
def use(self, target: Optional[Union[Unit, Vec2]] = None) -> bool
```

Cast on a unit, at a ground tile, or without a target. Unit casts land on the target's tile. Returns False for a newly revealed obstruction; known invalid targets raise Error. Args: target: Champion or camp to cast on, a tile to cast at, or None for an untargeted ability.

### valid_targets

```python
def valid_targets(self) -> AbilityTargetMask
```

Return the categories of target the ability accepts.

### valid_tiles

```python
def valid_tiles(self) -> Bitboard
```

Return the tiles within casting range; does not check visibility or occupancy.

<a id="cambc-abilitykind"></a>

## cambc.AbilityKind

### to_string

```python
def to_string(value: int) -> str
```

<a id="cambc-abilitytargetmask"></a>

## cambc.AbilityTargetMask

### __and__

```python
def __and__(self, other: int) -> Self
```

### __contains__

```python
def __contains__(self, flags: Self) -> bool
```

### __invert__

```python
def __invert__(self) -> Self
```

### __iter__

```python
def __iter__(self) -> Iterator[Self]
```

### __or__

```python
def __or__(self, other: int) -> Self
```

### __rand__

```python
def __rand__(self, other: int) -> Self
```

### __ror__

```python
def __ror__(self, other: int) -> Self
```

### __rsub__

```python
def __rsub__(self, other: int) -> Self
```

### __rxor__

```python
def __rxor__(self, other: int) -> Self
```

### __sub__

```python
def __sub__(self, other: int) -> Self
```

### __xor__

```python
def __xor__(self, other: int) -> Self
```

### all

```python
def all(cls) -> Self
```

Return a set with every named flag.

### empty

```python
def empty(cls) -> Self
```

Return a set with no flags.

### from_bits

```python
def from_bits(cls, bits: int) -> Optional[Self]
```

Return the set for raw bits, or None if any bit is not a named flag. Args: bits: Raw flag bits.

### from_bits_truncate

```python
def from_bits_truncate(cls, bits: int) -> Self
```

Return the set for raw bits, dropping bits that are not named flags. Args: bits: Raw flag bits.

### intersects

```python
def intersects(self, flags: Self) -> bool
```

Return whether this set shares any flag with flags. Args: flags: Flags to test.

### is_all

```python
def is_all(self) -> bool
```

Return whether every named flag is set.

<a id="cambc-altarlock"></a>

## cambc.AltarLock

### hits_remaining

```python
def hits_remaining(self) -> int
```

Return how many hits the altar lock can still take.

### is_ally

```python
def is_ally(self) -> bool
```

Check whether this altar lock belongs to the observing team.

### is_enemy

```python
def is_enemy(self) -> bool
```

Check whether this altar lock belongs to the opposing team.

### position

```python
def position(self) -> Vec2
```

Return the altar lock's tile.

### team

```python
def team(self) -> Team
```

Return the team that owns the altar lock.

<a id="cambc-bitboard"></a>

## cambc.Bitboard

### __and__

```python
def __and__(self, other: Bitboard) -> Bitboard
```

### __eq__

```python
def __eq__(self, other: object) -> bool
```

### __iand__

```python
def __iand__(self, other: Bitboard) -> Self
```

### __init__

```python
def __init__(self) -> None
```

### __invert__

```python
def __invert__(self) -> Bitboard
```

### __ior__

```python
def __ior__(self, other: Bitboard) -> Self
```

### __ixor__

```python
def __ixor__(self, other: Bitboard) -> Self
```

### __or__

```python
def __or__(self, other: Bitboard) -> Bitboard
```

### __xor__

```python
def __xor__(self, other: Bitboard) -> Bitboard
```

### clear

```python
def clear(self) -> None
```

Clear every tile.

### copy

```python
def copy(self) -> Bitboard
```

Return an independent copy.

### count

```python
def count(self) -> int
```

Return the number of set tiles.

### draw_chebyshev

```python
def draw_chebyshev(self, center: Vec2, radius: float) -> None
```

Set every tile within a Chebyshev radius of a centre tile. Args: center: Centre tile. radius: Chebyshev radius in tiles.

### draw_circle

```python
def draw_circle(self, center: Vec2, radius: float) -> None
```

Set every tile within a Euclidean radius of a centre tile. Args: center: Centre tile. radius: Euclidean radius in tiles.

### export_linear_buffer

```python
def export_linear_buffer(self) -> bytes
```

Return the contents as a row-major buffer with one value per tile.

### export_linear_buffer_into

```python
def export_linear_buffer_into(self, out: Buffer) -> None
```

Write the contents as a row-major buffer with one value per tile. Args: out: Writable bytes-like object exactly linear_buffer_size() long.

### export_raw_buffer

```python
def export_raw_buffer(self) -> bytes
```

Return the contents as an engine-chunked buffer.

### export_raw_buffer_into

```python
def export_raw_buffer_into(self, out: Buffer) -> None
```

Write the contents as an engine-chunked buffer. Args: out: Writable bytes-like object exactly raw_buffer_size() long.

### fill

```python
def fill(self) -> None
```

Set every tile on the map.

### height

```python
def height(self) -> int
```

Return the map height in tiles.

### import_linear_buffer

```python
def import_linear_buffer(self, data: Buffer) -> None
```

Replace the contents from a row-major buffer with one value per tile. Args: data: Bytes-like object exactly linear_buffer_size() long.

### import_raw_buffer

```python
def import_raw_buffer(self, data: Buffer) -> None
```

Replace the contents from an engine-chunked buffer. Args: data: Bytes-like object exactly raw_buffer_size() long.

### is_empty

```python
def is_empty(self) -> bool
```

Return whether no tile is set.

### is_set

```python
def is_set(self, position: Vec2) -> bool
```

Return whether the tile is set; raises Error outside the map. Args: position: Tile to query.

### linear_buffer_size

```python
def linear_buffer_size() -> int
```

Return the size in bytes of the row-major buffer.

### positions

```python
def positions(self) -> list[Vec2]
```

Return the set tiles in row-major order.

### print

```python
def print(self) -> None
```

Print this board to stdout for debugging.

### raw_buffer_size

```python
def raw_buffer_size() -> int
```

Return the size in bytes of the engine-chunked buffer.

### reachable_tiles

```python
def reachable_tiles( self, origin: Vec2, distance: int, frontier: Optional[Bitboard] = None, scratch: Optional[Bitboard] = None ) -> Bitboard
```

Return the tiles reachable from origin, treating this board as walls. Args: origin: Start tile. distance: Maximum number of 8-directional steps from origin. frontier: Optional working Bitboard; its contents are overwritten. scratch: Optional working Bitboard; its contents are overwritten.

### reachable_tiles_into

```python
def reachable_tiles_into( self, origin: Vec2, distance: int, out: Bitboard, frontier: Optional[Bitboard] = None, scratch: Optional[Bitboard] = None ) -> None
```

Like reachable_tiles, but writes into out. Args: origin: Start tile. distance: Maximum number of 8-directional steps from origin. out: Destination; its previous contents are overwritten. frontier: Optional working Bitboard; its contents are overwritten. scratch: Optional working Bitboard; its contents are overwritten.

### reflect

```python
def reflect(self, symmetry: int) -> Bitboard
```

Return a copy transformed by a map symmetry. Args: symmetry: Map symmetry to apply.

### reflect_horizontal

```python
def reflect_horizontal(self) -> Bitboard
```

Return a copy reflected across the map horizontally, reversing x.

### reflect_horizontal_into

```python
def reflect_horizontal_into(self, out: Bitboard) -> None
```

Like reflect_horizontal, but writes into out. Args: out: Destination; its previous contents are overwritten.

### reflect_into

```python
def reflect_into(self, symmetry: int, out: Bitboard) -> None
```

Like reflect, but writes into out. Args: symmetry: Map symmetry to apply. out: Destination; its previous contents are overwritten.

### reflect_vertical

```python
def reflect_vertical(self) -> Bitboard
```

Return a copy reflected across the map vertically, reversing y.

### reflect_vertical_into

```python
def reflect_vertical_into(self, out: Bitboard) -> None
```

Like reflect_vertical, but writes into out. Args: out: Destination; its previous contents are overwritten.

### rotate_180

```python
def rotate_180(self) -> Bitboard
```

Return a copy rotated 180 degrees within the map.

### rotate_180_into

```python
def rotate_180_into(self, out: Bitboard) -> None
```

Like rotate_180, but writes into out. Args: out: Destination; its previous contents are overwritten.

### set

```python
def set(self, position: Vec2, value: bool = True) -> None
```

Set or clear a tile; raises Error outside the map. Args: position: Tile to update. value: True to set the tile, False to clear it.

### shadow_cast

```python
def shadow_cast(self, origin: Vec2, distance: int) -> Bitboard
```

Return the tiles visible from origin, treating this board as opaque walls. Args: origin: Viewer tile. distance: Maximum sight radius in tiles.

### shadow_cast_into

```python
def shadow_cast_into(self, origin: Vec2, distance: int, out: Bitboard) -> None
```

Like shadow_cast, but writes into out. Args: origin: Viewer tile. distance: Maximum sight radius in tiles. out: Destination; its previous contents are overwritten.

### shift_right

```python
def shift_right(self, count: int) -> Bitboard
```

Return a copy shifted horizontally; tiles shifted off the map are dropped. Args: count: Columns to shift; negative values shift left.

### shift_right_into

```python
def shift_right_into(self, count: int, out: Bitboard) -> None
```

Like shift_right, but writes into out. Args: count: Columns to shift; negative values shift left. out: Destination; its previous contents are overwritten.

### shift_up

```python
def shift_up(self, count: int) -> Bitboard
```

Return a copy shifted vertically; tiles shifted off the map are dropped. Args: count: Rows to shift; negative values shift down.

### shift_up_into

```python
def shift_up_into(self, count: int, out: Bitboard) -> None
```

Like shift_up, but writes into out. Args: count: Rows to shift; negative values shift down. out: Destination; its previous contents are overwritten.

### toggle

```python
def toggle(self, position: Vec2) -> None
```

Flip a tile; raises Error outside the map. Args: position: Tile to flip.

### width

```python
def width(self) -> int
```

Return the map width in tiles.

<a id="cambc-buffcollection"></a>

## cambc.BuffCollection

### __init__

```python
def __init__(self, buffs: list[Optional[Buff]], present: tuple[Buff, ...]) -> None
```

### __iter__

```python
def __iter__(self) -> Iterator[Buff]
```

### __len__

```python
def __len__(self) -> int
```

### get

```python
def get(self, kind: Union[int, type[Buff]]) -> Buff
```

Return the captured buff of a kind; raises KeyError if it was absent. Args: kind: Buff kind to look up.

### has

```python
def has(self, kind: Union[int, type[Buff]]) -> bool
```

Return whether a buff of a kind was active when the collection was captured. Args: kind: Buff kind to test for.

### has_enhanced_attack

```python
def has_enhanced_attack(self) -> bool
```

Check whether the captured collection has an enhanced-attack buff.

### has_shield

```python
def has_shield(self) -> bool
```

Check whether the captured collection has a shield buff.

### has_stun

```python
def has_stun(self) -> bool
```

Check whether the captured collection has a stun buff.

### is_empty

```python
def is_empty(self) -> bool
```

Return whether no buffs were active when the collection was captured.

<a id="cambc-buffrestrictions"></a>

## cambc.BuffRestrictions

### __and__

```python
def __and__(self, other: int) -> Self
```

### __contains__

```python
def __contains__(self, flags: Self) -> bool
```

### __invert__

```python
def __invert__(self) -> Self
```

### __iter__

```python
def __iter__(self) -> Iterator[Self]
```

### __or__

```python
def __or__(self, other: int) -> Self
```

### __rand__

```python
def __rand__(self, other: int) -> Self
```

### __ror__

```python
def __ror__(self, other: int) -> Self
```

### __rsub__

```python
def __rsub__(self, other: int) -> Self
```

### __rxor__

```python
def __rxor__(self, other: int) -> Self
```

### __sub__

```python
def __sub__(self, other: int) -> Self
```

### __xor__

```python
def __xor__(self, other: int) -> Self
```

### all

```python
def all(cls) -> Self
```

Return a set with every named flag.

### empty

```python
def empty(cls) -> Self
```

Return a set with no flags.

### from_bits

```python
def from_bits(cls, bits: int) -> Optional[Self]
```

Return the set for raw bits, or None if any bit is not a named flag. Args: bits: Raw flag bits.

### from_bits_truncate

```python
def from_bits_truncate(cls, bits: int) -> Self
```

Return the set for raw bits, dropping bits that are not named flags. Args: bits: Raw flag bits.

### intersects

```python
def intersects(self, flags: Self) -> bool
```

Return whether this set shares any flag with flags. Args: flags: Flags to test.

### is_all

```python
def is_all(self) -> bool
```

Return whether every named flag is set.

<a id="cambc-bufftypes"></a>

## cambc.BuffTypes

### to_string

```python
def to_string(value: int) -> str
```

<a id="cambc-camp"></a>

## cambc.Camp

### __eq__

```python
def __eq__(self, other: object) -> bool
```

### __hash__

```python
def __hash__(self) -> int
```

### __index__

```python
def __index__(self) -> int
```

### __repr__

```python
def __repr__(self) -> str
```

### attack_range

```python
def attack_range(self) -> int
```

Return the attack range in Chebyshev tiles; melee camps have range 1.

### base_stats

```python
def base_stats(self) -> CampStats
```

Return the camp type's design stats.

### camp_group

```python
def camp_group(self) -> game_map.CampGroup
```

Return the group this camp belongs to.

### focus

```python
def focus(self) -> float
```

Return current focus; raises Error if the unit is not visible.

### health

```python
def health(self) -> float
```

Return current health; raises Error if the unit is not visible.

### is_elk

```python
def is_elk(self) -> bool
```

Check whether this camp is an elk.

### is_gem_cluster

```python
def is_gem_cluster(self) -> bool
```

Check whether this camp is a gem cluster.

### is_gold_cluster

```python
def is_gold_cluster(self) -> bool
```

Check whether this camp is a gold cluster.

### is_monolith

```python
def is_monolith(self) -> bool
```

Check whether this camp is a monolith.

### is_visible

```python
def is_visible(self) -> bool
```

Return whether the camp is currently visible.

### is_wolf

```python
def is_wolf(self) -> bool
```

Check whether this camp is a wolf.

### kind

```python
def kind(self) -> CampType
```

Return the camp's type.

### max_health

```python
def max_health(self) -> float
```

Return current maximum health; raises Error if the unit is not visible.

### position

```python
def position(self) -> Vec2
```

Return the current tile; raises Error if the unit is not visible.

### spawn_position

```python
def spawn_position(self) -> Vec2
```

Return the camp's spawn tile, not its live position.

### strength

```python
def strength(self) -> float
```

Return current strength; raises Error if the unit is not visible.

<a id="cambc-camptype"></a>

## cambc.CampType

### to_string

```python
def to_string(value: int) -> str
```

<a id="cambc-champion"></a>

## cambc.Champion

### __eq__

```python
def __eq__(self, other: object) -> bool
```

### __hash__

```python
def __hash__(self) -> int
```

### __index__

```python
def __index__(self) -> int
```

### __repr__

```python
def __repr__(self) -> str
```

### abilities

```python
def abilities(self) -> tuple[Ability, Ability]
```

Return the champion's ability slots.

### attack

```python
def attack(self, target: Union[Unit, AltarLock]) -> None
```

Basic-attack a visible champion, camp or altar lock in range; requires self. Args: target: Unit or altar lock to attack.

### attack_range

```python
def attack_range(self) -> int
```

Return the attack range in Chebyshev tiles; melee champions have range 1.

### base_stats

```python
def base_stats(self) -> ChampionStats
```

Return the champion type's design stats.

### buy

```python
def buy(self, kind: Union[ItemType, ConsumableType], count: int = 1) -> None
```

Buy count items, or one consumable. Args: kind: Item or consumable to buy. count: Number of items to buy; consumables are bought one at a time.

### can_attack

```python
def can_attack(self) -> bool
```

Check whether this champion can attack.

*Example: Check the action allowance before spending fuel to choose an attack target.*

```python
me = bc.me()
action_available = me.can_attack()
```

### can_buy

```python
def can_buy(self, item: Union[ItemType, ConsumableType], count: object = _COUNT_OMITTED) -> bool
```

Return whether the champion can buy an item or consumable in its current state. Args: item: Item or consumable to buy. count: Number of copies to buy.

### can_cast

```python
def can_cast(self) -> bool
```

Check whether this champion can cast.

*Example: Check the action allowance before spending fuel to evaluate ready abilities.*

```python
me = bc.me()
action_available = me.can_cast()
```

### can_move

```python
def can_move(self) -> bool
```

Check whether this champion can move.

*Example: Check the action allowance before spending fuel to plan a path.*

```python
me = bc.me()
action_available = me.can_move()
```

### can_sell

```python
def can_sell(self) -> bool
```

Return whether the champion can sell items in its current state.

### cancel_recall

```python
def cancel_recall(self) -> None
```

Cancel the current recall; requires self.

### cancel_submit_gems

```python
def cancel_submit_gems(self) -> None
```

Cancel the current tribute; requires self.

### champion_name

```python
def champion_name(self) -> ChampionType
```

Return the champion's type.

### consumables

```python
def consumables(self) -> tuple[Consumable, ...]
```

Consumable slots, indexed by ConsumableType.

### design

```python
def design(cls, kind: ChampionType) -> Champion
```

Static design of a champion type, as used during the draft. Args: kind: Champion type to describe.

### end_turn

```python
def end_turn(self) -> None
```

End the turn now; requires self.

### focus

```python
def focus(self) -> float
```

Return current focus; raises Error if the unit is not visible.

### gem_count

```python
def gem_count(self) -> int
```

Return the gems the champion is carrying.

### gold_count

```python
def gold_count(self) -> int
```

Return the gold the champion is carrying.

### has_completed_turn

```python
def has_completed_turn(self) -> bool
```

Check whether this champion has completed its turn.

### health

```python
def health(self) -> float
```

Return current health; raises Error if the unit is not visible.

*Example: Recall when badly injured and safe from interruption.*

```python
me = bc.me()
if safe_to_recall and me.health() < me.max_health() * 0.3:
    me.recall()
```

### is_alive

```python
def is_alive(self) -> bool
```

Return whether the champion is alive.

### is_ally

```python
def is_ally(self) -> bool
```

Check whether this champion belongs to the observing team.

### is_enemy

```python
def is_enemy(self) -> bool
```

Check whether this champion belongs to the opposing team.

### is_recalling

```python
def is_recalling(self) -> bool
```

Check whether this champion is recalling.

### is_submitting_gems

```python
def is_submitting_gems(self) -> bool
```

Check whether this champion is submitting gems.

### is_teleporting

```python
def is_teleporting(self) -> bool
```

Check whether this champion is teleporting.

### is_visible

```python
def is_visible(self) -> bool
```

Return whether the champion is currently visible.

### item_count

```python
def item_count(self) -> list[int]
```

Carried item counts, indexed by ItemType.

### max_health

```python
def max_health(self) -> float
```

Return current maximum health; raises Error if the unit is not visible.

*Example: Recall when badly injured and safe from interruption.*

```python
me = bc.me()
if safe_to_recall and me.health() < me.max_health() * 0.3:
    me.recall()
```

### move

```python
def move(self, delta: Vec2) -> bool
```

Return False for a newly revealed obstruction; known invalid destinations raise Error. Args: delta: Displacement from the current position.

*Example: Take a planned step; false means no movement occurred.*

```python
me = bc.me()
if me.can_move():
    moved = me.move(direction)
```

### move_absolute

```python
def move_absolute(self, destination: Vec2) -> bool
```

Return False for a newly revealed obstruction; known invalid destinations raise Error. Args: destination: Map tile to move to.

*Example: Take a planned step; false means no movement occurred.*

```python
me = bc.me()
if me.can_move():
    moved = me.move_absolute(destination)
```

### move_towards

```python
def move_towards(self, target: Vec2) -> bool
```

Move to the reachable tile on a shortest path to target, avoiding walls, holes, altars, the enemy spawn and visible units. Return False without moving when already there, unable to move, or target is blocked or unreachable, and for a newly revealed obstruction. Args: target: Map tile to approach.

*Example: Take a planned step; false means no movement occurred.*

```python
me = bc.me()
if me.can_move():
    moved = me.move_towards(destination)
```

### passive

```python
def passive(self) -> PassiveType
```

Return the champion's passive.

### place_ward

```python
def place_ward(self, destination: Vec2) -> bool
```

Return False for a newly revealed obstruction; known invalid destinations raise Error. Args: destination: Tile to place the ward on.

### position

```python
def position(self) -> Vec2
```

Return the current tile; raises Error if the unit is not visible.

### prev_priority

```python
def prev_priority(self) -> int
```

Return the priority used for the current round.

### priority

```python
def priority(self) -> int
```

Return the priority that will apply from the next round.

### recall

```python
def recall(self) -> None
```

Start channelling a recall to the team spawn; requires self.

*Example: Recall when badly injured and safe from interruption.*

```python
me = bc.me()
if safe_to_recall and me.health() < me.max_health() * 0.3:
    me.recall()
```

### remaining_channel_time

```python
def remaining_channel_time(self) -> int
```

Return the rounds left on the current recall, tribute or teleport channel.

### restrictions

```python
def restrictions(self) -> BuffRestrictions
```

Return the actions the champion's buffs currently prohibit.

### sell

```python
def sell(self, kind: ItemType, count: int = 1) -> None
```

Sell items; requires self and the engine validates location and inventory. Args: kind: Item to sell. count: Number of copies to sell.

### set_priority

```python
def set_priority(self, priority: int) -> None
```

Set the champion's scheduling priority; requires self. Args: priority: New priority; takes effect from the next round and persists.

### state

```python
def state(self) -> ChampionState
```

Return the champion's life, channel and action flags.

### strength

```python
def strength(self) -> float
```

Return current strength; raises Error if the unit is not visible.

### submit_gems

```python
def submit_gems(self, altar: Vec2) -> None
```

Start tributing carried gems at an altar; requires self. Args: altar: Altar tile to tribute at.

### team

```python
def team(self) -> Team
```

Return the champion's team.

### visible_tiles

```python
def visible_tiles(self) -> Bitboard
```

Current vision for this champion.

### visible_tiles_from

```python
def visible_tiles_from(self, position: Vec2) -> Bitboard
```

Vision this champion would have at position. Args: position: Hypothetical tile to see from.

### visible_tiles_from_into

```python
def visible_tiles_from_into(self, position: Vec2, out: Bitboard) -> None
```

Like visible_tiles_from, but writes into out. Args: position: Hypothetical tile to see from. out: Destination Bitboard; its previous contents are overwritten.

### visible_tiles_into

```python
def visible_tiles_into(self, out: Bitboard) -> None
```

Like visible_tiles, but writes into out. Args: out: Destination Bitboard; its previous contents are overwritten.

### ward_cooldown

```python
def ward_cooldown(self) -> int
```

Return the rounds until another ward can be placed.

### ward_placement_tiles

```python
def ward_placement_tiles(self) -> Bitboard
```

Return the tiles where this champion could place a ward now.

### ward_placement_tiles_into

```python
def ward_placement_tiles_into(self, out: Bitboard) -> None
```

Like ward_placement_tiles, but writes into out. Args: out: Destination Bitboard; its previous contents are overwritten.

### ward_positions

```python
def ward_positions(self) -> list[Vec2]
```

Return the tiles of this champion's placed wards.

<a id="cambc-championdraft"></a>

## cambc.ChampionDraft

### to_string

```python
def to_string(value: int) -> str
```

<a id="cambc-championstate"></a>

## cambc.ChampionState

### __and__

```python
def __and__(self, other: int) -> Self
```

### __contains__

```python
def __contains__(self, flags: Self) -> bool
```

### __invert__

```python
def __invert__(self) -> Self
```

### __iter__

```python
def __iter__(self) -> Iterator[Self]
```

### __or__

```python
def __or__(self, other: int) -> Self
```

### __rand__

```python
def __rand__(self, other: int) -> Self
```

### __ror__

```python
def __ror__(self, other: int) -> Self
```

### __rsub__

```python
def __rsub__(self, other: int) -> Self
```

### __rxor__

```python
def __rxor__(self, other: int) -> Self
```

### __sub__

```python
def __sub__(self, other: int) -> Self
```

### __xor__

```python
def __xor__(self, other: int) -> Self
```

### all

```python
def all(cls) -> Self
```

Return a set with every named flag.

### empty

```python
def empty(cls) -> Self
```

Return a set with no flags.

### from_bits

```python
def from_bits(cls, bits: int) -> Optional[Self]
```

Return the set for raw bits, or None if any bit is not a named flag. Args: bits: Raw flag bits.

### from_bits_truncate

```python
def from_bits_truncate(cls, bits: int) -> Self
```

Return the set for raw bits, dropping bits that are not named flags. Args: bits: Raw flag bits.

### intersects

```python
def intersects(self, flags: Self) -> bool
```

Return whether this set shares any flag with flags. Args: flags: Flags to test.

### is_all

```python
def is_all(self) -> bool
```

Return whether every named flag is set.

### is_dead

```python
def is_dead(self) -> bool
```

<a id="cambc-championtype"></a>

## cambc.ChampionType

### to_string

```python
def to_string(value: int) -> str
```

<a id="cambc-consumable"></a>

## cambc.Consumable

### __eq__

```python
def __eq__(self, other: object) -> bool
```

### __hash__

```python
def __hash__(self) -> int
```

### __init__

```python
def __init__(self) -> None
```

### __repr__

```python
def __repr__(self) -> str
```

### count

```python
def count(self) -> int
```

Return how many the champion is carrying.

### kind

```python
def kind(self) -> ConsumableType
```

Return the consumable's type.

### use

```python
def use(self, destination: Optional[Vec2] = None) -> bool
```

Return False for a newly revealed obstruction; known invalid destinations raise Error. Args: destination: Tile to use the consumable at.

<a id="cambc-consumabletype"></a>

## cambc.ConsumableType

### __new__

```python
def __new__(cls, value: int) -> ConsumableType
```

### __repr__

```python
def __repr__(self) -> str
```

### carry_limit

```python
def carry_limit(self) -> int
```

Return how many a champion can carry at once.

### cost

```python
def cost(self) -> int
```

Return the gold cost to buy one.

### info

```python
def info(self) -> ConsumableInfo
```

Return the consumable's static design data.

### name

```python
def name(self) -> str
```

Return the consumable's display name.

<a id="cambc-debug"></a>

## cambc.debug

### draw_dot

```python
def draw_dot(position: Vec2, rgb: int) -> None
```

Draw a debug dot in the replay. Args: position: Tile to mark. rgb: Packed 0xRRGGBB colour.

*Example: Mark a decision in your replay debug overlay to understand the bot's route or target.*

```python
bc.debug.draw_dot(position, rgb)
```

### draw_line

```python
def draw_line(start: Vec2, end: Vec2, rgb: int) -> None
```

Draw a debug line in the replay. Args: start: Start tile. end: End tile. rgb: Packed 0xRRGGBB colour.

*Example: Mark a decision in your replay debug overlay to understand the bot's route or target.*

```python
bc.debug.draw_line(start, end, rgb)
```

<a id="cambc-distancefield"></a>

## cambc.DistanceField

### __eq__

```python
def __eq__(self, other: object) -> bool
```

### __init__

```python
def __init__(self) -> None
```

### compute

```python
def compute(self, walls: Bitboard, roots: Bitboard, visited: Bitboard, max_distance: int = ...) -> None
```

Compute distances from roots around walls into this field. Args: walls: Impassable tiles. roots: Tiles at distance zero. visited: Receives the tiles the search reached. max_distance: Tiles farther than this are left unreached.

*Example: Find a step towards the goal tiles. The result is a direction for move.*

```python
field = bc.DistanceField()
field.compute(blocked, goals, bc.Bitboard())
direction = field.next_move_from(bc.me().position())
```

### compute_to

```python
def compute_to( self, walls: Bitboard, roots: Bitboard, destinations: Bitboard, visited: Bitboard, max_distance: int = ... ) -> None
```

Compute distances from roots until destinations are reached or the search is exhausted. Args: walls: Impassable tiles. roots: Tiles at distance zero. destinations: The search stops once these tiles are reached. visited: Receives the tiles the search reached. max_distance: Tiles farther than this are left unreached.

### compute_to_with_expansion_count

```python
def compute_to_with_expansion_count( self, walls: Bitboard, roots: Bitboard, destinations: Bitboard, visited: Bitboard, max_distance: int = ... ) -> int
```

Like compute_to, but return the number of tiles the search expanded. Args: walls: Impassable tiles. roots: Tiles at distance zero. destinations: The search stops once these tiles are reached. visited: Receives the tiles the search reached. max_distance: Tiles farther than this are left unreached.

### compute_with_expansion_count

```python
def compute_with_expansion_count( self, walls: Bitboard, roots: Bitboard, visited: Bitboard, max_distance: int = ... ) -> int
```

Like compute, but return the number of tiles the search expanded. Args: walls: Impassable tiles. roots: Tiles at distance zero. visited: Receives the tiles the search reached. max_distance: Tiles farther than this are left unreached.

### copy

```python
def copy(self) -> DistanceField
```

Return an independent copy.

### export_linear_buffer

```python
def export_linear_buffer(self) -> bytes
```

Return the contents as a row-major buffer with one value per tile.

### export_linear_buffer_into

```python
def export_linear_buffer_into(self, out: Buffer) -> None
```

Write the contents as a row-major buffer with one value per tile. Args: out: Writable bytes-like object exactly linear_buffer_size() long.

### export_raw_buffer

```python
def export_raw_buffer(self) -> bytes
```

Return the contents as an engine-chunked buffer.

### export_raw_buffer_into

```python
def export_raw_buffer_into(self, out: Buffer) -> None
```

Write the contents as an engine-chunked buffer. Args: out: Writable bytes-like object exactly raw_buffer_size() long.

### get

```python
def get(self, position: Vec2) -> int
```

Return the distance stored at a tile; raises Error outside the map. Args: position: Tile to query.

### height

```python
def height(self) -> int
```

Return the map height in tiles.

### import_linear_buffer

```python
def import_linear_buffer(self, data: Buffer) -> None
```

Replace the contents from a row-major buffer with one value per tile. Args: data: Bytes-like object exactly linear_buffer_size() long.

### import_raw_buffer

```python
def import_raw_buffer(self, data: Buffer) -> None
```

Replace the contents from an engine-chunked buffer. Args: data: Bytes-like object exactly raw_buffer_size() long.

### linear_buffer_size

```python
def linear_buffer_size() -> int
```

Return the size in bytes of the row-major buffer.

### next_move_from

```python
def next_move_from(self, position: Vec2) -> Optional[Vec2]
```

Return the first optimal step towards a root as a direction delta, or None at a root or unreached tile. Args: position: Tile to step from.

*Example: Find a step towards the goal tiles. The result is a direction for move.*

```python
field = bc.DistanceField()
field.compute(blocked, goals, bc.Bitboard())
direction = field.next_move_from(bc.me().position())
```

### next_moves_from

```python
def next_moves_from(self, position: Vec2) -> list[Vec2]
```

Return every optimal step towards a root as direction deltas, in compass order from north. Args: position: Tile to step from.

### print

```python
def print(self) -> None
```

Print this board to stdout for debugging.

### raw_buffer_size

```python
def raw_buffer_size() -> int
```

Return the size in bytes of the engine-chunked buffer.

### set

```python
def set(self, position: Vec2, value: int) -> None
```

Store a distance at a tile; raises Error outside the map. Args: position: Tile to update. value: Distance to store.

### width

```python
def width(self) -> int
```

Return the map width in tiles.

<a id="cambc-draft"></a>

## cambc.draft

### current_draft

```python
def current_draft(team: Team) -> list[ChampionDraft]
```

Picks a team has made so far, in order. Args: team: Team whose picks to return.

### pick

```python
def pick(champion: ChampionDraft) -> None
```

Pick a champion for the current draft round; only valid during the draft. Args: champion: Champion to pick.

### team_size

```python
def team_size() -> int
```

Champions each team drafts.

<a id="cambc-draftmemorybuffer"></a>

## cambc.DraftMemoryBuffer

### __bytes__

```python
def __bytes__(self) -> bytes
```

### __getitem__

```python
def __getitem__(self, offset: int) -> int
```

### __init__

```python
def __init__(self) -> None
```

### __iter__

```python
def __iter__(self) -> Iterator[int]
```

### __len__

```python
def __len__(self) -> int
```

### is_empty

```python
def is_empty(self) -> bool
```

Return whether no draft memory was submitted.

### submit

```python
def submit(self, data: Union[bytes, bytearray, memoryview, DraftMemoryBuffer]) -> None
```

Submit bytes-like data as the next draft memory. Args: data: Bytes-like object to pass to this team's gameplay bots.

<a id="cambc-error"></a>

## cambc.Error

### __init__

```python
def __init__(self, code: int, message: str = "") -> None
```

*Example: Inspect a caught SDK error when diagnosing a rejected action.*

```python
result = bc.Error(code, message)
```

### __str__

```python
def __str__(self) -> str
```

*Example: Inspect a caught SDK error when diagnosing a rejected action.*

```python
result = str(subject)
```

<a id="cambc-errorcode"></a>

## cambc.ErrorCode

### to_string

```python
def to_string(value: int) -> str
```

*Example: Inspect a caught SDK error when diagnosing a rejected action.*

```python
result = bc.ErrorCode.to_string(value)
```

<a id="cambc-game-map"></a>

## cambc.game_map

### altars

```python
def altars() -> Bitboard
```

Return the altar tiles, where gems are tributed.

*Example: Build a terrain-only walking mask. Also exclude occupied tiles and the enemy spawn when selecting a legal step.*

```python
blocked = bc.game_map.walls() | bc.game_map.holes() | bc.game_map.altars()
walkable = ~blocked
```

### bushes

```python
def bushes() -> Bitboard
```

Return the bush tiles, which hide champions from outside vision.

### camp

```python
def camp(position: Vec2) -> Camp
```

The camp that spawns at position; IndexError if none does. Args: position: Spawn tile of the camp.

### camp_groups

```python
def camp_groups() -> tuple[CampGroup, ...]
```

Camp groups, also available during the draft.

### height

```python
def height() -> int
```

Return the map height in tiles.

### holes

```python
def holes() -> Bitboard
```

Return the hole tiles, which block movement but not vision.

*Example: Build a terrain-only walking mask. Also exclude occupied tiles and the enemy spawn when selecting a legal step.*

```python
blocked = bc.game_map.walls() | bc.game_map.holes() | bc.game_map.altars()
walkable = ~blocked
```

### is_in_bounds

```python
def is_in_bounds(position: Vec2) -> bool
```

Return whether a position lies on the map. Args: position: Position to check.

### reflect_horizontal

```python
def reflect_horizontal(position: Vec2) -> Vec2
```

Return a position reflected across the map horizontally, reversing x. Args: position: Map position to reflect.

### reflect_vertical

```python
def reflect_vertical(position: Vec2) -> Vec2
```

Return a position reflected across the map vertically, reversing y. Args: position: Map position to reflect.

### rotate_180

```python
def rotate_180(position: Vec2) -> Vec2
```

Return a position rotated 180 degrees within the map. Args: position: Map position to rotate.

### spawn_region

```python
def spawn_region(team: Team) -> Bitboard
```

Return a team's spawn region. Args: team: Team whose spawn region to return.

### symmetry

```python
def symmetry() -> Symmetry
```

Return the symmetry the map was generated with.

### walls

```python
def walls() -> Bitboard
```

Cached wall mask; copy() before mutating.

*Example: Build a terrain-only walking mask. Also exclude occupied tiles and the enemy spawn when selecting a legal step.*

```python
blocked = bc.game_map.walls() | bc.game_map.holes() | bc.game_map.altars()
walkable = ~blocked
```

### width

```python
def width() -> int
```

Return the map width in tiles.

<a id="cambc-game-map-campgroup"></a>

## cambc.game_map.CampGroup

### __eq__

```python
def __eq__(self, other: object) -> bool
```

### __hash__

```python
def __hash__(self) -> int
```

### __index__

```python
def __index__(self) -> int
```

### __init__

```python
def __init__(self) -> None
```

### __iter__

```python
def __iter__(self) -> Iterator[Camp]
```

### __len__

```python
def __len__(self) -> int
```

### camps

```python
def camps(self) -> tuple[Camp, ...]
```

Return the camps in the group.

### gem_value

```python
def gem_value(self) -> int
```

Return the gems awarded for clearing the group.

### gold_value

```python
def gold_value(self) -> int
```

Return the gold awarded for clearing the group.

### max_respawn_timer

```python
def max_respawn_timer(self) -> int
```

Return the number of rounds the group takes to respawn after being cleared.

### spawn_tiles

```python
def spawn_tiles(self) -> Bitboard
```

Return the spawn tiles of the group's camps.

### spawn_tiles_into

```python
def spawn_tiles_into(self, out: Bitboard) -> None
```

Like spawn_tiles, but writes into out. Args: out: Destination Bitboard; its previous contents are overwritten.

### state

```python
def state(self) -> CampGroupState
```

Return the group's current state.

<a id="cambc-itempassive"></a>

## cambc.ItemPassive

### to_string

```python
def to_string(value: int) -> str
```

<a id="cambc-itemtype"></a>

## cambc.ItemType

### __new__

```python
def __new__(cls, value: int) -> ItemType
```

### __repr__

```python
def __repr__(self) -> str
```

### combine_count

```python
def combine_count(self) -> int
```

Return how many copies combine into the result item.

### cost

```python
def cost(self) -> int
```

Return the gold cost to buy the item.

### focus_points

```python
def focus_points(self) -> int
```

Return the focus the item grants.

### health_points

```python
def health_points(self) -> int
```

Return the maximum health the item grants.

### info

```python
def info(self) -> ItemInfo
```

Return the item's static design data.

### is_purchasable

```python
def is_purchasable(self) -> bool
```

Return whether the item can be bought directly from the shop.

### name

```python
def name(self) -> str
```

Return the item's display name.

### passive

```python
def passive(self) -> Optional[ItemPassive]
```

Return the passive effect the item grants.

### passive_magnitude

```python
def passive_magnitude(self) -> float
```

Return the strength of the item's passive effect.

### result

```python
def result(self) -> Optional[ItemType]
```

Return the item these copies combine into, or None if it does not combine.

### strength_points

```python
def strength_points(self) -> int
```

Return the strength the item grants.

<a id="cambc-passivetype"></a>

## cambc.PassiveType

### to_string

```python
def to_string(value: int) -> str
```

<a id="cambc-sharedmemorybuffer"></a>

## cambc.SharedMemoryBuffer

### __getitem__

```python
def __getitem__(self, offset: int) -> int
```

### __len__

```python
def __len__(self) -> int
```

### __setitem__

```python
def __setitem__(self, offset: int, value: int) -> None
```

### read

```python
def read(self, offset: int, out: Union[bytearray, memoryview]) -> None
```

Fill a writable bytes-like object from offset. Args: offset: Byte offset into shared memory. out: Writable bytes-like object; its length sets how many bytes are read.

*Example: Reserve byte zero in your team's memory layout for a shared objective ID. All allied bots must agree on its meaning.*

```python
data = bytearray(1)
bc.shared_memory.read(0, data)
objective_id = data[0]
```

### size

```python
def size() -> int
```

Return the shared memory size in bytes.

### write

```python
def write(self, offset: int, data: Union[bytes, bytearray, memoryview]) -> None
```

Write a bytes-like object starting at offset. Args: offset: Byte offset into shared memory. data: Bytes-like object to write.

*Example: Reserve byte zero in your team's memory layout for a shared objective ID. All allied bots must agree on its meaning.*

```python
bc.shared_memory.write(0, bytes([2]))  # Agree to focus objective 2.
```

<a id="cambc-symmetry"></a>

## cambc.Symmetry

### to_string

```python
def to_string(value: int) -> str
```

<a id="cambc-team"></a>

## cambc.Team

### opponent

```python
def opponent(team: int) -> int
```

### opponent

```python
def opponent(team: Team) -> Team
```

### to_string

```python
def to_string(value: int) -> str
```

<a id="cambc-teleport"></a>

## cambc.Teleport

### champion

```python
def champion(self) -> Champion
```

Return the champion channelling the teleport.

### is_ally

```python
def is_ally(self) -> bool
```

Check whether this teleport belongs to the observing team.

### is_enemy

```python
def is_enemy(self) -> bool
```

Check whether this teleport belongs to the opposing team.

### position

```python
def position(self) -> Vec2
```

Return the reserved destination tile.

### remaining_time

```python
def remaining_time(self) -> int
```

Return the rounds left before the teleport completes.

### team

```python
def team(self) -> Team
```

Return the team of the teleporting champion.

### visible_tiles

```python
def visible_tiles(self) -> Bitboard
```

Return the tiles visible from the reservation.

### visible_tiles_into

```python
def visible_tiles_into(self, out: Bitboard) -> None
```

Like visible_tiles, but writes into out. Args: out: Destination Bitboard; its previous contents are overwritten.

<a id="cambc-unit"></a>

## cambc.Unit

### __eq__

```python
def __eq__(self, other: object) -> bool
```

### __hash__

```python
def __hash__(self) -> int
```

### __init__

```python
def __init__(self) -> None
```

### attack_range

```python
def attack_range(self) -> int
```

Return the attack range in Chebyshev tiles; melee units have range 1.

### attack_tiles

```python
def attack_tiles(self) -> Bitboard
```

Return the tiles within attack range of the unit's current position.

### attack_tiles_into

```python
def attack_tiles_into(self, out: Bitboard) -> None
```

Like attack_tiles, but writes into out. Args: out: Destination Bitboard; its previous contents are overwritten.

### buffs

```python
def buffs(self) -> BuffCollection
```

Capture the unit's current buffs; raises Error if the unit is not visible.

### focus

```python
def focus(self) -> float
```

Return current focus; raises Error if the unit is not visible.

### health

```python
def health(self) -> float
```

Return current health; raises Error if the unit is not visible.

### is_visible

```python
def is_visible(self) -> bool
```

Return whether the unit is currently visible.

### max_health

```python
def max_health(self) -> float
```

Return current maximum health; raises Error if the unit is not visible.

### position

```python
def position(self) -> Vec2
```

Return the current tile; raises Error if the unit is not visible.

### strength

```python
def strength(self) -> float
```

Return current strength; raises Error if the unit is not visible.

<a id="cambc-vec2"></a>

## cambc.Vec2

### __add__

```python
def __add__(self, other: Vec2) -> Vec2
```

### __floordiv__

```python
def __floordiv__(self, n: int) -> Vec2
```

### __hash__

```python
def __hash__(self) -> int
```

### __init__

```python
def __init__(self, x: int, y: int) -> None
```

### __mul__

```python
def __mul__(self, n: int) -> Vec2
```

### __neg__

```python
def __neg__(self) -> Vec2
```

### __pos__

```python
def __pos__(self) -> Vec2
```

### __rmul__

```python
def __rmul__(self, n: int) -> Vec2
```

### __sub__

```python
def __sub__(self, other: Vec2) -> Vec2
```

### chebyshev_distance

```python
def chebyshev_distance(self, other: Vec2) -> int
```

Return the Chebyshev distance, the number of king moves between the tiles. Args: other: Other vector.

### cross

```python
def cross(self, other: Vec2) -> int
```

Return the signed 2D cross product. Args: other: Other vector.

### dot

```python
def dot(self, other: Vec2) -> int
```

Return the dot product. Args: other: Other vector.

### length_squared

```python
def length_squared(self) -> int
```

Return the squared Euclidean length.

### reflect_horizontal

```python
def reflect_horizontal(self) -> Vec2
```

Return this position reflected across the map horizontally, reversing x.

### reflect_vertical

```python
def reflect_vertical(self) -> Vec2
```

Return this position reflected across the map vertically, reversing y.

### rotate_180

```python
def rotate_180(self) -> Vec2
```

Return this position rotated 180 degrees within the map.

### rotate_ccw

```python
def rotate_ccw(self) -> Vec2
```

Return this direction rotated 45 degrees counter-clockwise.

### rotate_cw

```python
def rotate_cw(self) -> Vec2
```

Return this direction rotated 45 degrees clockwise.

### x

```python
def x(self) -> int
```

Horizontal coordinate or displacement.

### y

```python
def y(self) -> int
```

Vertical coordinate or displacement; +y is north.

<a id="cambc-vision"></a>

## cambc.vision

### altar_lock_at

```python
def altar_lock_at(position: Vec2) -> AltarLock
```

The altar lock on a tile, ally first. Args: position: Tile to query.

### altar_lock_tiles

```python
def altar_lock_tiles(team: Optional[Team] = None) -> Bitboard
```

Return the tiles of visible altar locks. Args: team: Team to include, or None for both teams.

### altar_lock_tiles_into

```python
def altar_lock_tiles_into(out: Bitboard, team: Optional[Team] = None) -> None
```

Like altar_lock_tiles, but writes into out. Args: out: Destination Bitboard; its previous contents are overwritten. team: Team to include, or None for both teams.

### altar_locks

```python
def altar_locks(team: Optional[Team] = None) -> list[AltarLock]
```

Return snapshots of visible altar locks. Args: team: Team to include, or None for both teams.

### camp_at

```python
def camp_at(position: Vec2) -> Camp
```

Return the visible camp currently on a tile; raises Error if there is none or the tile is hidden. Args: position: Tile to query.

### camp_groups

```python
def camp_groups() -> list[_map.CampGroup]
```

Camp groups with at least one spawn tile in vision.

### camp_tiles

```python
def camp_tiles() -> Bitboard
```

Return the tiles of visible camps.

### camp_tiles_into

```python
def camp_tiles_into(out: Bitboard) -> None
```

Like camp_tiles, but writes into out. Args: out: Destination Bitboard; its previous contents are overwritten.

### camps

```python
def camps() -> list[Camp]
```

Return the visible camps.

### champion_at

```python
def champion_at(position: Vec2) -> Champion
```

Return the visible champion on a tile; raises Error if there is none or the tile is hidden. Args: position: Tile to query.

### champion_tiles

```python
def champion_tiles(team: Optional[Team] = None) -> Bitboard
```

Visible champions of a team, or of both teams. Args: team: Team to include, or None for both teams.

### champion_tiles_into

```python
def champion_tiles_into(out: Bitboard, team: Optional[Team] = None) -> None
```

Like champion_tiles, but writes into out. Args: out: Destination Bitboard; its previous contents are overwritten. team: Team to include, or None for both teams.

### champions

```python
def champions(team: Optional[Team] = None) -> list[Champion]
```

Return the visible champions. Args: team: Team to include, or None for both teams.

### has_altar_lock

```python
def has_altar_lock(position: Vec2) -> bool
```

Return whether a visible altar lock of either team is on a tile. Args: position: Tile to query.

### has_camp

```python
def has_camp(position: Vec2) -> bool
```

Return whether a visible camp is on a tile. Args: position: Tile to query.

### has_champion

```python
def has_champion(position: Vec2) -> bool
```

Return whether a visible champion is on a tile. Args: position: Tile to query.

### has_teleport

```python
def has_teleport(position: Vec2) -> bool
```

Return whether a visible teleport reservation is on a tile. Args: position: Tile to query.

### has_ward

```python
def has_ward(position: Vec2, team: Optional[Team] = None) -> bool
```

Return whether a visible ward is on a tile; hidden wards return False. Args: position: Tile to query. team: Team to restrict to, or None for either team.

### teleport_at

```python
def teleport_at(position: Vec2) -> Teleport
```

The teleport reservation on a tile. Args: position: Tile to query.

### teleport_tiles

```python
def teleport_tiles() -> Bitboard
```

Return the tiles of visible teleport reservations.

### teleport_tiles_into

```python
def teleport_tiles_into(out: Bitboard) -> None
```

Like teleport_tiles, but writes into out. Args: out: Destination Bitboard; its previous contents are overwritten.

### teleports

```python
def teleports() -> list[Teleport]
```

Return snapshots of visible teleport reservations.

### visible_tiles

```python
def visible_tiles() -> Bitboard
```

Return every tile visible to the bot's champion.

### visible_tiles_into

```python
def visible_tiles_into(out: Bitboard) -> None
```

Like visible_tiles, but writes into out. Args: out: Destination Bitboard; its previous contents are overwritten.

### ward_at

```python
def ward_at(position: Vec2, team: Optional[Team] = None) -> Ward
```

Snapshot of the ward on a tile, optionally of one team. Args: position: Tile to query. team: Team to restrict to, or None for either team.

### ward_tiles

```python
def ward_tiles(team: Optional[Team] = None) -> Bitboard
```

Return the tiles of visible wards. Args: team: Team to include, or None for both teams.

### ward_tiles_into

```python
def ward_tiles_into(out: Bitboard, team: Optional[Team] = None) -> None
```

Like ward_tiles, but writes into out. Args: out: Destination Bitboard; its previous contents are overwritten. team: Team to include, or None for both teams.

### wards

```python
def wards(team: Optional[Team] = None) -> list[Ward]
```

Snapshots of visible wards, optionally of one team. Args: team: Team to include, or None for both teams.

<a id="cambc-ward"></a>

## cambc.Ward

### is_ally

```python
def is_ally(self) -> bool
```

Check whether this ward belongs to the observing team.

### is_enemy

```python
def is_enemy(self) -> bool
```

Check whether this ward belongs to the opposing team.

### position

```python
def position(self) -> Vec2
```

Return the ward's tile.

### remaining_time

```python
def remaining_time(self) -> Optional[int]
```

Return the rounds before the ward expires, or None if it does not expire.

### team

```python
def team(self) -> Team
```

Return the team that owns the ward.

### visible_tiles

```python
def visible_tiles(self) -> Bitboard
```

Return the tiles this ward sees.

### visible_tiles_from

```python
def visible_tiles_from(position: Vec2) -> Bitboard
```

Return the vision a ward would have at a tile. Args: position: Hypothetical ward tile.

### visible_tiles_from_into

```python
def visible_tiles_from_into(position: Vec2, out: Bitboard) -> None
```

Like visible_tiles_from, but writes into out. Args: position: Hypothetical ward tile. out: Destination Bitboard; its previous contents are overwritten.

### visible_tiles_into

```python
def visible_tiles_into(self, out: Bitboard) -> None
```

Like visible_tiles, but writes into out. Args: out: Destination Bitboard; its previous contents are overwritten.
