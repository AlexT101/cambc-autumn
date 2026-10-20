# Bot API reference: OCaml

*Public OCaml SDK functions, methods and camp-group state types.*

Start with [Getting Started](../guides/ocaml/first-bot.md). Other languages: [C++](./cpp.md) · [Rust](./rust.md) · [Python](./python.md).

## Contents

- [Cambc](#cambc) (17)
- [Cambc.Ability](#cambc-ability) (31)
- [Cambc.Ability_kind](#cambc-ability-kind) (3)
- [Cambc.Ability_target](#cambc-ability-target) (16)
- [Cambc.Altar_lock](#cambc-altar-lock) (3)
- [Cambc.Bitboard](#cambc-bitboard) (48)
- [Cambc.Buff](#cambc-buff) (9)
- [Cambc.Buff_kind](#cambc-buff-kind) (3)
- [Cambc.Buff_restrictions](#cambc-buff-restrictions) (16)
- [Cambc.Camp](#cambc-camp) (30)
- [Cambc.Camp_group](#cambc-camp-group) (11)
- [Cambc.Camp_state](#cambc-camp-state) (5)
- [Cambc.Camp_type](#cambc-camp-type) (3)
- [Cambc.Champion](#cambc-champion) (68)
- [Cambc.Champion_draft](#cambc-champion-draft) (3)
- [Cambc.Champion_state](#cambc-champion-state) (17)
- [Cambc.Champion_type](#cambc-champion-type) (3)
- [Cambc.Constants](#cambc-constants) (2)
- [Cambc.Constants.Passive_abilities](#cambc-constants-passive-abilities) (7)
- [Cambc.Consumable](#cambc-consumable) (7)
- [Cambc.Consumable_counts](#cambc-consumable-counts) (5)
- [Cambc.Debug](#cambc-debug) (2)
- [Cambc.Distance_field](#cambc-distance-field) (21)
- [Cambc.Draft](#cambc-draft) (3)
- [Cambc.Draft_memory](#cambc-draft-memory) (4)
- [Cambc.Error_code](#cambc-error-code) (3)
- [Cambc.Game_map](#cambc-game-map) (15)
- [Cambc.Game_unit](#cambc-game-unit) (11)
- [Cambc.Item](#cambc-item) (3)
- [Cambc.Item_counts](#cambc-item-counts) (5)
- [Cambc.Item_info](#cambc-item-info) (11)
- [Cambc.Item_passive](#cambc-item-passive) (2)
- [Cambc.Passive](#cambc-passive) (3)
- [Cambc.Shared_memory](#cambc-shared-memory) (9)
- [Cambc.Symmetry](#cambc-symmetry) (3)
- [Cambc.Team](#cambc-team) (4)
- [Cambc.Teleport](#cambc-teleport) (5)
- [Cambc.Vec2](#cambc-vec2) (33)
- [Cambc.Vision](#cambc-vision) (38)
- [Cambc.Ward](#cambc-ward) (8)

<a id="cambc"></a>

## Cambc

### Cambc_error

```ocaml
exception Cambc_error of Error_code.t * string
```

Raised by every failing call.

### camp

```ocaml
type camp
```

### champion

```ocaml
type champion
```

### champions

```ocaml
val champions : ?team:Team.t -> unit -> Champion.t list
```

`champions ?team ()` is every roster champion, including hidden ones.

- `team`: Team to include; both teams when omitted.

### constants

```ocaml
val constants : unit -> Constants.t
```

Game constants loaded at startup.

### debug_block

```ocaml
val debug_block : (unit -> unit) -> unit
```

`debug_block f` runs `f` without spending fuel when the bot is built in debug mode (`cambc run`, the default); skipped entirely in release mode (`--release`, and always on the platform). The free budget per block is 1000 turns, beyond which the rest is charged; ending the turn inside closes the free window. Usage: `debug_block (fun () -> expensive_debug_operation ())`.

- `f`: Runs in debug mode only; never called in release mode.

### end_turn

```ocaml
val end_turn : unit -> unit
```

End the current turn.

*Example: Stop optional planning when little fuel remains and yield the current turn.*

```ocaml
let yield_if_low_on_fuel () =
  if fuel_remaining () < 1000 then end_turn ()
```

### fuel_remaining

```ocaml
val fuel_remaining : unit -> int
```

Fuel left in the current turn.

*Example: Stop optional planning when little fuel remains and yield the current turn.*

```ocaml
let yield_if_low_on_fuel () =
  if fuel_remaining () < 1000 then end_turn ()
```

### global_submitted_gems

```ocaml
val global_submitted_gems : Team.t -> int
```

`global_submitted_gems team` is the total gems the team has tributed.

- `team`: Team to count.

### init

```ocaml
val init : unit -> unit
```

Load the SDK caches. This already runs at startup, before the bot's modules; calling it again does nothing.

### is_draft

```ocaml
val is_draft : unit -> bool
```

True when this instance runs the draft rather than controlling a champion.

### Missing_identity

```ocaml
exception Missing_identity
```

A champion design from `Champion.designs` used where a live champion is needed; Rust `Error::MissingIdentity`.

### No_range

```ocaml
exception No_range
```

An ability without a targeting range (attack reset); Rust `Error::NoRange`.

### resign

```ocaml
val resign : unit -> unit
```

Resign the game for the bot's team.

### round_number

```ocaml
val round_number : unit -> int
```

The current round number.

### self_champion

```ocaml
val self_champion : unit -> Champion.t
```

The champion this bot controls; raises during the draft.

### self_champion_opt

```ocaml
val self_champion_opt : unit -> Champion.t option
```

Like `self_champion`, but `None` during the draft.

<a id="cambc-ability"></a>

## Cambc.Ability

### can_target_allies

```ocaml
val can_target_allies : t -> bool
```

`can_target_allies a` is true when the ability can target allied champions.

- `a`: Ability slot.

### can_target_camps

```ocaml
val can_target_camps : t -> bool
```

`can_target_camps a` is true when the ability can target camps.

- `a`: Ability slot.

### can_target_enemies

```ocaml
val can_target_enemies : t -> bool
```

`can_target_enemies a` is true when the ability can target enemy champions.

- `a`: Ability slot.

### can_target_ground

```ocaml
val can_target_ground : t -> bool
```

`can_target_ground a` is true when the ability can target a tile.

- `a`: Ability slot.

### can_target_self

```ocaml
val can_target_self : t -> bool
```

`can_target_self a` is true when the ability can target its caster.

- `a`: Ability slot.

### cast

```ocaml
val cast : ?target:[ `Champion of champion | `Camp of camp ] -> ?at:Vec2.t -> t -> bool
```

Pass at most one of `~target` and `~at`. Unit casts land on the target's tile; ground casts take a tile. Returns false for a newly revealed obstruction; known invalid destinations raise `Cambc_error`.

- `target`: Champion or camp to cast on.
- `at`: Ground tile to cast at.
- `a`: Ability slot of the bot's own champion. Altar locks are not valid ability targets.

### cooldown

```ocaml
val cooldown : t -> int
```

`cooldown a` is the remaining cooldown; 0 means ready.

- `a`: Ability slot.

### damage_amount

```ocaml
val damage_amount : ?against:champion -> t -> float
```

`damage_amount ?against a` returns Focus-scaled damage, including dash landing damage and caster outgoing bonuses such as Heart of Ruin's passive. Without `against`, excludes target-dependent modifiers, shields and health limits. With `against`, predicts health lost after outgoing bonuses, mitigation and shields, capped at current health. Does not check range or whether a target is in the landing area.

- `against`: Optional visible champion the amount is computed against.
- `a`: Ability slot.

### heal_amount

```ocaml
val heal_amount : ?against:champion -> t -> float
```

`heal_amount ?against a` is the healing the ability would do, capped at the target's missing health when `against` is given.

- `against`: Optional visible champion the amount is computed against.
- `a`: Ability slot.

### info

```ocaml
type info = | Attack_reset of { properties : properties; enhanced_attack : bool } | Damage of { properties : properties; range : float; modifier : float } | Aoe_damage of { properties : properties; range : float; modifier : float; radius : float; duration : int; } | Cc of { properties : properties; range : float; modifier : float; duration : int } | Heal of { properties : properties; range : float; modifier : float } | Dash of { properties : properties; range : float; radius : float; modifier : float; duration : int } | Shield of { properties : properties; range : float; modifier : float; duration : int }
```

Ability metadata. For the `Dash` variant: Landing effects apply to enemies and camps only after a successful dash. `range`: Maximum dash travel distance in tiles. Diagonal steps count as one; the destination must be a different tile reachable by a legal dash path. `radius`: Chebyshev radius in tiles around the landing tile for damage and stun; 1 includes all eight neighbouring tiles. `modifier`: Landing damage multiplier: base damage = caster Focus * modifier, before damage bonuses and mitigation. 0 disables landing damage. `duration`: Stun duration applied on landing, in turns; 0 disables stun. This is not the dash travel time.

### info

```ocaml
val info : t -> info option
```

`info a` is the cached metadata, or `None` for an unused slot.

- `a`: Ability slot.

### is

```ocaml
val is : t -> Ability_kind.t -> bool
```

`is a k` is true when the slot holds an ability of kind `k`.

- `a`: Ability slot.
- `k`: Ability kind.

### is_aoe_damage

```ocaml
val is_aoe_damage : t -> bool
```

Check whether this is an area-damage ability.

- `a`: Ability slot.

### is_attack_reset

```ocaml
val is_attack_reset : t -> bool
```

Check whether this is an attack-reset ability.

- `a`: Ability slot.

### is_cc

```ocaml
val is_cc : t -> bool
```

Check whether this is a crowd-control ability.

- `a`: Ability slot.

### is_damage

```ocaml
val is_damage : t -> bool
```

Check whether this is a damage ability.

- `a`: Ability slot.

### is_dash

```ocaml
val is_dash : t -> bool
```

Check whether this is a dash ability.

- `a`: Ability slot.

### is_heal

```ocaml
val is_heal : t -> bool
```

Check whether this is a healing ability.

- `a`: Ability slot.

### is_on_cooldown

```ocaml
val is_on_cooldown : t -> bool
```

`is_on_cooldown a` is true while the cooldown is running.

- `a`: Ability slot.

### is_ready

```ocaml
val is_ready : t -> bool
```

Check whether this ability is ready to cast.

- `a`: Ability slot.

### is_shield

```ocaml
val is_shield : t -> bool
```

Check whether this is a shield ability.

- `a`: Ability slot.

### kind

```ocaml
val kind : info -> Ability_kind.t
```

`kind i` is the ability's kind.

- `i`: Ability metadata.

### mask_into

```ocaml
val mask_into : t -> Bitboard.t -> unit
```

Like `valid_tiles`, but writes into `out`. Raises `No_range` for attack resets.

- `a`: Ability slot.
- `out`: Destination; its previous contents are overwritten.

### properties

```ocaml
type properties = { max_cooldown : int; valid_targets : Ability_target.t; exclusive_with_movement : bool; }
```

### properties

```ocaml
val properties : info -> properties
```

`properties i` is the properties shared by every ability kind.

- `i`: Ability metadata.

### range

```ocaml
val range : info -> float option
```

`range i` is the casting range, or `None` for range-less abilities.

- `i`: Ability metadata.

### shield_amount

```ocaml
val shield_amount : ?against:champion -> t -> float
```

`shield_amount ?against a` is the shield the ability would grant.

- `against`: Optional visible champion the amount is computed against.
- `a`: Ability slot.

### slot

```ocaml
val slot : t -> int
```

`slot a` is the slot index on its champion.

- `a`: Ability slot.

### t

```ocaml
type t
```

### valid_targets

```ocaml
val valid_targets : t -> Ability_target.t
```

`valid_targets a` is the categories of target the ability accepts.

- `a`: Ability slot.

### valid_tiles

```ocaml
val valid_tiles : t -> Bitboard.t
```

`valid_tiles a` is the tiles within casting range; visibility and occupancy are not checked.

- `a`: Ability slot.

<a id="cambc-ability-kind"></a>

## Cambc.Ability_kind

### all

```ocaml
val all : t list
```

Every value, in declaration order.

### t

```ocaml
type t = | Attack_reset | Damage | Aoe_damage | Cc | Heal | Dash | Shield
```

### to_string

```ocaml
val to_string : t -> string
```

`to_string x` is the name of `x`.

- `x`: Value to name.

<a id="cambc-ability-target"></a>

## Cambc.Ability_target

### add

```ocaml
val add : flag -> t -> t
```

`add f s` is `s` with `f` set.

- `f`: Flag.
- `s`: Flag set.

### all

```ocaml
val all : flag list
```

Every named flag.

### diff

```ocaml
val diff : t -> t -> t
```

`diff a b` has the flags of `a` not in `b`.

- `a`: First set.
- `b`: Flags to remove.

### empty

```ocaml
val empty : t
```

The set with no flags.

### equal

```ocaml
val equal : t -> t -> bool
```

`equal a b` is true for identical sets.

- `a`: First set.
- `b`: Second set.

### flag

```ocaml
type flag = Camps | Enemies | Allies | Self | Ground
```

### hash

```ocaml
val hash : t -> int
```

Hash consistent with `equal`.

- `s`: Flag set.

### inter

```ocaml
val inter : t -> t -> t
```

`inter a b` has the flags of both sets.

- `a`: First set.
- `b`: Second set.

### is_empty

```ocaml
val is_empty : t -> bool
```

`is_empty s` is true when no flag is set.

- `s`: Flag set.

### mem

```ocaml
val mem : flag -> t -> bool
```

`mem f s` is true when `s` contains `f`.

- `f`: Flag.
- `s`: Flag set.

### of_list

```ocaml
val of_list : flag list -> t
```

`of_list fs` is the set of the listed flags.

- `fs`: Flags to set.

### remove

```ocaml
val remove : flag -> t -> t
```

`remove f s` is `s` with `f` cleared.

- `f`: Flag.
- `s`: Flag set.

### subset

```ocaml
val subset : t -> t -> bool
```

`subset a b` is true when every flag of `a` is in `b`.

- `a`: Candidate subset.
- `b`: Superset.

### t

```ocaml
type t
```

### to_list

```ocaml
val to_list : t -> flag list
```

`to_list s` lists the set flags.

- `s`: Flag set.

### union

```ocaml
val union : t -> t -> t
```

`union a b` has the flags of either set.

- `a`: First set.
- `b`: Second set.

<a id="cambc-altar-lock"></a>

## Cambc.Altar_lock

### is_ally

```ocaml
val is_ally : t -> bool
```

Check whether this altar lock belongs to the observing team.

- `l`: Altar lock snapshot.

### is_enemy

```ocaml
val is_enemy : t -> bool
```

Check whether this altar lock belongs to the opposing team.

- `l`: Altar lock snapshot.

### t

```ocaml
type t = { team : Team.t; position : Vec2.t; hits_remaining : int }
```

<a id="cambc-bitboard"></a>

## Cambc.Bitboard

### clear

```ocaml
val clear : t -> unit
```

`clear b` clears every tile.

- `b`: Bitboard.

### complement

```ocaml
val complement : t -> t
```

`complement b` sets exactly the map tiles `b` leaves clear.

- `b`: Bitboard.

### copy

```ocaml
val copy : t -> t
```

`copy b` is an independent copy.

- `b`: Bitboard.

### count

```ocaml
val count : t -> int
```

`count b` is the number of set tiles.

- `b`: Bitboard.

### create

```ocaml
val create : unit -> t
```

A board with no tiles set.

### draw_chebyshev

```ocaml
val draw_chebyshev : t -> Vec2.t -> float -> unit
```

`draw_chebyshev b center radius` sets every tile within a Chebyshev radius.

- `b`: Bitboard.
- `center`: Centre tile.
- `radius`: Chebyshev radius in tiles.

### draw_circle

```ocaml
val draw_circle : t -> Vec2.t -> float -> unit
```

`draw_circle b center radius` sets every tile within a Euclidean radius.

- `b`: Bitboard.
- `center`: Centre tile.
- `radius`: Euclidean radius in tiles.

### equal

```ocaml
val equal : t -> t -> bool
```

`equal a b` is true when both boards set the same tiles.

- `a`: First board.
- `b`: Second board.

### export_linear_buffer

```ocaml
val export_linear_buffer : t -> Bytes.t
```

`export_linear_buffer b` is the contents as a row-major buffer.

- `b`: Bitboard.

### export_linear_buffer_into

```ocaml
val export_linear_buffer_into : t -> Bytes.t -> unit
```

Like `export_linear_buffer`, but writes into `out`.

- `b`: Bitboard.
- `out`: Destination, exactly `linear_buffer_size` long.

### export_raw_buffer

```ocaml
val export_raw_buffer : t -> Bytes.t
```

`export_raw_buffer b` is the contents as an engine-chunked buffer.

- `b`: Bitboard.

### export_raw_buffer_into

```ocaml
val export_raw_buffer_into : t -> Bytes.t -> unit
```

Like `export_raw_buffer`, but writes into `out`.

- `b`: Bitboard.
- `out`: Destination, exactly `raw_buffer_size` long.

### fill

```ocaml
val fill : t -> unit
```

`fill b` sets every tile on the map.

- `b`: Bitboard.

### height

```ocaml
val height : t -> int
```

Map height in tiles.

- `b`: Bitboard.

### import_linear_buffer

```ocaml
val import_linear_buffer : t -> Bytes.t -> unit
```

`import_linear_buffer b data` replaces the contents from a row-major buffer.

- `b`: Bitboard.
- `data`: One value per tile in row-major order.

### import_raw_buffer

```ocaml
val import_raw_buffer : t -> Bytes.t -> unit
```

`import_raw_buffer b data` replaces the contents from an engine-chunked buffer.

- `b`: Bitboard.
- `data`: Engine-chunked bytes, exactly `raw_buffer_size` long.

### intersect

```ocaml
val intersect : t -> t -> t
```

`intersect a b` is a new board with tiles set in both.

- `a`: First board.
- `b`: Second board; may be `a`.

### intersect_assign

```ocaml
val intersect_assign : t -> t -> unit
```

`intersect_assign a b` keeps only the tiles of `a` also in `b`.

- `a`: First board.
- `b`: Second board; may be `a`.

### is_empty

```ocaml
val is_empty : t -> bool
```

`is_empty b` is true when no tile is set.

- `b`: Bitboard.

### is_set

```ocaml
val is_set : t -> Vec2.t -> bool
```

`is_set b p` is true when `p` is set; raises outside the map.

- `b`: Bitboard.
- `p`: Tile.

### linear_buffer_size

```ocaml
val linear_buffer_size : t -> int
```

Size in bytes of the row-major buffer.

- `b`: Bitboard.

### positions

```ocaml
val positions : t -> Vec2.t list
```

`positions b` lists the set tiles in row-major order.

- `b`: Bitboard.

### print

```ocaml
val print : t -> unit
```

`print b` prints the board to stdout for debugging.

- `b`: Bitboard.

### raw_buffer_size

```ocaml
val raw_buffer_size : t -> int
```

Size in bytes of the engine-chunked buffer.

- `b`: Bitboard.

### reachable_tiles

```ocaml
val reachable_tiles : ?scratch:t * t -> t -> Vec2.t -> distance:int -> t
```

`reachable_tiles ?scratch walls origin ~distance` is the tiles reachable from `origin` around `walls`.

- `scratch`: Optional pair of working boards; their contents are overwritten.
- `walls`: Impassable tiles.
- `origin`: Start tile.
- `distance`: Maximum number of 8-directional steps.

### reachable_tiles_into

```ocaml
val reachable_tiles_into : ?scratch:t * t -> t -> Vec2.t -> distance:int -> t -> unit
```

`reachable_tiles walls origin ~distance`; `?scratch` is reusable (frontier, scratch) storage.

- `scratch`: Optional pair of working boards; their contents are overwritten.
- `walls`: Impassable tiles.
- `origin`: Start tile.
- `distance`: Maximum number of 8-directional steps.
- `out`: Destination; its previous contents are overwritten.

### reflect

```ocaml
val reflect : t -> Symmetry.t -> t
```

`reflect b s` is a copy transformed by a map symmetry.

- `b`: Bitboard.
- `s`: Map symmetry.

### reflect_horizontal

```ocaml
val reflect_horizontal : t -> t
```

`reflect_horizontal b` is a copy reflected horizontally, reversing x.

- `b`: Bitboard.

### reflect_horizontal_into

```ocaml
val reflect_horizontal_into : t -> t -> unit
```

Like `reflect_horizontal`, but writes into `out`.

- `b`: Bitboard.
- `out`: Destination; its previous contents are overwritten.

### reflect_into

```ocaml
val reflect_into : t -> Symmetry.t -> t -> unit
```

Like `reflect`, but writes into `out`.

- `b`: Bitboard.
- `s`: Map symmetry.
- `out`: Destination; its previous contents are overwritten.

### reflect_vertical

```ocaml
val reflect_vertical : t -> t
```

`reflect_vertical b` is a copy reflected vertically, reversing y.

- `b`: Bitboard.

### reflect_vertical_into

```ocaml
val reflect_vertical_into : t -> t -> unit
```

Like `reflect_vertical`, but writes into `out`.

- `b`: Bitboard.
- `out`: Destination; its previous contents are overwritten.

### rotate_180

```ocaml
val rotate_180 : t -> t
```

`rotate_180 b` is a copy rotated 180 degrees within the map.

- `b`: Bitboard.

### rotate_180_into

```ocaml
val rotate_180_into : t -> t -> unit
```

Like `rotate_180`, but writes into `out`.

- `b`: Bitboard.
- `out`: Destination; its previous contents are overwritten.

### set

```ocaml
val set : t -> Vec2.t -> bool -> unit
```

`set b p value` sets or clears `p`; raises outside the map.

- `b`: Bitboard.
- `p`: Tile.
- `value`: `true` to set, `false` to clear.

### shadow_cast

```ocaml
val shadow_cast : t -> Vec2.t -> distance:int -> t
```

`shadow_cast walls origin ~distance` is the tiles visible from `origin` past opaque `walls`.

- `walls`: Opaque tiles.
- `origin`: Viewer tile.
- `distance`: Maximum sight radius in tiles.

### shadow_cast_into

```ocaml
val shadow_cast_into : t -> Vec2.t -> distance:int -> t -> unit
```

Like `shadow_cast`, but writes into `out`.

- `walls`: Opaque tiles.
- `origin`: Viewer tile.
- `distance`: Maximum sight radius in tiles.
- `out`: Destination; its previous contents are overwritten.

### shift_right

```ocaml
val shift_right : t -> int -> t
```

`shift_right b count` is a copy shifted horizontally; tiles shifted off the map are dropped.

- `b`: Bitboard.
- `count`: Columns to shift; negative values shift left.

### shift_right_into

```ocaml
val shift_right_into : t -> int -> t -> unit
```

`_into` functions overwrite the whole output. Unary bitboard operations may write in place.

- `b`: Bitboard.
- `count`: Columns to shift; negative values shift left.
- `out`: Destination; its previous contents are overwritten.

### shift_up

```ocaml
val shift_up : t -> int -> t
```

`shift_up b count` is a copy shifted vertically; tiles shifted off the map are dropped.

- `b`: Bitboard.
- `count`: Rows to shift; negative values shift down.

### shift_up_into

```ocaml
val shift_up_into : t -> int -> t -> unit
```

Like `shift_up`, but writes into `out`.

- `b`: Bitboard.
- `count`: Rows to shift; negative values shift down.
- `out`: Destination; its previous contents are overwritten.

### t

```ocaml
type t
```

### toggle

```ocaml
val toggle : t -> Vec2.t -> unit
```

`toggle b p` flips `p`; raises outside the map.

- `b`: Bitboard.
- `p`: Tile.

### union

```ocaml
val union : t -> t -> t
```

`union a b` is a new board with tiles set in either.

- `a`: First board.
- `b`: Second board; may be `a`.

### union_assign

```ocaml
val union_assign : t -> t -> unit
```

`union_assign a b` adds the tiles of `b` to `a`.

- `a`: First board.
- `b`: Second board; may be `a`.

### width

```ocaml
val width : t -> int
```

Map width in tiles.

- `b`: Bitboard.

### xor

```ocaml
val xor : t -> t -> t
```

`xor a b` is a new board with tiles set in exactly one.

- `a`: First board.
- `b`: Second board; may be `a`.

### xor_assign

```ocaml
val xor_assign : t -> t -> unit
```

`xor_assign a b` flips the tiles of `a` set in `b`.

- `a`: First board.
- `b`: Second board; may be `a`.

<a id="cambc-buff"></a>

## Cambc.Buff

### duration

```ocaml
val duration : t -> int
```

`duration b` is the remaining time in rounds.

- `b`: Buff snapshot.

### get

```ocaml
val get : t list -> Buff_kind.t -> t option
```

`get buffs k` is the buff of kind `k`, if present.

- `buffs`: Buff snapshots.
- `k`: Buff kind.

### has

```ocaml
val has : t list -> Buff_kind.t -> bool
```

`has buffs k` is true when a buff of kind `k` is present.

- `buffs`: Buff snapshots.
- `k`: Buff kind.

### has_enhanced_attack

```ocaml
val has_enhanced_attack : t list -> bool
```

Check whether the collection has an enhanced-attack buff.

- `buffs`: Buff snapshots.

### has_shield

```ocaml
val has_shield : t list -> bool
```

Check whether the collection has a shield buff.

- `buffs`: Buff snapshots.

### has_stun

```ocaml
val has_stun : t list -> bool
```

Check whether the collection has a stun buff.

- `buffs`: Buff snapshots.

### kind

```ocaml
val kind : t -> Buff_kind.t
```

`kind b` is the buff's kind.

- `b`: Buff snapshot.

### shield_value

```ocaml
val shield_value : t -> float option
```

`shield_value b` is the remaining shield, or `None` for other buffs.

- `b`: Buff snapshot.

### t

```ocaml
type t = | Shield of { duration : int; value : float } | Stun of { duration : int } | Enhanced_attack of { duration : int }
```

<a id="cambc-buff-kind"></a>

## Cambc.Buff_kind

### all

```ocaml
val all : t list
```

Every value, in declaration order.

### t

```ocaml
type t = | Shield | Stun | Enhanced_attack
```

### to_string

```ocaml
val to_string : t -> string
```

`to_string x` is the name of `x`.

- `x`: Value to name.

<a id="cambc-buff-restrictions"></a>

## Cambc.Buff_restrictions

### add

```ocaml
val add : flag -> t -> t
```

`add f s` is `s` with `f` set.

- `f`: Flag.
- `s`: Flag set.

### all

```ocaml
val all : flag list
```

Every named flag.

### diff

```ocaml
val diff : t -> t -> t
```

`diff a b` has the flags of `a` not in `b`.

- `a`: First set.
- `b`: Flags to remove.

### empty

```ocaml
val empty : t
```

The set with no flags.

### equal

```ocaml
val equal : t -> t -> bool
```

`equal a b` is true for identical sets.

- `a`: First set.
- `b`: Second set.

### flag

```ocaml
type flag = Move | Attack | Cast | Shop | Consumable | Ward
```

### hash

```ocaml
val hash : t -> int
```

Hash consistent with `equal`.

- `s`: Flag set.

### inter

```ocaml
val inter : t -> t -> t
```

`inter a b` has the flags of both sets.

- `a`: First set.
- `b`: Second set.

### is_empty

```ocaml
val is_empty : t -> bool
```

`is_empty s` is true when no flag is set.

- `s`: Flag set.

### mem

```ocaml
val mem : flag -> t -> bool
```

`mem f s` is true when `s` contains `f`.

- `f`: Flag.
- `s`: Flag set.

### of_list

```ocaml
val of_list : flag list -> t
```

`of_list fs` is the set of the listed flags.

- `fs`: Flags to set.

### remove

```ocaml
val remove : flag -> t -> t
```

`remove f s` is `s` with `f` cleared.

- `f`: Flag.
- `s`: Flag set.

### subset

```ocaml
val subset : t -> t -> bool
```

`subset a b` is true when every flag of `a` is in `b`.

- `a`: Candidate subset.
- `b`: Superset.

### t

```ocaml
type t
```

### to_list

```ocaml
val to_list : t -> flag list
```

`to_list s` lists the set flags.

- `s`: Flag set.

### union

```ocaml
val union : t -> t -> t
```

`union a b` has the flags of either set.

- `a`: First set.
- `b`: Second set.

<a id="cambc-camp"></a>

## Cambc.Camp

### attack_range

```ocaml
val attack_range : t -> int
```

`attack_range c` is the attack range in Chebyshev tiles; melee units have range 1.

- `c`: Camp.

### attack_tiles

```ocaml
val attack_tiles : t -> Bitboard.t
```

`attack_tiles c` is the tiles within attack range of `c`'s position.

- `c`: Camp.

### attack_tiles_into

```ocaml
val attack_tiles_into : t -> Bitboard.t -> unit
```

Like `attack_tiles`, but writes into `out`.

- `c`: Camp.
- `out`: Destination; its previous contents are overwritten.

### base_stats

```ocaml
type base_stats = { vision_radius : float; base_move_speed : int; base_attack_range : int; base_health : float; health_growth : float; base_strength : float; strength_growth : float; base_focus : float; focus_growth : float; }
```

### base_stats

```ocaml
val base_stats : t -> base_stats
```

`base_stats c` is the camp type's design stats.

- `c`: Camp.

### buffs

```ocaml
val buffs : t -> Buff.t list
```

`buffs c` is the current buffs; raises if `c` is not visible.

- `c`: Camp.

### camp_group

```ocaml
val camp_group : t -> Camp_group.t
```

`camp_group c` is the group the camp belongs to.

- `c`: Camp.

### equal

```ocaml
val equal : t -> t -> bool
```

`equal a b` is true for the same camp.

- `a`: First camp.
- `b`: Second camp.

### focus

```ocaml
val focus : t -> float
```

`focus c` is current focus; raises if `c` is not visible.

- `c`: Camp.

### hash

```ocaml
val hash : t -> int
```

Hash consistent with `equal`.

- `c`: Camp.

### health

```ocaml
val health : t -> float
```

`health c` is current health; raises if `c` is not visible.

- `c`: Camp.

### is_alive

```ocaml
val is_alive : t -> bool
```

Query whether this camp is living (awake or asleep); uses the visibility checks of `state`.

### is_asleep

```ocaml
val is_asleep : t -> bool
```

Query whether this camp is living but dormant; uses the visibility checks of `state`.

### is_awake

```ocaml
val is_awake : t -> bool
```

Query whether this camp is awake; uses the same visibility checks as `state`.

### is_dead

```ocaml
val is_dead : t -> bool
```

Query whether this camp is dead; uses the same visibility checks as `state`.

### is_elk

```ocaml
val is_elk : t -> bool
```

Check whether this camp is an elk.

- `c`: Camp.

### is_gem_cluster

```ocaml
val is_gem_cluster : t -> bool
```

Check whether this camp is a gem cluster.

- `c`: Camp.

### is_gold_cluster

```ocaml
val is_gold_cluster : t -> bool
```

Check whether this camp is a gold cluster.

- `c`: Camp.

### is_golem

```ocaml
val is_golem : t -> bool
```

Check whether this camp is a golem.

- `c`: Camp.

### is_monolith

```ocaml
val is_monolith : t -> bool
```

Check whether this camp is a monolith.

- `c`: Camp.

### is_visible

```ocaml
val is_visible : t -> bool
```

`is_visible c` is true when `c` is currently visible.

- `c`: Camp.

### is_wolf

```ocaml
val is_wolf : t -> bool
```

Check whether this camp is a wolf.

- `c`: Camp.

### kind

```ocaml
val kind : t -> Camp_type.t
```

`kind c` is the camp's type.

- `c`: Camp.

### max_health

```ocaml
val max_health : t -> float
```

`max_health c` is current maximum health; raises if `c` is not visible.

- `c`: Camp.

### position

```ocaml
val position : t -> Vec2.t
```

`position c` is the current tile; raises if `c` is not visible.

- `c`: Camp.

### spawn_position

```ocaml
val spawn_position : t -> Vec2.t
```

`spawn_position c` is the camp's spawn tile, not its live position.

- `c`: Camp.

### state

```ocaml
type state = Camp_state.t = Dead | Alive | Asleep
```

Individual camp lifecycle. `Alive` means awake; `Asleep` means living but dormant.

### state

```ocaml
val state : t -> state
```

Query `Dead`, `Alive` (awake), or `Asleep`. The current tile, or last occupied tile when dead, must be in vision; hidden camps raise `Api_not_in_vision`. This is separate from the camp-group state.

- `c`: Camp to inspect.

### strength

```ocaml
val strength : t -> float
```

`strength c` is current strength; raises if `c` is not visible.

- `c`: Camp.

### t

```ocaml
type t = camp
```

<a id="cambc-camp-group"></a>

## Cambc.Camp_group

### camps

```ocaml
val camps : t -> camp list
```

`camps g` is the camps in the group.

- `g`: Camp group.

### equal

```ocaml
val equal : t -> t -> bool
```

`equal a b` is true for the same group.

- `a`: First group.
- `b`: Second group.

### gem_value

```ocaml
val gem_value : t -> int
```

`gem_value g` is the gems awarded for clearing the group.

- `g`: Camp group.

### gold_value

```ocaml
val gold_value : t -> int
```

`gold_value g` is the gold awarded for clearing the group.

- `g`: Camp group.

### hash

```ocaml
val hash : t -> int
```

Hash consistent with `equal`.

- `g`: Camp group.

### max_respawn_timer

```ocaml
val max_respawn_timer : t -> int
```

`max_respawn_timer g` is the rounds the group takes to respawn after being cleared.

- `g`: Camp group.

### spawn_tiles

```ocaml
val spawn_tiles : t -> Bitboard.t
```

`spawn_tiles g` is the spawn tiles of the group's camps. The board is shared and cached: copy before mutating.

- `g`: Camp group.

### spawn_tiles_into

```ocaml
val spawn_tiles_into : t -> Bitboard.t -> unit
```

Like `spawn_tiles`, but writes into `out`.

- `g`: Camp group.
- `out`: Destination; its previous contents are overwritten.

### state

```ocaml
type state = Alive | Reward_available | Respawning of int
```

Returned by Camp_group.state group. Alive has living camps; Reward_available is defeated but unclaimed; Respawning timer carries the remaining round countdown. Zero means respawning is blocked by occupied spawn tiles. Reading state requires at least one original camp spawn tile in current vision; otherwise the SDK reports a visibility error. max_respawn_timer gives the configured full duration, not the remaining countdown.

*Example: Read the remaining respawn rounds for a group with an original spawn tile in current vision. Alive and unclaimed-reward states have no countdown.*

```ocaml
match Camp_group.state group with
| Camp_group.Respawning timer -> Printf.printf "%d\n" timer
| _ -> ()
```

### state

```ocaml
val state : t -> state
```

`state g` is the group's current state.

- `g`: Camp group.

*Example: Read the remaining respawn rounds for a group with an original spawn tile in current vision. Alive and unclaimed-reward states have no countdown.*

```ocaml
match Camp_group.state group with
| Camp_group.Respawning timer -> Printf.printf "%d\n" timer
| _ -> ()
```

### t

```ocaml
type t
```

<a id="cambc-camp-state"></a>

## Cambc.Camp_state

### is_alive

```ocaml
val is_alive : t -> bool
```

Check whether the captured state is living, including asleep camps.

### is_asleep

```ocaml
val is_asleep : t -> bool
```

Check whether the captured state is living but dormant.

### is_awake

```ocaml
val is_awake : t -> bool
```

Check whether the captured state is awake (the `Alive` enum value).

### is_dead

```ocaml
val is_dead : t -> bool
```

Check whether the captured state is dead.

### t

```ocaml
type t = Dead | Alive | Asleep
```

An individual camp's captured lifecycle; states are mutually exclusive, not flags.

<a id="cambc-camp-type"></a>

## Cambc.Camp_type

### all

```ocaml
val all : t list
```

Every value, in declaration order.

### t

```ocaml
type t = | Wolf | Elk | Gem_cluster | Gold_cluster | Monolith | Golem
```

### to_string

```ocaml
val to_string : t -> string
```

`to_string x` is the name of `x`.

- `x`: Value to name.

<a id="cambc-champion"></a>

## Cambc.Champion

### abilities

```ocaml
val abilities : t -> Ability.t array
```

`abilities c` is the champion's ability slots.

- `c`: Champion.

### attack

```ocaml
val attack : t -> [ `Champion of champion | `Camp of camp | `Altar_lock of Altar_lock.t ] -> unit
```

`attack c target` basic-attacks a visible champion, camp or altar lock in range.

- `c`: The bot's own champion.
- `target`: Unit or altar lock to attack.

### attack_range

```ocaml
val attack_range : t -> int
```

`attack_range c` is the attack range in Chebyshev tiles; melee champions have range 1.

- `c`: Champion.

### attack_tiles

```ocaml
val attack_tiles : t -> Bitboard.t
```

`attack_tiles c` is the tiles within attack range of `c`'s position.

- `c`: Champion.

### attack_tiles_into

```ocaml
val attack_tiles_into : t -> Bitboard.t -> unit
```

Like `attack_tiles`, but writes into `out`.

- `c`: Champion.
- `out`: Destination; its previous contents are overwritten.

### base_stats

```ocaml
type base_stats = { vision_radius : int; base_move_speed : int; base_attack_range : int; base_health : float; health_growth : float; base_strength : float; strength_growth : float; base_focus : float; focus_growth : float; camp_damage_multiplier : float; }
```

### base_stats

```ocaml
val base_stats : t -> base_stats
```

`base_stats c` is the champion type's design stats.

- `c`: Champion.

### buffs

```ocaml
val buffs : t -> Buff.t list
```

`buffs c` is the champion's current buffs; raises if `c` is not visible.

- `c`: Champion.

### buy

```ocaml
val buy : ?count:int -> t -> Item.t -> unit
```

`buy ?count c item` buys items; the engine validates location, gold and recipe.

- `count`: Number of copies; defaults to 1.
- `c`: The bot's own champion.
- `item`: Item type.

### buy_consumable

```ocaml
val buy_consumable : t -> Consumable.t -> unit
```

`buy_consumable c k` buys one consumable; the engine validates gold and carry limit.

- `c`: The bot's own champion.
- `k`: Consumable type.

### can_attack

```ocaml
val can_attack : t -> bool
```

Check whether this champion can attack.

- `c`: Champion.

*Example: Check the action allowance before spending fuel to choose an attack target.*

```ocaml
let action_available =
  let me = self_champion () in
  Champion.can_attack me
```

### can_buy

```ocaml
val can_buy : ?count:int -> t -> Item.t -> bool
```

`can_buy ?count c item` is true when `c` can buy `item` in its current state.

- `count`: Number of copies; defaults to 1.
- `c`: Champion.
- `item`: Item type.

### can_buy_consumable

```ocaml
val can_buy_consumable : t -> Consumable.t -> bool
```

`can_buy_consumable c k` is true when `c` can buy a consumable now.

- `c`: Champion.
- `k`: Consumable type.

### can_cast

```ocaml
val can_cast : t -> bool
```

Check whether this champion can cast.

- `c`: Champion.

*Example: Check the action allowance before spending fuel to evaluate ready abilities.*

```ocaml
let action_available =
  let me = self_champion () in
  Champion.can_cast me
```

### can_move

```ocaml
val can_move : t -> bool
```

Check whether this champion can move.

- `c`: Champion.

*Example: Check the action allowance before spending fuel to plan a path.*

```ocaml
let action_available =
  let me = self_champion () in
  Champion.can_move me
```

### can_sell

```ocaml
val can_sell : t -> bool
```

`can_sell c` is true when `c` can sell items in its current state.

- `c`: Champion.

### cancel_recall

```ocaml
val cancel_recall : t -> unit
```

`cancel_recall c` cancels the current recall.

- `c`: The bot's own champion.

### cancel_submit_gems

```ocaml
val cancel_submit_gems : t -> unit
```

`cancel_submit_gems c` cancels the current tribute.

- `c`: The bot's own champion.

### champion_name

```ocaml
val champion_name : t -> Champion_type.t
```

`champion_name c` is the champion's type.

- `c`: Champion.

### consumable_count

```ocaml
val consumable_count : t -> Consumable.t -> int
```

`consumable_count c k` is how many of a consumable `c` carries.

- `c`: Champion.
- `k`: Consumable type.

### consumable_counts

```ocaml
val consumable_counts : t -> Consumable_counts.t
```

`consumable_counts c` is `c`'s consumable inventory.

- `c`: Champion.

### designs

```ocaml
val designs : unit -> t array
```

Static designs of every champion type, as used during the draft.

### end_turn

```ocaml
val end_turn : t -> unit
```

`end_turn c` ends the turn now.

- `c`: The bot's own champion.

### equal

```ocaml
val equal : t -> t -> bool
```

`equal a b` is true for the same champion.

- `a`: First champion.
- `b`: Second champion.

### focus

```ocaml
val focus : t -> float
```

`focus c` is current focus; raises if `c` is not visible.

- `c`: Champion.

### gem_count

```ocaml
val gem_count : t -> int
```

`gem_count c` is the gems `c` is carrying.

- `c`: Champion.

### gold_count

```ocaml
val gold_count : t -> int
```

`gold_count c` is the gold `c` is carrying.

- `c`: Champion.

### has_completed_turn

```ocaml
val has_completed_turn : t -> bool
```

Check whether this champion has completed its turn.

- `c`: Champion.

### hash

```ocaml
val hash : t -> int
```

Hash consistent with `equal`.

- `c`: Champion.

### health

```ocaml
val health : t -> float
```

`health c` is current health; raises if `c` is not visible.

- `c`: Champion.

*Example: Recall when badly injured and safe from interruption.*

```ocaml
let retreat_if_needed safe_to_recall =
  let me = self_champion () in
  if safe_to_recall && Champion.health me < Champion.max_health me *. 0.3 then
    Champion.recall me
```

### is_alive

```ocaml
val is_alive : t -> bool
```

`is_alive c` is true while the champion is alive.

- `c`: Champion.

### is_ally

```ocaml
val is_ally : t -> bool
```

Check whether this champion belongs to the observing team.

- `c`: Champion.

### is_dead

```ocaml
val is_dead : t -> bool
```

`is_dead c` is `not (is_alive c)`.

- `c`: Champion.

### is_enemy

```ocaml
val is_enemy : t -> bool
```

Check whether this champion belongs to the opposing team.

- `c`: Champion.

### is_recalling

```ocaml
val is_recalling : t -> bool
```

Check whether this champion is recalling.

- `c`: Champion.

### is_submitting_gems

```ocaml
val is_submitting_gems : t -> bool
```

Check whether this champion is submitting gems.

- `c`: Champion.

### is_teleporting

```ocaml
val is_teleporting : t -> bool
```

Check whether this champion is teleporting.

- `c`: Champion.

### is_visible

```ocaml
val is_visible : t -> bool
```

`is_visible c` is true when the champion is currently visible.

- `c`: Champion.

### item_count

```ocaml
val item_count : t -> Item.t -> int
```

`item_count c item` is how many of `item` `c` holds.

- `c`: Champion.
- `item`: Item type.

### item_counts

```ocaml
val item_counts : t -> Item_counts.t
```

`item_counts c` is `c`'s item inventory.

- `c`: Champion.

### max_health

```ocaml
val max_health : t -> float
```

`max_health c` is current maximum health; raises if `c` is not visible.

- `c`: Champion.

*Example: Recall when badly injured and safe from interruption.*

```ocaml
let retreat_if_needed safe_to_recall =
  let me = self_champion () in
  if safe_to_recall && Champion.health me < Champion.max_health me *. 0.3 then
    Champion.recall me
```

### move

```ocaml
val move : t -> Vec2.t -> bool
```

Returns false for a newly revealed obstruction; known invalid destinations raise `Cambc_error`.

- `c`: The bot's own champion.
- `delta`: Displacement from the current position.

*Example: Take a planned step; false means no movement occurred.*

```ocaml
let me = self_champion () in
if Champion.can_move me then
  let moved = Champion.move me direction in
  ignore moved
```

### move_absolute

```ocaml
val move_absolute : t -> Vec2.t -> bool
```

Returns false for a newly revealed obstruction; known invalid destinations raise `Cambc_error`.

- `c`: The bot's own champion.
- `destination`: Map tile to move to.

*Example: Take a planned step; false means no movement occurred.*

```ocaml
let me = self_champion () in
if Champion.can_move me then
  let moved = Champion.move_absolute me destination in
  ignore moved
```

### move_towards

```ocaml
val move_towards : t -> Vec2.t -> bool
```

Move to the reachable tile on a shortest path to `target`. Always treat the target as free for pathfinding, while avoiding other walls, holes, altars, enemy spawn tiles, visible units and teleport reservations. Returns false when already there, unable to move, no route exists, or a hidden obstruction is revealed. The engine still validates the chosen landing tile: trying to enter a known blocked target raises `Cambc_error`.

- `c`: The bot's own champion.
- `target`: Map tile to approach.

*Example: Path towards a target even when its tile is blocked. Stop at the desired range: the engine still rejects landing on a known blocked tile.*

```ocaml
let me = self_champion () in
if Champion.can_move me then
  let moved = Champion.move_towards me destination in
  ignore moved
```

### passive

```ocaml
val passive : t -> Passive.t
```

`passive c` is the champion's passive.

- `c`: Champion.

### place_ward

```ocaml
val place_ward : t -> Vec2.t -> bool
```

Returns false for a newly revealed obstruction; known invalid destinations raise `Cambc_error`.

- `c`: The bot's own champion.
- `destination`: Tile to place the ward on.

### position

```ocaml
val position : t -> Vec2.t
```

`position c` is the current tile; raises if `c` is not visible.

- `c`: Champion.

### prev_priority

```ocaml
val prev_priority : t -> int
```

`prev_priority c` is the priority used for the current round.

- `c`: Champion.

### priority

```ocaml
val priority : t -> int
```

`priority c` is the priority that will apply from the next round.

- `c`: Champion.

### recall

```ocaml
val recall : t -> unit
```

`recall c` starts channelling a recall to the team spawn.

- `c`: The bot's own champion.

*Example: Recall when badly injured and safe from interruption.*

```ocaml
let retreat_if_needed safe_to_recall =
  let me = self_champion () in
  if safe_to_recall && Champion.health me < Champion.max_health me *. 0.3 then
    Champion.recall me
```

### remaining_channel_time

```ocaml
val remaining_channel_time : t -> int
```

`remaining_channel_time c` is the rounds left on the current recall, tribute or teleport channel.

- `c`: Champion.

### restrictions

```ocaml
val restrictions : t -> Buff_restrictions.t
```

`restrictions c` is the actions the champion's buffs currently prohibit.

- `c`: Champion.

### sell

```ocaml
val sell : ?count:int -> t -> Item.t -> unit
```

`sell ?count c item` sells items; the engine validates inventory and location.

- `count`: Number of copies; defaults to 1.
- `c`: The bot's own champion.
- `item`: Item type.

### set_priority

```ocaml
val set_priority : t -> int -> unit
```

`set_priority c priority` sets the scheduling priority.

- `c`: The bot's own champion.
- `priority`: New priority; takes effect from the next round and persists.

### state

```ocaml
val state : t -> Champion_state.t
```

`state c` is the champion's life, channel and action flags.

- `c`: Champion.

### strength

```ocaml
val strength : t -> float
```

`strength c` is current strength; raises if `c` is not visible.

- `c`: Champion.

### submit_gems

```ocaml
val submit_gems : t -> Vec2.t -> unit
```

`submit_gems c altar` starts tributing carried gems at an altar.

- `c`: The bot's own champion.
- `altar`: Altar tile to tribute at.

### t

```ocaml
type t = champion
```

### team

```ocaml
val team : t -> Team.t
```

`team c` is the champion's team.

- `c`: Champion.

### use_consumable

```ocaml
val use_consumable : ?at:Vec2.t -> t -> Consumable.t -> bool
```

Returns false for a newly revealed obstruction; known invalid destinations raise `Cambc_error`.

- `at`: Tile to use the consumable at, for targeted consumables.
- `c`: The bot's own champion.
- `k`: Consumable to use.

### visible_tiles

```ocaml
val visible_tiles : t -> Bitboard.t
```

`visible_tiles c` is the tiles `c` currently sees.

- `c`: Champion.

### visible_tiles_from

```ocaml
val visible_tiles_from : Vec2.t -> t -> Bitboard.t
```

`visible_tiles_from p c` is the vision `c` would have at `p`.

- `p`: Hypothetical tile to see from.
- `c`: Champion.

### visible_tiles_from_into

```ocaml
val visible_tiles_from_into : Vec2.t -> t -> Bitboard.t -> unit
```

Like `visible_tiles_from`, but writes into `out`.

- `p`: Hypothetical tile to see from.
- `c`: Champion.
- `out`: Destination; its previous contents are overwritten.

### visible_tiles_into

```ocaml
val visible_tiles_into : t -> Bitboard.t -> unit
```

Like `visible_tiles`, but writes into `out`.

- `c`: Champion.
- `out`: Destination; its previous contents are overwritten.

### ward_cooldown

```ocaml
val ward_cooldown : t -> int
```

`ward_cooldown c` is the rounds until `c` can place another ward.

- `c`: Champion.

### ward_placement_tiles

```ocaml
val ward_placement_tiles : t -> Bitboard.t
```

`ward_placement_tiles c` is the tiles where `c` could place a ward now.

- `c`: Champion.

### ward_placement_tiles_into

```ocaml
val ward_placement_tiles_into : t -> Bitboard.t -> unit
```

Like `ward_placement_tiles`, but writes into `out`.

- `c`: Champion.
- `out`: Destination; its previous contents are overwritten.

### ward_positions

```ocaml
val ward_positions : t -> Vec2.t list
```

`ward_positions c` is the tiles of `c`'s placed wards.

- `c`: Champion.

<a id="cambc-champion-draft"></a>

## Cambc.Champion_draft

### all

```ocaml
val all : t list
```

Every value, in declaration order.

### t

```ocaml
type t = | Ryth | Vesper_vale | Vendetta | Cassi_and_issac | Stellar | Prism | Marcella | Willow | Ren | Varg | Tavi | Heart_of_ruin
```

### to_string

```ocaml
val to_string : t -> string
```

`to_string x` is the name of `x`.

- `x`: Value to name.

<a id="cambc-champion-state"></a>

## Cambc.Champion_state

### add

```ocaml
val add : flag -> t -> t
```

`add f s` is `s` with `f` set.

- `f`: Flag.
- `s`: Flag set.

### all

```ocaml
val all : flag list
```

Every named flag.

### diff

```ocaml
val diff : t -> t -> t
```

`diff a b` has the flags of `a` not in `b`.

- `a`: First set.
- `b`: Flags to remove.

### empty

```ocaml
val empty : t
```

The set with no flags.

### equal

```ocaml
val equal : t -> t -> bool
```

`equal a b` is true for identical sets.

- `a`: First set.
- `b`: Second set.

### flag

```ocaml
type flag = | Alive | Recalling | Submitting_gems | Can_move | Can_attack | Completed_turn | Recall_started | Submit_gems_started | Recall_cancelled | Submit_gems_cancelled | Can_cast | Teleporting
```

### hash

```ocaml
val hash : t -> int
```

Hash consistent with `equal`.

- `s`: Flag set.

### inter

```ocaml
val inter : t -> t -> t
```

`inter a b` has the flags of both sets.

- `a`: First set.
- `b`: Second set.

### is_dead

```ocaml
val is_dead : t -> bool
```

`is_dead s` is true when the alive flag is clear.

- `s`: Champion state.

### is_empty

```ocaml
val is_empty : t -> bool
```

`is_empty s` is true when no flag is set.

- `s`: Flag set.

### mem

```ocaml
val mem : flag -> t -> bool
```

`mem f s` is true when `s` contains `f`.

- `f`: Flag.
- `s`: Flag set.

### of_list

```ocaml
val of_list : flag list -> t
```

`of_list fs` is the set of the listed flags.

- `fs`: Flags to set.

### remove

```ocaml
val remove : flag -> t -> t
```

`remove f s` is `s` with `f` cleared.

- `f`: Flag.
- `s`: Flag set.

### subset

```ocaml
val subset : t -> t -> bool
```

`subset a b` is true when every flag of `a` is in `b`.

- `a`: Candidate subset.
- `b`: Superset.

### t

```ocaml
type t
```

### to_list

```ocaml
val to_list : t -> flag list
```

`to_list s` lists the set flags.

- `s`: Flag set.

### union

```ocaml
val union : t -> t -> t
```

`union a b` has the flags of either set.

- `a`: First set.
- `b`: Second set.

<a id="cambc-champion-type"></a>

## Cambc.Champion_type

### all

```ocaml
val all : t list
```

Every value, in declaration order.

### t

```ocaml
type t = | Ryth | Vesper_vale | Vendetta | Cassi | Issac | Stellar | Prism | Marcella | Willow | Ren | Varg | Tavi | Heart_of_ruin
```

### to_string

```ocaml
val to_string : t -> string
```

`to_string x` is the name of `x`.

- `x`: Value to name.

<a id="cambc-constants"></a>

## Cambc.Constants

### get

```ocaml
val get : unit -> t
```

Game constants loaded at startup.

### t

```ocaml
type t = { capture_time : int; camp_sleep_time : int; respawn_time : int; recall_time : int; submit_gem_duration_multiplier : float; submit_gem_base_duration : int; submit_gem_minimum_duration : int; submit_gems_range : int; max_rounds : int; winning_gems : int; kill_gold : int; assist_gold : int; passive_gold : int; spawn_healing : float; active_wards : int; shared_memory_bytes : int; draft_memory_bytes : int; tile_reveal_rounds : int; ward_cooldown : int; ward_lifetime : int; ward_vision_radius : float; ward_placement_radius : float; altar_lock_hits : int; tp_crystal_time : int; }
```

<a id="cambc-constants-passive-abilities"></a>

## Cambc.Constants.Passive_abilities

### heart_of_ruin_missing_health_damage_max_bonus

```ocaml
val heart_of_ruin_missing_health_damage_max_bonus : float
```

Heart of Ruin: maximum bonus to all damage at 100% missing health.

### marcella_tribute_gold_per_gem

```ocaml
val marcella_tribute_gold_per_gem : int
```

Marcella: gold gained per gem tributed.

### prism_focus_per_gem

```ocaml
val prism_focus_per_gem : float
```

Focus Prism gains per carried gem.

### ren_retaliation_focus_ratio

```ocaml
val ren_retaliation_focus_ratio : float
```

Fraction of focus Ren deals back as retaliation damage.

### ryth_health_strength_ratio

```ocaml
val ryth_health_strength_ratio : float
```

Strength Ryth gains per point of bonus health.

### varg_splash_radius

```ocaml
val varg_splash_radius : float
```

Radius of Varg's splash damage, in tiles.

### vesper_vale_bonus_gold_percent

```ocaml
val vesper_vale_bonus_gold_percent : int
```

Extra gold Vesper Vale gains, in percent.

<a id="cambc-consumable"></a>

## Cambc.Consumable

### all

```ocaml
val all : t list
```

Every value, in declaration order.

### carry_limit

```ocaml
val carry_limit : t -> int
```

`carry_limit c` is how many a champion can carry.

- `c`: Consumable type.

### cost

```ocaml
val cost : t -> int
```

`cost c` is the gold cost of one.

- `c`: Consumable type.

### info

```ocaml
type info = { cost : int; carry_limit : int }
```

### info

```ocaml
val info : t -> info
```

`info c` is the consumable's static design data.

- `c`: Consumable type.

### t

```ocaml
type t = Tp_crystal | Altar_lock
```

### to_string

```ocaml
val to_string : t -> string
```

`to_string x` is the name of `x`.

- `x`: Value to name.

<a id="cambc-consumable-counts"></a>

## Cambc.Consumable_counts

### fold

```ocaml
val fold : (Consumable.t -> int -> 'a -> 'a) -> t -> 'a -> 'a
```

`fold fn c init` folds `fn` over each held type and its count.

- `fn`: Folding function.
- `c`: Inventory counts.
- `init`: Initial accumulator.

### get

```ocaml
val get : t -> Consumable.t -> int
```

`get c k` is the number of `k` in the inventory.

- `c`: Inventory counts.
- `k`: Consumable type.

### iter

```ocaml
val iter : (Consumable.t -> int -> unit) -> t -> unit
```

`iter fn c` calls `fn` on each held type and its count.

- `fn`: Callback.
- `c`: Inventory counts.

### t

```ocaml
type t
```

### to_list

```ocaml
val to_list : t -> (Consumable.t * int) list
```

`to_list c` lists each held type with its count.

- `c`: Inventory counts.

<a id="cambc-debug"></a>

## Cambc.Debug

### draw_dot

```ocaml
val draw_dot : Vec2.t -> int -> unit
```

`draw_dot p rgb` draws a debug dot in the replay.

- `p`: Tile to mark.
- `rgb`: Packed `0xRRGGBB` colour.

*Example: Mark a decision in your replay debug overlay to understand the bot's route or target.*

```ocaml
let result = Debug.draw_dot value1 value2
```

### draw_line

```ocaml
val draw_line : Vec2.t -> Vec2.t -> int -> unit
```

`draw_line a b rgb` draws a debug line in the replay.

- `a`: Start tile.
- `b`: End tile.
- `rgb`: Packed `0xRRGGBB` colour.

*Example: Mark a decision in your replay debug overlay to understand the bot's route or target.*

```ocaml
let result = Debug.draw_line value1 value2 value3
```

<a id="cambc-distance-field"></a>

## Cambc.Distance_field

### compute

```ocaml
val compute : ?destinations:Bitboard.t -> t -> walls:Bitboard.t -> roots:Bitboard.t -> visited:Bitboard.t -> max_distance:int -> unit
```

BFS from `roots`; with `?destinations` stops once all are reached.

*Example: Find a step towards the goal tiles. The result is a direction for move.*

```ocaml
let field = Distance_field.create () in
let visited = Bitboard.create () in
Distance_field.compute field ~walls:blocked ~roots:goals ~visited
  ~max_distance:Distance_field.unreachable;
let direction = Distance_field.next_move_from field (Champion.position (self_champion ())) in
direction
```

### compute_with_expansion_count

```ocaml
val compute_with_expansion_count : ?destinations:Bitboard.t -> t -> walls:Bitboard.t -> roots:Bitboard.t -> visited:Bitboard.t -> max_distance:int -> int
```

Like `compute`, but returns the number of expansion steps.

- `destinations`: Optional target tiles; stop once all are reached.
- `walls`: Impassable tiles.
- `roots`: Tiles at distance zero.
- `visited`: Receives the tiles the search reached.
- `max_distance`: Tiles farther than this are left unreached.

### copy

```ocaml
val copy : t -> t
```

`copy d` is an independent copy.

- `d`: Distance field.

### create

```ocaml
val create : unit -> t
```

A field with every tile unreachable.

### export_linear_buffer

```ocaml
val export_linear_buffer : t -> int array
```

`export_linear_buffer d` is the row-major distances.

- `d`: Distance field.

### export_linear_buffer_into

```ocaml
val export_linear_buffer_into : t -> int array -> unit
```

Like `export_linear_buffer`, but writes into `out`.

- `d`: Distance field.
- `out`: Destination with one entry per tile.

### export_raw_buffer

```ocaml
val export_raw_buffer : t -> Bytes.t
```

`export_raw_buffer d` is the contents as an engine-chunked buffer.

- `d`: Distance field.

### export_raw_buffer_into

```ocaml
val export_raw_buffer_into : t -> Bytes.t -> unit
```

Like `export_raw_buffer`, but writes into `out`.

- `d`: Distance field.
- `out`: Destination, exactly `raw_buffer_size` long.

### get

```ocaml
val get : t -> Vec2.t -> int
```

`get d p` is the distance at `p`; raises outside the map.

- `d`: Distance field.
- `p`: Tile.

### height

```ocaml
val height : t -> int
```

Map height in tiles.

- `d`: Distance field.

### import_linear_buffer

```ocaml
val import_linear_buffer : t -> int array -> unit
```

`import_linear_buffer d values` replaces the contents from row-major distances.

- `d`: Distance field.
- `values`: One distance per tile in row-major order.

### import_raw_buffer

```ocaml
val import_raw_buffer : t -> Bytes.t -> unit
```

`import_raw_buffer d data` replaces the contents from an engine-chunked buffer.

- `d`: Distance field.
- `data`: Engine-chunked bytes, exactly `raw_buffer_size` long.

### linear_buffer_size

```ocaml
val linear_buffer_size : t -> int
```

Number of row-major values.

- `d`: Distance field.

### next_move_from

```ocaml
val next_move_from : t -> Vec2.t -> Vec2.t option
```

`next_move_from d p` is the first optimal step towards a root as a direction delta, or `None` at a root or unreached tile.

- `d`: Distance field.
- `p`: Tile to step from. First optimal step from a tile towards a root, as a direction delta in compass order from north; `None` at a root or unreached tile.

*Example: Find a step towards the goal tiles. The result is a direction for move.*

```ocaml
let field = Distance_field.create () in
let visited = Bitboard.create () in
Distance_field.compute field ~walls:blocked ~roots:goals ~visited
  ~max_distance:Distance_field.unreachable;
let direction = Distance_field.next_move_from field (Champion.position (self_champion ())) in
direction
```

### next_moves_from

```ocaml
val next_moves_from : t -> Vec2.t -> Vec2.t list
```

Every optimal step from a tile towards a root, as direction deltas in compass order.

### print

```ocaml
val print : t -> unit
```

`print d` prints the field to stdout for debugging.

- `d`: Distance field.

### raw_buffer_size

```ocaml
val raw_buffer_size : t -> int
```

Size in bytes of the engine-chunked buffer.

- `d`: Distance field.

### set

```ocaml
val set : t -> Vec2.t -> int -> unit
```

`set d p value` stores a distance at `p`; raises outside the map.

- `d`: Distance field.
- `p`: Tile.
- `value`: Distance to store.

### t

```ocaml
type t
```

### unreachable

```ocaml
val unreachable : int
```

Distance stored for tiles the search did not reach.

### width

```ocaml
val width : t -> int
```

Map width in tiles.

- `d`: Distance field.

<a id="cambc-draft"></a>

## Cambc.Draft

### current

```ocaml
val current : Team.t -> Champion_draft.t list
```

`current team` is the team's picks so far, in order.

- `team`: Team whose picks to return.

### pick

```ocaml
val pick : Champion_draft.t -> unit
```

`pick champion` picks a champion for the current draft round; only valid during the draft.

- `champion`: Champion to pick.

### team_size

```ocaml
val team_size : unit -> int
```

Number of champions each team drafts.

<a id="cambc-draft-memory"></a>

## Cambc.Draft_memory

### bytes

```ocaml
val bytes : unit -> Bytes.t
```

Copy of the draft memory snapshot.

### get

```ocaml
val get : int -> int
```

`get offset` reads one byte of the snapshot.

- `offset`: Byte offset into the snapshot.

### length

```ocaml
val length : unit -> int
```

Length of the draft memory snapshot in bytes.

### submit

```ocaml
val submit : Bytes.t -> unit
```

`submit data` sets the draft memory passed to this team's gameplay bots; only valid during the draft.

- `data`: Bytes to submit.

<a id="cambc-error-code"></a>

## Cambc.Error_code

### all

```ocaml
val all : t list
```

Every value, in declaration order.

*Example: Inspect a caught SDK error when diagnosing a rejected action.*

```ocaml
let result = Error_code.all
```

### t

```ocaml
type t = | Success | Invalid_handle | Out_of_memory | File_not_found | Null_pointer | Invalid_argument | Map_parse_error | Invalid_map_file | Invalid_map_version | Replay_parse_error | Invalid_replay_file | Invalid_replay_version | Invalid_draft | Draft_not_drafting | Draft_duplicate_champion | Draft_invalid_round | Draft_unavailable | Already_initialized | Invalid_action | Invalid_action_memory_bad_range | Invalid_action_memory_draft_frozen | Invalid_action_move_cant_move | Invalid_action_move_bad_destination | Invalid_action_spell_cast_invalid_source | Invalid_action_spell_cast_invalid_slot | Invalid_action_spell_cast_no_ability | Invalid_action_spell_cast_cant_cast | Invalid_action_spell_cast_already_cast | Invalid_action_spell_cast_on_cooldown | Invalid_action_spell_cast_no_charges | Invalid_action_spell_cast_bad_target | Invalid_action_spell_cast_out_of_range | Invalid_action_spell_cast_bad_destination | Invalid_action_cant_act | Invalid_action_is_recalling | Invalid_action_is_submitting_gems | Invalid_action_move_already_moved | Invalid_action_move_out_of_range | Invalid_action_move_unreachable | Invalid_action_attack_invalid_source | Invalid_action_attack_cant_attack | Invalid_action_attack_already_attacked | Invalid_action_attack_bad_target | Invalid_action_attack_out_of_range | Invalid_action_recall_cant_channel | Invalid_action_submit_gems_cant_channel | Invalid_action_submit_gems_no_gems | Invalid_action_submit_gems_bad_altar | Invalid_action_submit_gems_out_of_range | Invalid_action_buy_item_not_on_spawn | Invalid_action_buy_item_invalid_item | Invalid_action_buy_item_invalid_count | Invalid_action_buy_item_not_enough_gold | Invalid_action_buy_item_inventory_full | Invalid_action_buy_item_stats_overflow | Invalid_action_buy_consumable_not_on_spawn | Invalid_action_buy_consumable_invalid_type | Invalid_action_buy_consumable_invalid_count | Invalid_action_buy_consumable_inventory_full | Invalid_action_buy_consumable_not_enough_gold | Invalid_action_use_consumable_invalid_type | Invalid_action_use_consumable_not_owned | Invalid_action_place_ward_no_charges | Invalid_action_place_ward_cant_place | Invalid_action_place_ward_bad_destination | Invalid_action_place_ward_out_of_range | Map_set_team_aspawn_area_bad_position | Map_add_bush_bad_position | Map_remove_bush_bad_position | Map_add_wall_bad_position | Map_remove_wall_bad_position | Map_add_hole_bad_position | Map_remove_hole_bad_position | Map_add_altar_bad_position | Map_remove_altar_bad_position | Map_get_bush_bad_position | Map_get_wall_bad_position | Map_get_hole_bad_position | Map_get_altar_bad_position | Map_get_camp_handle_at_bad_position | Map_add_camp_bad_position | Map_set_camp_bad_position | Invalid_action_champion_teleport_bad_destination | Invalid_action_respawn_group_blocked_spawn | Invalid_action_camp_teleport_bad_destination | Timeline_bad_seek_position | Timeline_bad_seek_substep | Api_no_map | Managed_resources_bad_position | Managed_resources_bad_radius | Managed_resources_aliasing | Managed_resources_metadata_mismatch | Managed_resources_opaque_origin | Api_invalid_team | Api_invalid_perspective | Api_not_initialized | Api_bad_position | Api_not_in_vision | Api_not_found | Api_invalid_camp_group | Api_invalid_camp_info | Api_invalid_camp | Api_invalid_champion | Api_invalid_ward | Api_invalid_ability | Api_not_teammate | Api_camp_group_not_waiting_to_respawn | Api_champion_alive | Api_invalid_champion_type | Api_invalid_camp_type | Api_value_out_of_range | Api_buffer_too_small | Api_not_owner | Invalid_action_recall_already_used | Invalid_action_submit_gems_already_used | Invalid_action_cancel_channel_not_channeling | Invalid_action_cancel_channel_already_used | Invalid_action_place_ward_ally_ward_present | Invalid_action_altar_lock_bad_altar | Invalid_action_altar_lock_out_of_range | Invalid_action_altar_lock_already_locked | Invalid_action_is_teleporting | Invalid_action_cancel_channel_not_cancellable | Invalid_action_submit_gems_altar_locked | Invalid_action_spell_cast_already_moved | Invalid_action_move_exclusive_spell_cast | Invalid_action_sell_not_tavi | Invalid_action_sell_invalid_item | Invalid_action_sell_not_owned | Invalid_action_sell_already_sold | Invalid_action_sell_gold_overflow | Invalid_action_sell_not_on_spawn | Draft_already_picked | Draft_no_champion_selected | Unknown of int
```

### to_string

```ocaml
val to_string : t -> string
```

`to_string x` is the name of `x`.

- `x`: Value to name.

*Example: Inspect a caught SDK error when diagnosing a rejected action.*

```ocaml
let result = Error_code.to_string value1
```

<a id="cambc-game-map"></a>

## Cambc.Game_map

### altars

```ocaml
val altars : unit -> Bitboard.t
```

Altar tiles, where gems are tributed.

*Example: Build a terrain-only walking mask. Also exclude occupied tiles and the enemy spawn when selecting a legal step.*

```ocaml
let blocked =
  Bitboard.union (Game_map.walls ())
    (Bitboard.union (Game_map.holes ()) (Game_map.altars ()))
let walkable = Bitboard.complement blocked
```

### bushes

```ocaml
val bushes : unit -> Bitboard.t
```

Bush tiles, which hide champions from outside vision.

### camp_at

```ocaml
val camp_at : Vec2.t -> Camp.t
```

`camp_at p` is the camp that spawns at `p`; raises if none does.

- `p`: Spawn tile.

### camp_at_opt

```ocaml
val camp_at_opt : Vec2.t -> Camp.t option
```

Like `camp_at`, but `None` if no camp spawns at `p`.

- `p`: Spawn tile.

### camp_groups

```ocaml
val camp_groups : unit -> Camp_group.t list
```

Every camp group on the map, also available in draft.

### height

```ocaml
val height : unit -> int
```

Map height in tiles.

### holes

```ocaml
val holes : unit -> Bitboard.t
```

Hole tiles, which block movement but not vision.

*Example: Build a terrain-only walking mask. Also exclude occupied tiles and the enemy spawn when selecting a legal step.*

```ocaml
let blocked =
  Bitboard.union (Game_map.walls ())
    (Bitboard.union (Game_map.holes ()) (Game_map.altars ()))
let walkable = Bitboard.complement blocked
```

### is_in_bounds

```ocaml
val is_in_bounds : Vec2.t -> bool
```

`is_in_bounds p` is true when `p` lies on the map.

- `p`: Position to check.

### reflect_horizontal

```ocaml
val reflect_horizontal : Vec2.t -> Vec2.t
```

`reflect_horizontal p` reflects `p` horizontally, reversing x.

- `p`: Map position.

### reflect_vertical

```ocaml
val reflect_vertical : Vec2.t -> Vec2.t
```

`reflect_vertical p` reflects `p` vertically, reversing y.

- `p`: Map position.

### rotate_180

```ocaml
val rotate_180 : Vec2.t -> Vec2.t
```

`rotate_180 p` rotates `p` 180 degrees within the map.

- `p`: Map position.

### spawn_region

```ocaml
val spawn_region : Team.t -> Bitboard.t
```

`spawn_region team` is the team's spawn region.

- `team`: Team whose spawn region to return.

### symmetry

```ocaml
val symmetry : unit -> Symmetry.t
```

The symmetry the map was generated with.

### walls

```ocaml
val walls : unit -> Bitboard.t
```

Wall tiles. Terrain and spawn boards are shared cached values: copy before mutating.

*Example: Build a terrain-only walking mask. Also exclude occupied tiles and the enemy spawn when selecting a legal step.*

```ocaml
let blocked =
  Bitboard.union (Game_map.walls ())
    (Bitboard.union (Game_map.holes ()) (Game_map.altars ()))
let walkable = Bitboard.complement blocked
```

### width

```ocaml
val width : unit -> int
```

Map width in tiles.

<a id="cambc-game-unit"></a>

## Cambc.Game_unit

### attack_range

```ocaml
val attack_range : t -> int
```

`attack_range u` is the attack range in Chebyshev tiles; melee units have range 1.

- `u`: Unit.

### attack_tiles

```ocaml
val attack_tiles : t -> Bitboard.t
```

`attack_tiles u` is the tiles within attack range of `u`'s position.

- `u`: Unit.

### attack_tiles_into

```ocaml
val attack_tiles_into : t -> Bitboard.t -> unit
```

Like `attack_tiles`, but writes into `out`.

- `u`: Unit.
- `out`: Destination; its previous contents are overwritten.

### buffs

```ocaml
val buffs : t -> Buff.t list
```

`buffs u` is the current buffs; raises if `u` is not visible.

- `u`: Unit.

### focus

```ocaml
val focus : t -> float
```

`focus u` is current focus; raises if `u` is not visible.

- `u`: Unit.

### health

```ocaml
val health : t -> float
```

`health u` is current health; raises if `u` is not visible.

- `u`: Unit.

### is_visible

```ocaml
val is_visible : t -> bool
```

`is_visible u` is true when `u` is currently visible.

- `u`: Unit.

### max_health

```ocaml
val max_health : t -> float
```

`max_health u` is current maximum health; raises if `u` is not visible.

- `u`: Unit.

### position

```ocaml
val position : t -> Vec2.t
```

`position u` is the current tile; raises if `u` is not visible.

- `u`: Unit.

### strength

```ocaml
val strength : t -> float
```

`strength u` is current strength; raises if `u` is not visible.

- `u`: Unit.

### t

```ocaml
type t = [ `Champion of champion | `Camp of camp ]
```

<a id="cambc-item"></a>

## Cambc.Item

### all

```ocaml
val all : t list
```

Every value, in declaration order.

### t

```ocaml
type t = | Monster_shard_of_strength | Monster_emblem_of_strength | Monster_shard_of_focus | Monster_emblem_of_focus | Monster_shard_of_health | Monster_emblem_of_health | Power_shard_of_strength | Power_emblem_of_strength | Power_shard_of_focus | Power_emblem_of_focus | Power_shard_of_health | Power_emblem_of_health | Durability_shard_of_strength | Durability_emblem_of_strength | Durability_shard_of_focus | Durability_emblem_of_focus | Durability_shard_of_health | Durability_emblem_of_health | Treasure_shard_of_strength | Treasure_emblem_of_strength | Treasure_shard_of_focus | Treasure_emblem_of_focus | Treasure_shard_of_health | Treasure_emblem_of_health | Jungle_shard_of_strength | Jungle_emblem_of_strength | Jungle_shard_of_focus | Jungle_emblem_of_focus | Jungle_shard_of_health | Jungle_emblem_of_health | Home_shard_of_strength | Home_emblem_of_strength | Home_shard_of_focus | Home_emblem_of_focus | Home_shard_of_health | Home_emblem_of_health | Bruiser_shard_of_strength | Bruiser_emblem_of_strength | Bruiser_shard_of_focus | Bruiser_emblem_of_focus | Bruiser_shard_of_health | Bruiser_emblem_of_health
```

### to_string

```ocaml
val to_string : t -> string
```

`to_string x` is the name of `x`.

- `x`: Value to name.

<a id="cambc-item-counts"></a>

## Cambc.Item_counts

### fold

```ocaml
val fold : (Item.t -> int -> 'a -> 'a) -> t -> 'a -> 'a
```

`fold fn c init` folds `fn` over each held type and its count.

- `fn`: Folding function.
- `c`: Inventory counts.
- `init`: Initial accumulator.

### get

```ocaml
val get : t -> Item.t -> int
```

`get c k` is the number of `k` in the inventory.

- `c`: Inventory counts.
- `k`: Item type.

### iter

```ocaml
val iter : (Item.t -> int -> unit) -> t -> unit
```

`iter fn c` calls `fn` on each held type and its count.

- `fn`: Callback.
- `c`: Inventory counts.

### t

```ocaml
type t
```

### to_list

```ocaml
val to_list : t -> (Item.t * int) list
```

`to_list c` lists each held type with its count.

- `c`: Inventory counts.

<a id="cambc-item-info"></a>

## Cambc.Item_info

### combine_count

```ocaml
val combine_count : Item.t -> int
```

`combine_count item` is how many copies combine into the result item.

- `item`: Item type.

### cost

```ocaml
val cost : Item.t -> int
```

`cost item` is the gold cost to buy the item.

- `item`: Item type.

### focus_points

```ocaml
val focus_points : Item.t -> int
```

Focus the item grants.

- `item`: Item type.

### get

```ocaml
val get : Item.t -> t
```

`get item` is the item's static design data.

- `item`: Item type.

### health_points

```ocaml
val health_points : Item.t -> int
```

Maximum health the item grants.

- `item`: Item type.

### is_purchasable

```ocaml
val is_purchasable : Item.t -> bool
```

`is_purchasable item` is true when the shop sells the item directly.

- `item`: Item type.

### passive

```ocaml
val passive : Item.t -> Item_passive.t option
```

Passive effect the item grants, if any.

- `item`: Item type.

### passive_magnitude

```ocaml
val passive_magnitude : Item.t -> float
```

Strength of the item's passive effect.

- `item`: Item type.

### result

```ocaml
val result : Item.t -> Item.t option
```

`result item` is the item these copies combine into, if any.

- `item`: Item type.

### strength_points

```ocaml
val strength_points : Item.t -> int
```

Strength the item grants.

- `item`: Item type.

### t

```ocaml
type t = { cost : int; combine_count : int; result : Item.t option; health_points : int; strength_points : int; focus_points : int; passive : Item_passive.t option; passive_magnitude : float; purchasable : bool; }
```

<a id="cambc-item-passive"></a>

## Cambc.Item_passive

### t

```ocaml
type t = Monster | Durability | Treasure | Jungle | Home
```

### to_string

```ocaml
val to_string : t -> string
```

`to_string p` is the name of an item passive.

- `p`: Item passive.

<a id="cambc-passive"></a>

## Cambc.Passive

### all

```ocaml
val all : t list
```

Every value, in declaration order.

### t

```ocaml
type t = | None | Bonus_gold | Remote_shop | Gem_focus | Splash_attack | Health_strength | Reset_cooldowns_on_kill | Retaliation | Stun_immunity | Missing_health_damage
```

### to_string

```ocaml
val to_string : t -> string
```

`to_string x` is the name of `x`.

- `x`: Value to name.

<a id="cambc-shared-memory"></a>

## Cambc.Shared_memory

### get

```ocaml
val get : int -> int
```

`get offset` reads one byte.

- `offset`: Byte offset into shared memory.

### kind

```ocaml
type _ kind = | U8 : int kind | I8 : int kind | U16 : int kind | I16 : int kind | U32 : int kind | I32 : int kind | I64 : int64 kind | F32 : float kind | F64 : float kind
```

Element types for typed reads/writes (little-endian, like the Rust/C++ SDKs).

### read

```ocaml
val read : offset:int -> int -> Bytes.t
```

`read ~offset len` reads `len` bytes; raises if the range does not fit.

- `offset`: Byte offset into shared memory.
- `len`: Number of bytes to read.

*Example: Reserve byte zero in your team's memory layout for a shared objective ID. All allied bots must agree on its meaning.*

```ocaml
let read_objective () =
  let data = Shared_memory.read ~offset:0 1 in
  Char.code (Bytes.get data 0)
```

### read_into

```ocaml
val read_into : offset:int -> Bytes.t -> unit
```

`read_into ~offset out` fills `out` from shared memory.

- `offset`: Byte offset into shared memory.
- `out`: Destination; its length sets how many bytes are read.

### read_values

```ocaml
val read_values : offset:int -> 'a kind -> int -> 'a array
```

`read_values ~offset kind n` reads `n` typed values in little-endian layout.

- `offset`: Byte offset into shared memory.
- `kind`: Element type.
- `n`: Number of values to read.

### set

```ocaml
val set : int -> int -> unit
```

`set offset value` writes one byte.

- `offset`: Byte offset into shared memory.
- `value`: Byte to store, 0 to 255.

### size

```ocaml
val size : unit -> int
```

Shared memory size in bytes.

### write

```ocaml
val write : offset:int -> Bytes.t -> unit
```

`write ~offset data` writes bytes; raises if the range does not fit.

- `offset`: Byte offset into shared memory.
- `data`: Bytes to write.

*Example: Reserve byte zero in your team's memory layout for a shared objective ID. All allied bots must agree on its meaning.*

```ocaml
let share_objective () =
  Shared_memory.write ~offset:0 (Bytes.make 1 (Char.chr 2))
```

### write_values

```ocaml
val write_values : offset:int -> 'a kind -> 'a array -> unit
```

`write_values ~offset kind values` writes typed values in little-endian layout.

- `offset`: Byte offset into shared memory.
- `kind`: Element type.
- `values`: Values to write.

<a id="cambc-symmetry"></a>

## Cambc.Symmetry

### all

```ocaml
val all : t list
```

Every value, in declaration order.

### t

```ocaml
type t = | Horizontal | Vertical | Rotational180
```

### to_string

```ocaml
val to_string : t -> string
```

`to_string x` is the name of `x`.

- `x`: Value to name.

<a id="cambc-team"></a>

## Cambc.Team

### equal

```ocaml
val equal : t -> t -> bool
```

`equal a b` is true for the same team.

- `a`: First team.
- `b`: Second team.

### opponent

```ocaml
val opponent : t -> t
```

`opponent t` is the other team.

- `t`: Team.

### t

```ocaml
type t = Ally | Enemy
```

### to_string

```ocaml
val to_string : t -> string
```

Name of a team.

- `t`: Team.

<a id="cambc-teleport"></a>

## Cambc.Teleport

### is_ally

```ocaml
val is_ally : t -> bool
```

Check whether this teleport belongs to the observing team.

- `t`: Teleport snapshot.

### is_enemy

```ocaml
val is_enemy : t -> bool
```

Check whether this teleport belongs to the opposing team.

- `t`: Teleport snapshot.

### t

```ocaml
type t = { champion : champion; team : Team.t; position : Vec2.t; remaining_time : int; }
```

### visible_tiles

```ocaml
val visible_tiles : t -> Bitboard.t
```

`visible_tiles t` is the tiles visible from the reservation.

- `t`: Teleport snapshot.

### visible_tiles_into

```ocaml
val visible_tiles_into : t -> Bitboard.t -> unit
```

Like `visible_tiles`, but writes into `out`.

- `t`: Teleport snapshot.
- `out`: Destination; its previous contents are overwritten.

<a id="cambc-vec2"></a>

## Cambc.Vec2

### ( - )

```ocaml
val ( - ) : t -> t -> t
```

Same as `sub`.

### ( * )

```ocaml
val ( * ) : int -> t -> t
```

Same as `scale`.

### ( + )

```ocaml
val ( + ) : t -> t -> t
```

Same as `add`.

### ( ~- )

```ocaml
val ( ~- ) : t -> t
```

Same as `neg`.

### add

```ocaml
val add : t -> t -> t
```

`add a b` is the component-wise sum.

- `a`: First vector.
- `b`: Second vector.

### chebyshev_distance

```ocaml
val chebyshev_distance : t -> t -> int
```

`chebyshev_distance a b` is the number of king moves between the tiles.

- `a`: First vector.
- `b`: Second vector.

### compare

```ocaml
val compare : t -> t -> int
```

Total order on vectors, by `x` then `y`.

- `a`: First vector.
- `b`: Second vector.

### cross

```ocaml
val cross : t -> t -> int
```

`cross a b` is the signed 2D cross product.

- `a`: First vector.
- `b`: Second vector.

### div

```ocaml
val div : t -> int -> t
```

`div v k` divides both components by `k`, truncating; raises on zero.

- `v`: Vector.
- `k`: Divisor.

### dot

```ocaml
val dot : t -> t -> int
```

`dot a b` is the dot product.

- `a`: First vector.
- `b`: Second vector.

### east

```ocaml
val east : t
```

`(1, 0)`.

### equal

```ocaml
val equal : t -> t -> bool
```

`equal a b` is true when both coordinates match.

- `a`: First vector.
- `b`: Second vector.

### hash

```ocaml
val hash : t -> int
```

Hash consistent with `equal`.

- `v`: Vector.

### length_squared

```ocaml
val length_squared : t -> int
```

`length_squared v` is the squared Euclidean length.

- `v`: Vector.

### make

```ocaml
val make : int -> int -> t
```

`make x y` is the vector `(x, y)`.

- `x`: Horizontal coordinate.
- `y`: Vertical coordinate.

### neg

```ocaml
val neg : t -> t
```

`neg v` negates both components.

- `v`: Vector.

### north

```ocaml
val north : t
```

`(0, 1)`; +y is north, matching the engine and `rotate_cw`/`rotate_ccw`.

### north_east

```ocaml
val north_east : t
```

`(1, 1)`.

### north_west

```ocaml
val north_west : t
```

`(-1, 1)`.

### reflect_horizontal

```ocaml
val reflect_horizontal : t -> t
```

`reflect_horizontal p` reflects a map position horizontally, reversing x.

- `p`: Map position.

### reflect_vertical

```ocaml
val reflect_vertical : t -> t
```

`reflect_vertical p` reflects a map position vertically, reversing y.

- `p`: Map position.

### rotate_180

```ocaml
val rotate_180 : t -> t
```

`rotate_180 p` rotates a map position 180 degrees within the map.

- `p`: Map position.

### rotate_ccw

```ocaml
val rotate_ccw : t -> t
```

`rotate_ccw v` rotates a direction 45 degrees counter-clockwise.

- `v`: Vector.

### rotate_cw

```ocaml
val rotate_cw : t -> t
```

`rotate_cw v` rotates a direction 45 degrees clockwise.

- `v`: Vector.

### scale

```ocaml
val scale : int -> t -> t
```

`scale k v` multiplies both components by `k`.

- `k`: Scale factor.
- `v`: Vector.

### south

```ocaml
val south : t
```

`(0, -1)`.

### south_east

```ocaml
val south_east : t
```

`(1, -1)`.

### south_west

```ocaml
val south_west : t
```

`(-1, -1)`.

### sub

```ocaml
val sub : t -> t -> t
```

`sub a b` is the component-wise difference `a - b`.

- `a`: First vector.
- `b`: Second vector.

### t

```ocaml
type t = { x : int; y : int }
```

### to_string

```ocaml
val to_string : t -> string
```

`to_string v` formats the vector as `(x, y)`.

- `v`: Vector.

### west

```ocaml
val west : t
```

`(-1, 0)`.

### zero

```ocaml
val zero : t
```

`(0, 0)`.

<a id="cambc-vision"></a>

## Cambc.Vision

### altar_lock_at

```ocaml
val altar_lock_at : Vec2.t -> Altar_lock.t
```

`altar_lock_at p` is the visible altar lock on `p`, ally first; raises if there is none.

- `p`: Tile to query.

### altar_lock_at_opt

```ocaml
val altar_lock_at_opt : Vec2.t -> Altar_lock.t option
```

Like `altar_lock_at`, but `None` instead of raising.

- `p`: Tile to query.

### altar_lock_tiles

```ocaml
val altar_lock_tiles : ?team:Team.t -> unit -> Bitboard.t
```

`altar_lock_tiles ?team ()` is the tiles of visible altar locks.

- `team`: Team to include; both teams when omitted.

### altar_lock_tiles_into

```ocaml
val altar_lock_tiles_into : ?team:Team.t -> Bitboard.t -> unit
```

Like `altar_lock_tiles`, but writes into `out`.

- `team`: Team to include; both teams when omitted.
- `out`: Destination; its previous contents are overwritten.

### altar_locks

```ocaml
val altar_locks : ?team:Team.t -> unit -> Altar_lock.t list
```

`altar_locks ?team ()` is snapshots of visible altar locks.

- `team`: Team to include; both teams when omitted.

### asleep_camp_tiles

```ocaml
val asleep_camp_tiles : unit -> Bitboard.t
```

Tiles of visible asleep camps. Dead camps are excluded.

### asleep_camp_tiles_into

```ocaml
val asleep_camp_tiles_into : Bitboard.t -> unit
```

Like `asleep_camp_tiles`, but writes into `out`.

- `out`: Destination; its previous contents are overwritten.

### awake_camp_tiles

```ocaml
val awake_camp_tiles : unit -> Bitboard.t
```

Tiles of visible awake camps. Dead camps are excluded.

### awake_camp_tiles_into

```ocaml
val awake_camp_tiles_into : Bitboard.t -> unit
```

Like `awake_camp_tiles`, but writes into `out`.

- `out`: Destination; its previous contents are overwritten.

### camp_at

```ocaml
val camp_at : Vec2.t -> Camp.t
```

`camp_at p` is the visible camp currently on `p`; raises if there is none or the tile is hidden.

- `p`: Tile to query.

### camp_at_opt

```ocaml
val camp_at_opt : Vec2.t -> Camp.t option
```

Like `camp_at`, but `None` instead of raising.

- `p`: Tile to query.

### camp_groups

```ocaml
val camp_groups : unit -> Camp_group.t list
```

Camp groups with at least one visible camp.

### camp_tiles

```ocaml
val camp_tiles : unit -> Bitboard.t
```

Tiles of visible camps.

### camp_tiles_into

```ocaml
val camp_tiles_into : Bitboard.t -> unit
```

Like `camp_tiles`, but writes into `out`.

- `out`: Destination; its previous contents are overwritten.

### camps

```ocaml
val camps : unit -> Camp.t list
```

Visible camps.

### champion_at

```ocaml
val champion_at : Vec2.t -> Champion.t
```

`champion_at p` is the visible champion on `p`; raises if there is none or the tile is hidden.

- `p`: Tile to query.

### champion_at_opt

```ocaml
val champion_at_opt : Vec2.t -> Champion.t option
```

Like `champion_at`, but `None` instead of raising.

- `p`: Tile to query.

### champion_tiles

```ocaml
val champion_tiles : ?team:Team.t -> unit -> Bitboard.t
```

`champion_tiles ?team ()` is the tiles of visible champions.

- `team`: Team to include; both teams when omitted.

### champion_tiles_into

```ocaml
val champion_tiles_into : ?team:Team.t -> Bitboard.t -> unit
```

Like `champion_tiles`, but writes into `out`.

- `team`: Team to include; both teams when omitted.
- `out`: Destination; its previous contents are overwritten.

### champions

```ocaml
val champions : ?team:Team.t -> unit -> Champion.t list
```

`champions ?team ()` is the visible champions.

- `team`: Team to include; both teams when omitted.

### has_altar_lock

```ocaml
val has_altar_lock : Vec2.t -> bool
```

`has_altar_lock p` is true when a visible altar lock of either team is on `p`.

- `p`: Tile to query.

### has_camp

```ocaml
val has_camp : Vec2.t -> bool
```

`has_camp p` is true when a visible camp is on `p`.

- `p`: Tile to query.

### has_champion

```ocaml
val has_champion : Vec2.t -> bool
```

`has_champion p` is true when a visible champion is on `p`.

- `p`: Tile to query.

### has_teleport

```ocaml
val has_teleport : Vec2.t -> bool
```

`has_teleport p` is true when a visible teleport reservation is on `p`.

- `p`: Tile to query.

### has_ward

```ocaml
val has_ward : ?team:Team.t -> Vec2.t -> bool
```

`has_ward ?team p` is true when a visible ward is on `p`; hidden wards give `false`.

- `team`: Team to restrict to; either team when omitted.
- `p`: Tile to query.

### in_vision

```ocaml
val in_vision : Vec2.t -> bool
```

Check current self vision, including owned ward vision, even on empty tiles. Hidden tiles return `false`; out-of-bounds positions raise `Api_bad_position`.

- `position`: Tile to query.

### teleport_at

```ocaml
val teleport_at : Vec2.t -> Teleport.t
```

`teleport_at p` is the visible teleport reservation on `p`; raises if there is none.

- `p`: Tile to query.

### teleport_at_opt

```ocaml
val teleport_at_opt : Vec2.t -> Teleport.t option
```

Like `teleport_at`, but `None` instead of raising.

- `p`: Tile to query.

### teleport_tiles

```ocaml
val teleport_tiles : unit -> Bitboard.t
```

Tiles of visible teleport reservations.

### teleport_tiles_into

```ocaml
val teleport_tiles_into : Bitboard.t -> unit
```

Like `teleport_tiles`, but writes into `out`.

- `out`: Destination; its previous contents are overwritten.

### teleports

```ocaml
val teleports : unit -> Teleport.t list
```

Snapshots of visible teleport reservations.

### visible_tiles

```ocaml
val visible_tiles : unit -> Bitboard.t
```

Every tile visible to the bot's champion.

### visible_tiles_into

```ocaml
val visible_tiles_into : Bitboard.t -> unit
```

Like `visible_tiles`, but writes into `out`.

- `out`: Destination; its previous contents are overwritten.

### ward_at

```ocaml
val ward_at : ?team:Team.t -> Vec2.t -> Ward.t
```

`ward_at ?team p` is the visible ward on `p`; raises if there is none.

- `team`: Team to restrict to; either team when omitted.
- `p`: Tile to query.

### ward_at_opt

```ocaml
val ward_at_opt : ?team:Team.t -> Vec2.t -> Ward.t option
```

Like `ward_at`, but `None` instead of raising.

- `team`: Team to restrict to; either team when omitted.
- `p`: Tile to query.

### ward_tiles

```ocaml
val ward_tiles : ?team:Team.t -> unit -> Bitboard.t
```

`ward_tiles ?team ()` is the tiles of visible wards.

- `team`: Team to include; both teams when omitted.

### ward_tiles_into

```ocaml
val ward_tiles_into : ?team:Team.t -> Bitboard.t -> unit
```

Like `ward_tiles`, but writes into `out`.

- `team`: Team to include; both teams when omitted.
- `out`: Destination; its previous contents are overwritten.

### wards

```ocaml
val wards : ?team:Team.t -> unit -> Ward.t list
```

`wards ?team ()` is snapshots of visible wards.

- `team`: Team to include; both teams when omitted.

<a id="cambc-ward"></a>

## Cambc.Ward

### is_ally

```ocaml
val is_ally : t -> bool
```

Check whether this ward belongs to the observing team.

- `w`: Ward snapshot.

### is_enemy

```ocaml
val is_enemy : t -> bool
```

Check whether this ward belongs to the opposing team.

- `w`: Ward snapshot.

### owner

```ocaml
val owner : t -> champion
```

Return the owning champion captured when this ward was visible, even if the owner is hidden. Live champion state still requires the champion to be in vision.

- `w`: Ward snapshot.

### t

```ocaml
type t = { position : Vec2.t; team : Team.t; remaining_time : int option; owner : champion }
```

### visible_tiles

```ocaml
val visible_tiles : t -> Bitboard.t
```

`visible_tiles w` is the tiles the ward sees.

- `w`: Ward snapshot.

### visible_tiles_from

```ocaml
val visible_tiles_from : Vec2.t -> Bitboard.t
```

`visible_tiles_from p` is the vision an ordinary ward would have at `p`.

- `p`: Hypothetical ward tile.

### visible_tiles_from_into

```ocaml
val visible_tiles_from_into : Vec2.t -> Bitboard.t -> unit
```

Like `visible_tiles_from`, but writes into `out`.

- `p`: Hypothetical ward tile.
- `out`: Destination; its previous contents are overwritten.

### visible_tiles_into

```ocaml
val visible_tiles_into : t -> Bitboard.t -> unit
```

Like `visible_tiles`, but writes into `out`.

- `w`: Ward snapshot.
- `out`: Destination; its previous contents are overwritten.
