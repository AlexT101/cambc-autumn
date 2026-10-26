# Bot API reference: C++

*Public C++ SDK functions, methods and camp-group state types.*

Start with [Getting Started](../guides/cpp/first-bot.md).

## Contents

- [cambc](#cambc) (82)
- [cambc::ability](#cambc-ability) (35)
- [cambc::ability_aoe_damage](#cambc-ability-aoe-damage) (1)
- [cambc::ability_attack_reset](#cambc-ability-attack-reset) (1)
- [cambc::ability_cc](#cambc-ability-cc) (1)
- [cambc::ability_damage](#cambc-ability-damage) (1)
- [cambc::ability_dash](#cambc-ability-dash) (1)
- [cambc::ability_heal](#cambc-ability-heal) (1)
- [cambc::ability_properties](#cambc-ability-properties) (1)
- [cambc::ability_shield](#cambc-ability-shield) (1)
- [cambc::ability_target_mask](#cambc-ability-target-mask) (27)
- [cambc::altar_lock](#cambc-altar-lock) (7)
- [cambc::bitboard](#cambc-bitboard) (60)
- [cambc::buff_collection](#cambc-buff-collection) (13)
- [cambc::buff_collection::const_iterator](#cambc-buff-collection-const-iterator) (14)
- [cambc::buff_enhanced_attack](#cambc-buff-enhanced-attack) (1)
- [cambc::buff_restrictions](#cambc-buff-restrictions) (27)
- [cambc::buff_shield](#cambc-buff-shield) (1)
- [cambc::buff_stun](#cambc-buff-stun) (1)
- [cambc::camp](#cambc-camp) (24)
- [cambc::camp_state](#cambc-camp-state) (9)
- [cambc::champion](#cambc-champion) (60)
- [cambc::champion_state](#cambc-champion-state) (28)
- [cambc::consumable](#cambc-consumable) (5)
- [cambc::consumable_info](#cambc-consumable-info) (1)
- [cambc::consumable_type](#cambc-consumable-type) (9)
- [cambc::debug](#cambc-debug) (2)
- [cambc::distance_field](#cambc-distance-field) (28)
- [cambc::draft](#cambc-draft) (3)
- [cambc::draft_memory_buffer](#cambc-draft-memory-buffer) (12)
- [cambc::enum_map](#cambc-enum-map) (10)
- [cambc::error](#cambc-error) (5)
- [cambc::item_info](#cambc-item-info) (1)
- [cambc::item_type](#cambc-item-type) (16)
- [cambc::map](#cambc-map) (21)
- [cambc::map::camp_group](#cambc-map-camp-group) (12)
- [cambc::shared_memory_buffer](#cambc-shared-memory-buffer) (7)
- [cambc::shared_memory_buffer::reference](#cambc-shared-memory-buffer-reference) (5)
- [cambc::teleport](#cambc-teleport) (10)
- [cambc::type_tag_t](#cambc-type-tag-t) (1)
- [cambc::uninitialized_t](#cambc-uninitialized-t) (1)
- [cambc::unit](#cambc-unit) (11)
- [cambc::vec2](#cambc-vec2) (23)
- [cambc::vision](#cambc-vision) (44)
- [cambc::ward](#cambc-ward) (11)
- [std](#std) (4)

<a id="cambc"></a>

## cambc

### ability

```cpp
class ability { };
```

A champion ability slot; actions require the owning champion to be self.

### ability_aoe_damage

```cpp
struct ability_aoe_damage : ability_properties { static constexpr ability_kind kind; float range, modifier, radius; std::int32_t duration; };
```

Cached area-damage metadata, including effect radius and duration.

### ability_attack_reset

```cpp
struct ability_attack_reset : ability_properties { static constexpr ability_kind kind; bool enhanced_attack; };
```

Attack-reset metadata; this payload has no targeting range.

### ability_cc

```cpp
struct ability_cc : ability_properties { static constexpr ability_kind kind; float range, modifier; std::int32_t duration; };
```

Cached crowd-control ability metadata.

### ability_damage

```cpp
struct ability_damage : ability_properties { static constexpr ability_kind kind; float range, modifier; };
```

Cached direct-damage ability metadata.

### ability_dash

```cpp
struct ability_dash : ability_properties { static constexpr ability_kind kind; float range; float radius; float modifier; std::int32_t duration; };
```

Dash metadata. Landing effects apply to enemies and camps only after a successful dash. range: Maximum dash travel distance in tiles. Diagonal steps count as one; the destination must be a different tile reachable by a legal dash path. radius: Chebyshev radius in tiles around the landing tile for damage and stun; 1 includes all eight neighbouring tiles. modifier: Landing damage multiplier: base damage = caster Focus * modifier, before damage bonuses and mitigation. 0 disables landing damage. duration: Stun duration applied on landing, in turns; 0 disables stun. This is not the dash travel time.

### ability_heal

```cpp
struct ability_heal : ability_properties { static constexpr ability_kind kind; float range, modifier; };
```

Cached healing ability metadata.

### ability_info

```cpp
using ability_info = std::variant<ability_attack_reset, ability_damage, ability_aoe_damage, ability_cc, ability_heal, ability_dash, ability_shield>;
```

Owned, tagged ability metadata; use ability_types tags to select a typed payload.

### ability_kind

```cpp
enum class ability_kind : std::uint32_t { attack_reset = 1, damage, aoe_damage, cc, heal, dash, shield };
```

Ability payload types reported by the engine.

### ability_properties

```cpp
struct ability_properties { std::int32_t max_cooldown; ability_target_mask valid_targets; bool exclusive_with_movement; };
```

Properties shared by every ability payload.

### ability_shield

```cpp
struct ability_shield : ability_properties { static constexpr ability_kind kind; float range, modifier; std::int32_t duration; };
```

Cached shield ability metadata.

### ability_target_mask

```cpp
class ability_target_mask { public: static const ability_target_mask camps, enemies, allies, self, ground; };
```

Allowed ability target categories, not a geometric range mask.

### altar_lock

```cpp
class altar_lock { };
```

An immutable observation of a visible altar lock.

### bitboard

```cpp
class bitboard { };
```

Aligned tile mask, empty by default. Raw buffers are engine-chunked; linear buffers are row-major, least-significant bit first.

### buff_collection

```cpp
class buff_collection { };
```

Buff values captured at construction. Call unit::buffs() for fresh values.

### buff_enhanced_attack

```cpp
struct buff_enhanced_attack { static constexpr buff_types kind; std::int32_t duration; };
```

Owned enhanced-attack snapshot with remaining duration.

### buff_restrictions

```cpp
class buff_restrictions { public: static const buff_restrictions move, attack, cast, shop, consumable, ward; };
```

Prohibited actions; contains(buff_restrictions::ward) checks ward placement.

### buff_shield

```cpp
struct buff_shield { static constexpr buff_types kind; std::int32_t duration; float value; };
```

Owned shield snapshot with remaining duration and shield value.

### buff_stun

```cpp
struct buff_stun { static constexpr buff_types kind; std::int32_t duration; };
```

Buff timers are remaining engine rounds, including any application-round extension.

### buff_t

```cpp
using buff_t = std::variant<buff_shield, buff_stun, buff_enhanced_attack>;
```

Owned, tagged active-buff snapshot; each alternative includes its remaining duration.

### buff_types

```cpp
enum class buff_types : std::uint32_t { shield, stun, enhanced_attack, count };
```

Supported active buff kinds; count is an inventory-size sentinel.

### camp

```cpp
class camp : public unit { };
```

A runtime camp, with public spawn metadata and visibility-checked combat queries.

### camp_state

```cpp
class camp_state { public: enum class enum_type : std::uint32_t { dead = 0, alive = 1, asleep = 2 }; static const camp_state dead; static const camp_state alive; static const camp_state asleep; };
```

An individual camp's captured lifecycle. States are mutually exclusive, not flags.

### camp_stats

```cpp
struct camp_stats { float vision_radius; std::int32_t base_move_speed, base_attack_range; float base_health, health_growth, base_strength, strength_growth; float base_focus, focus_growth; };
```

Camp design stats and growth parameters; layout matches Game_CampStats.

### camp_type

```cpp
enum class camp_type : std::int32_t { wolf, elk, gem_cluster, gold_cluster, monolith, golem };
```

Physical camp types.

### champion

```cpp
class champion : public unit { };
```

Champion handle with live queries and self-only actions.

### champion_draft

```cpp
enum class champion_draft : std::int32_t { ryth = 0, vesper_vale, vendetta, cassi_and_issac, stellar, prism, marcella, willow, ren, varg, tavi, heart_of_ruin, };
```

Draft choices; Cassi and Issac share one pick.

### champion_state

```cpp
class champion_state { public: static const champion_state alive, recalling, submitting_gems, can_move, can_attack, completed_turn, recall_started, submit_gems_started, recall_cancelled, submit_gems_cancelled, can_cast, teleporting; };
```

Current life, channel and action flags; contains(champion_state::alive) checks the life bit.

### champion_stats

```cpp
struct champion_stats { std::int32_t vision_radius, base_move_speed, base_attack_range; float base_health, health_growth, base_strength, strength_growth; float base_focus, focus_growth, camp_damage_multiplier; };
```

Champion design stats and growth values.

### champion_type

```cpp
enum class champion_type : std::int32_t { ryth = 0, vesper_vale, vendetta, cassi, issac, stellar, prism, marcella, willow, ren, varg, tavi, heart_of_ruin, };
```

Physical champion types; Cassi and Issac are separate champions.

### champions

```cpp
std::vector<cambc::champion> champions()
```

Get allied and enemy champion handles, including champions outside vision.

### champions

```cpp
std::vector<cambc::champion> champions(team side)
```

Get all champion handles on one side, including champions outside vision.

- `side`: Team to include.

### consumable

```cpp
class consumable { };
```

A consumable inventory entry belonging to a champion.

### consumable_info

```cpp
struct consumable_info { std::uint32_t cost, carry_limit; };
```

Engine-provided consumable price and inventory carry limit.

### consumable_type

```cpp
class consumable_type { public: enum class enum_type : std::uint32_t { tp_crystal, altar_lock, count }; static const consumable_type tp_crystal; static const consumable_type altar_lock; static const consumable_type count; };
```

Consumable inventory keys.

### debug_block

```cpp
debug_block(...)
```

Run the statements without spending fuel when the bot is built in debug mode (`cambc run`, the default); skipped entirely in release mode (`--release`, and always on the platform). The free budget per block is 1000 turns, beyond which the rest of the block is charged; ending the turn inside a block closes the free window. A macro: the code runs inline — `break`/`continue` apply to the enclosing loop, `return` leaves the enclosing function and fuel resumes on the way out. In release mode the code is type-checked but never evaluated. Call it unqualified (`debug_block({ ... });`), not as `cambc::debug_block`, and use no preprocessor directives inside.

### distance_field

```cpp
class distance_field { };
```

Tile distances stored in engine-chunked order. Linear buffers contain row-major uint16 values.

### draft_memory_buffer

```cpp
class draft_memory_buffer { };
```

Fixed-size team draft bytes captured at startup; assignment submits bytes without changing the snapshot.

### end_turn

```cpp
void end_turn()
```

Yield the authenticated bot's current turn to the host.

*Example: Stop optional planning when little fuel remains and yield the current turn.*

```cpp
if (bc::fuel_remaining() < 1000) {
    bc::end_turn();
}
```

### enum_map

```cpp
template <class T, class Value = std::uint32_t> requires (std::is_enum_v<T> || requires { typename T::enum_type; requires std::is_enum_v<typename T::enum_type>; }) class enum_map { };
```

Contiguous, zero-initialised values indexed by an enum or enum wrapper with a count sentinel.

### error

```cpp
class error : public std::runtime_error { };
```

Engine failure with its error code and a copied diagnostic.

### error_code

```cpp
enum class error_code : std::int32_t { success = 0, invalid_handle = 1, out_of_memory = 2, file_not_found = 3, null_pointer = 4, invalid_argument = 5, map_parse_error = 6, invalid_map_file = 7, invalid_map_version = 8, replay_parse_error = 9, invalid_replay_file = 10, invalid_replay_version = 11, invalid_draft = 12, draft_not_drafting = 13, draft_duplicate_champion = 14, draft_invalid_round = 15, draft_unavailable = 16, already_initialized = 17, invalid_action = 18, invalid_action_memory_bad_range = 19, invalid_action_memory_draft_frozen = 20, invalid_action_move_cant_move = 21, invalid_action_move_bad_destination = 22, invalid_action_spell_cast_invalid_source = 23, invalid_action_spell_cast_invalid_slot = 24, invalid_action_spell_cast_no_ability = 25, invalid_action_spell_cast_cant_cast = 26, invalid_action_spell_cast_already_cast = 27, invalid_action_spell_cast_on_cooldown = 28, invalid_action_spell_cast_no_charges = 29, invalid_action_spell_cast_bad_target = 30, invalid_action_spell_cast_out_of_range = 31, invalid_action_spell_cast_bad_destination = 32, invalid_action_cant_act = 33, invalid_action_is_recalling = 34, invalid_action_is_submitting_gems = 35, invalid_action_move_already_moved = 36, invalid_action_move_out_of_range = 37, invalid_action_move_unreachable = 38, invalid_action_attack_invalid_source = 39, invalid_action_attack_cant_attack = 40, invalid_action_attack_already_attacked = 41, invalid_action_attack_bad_target = 42, invalid_action_attack_out_of_range = 43, invalid_action_recall_cant_channel = 44, invalid_action_submit_gems_cant_channel = 45, invalid_action_submit_gems_no_gems = 46, invalid_action_submit_gems_bad_altar = 47, invalid_action_submit_gems_out_of_range = 48, invalid_action_buy_item_not_on_spawn = 49, invalid_action_buy_item_invalid_item = 50, invalid_action_buy_item_invalid_count = 51, invalid_action_buy_item_not_enough_gold = 52, invalid_action_buy_item_inventory_full = 53, invalid_action_buy_item_stats_overflow = 54, invalid_action_buy_consumable_not_on_spawn = 55, invalid_action_buy_consumable_invalid_type = 56, invalid_action_buy_consumable_invalid_count = 57, invalid_action_buy_consumable_inventory_full = 58, invalid_action_buy_consumable_not_enough_gold = 59, invalid_action_use_consumable_invalid_type = 60, invalid_action_use_consumable_not_owned = 61, invalid_action_place_ward_no_charges = 62, invalid_action_place_ward_cant_place = 63, invalid_action_place_ward_bad_destination = 64, invalid_action_place_ward_out_of_range = 65, map_set_team_aspawn_area_bad_position = 66, map_add_bush_bad_position = 67, map_remove_bush_bad_position = 68, map_add_wall_bad_position = 69, map_remove_wall_bad_position = 70, map_add_hole_bad_position = 71, map_remove_hole_bad_position = 72, map_add_altar_bad_position = 73, map_remove_altar_bad_position = 74, map_get_bush_bad_position = 75, map_get_wall_bad_position = 76, map_get_hole_bad_position = 77, map_get_altar_bad_position = 78, map_get_camp_handle_at_bad_position = 79, map_add_camp_bad_position = 80, map_set_camp_bad_position = 81, invalid_action_champion_teleport_bad_destination = 82, invalid_action_respawn_group_blocked_spawn = 83, invalid_action_camp_teleport_bad_destination = 84, timeline_bad_seek_position = 85, timeline_bad_seek_substep = 86, api_no_map = 87, managed_resources_bad_position = 88, managed_resources_bad_radius = 89, managed_resources_aliasing = 90, managed_resources_metadata_mismatch = 91, managed_resources_opaque_origin = 92, api_invalid_team = 93, api_invalid_perspective = 94, api_not_initialized = 95, api_bad_position = 96, api_not_in_vision = 97, api_not_found = 98, api_invalid_camp_group = 99, api_invalid_camp_info = 100, api_invalid_camp = 101, api_invalid_champion = 102, api_invalid_ward = 103, api_invalid_ability = 104, api_not_teammate = 105, api_camp_group_not_waiting_to_respawn = 106, api_champion_alive = 107, api_invalid_champion_type = 108, api_invalid_camp_type = 109, api_value_out_of_range = 110, api_buffer_too_small = 111, api_not_owner = 112, invalid_action_recall_already_used = 113, invalid_action_submit_gems_already_used = 114, invalid_action_cancel_channel_not_channeling = 115, invalid_action_cancel_channel_already_used = 116, invalid_action_place_ward_ally_ward_present = 117, invalid_action_altar_lock_bad_altar = 118, invalid_action_altar_lock_out_of_range = 119, invalid_action_altar_lock_already_locked = 120, invalid_action_is_teleporting = 123, invalid_action_cancel_channel_not_cancellable = 124, invalid_action_submit_gems_altar_locked = 125, invalid_action_spell_cast_already_moved = 126, invalid_action_move_exclusive_spell_cast = 127, invalid_action_sell_not_tavi = 128, invalid_action_sell_invalid_item = 129, invalid_action_sell_not_owned = 130, invalid_action_sell_already_sold = 131, invalid_action_sell_gold_overflow = 132, invalid_action_sell_not_on_spawn = 133, draft_already_picked = 134, draft_no_champion_selected = 135, };
```

Engine error codes; numeric values mirror EngineC/Errors.h.

### fuel_remaining

```cpp
std::uint64_t fuel_remaining()
```

Get the fuel left in the current turn's budget; the first draft turn gets 100x and each champion's first turn gets 2x.

*Example: Stop optional planning when little fuel remains and yield the current turn.*

```cpp
if (bc::fuel_remaining() < 1000) {
    bc::end_turn();
}
```

### get_item_enum

```cpp
constexpr item_type get_item_enum(item_family family, item_stat stat, bool shard = true)
```

Select an item without spelling out its full enum name.

- `family`: Emblem family.
- `stat`: Stat granted by the item.
- `shard`: True selects a shard (default); false selects an emblem.

*Example: Select a completed Greed strength emblem by family and stat. Shards are the default in C++, Python and OCaml; Rust takes an explicit boolean.*

```cpp
auto item = bc::get_item_enum(bc::item_family::greed, bc::item_stat::strength, false);
```

### global_submitted_gems

```cpp
std::uint32_t global_submitted_gems(team side)
```

Get the total gems submitted by a team.

- `side`: Team to count.

### handle_camp_group_t

```cpp
enum class handle_camp_group_t : std::uint32_t { };
```

Strong identity of an engine-defined physical camp group.

### handle_camp_t

```cpp
enum class handle_camp_t : std::uint32_t { };
```

Strong camp identity; convert to an integer only at the host ABI boundary.

### handle_champion_t

```cpp
enum class handle_champion_t : std::uint32_t { };
```

Strong champion identity; convert to an integer only at the host ABI boundary.

### is_draft

```cpp
bool is_draft() noexcept
```

Whether this guest has a draft perspective, without querying the host.

### item

```cpp
using item = item_type;
```

Item-kind alias used by inventory entries.

### item_family

```cpp
enum class item_family : std::int32_t { monster, power, durability, treasure, jungle, home, bruiser, tribute, capture, prospector, hunter, skirmish, greed, collectors };
```

Item family, independent of its stat and shard/emblem tier.

### item_info

```cpp
struct item_info { std::uint32_t cost, combine_count; std::optional<item_type> result; std::int32_t health_points, strength_points, focus_points; std::optional<item_passive> passive; float passive_magnitude; bool purchasable; };
```

Owned item metadata queried from the engine; combinations consume ingredients.

### item_passive

```cpp
enum class item_passive : std::uint32_t { monster = 1, durability, treasure, jungle, home, tribute, capture, prospector, hunter, skirmish, collectors };
```

Optional item passive tags; no passive is represented by an empty optional.

### item_stat

```cpp
enum class item_stat : std::int32_t { strength, focus, health };
```

Stat selected for an item.

### item_type

```cpp
class item_type { public: enum class enum_type : std::uint32_t { monster_shard_of_strength, monster_emblem_of_strength, monster_shard_of_focus, monster_emblem_of_focus, monster_shard_of_health, monster_emblem_of_health, power_shard_of_strength, power_emblem_of_strength, power_shard_of_focus, power_emblem_of_focus, power_shard_of_health, power_emblem_of_health, durability_shard_of_strength, durability_emblem_of_strength, durability_shard_of_focus, durability_emblem_of_focus, durability_shard_of_health, durability_emblem_of_health, treasure_shard_of_strength, treasure_emblem_of_strength, treasure_shard_of_focus, treasure_emblem_of_focus, treasure_shard_of_health, treasure_emblem_of_health, jungle_shard_of_strength, jungle_emblem_of_strength, jungle_shard_of_focus, jungle_emblem_of_focus, jungle_shard_of_health, jungle_emblem_of_health, home_shard_of_strength, home_emblem_of_strength, home_shard_of_focus, home_emblem_of_focus, home_shard_of_health, home_emblem_of_health, bruiser_shard_of_strength, bruiser_emblem_of_strength, bruiser_shard_of_focus, bruiser_emblem_of_focus, bruiser_shard_of_health, bruiser_emblem_of_health, tribute_shard_of_strength, tribute_emblem_of_strength, tribute_shard_of_focus, tribute_emblem_of_focus, tribute_shard_of_health, tribute_emblem_of_health, capture_shard_of_strength, capture_emblem_of_strength, capture_shard_of_focus, capture_emblem_of_focus, capture_shard_of_health, capture_emblem_of_health, prospector_shard_of_strength, prospector_emblem_of_strength, prospector_shard_of_focus, prospector_emblem_of_focus, prospector_shard_of_health, prospector_emblem_of_health, hunter_shard_of_strength, hunter_emblem_of_strength, hunter_shard_of_focus, hunter_emblem_of_focus, hunter_shard_of_health, hunter_emblem_of_health, skirmish_shard_of_strength, skirmish_emblem_of_strength, skirmish_shard_of_focus, skirmish_emblem_of_focus, skirmish_shard_of_health, skirmish_emblem_of_health, greed_shard_of_strength, greed_emblem_of_strength, greed_shard_of_focus, greed_emblem_of_focus, greed_shard_of_health, greed_emblem_of_health, collectors_shard_of_strength, collectors_emblem_of_strength, collectors_shard_of_focus, collectors_emblem_of_focus, collectors_shard_of_health, collectors_emblem_of_health, count }; static const item_type monster_shard_of_strength; static const item_type monster_emblem_of_strength; static const item_type monster_shard_of_focus; static const item_type monster_emblem_of_focus; static const item_type monster_shard_of_health; static const item_type monster_emblem_of_health; static const item_type power_shard_of_strength; static const item_type power_emblem_of_strength; static const item_type power_shard_of_focus; static const item_type power_emblem_of_focus; static const item_type power_shard_of_health; static const item_type power_emblem_of_health; static const item_type durability_shard_of_strength; static const item_type durability_emblem_of_strength; static const item_type durability_shard_of_focus; static const item_type durability_emblem_of_focus; static const item_type durability_shard_of_health; static const item_type durability_emblem_of_health; static const item_type treasure_shard_of_strength; static const item_type treasure_emblem_of_strength; static const item_type treasure_shard_of_focus; static const item_type treasure_emblem_of_focus; static const item_type treasure_shard_of_health; static const item_type treasure_emblem_of_health; static const item_type jungle_shard_of_strength; static const item_type jungle_emblem_of_strength; static const item_type jungle_shard_of_focus; static const item_type jungle_emblem_of_focus; static const item_type jungle_shard_of_health; static const item_type jungle_emblem_of_health; static const item_type home_shard_of_strength; static const item_type home_emblem_of_strength; static const item_type home_shard_of_focus; static const item_type home_emblem_of_focus; static const item_type home_shard_of_health; static const item_type home_emblem_of_health; static const item_type bruiser_shard_of_strength; static const item_type bruiser_emblem_of_strength; static const item_type bruiser_shard_of_focus; static const item_type bruiser_emblem_of_focus; static const item_type bruiser_shard_of_health; static const item_type bruiser_emblem_of_health; static const item_type tribute_shard_of_strength; static const item_type tribute_emblem_of_strength; static const item_type tribute_shard_of_focus; static const item_type tribute_emblem_of_focus; static const item_type tribute_shard_of_health; static const item_type tribute_emblem_of_health; static const item_type capture_shard_of_strength; static const item_type capture_emblem_of_strength; static const item_type capture_shard_of_focus; static const item_type capture_emblem_of_focus; static const item_type capture_shard_of_health; static const item_type capture_emblem_of_health; static const item_type prospector_shard_of_strength; static const item_type prospector_emblem_of_strength; static const item_type prospector_shard_of_focus; static const item_type prospector_emblem_of_focus; static const item_type prospector_shard_of_health; static const item_type prospector_emblem_of_health; static const item_type hunter_shard_of_strength; static const item_type hunter_emblem_of_strength; static const item_type hunter_shard_of_focus; static const item_type hunter_emblem_of_focus; static const item_type hunter_shard_of_health; static const item_type hunter_emblem_of_health; static const item_type skirmish_shard_of_strength; static const item_type skirmish_emblem_of_strength; static const item_type skirmish_shard_of_focus; static const item_type skirmish_emblem_of_focus; static const item_type skirmish_shard_of_health; static const item_type skirmish_emblem_of_health; static const item_type greed_shard_of_strength; static const item_type greed_emblem_of_strength; static const item_type greed_shard_of_focus; static const item_type greed_emblem_of_focus; static const item_type greed_shard_of_health; static const item_type greed_emblem_of_health; static const item_type collectors_shard_of_strength; static const item_type collectors_emblem_of_strength; static const item_type collectors_shard_of_focus; static const item_type collectors_emblem_of_focus; static const item_type collectors_shard_of_health; static const item_type collectors_emblem_of_health; static const item_type count; };
```

Purchasable item types.

### opponent

```cpp
constexpr team opponent(team side) noexcept
```

Get the other team.

- `side`: Team to flip.

### passive_type

```cpp
enum class passive_type : std::uint8_t { none, bonus_gold, remote_shop, gem_focus, splash_attack, health_strength, reset_cooldowns_on_kill, retaliation, stun_immunity, missing_health_damage = 10, };
```

Champion passive effect tags from the engine definition.

### resign

```cpp
void resign()
```

Resign the game. A successful resign never returns, so buffered output is flushed first.

### round_number

```cpp
std::uint32_t round_number()
```

Get the current round number.

### self

```cpp
cambc::champion& self()
```

Return this guest's authenticated champion; throws std::bad_optional_access during drafting.

### shared_memory_buffer

```cpp
class shared_memory_buffer { };
```

Bounds-checked access to this team's shared bytes; reads and writes always reach the host.

### symmetry

```cpp
enum class symmetry : std::int32_t { horizontal, vertical, rotational180 };
```

Map symmetry used to reflect tiles.

### team

```cpp
enum class team { ally, enemy };
```

Teams relative to the bot.

### teleport

```cpp
class teleport { };
```

A visible teleport reservation snapshot, including the observer's own channel.

### to_string

```cpp
std::string to_string(ability_kind value)
```

Get the enumerator name.

- `value`: Value to format.

### to_string

```cpp
std::string to_string(buff_types value)
```

Get the enumerator name.

- `value`: Value to format.

### to_string

```cpp
std::string to_string(camp_type value)
```

Get the enumerator name.

- `value`: Value to format.

### to_string

```cpp
std::string to_string(champion_draft value)
```

Get the enumerator name.

- `value`: Value to format.

### to_string

```cpp
std::string to_string(champion_type value)
```

Get the enumerator name.

- `value`: Value to format.

### to_string

```cpp
std::string to_string(consumable_type value)
```

Get the enumerator name.

- `value`: Value to format.

### to_string

```cpp
std::string to_string(error_code value)
```

Get the enumerator name.

- `value`: Value to format.

### to_string

```cpp
std::string to_string(item_passive value)
```

Get the enumerator name.

- `value`: Value to format.

### to_string

```cpp
std::string to_string(item_type value)
```

Get the enumerator name.

- `value`: Value to format.

### to_string

```cpp
std::string to_string(passive_type value)
```

Get the enumerator name.

- `value`: Value to format.

### to_string

```cpp
std::string to_string(symmetry value)
```

Get the enumerator name.

- `value`: Value to format.

### to_string

```cpp
std::string to_string(team value)
```

Get the enumerator name.

- `value`: Value to format.

### to_string

```cpp
std::string to_string(vec2 value)
```

Format as "(x, y)".

- `value`: Value to format.

### type_tag_t

```cpp
template <class T> struct type_tag_t { using type = T; };
```

Select a typed ability or buff payload without constructing a payload value.

### uninitialized_t

```cpp
struct uninitialized_t { };
```

Tag for constructing a bitboard without initialising its contents.

### unit

```cpp
class unit { };
```

Common live combat queries for champions and camps.

### vec2

```cpp
class vec2 { public: std::int32_t x, y; static const vec2 north, north_east, east, south_east, south, south_west, west, north_west; };
```

Integer tile position or displacement.

### ward

```cpp
class ward { };
```

Immutable snapshot of a visible ward.

<a id="cambc-ability"></a>

## cambc::ability

### ability

```cpp
explicit ability(const detail::ability_props& props, std::uint32_t slot)
```

Copy immutable design metadata.

### can_target_allies

```cpp
bool can_target_allies() const
```

Check the allowed-target mask for allied champions.

### can_target_camps

```cpp
bool can_target_camps() const
```

Check target categories, not cast readiness, range or visibility; allies/enemies exclude self.

### can_target_enemies

```cpp
bool can_target_enemies() const
```

Check the allowed-target mask for enemy champions.

### can_target_ground

```cpp
bool can_target_ground() const
```

Check the allowed-target mask for a tile destination.

### can_target_self

```cpp
bool can_target_self() const
```

Check the allowed-target mask for the casting champion.

### cooldown

```cpp
std::int32_t cooldown() const
```

Get the remaining owner turn-end ticks; zero means ready.

### damage_amount

```cpp
float damage_amount() const
```

Query Focus-scaled damage, including dash landing damage and caster outgoing bonuses such as Heart of Ruin's passive. Excludes target-dependent modifiers, shields and health limits.

### damage_amount

```cpp
float damage_amount(const champion& target) const
```

Predict health lost after mitigation and shields, capped at current health. Target must be visible.

- `target`: Visible champion that would be hit.

### get

```cpp
template <class T> T get() const
```

Extract a payload; throws std::bad_optional_access if absent, std::bad_variant_access for a different kind.

### heal_amount

```cpp
float heal_amount() const
```

Query heal before absorption/health limits; includes caster items and passives.

### heal_amount

```cpp
float heal_amount(const champion& target) const
```

Cap healing at the visible target's missing health. Does not cast or consume resources.

- `target`: Visible champion that would be healed.

### info

```cpp
const ability_info& info(ability_kind kind) const
```

Get selected metadata; unavailable or mismatched payloads throw.

- `kind`: Ability kind the slot must hold.

### info

```cpp
const std::optional<ability_info>& info() const
```

Get constructor-cached ability properties; empty for an unused slot. Rethrow the cached visibility error if the owner could not be inspected at construction.

### is

```cpp
bool is(ability_kind kind) const noexcept
```

Check the kind of constructor-cached ability metadata without querying the host.

- `kind`: Ability kind to test for.

### is

```cpp
template <class T> bool is(type_tag_t<T>) const noexcept
```

Check whether constructor-cached metadata holds the selected payload type.

### is_aoe_damage

```cpp
bool is_aoe_damage() const noexcept
```

Check whether this is an area-damage ability.

### is_attack_reset

```cpp
bool is_attack_reset() const noexcept
```

Check whether this is an attack-reset ability.

### is_cc

```cpp
bool is_cc() const noexcept
```

Check whether this is a crowd-control ability.

### is_damage

```cpp
bool is_damage() const noexcept
```

Check whether this is a damage ability.

### is_dash

```cpp
bool is_dash() const noexcept
```

Check whether this is a dash ability.

### is_heal

```cpp
bool is_heal() const noexcept
```

Check whether this is a healing ability.

### is_on_cooldown

```cpp
bool is_on_cooldown() const
```

Query whether the live ability has a positive remaining cooldown.

### is_ready

```cpp
bool is_ready() const
```

Check whether this ability is ready to cast.

### is_shield

```cpp
bool is_shield() const noexcept
```

Check whether this is a shield ability.

### mask_into

```cpp
void mask_into(bitboard& out) const
```

Like `valid_tiles`, but writes into `out` instead of returning a new board.

- `out`: Destination; its previous contents are overwritten.

### shield_amount

```cpp
float shield_amount() const
```

Query shield before absorption/health limits; includes caster items and passives.

### shield_amount

```cpp
float shield_amount(const champion& target) const
```

Query full shield strength for a visible target. Does not cast or consume resources.

- `target`: Visible champion that would be shielded.

### slot

```cpp
std::uint32_t slot() const noexcept
```

Return this ability's fixed champion slot index.

### use

```cpp
bool use() const
```

Cast without a target or destination. Returns false for a newly revealed hidden obstruction; known invalid destinations throw.

### use

```cpp
bool use(const camp& target) const
```

Cast on a camp; the cast lands on the target's tile. Returns false for a newly revealed hidden obstruction; known invalid destinations throw.

- `target`: Camp to cast on.

### use

```cpp
bool use(const champion& target) const
```

Cast on a champion; unit casts land on the target's tile. Returns false for a newly revealed hidden obstruction; known invalid destinations throw.

- `target`: Champion to cast on.

### use

```cpp
bool use(vec2 destination) const
```

Cast at a ground tile. Returns false for a newly revealed hidden obstruction; known invalid destinations throw.

- `destination`: Ground tile to cast at.

### valid_targets

```cpp
ability_target_mask valid_targets() const
```

Get the target-category flags of the owner's immutable ability design.

### valid_tiles

```cpp
bitboard valid_tiles() const
```

Casting range only; does not filter visibility, occupancy or target categories. Throws for range-less or unused slots, hidden owners, and design-only abilities.

<a id="cambc-ability-aoe-damage"></a>

## cambc::ability_aoe_damage

### operator==

```cpp
friend bool operator==(const ability_aoe_damage&, const ability_aoe_damage&) = default
```

Compare every field.

<a id="cambc-ability-attack-reset"></a>

## cambc::ability_attack_reset

### operator==

```cpp
friend bool operator==(const ability_attack_reset&, const ability_attack_reset&) = default
```

Compare every field.

<a id="cambc-ability-cc"></a>

## cambc::ability_cc

### operator==

```cpp
friend bool operator==(const ability_cc&, const ability_cc&) = default
```

Compare every field.

<a id="cambc-ability-damage"></a>

## cambc::ability_damage

### operator==

```cpp
friend bool operator==(const ability_damage&, const ability_damage&) = default
```

Compare every field.

<a id="cambc-ability-dash"></a>

## cambc::ability_dash

### operator==

```cpp
friend bool operator==(const ability_dash&, const ability_dash&) = default
```

Compare every field.

<a id="cambc-ability-heal"></a>

## cambc::ability_heal

### operator==

```cpp
friend bool operator==(const ability_heal&, const ability_heal&) = default
```

Compare every field.

<a id="cambc-ability-properties"></a>

## cambc::ability_properties

### operator==

```cpp
friend bool operator==(const ability_properties&, const ability_properties&) = default
```

Compare every field.

<a id="cambc-ability-shield"></a>

## cambc::ability_shield

### operator==

```cpp
friend bool operator==(const ability_shield&, const ability_shield&) = default
```

Compare every field.

<a id="cambc-ability-target-mask"></a>

## cambc::ability_target_mask

### ability_target_mask

```cpp
constexpr ability_target_mask() noexcept = default
```

Construct a mask with no target categories.

### all

```cpp
static constexpr ability_target_mask all() noexcept
```

Construct a mask with every known flag set.

### begin

```cpp
constexpr iterator begin() const noexcept
```

### bits

```cpp
constexpr std::uint32_t bits() const noexcept
```

Return the underlying engine bit pattern, including unknown flags.

### contains

```cpp
constexpr bool contains(ability_target_mask flags) const noexcept
```

Check that all selected bits are present; an empty mask is always contained.

- `flags`: Flags to test.

### empty

```cpp
static constexpr ability_target_mask empty() noexcept
```

Construct an empty mask.

### end

```cpp
constexpr iterator end() const noexcept
```

### from_bits

```cpp
static constexpr std::optional<ability_target_mask> from_bits(std::uint32_t bits) noexcept
```

Decode raw engine bits, or return nullopt if any bit is not a known flag.

- `bits`: Raw flag bits.

### from_bits_retain

```cpp
static constexpr ability_target_mask from_bits_retain(std::uint32_t bits) noexcept
```

Decode raw engine bits without discarding unknown future flags.

- `bits`: Raw flag bits, kept as is including unnamed bits.

### from_bits_truncate

```cpp
static constexpr ability_target_mask from_bits_truncate(std::uint32_t bits) noexcept
```

Decode raw engine bits, discarding unknown flags.

- `bits`: Raw flag bits; unnamed bits are dropped.

### insert

```cpp
constexpr void insert(ability_target_mask flags) noexcept
```

Set selected flags.

- `flags`: Flags to set.

### intersects

```cpp
constexpr bool intersects(ability_target_mask flags) const noexcept
```

Check whether any selected bit is present.

- `flags`: Flags to test.

### is_all

```cpp
constexpr bool is_all() const noexcept
```

Check whether every known flag is set.

### is_empty

```cpp
constexpr bool is_empty() const noexcept
```

Check whether no bits, known or unknown, are set.

### operator-

```cpp
friend constexpr ability_target_mask operator-(ability_target_mask a, ability_target_mask b) noexcept
```

Return the flags in a that are not in b.

### operator-=

```cpp
constexpr ability_target_mask& operator-=(ability_target_mask flags) noexcept
```

Remove selected flags.

### operator&

```cpp
friend constexpr ability_target_mask operator&(ability_target_mask a, ability_target_mask b) noexcept
```

Intersect bitmasks.

### operator&=

```cpp
constexpr ability_target_mask& operator&=(ability_target_mask flags) noexcept
```

Retain only selected flags.

### operator^

```cpp
friend constexpr ability_target_mask operator^(ability_target_mask a, ability_target_mask b) noexcept
```

Toggle selected bits.

### operator^=

```cpp
constexpr ability_target_mask& operator^=(ability_target_mask flags) noexcept
```

Toggle selected flags.

### operator==

```cpp
friend constexpr bool operator==(ability_target_mask a, ability_target_mask b) noexcept
```

Compare every bit, including unknown flags.

### operator|

```cpp
friend constexpr ability_target_mask operator|(ability_target_mask a, ability_target_mask b) noexcept
```

Compose bitmasks without discarding unknown flags.

### operator|=

```cpp
constexpr ability_target_mask& operator|=(ability_target_mask flags) noexcept
```

Insert selected flags.

### operator~

```cpp
friend constexpr ability_target_mask operator~(ability_target_mask value) noexcept
```

Complement known flags; unknown flags are discarded.

### remove

```cpp
constexpr void remove(ability_target_mask flags) noexcept
```

Clear selected flags.

- `flags`: Flags to clear.

### set

```cpp
constexpr void set(ability_target_mask flags, bool value) noexcept
```

Insert selected flags when value is true, otherwise remove them.

- `flags`: Flags to update.
- `value`: `true` to set the flags, `false` to clear them.

### toggle

```cpp
constexpr void toggle(ability_target_mask flags) noexcept
```

Toggle selected flags.

- `flags`: Flags to flip.

<a id="cambc-altar-lock"></a>

## cambc::altar_lock

### altar_lock

```cpp
explicit altar_lock(detail::altar_lock_info value)
```

Copy a visible altar-lock observation; its fields remain a snapshot.

### hits_remaining

```cpp
std::uint32_t hits_remaining() const noexcept
```

Get the remaining hits from the captured altar-lock observation.

### is_ally

```cpp
bool is_ally() const
```

Check whether this altar lock belongs to the observing team.

### is_enemy

```cpp
bool is_enemy() const
```

Check whether this altar lock belongs to the opposing team.

### operator==

```cpp
friend bool operator==(const altar_lock&, const altar_lock&) = default
```

Compare every captured field.

### position

```cpp
vec2 position() const noexcept
```

Get the tile captured in this altar-lock observation.

### team

```cpp
team team() const
```

Get the owning team relative to the authenticated bot.

<a id="cambc-bitboard"></a>

## cambc::bitboard

### bitboard

```cpp
bitboard()
```

Allocate an empty mask.

### bitboard

```cpp
bitboard(bitboard&&) noexcept = default
```

Transfer board storage without querying the host.

### bitboard

```cpp
bitboard(const bitboard& other)
```

Copy the raw buffer, including padding.

### bitboard

```cpp
explicit bitboard(uninitialized_t)
```

Allocate aligned storage without initialising it.

### clear

```cpp
void clear()
```

Clear all storage, including padding bits.

### count

```cpp
std::uint32_t count() const
```

Count set map tiles.

### draw_chebyshev

```cpp
void draw_chebyshev(vec2 center, float radius)
```

Add tiles within a Chebyshev radius.

- `center`: Centre tile.
- `radius`: Chebyshev radius in tiles.

### draw_circle

```cpp
void draw_circle(vec2 center, float radius)
```

Add tiles within a Euclidean radius.

- `center`: Centre tile.
- `radius`: Euclidean radius in tiles.

### export_linear_buffer

```cpp
std::vector<std::uint8_t> export_linear_buffer() const
```

Return a packed row-major copy.

### export_linear_buffer

```cpp
void export_linear_buffer(std::span<std::uint8_t> bytes) const
```

Export to a caller-provided row-major buffer.

- `bytes`: Destination with one byte per tile in row-major order, exactly `linear_buffer_size()` long.

### export_raw_buffer

```cpp
std::vector<std::uint8_t> export_raw_buffer() const
```

Return a copy of raw storage.

### export_raw_buffer

```cpp
void export_raw_buffer(std::span<std::uint8_t> bytes) const
```

Copy raw storage to a caller-provided buffer.

- `bytes`: Destination, exactly `raw_buffer_size()` long.

### fill

```cpp
void fill()
```

Set every in-bounds tile bit; padding is handled by the engine.

### height

```cpp
std::int32_t height() const
```

Get the map height in tiles.

### import_linear_buffer

```cpp
void import_linear_buffer(std::span<const std::uint8_t> bytes)
```

Import a packed row-major buffer.

- `bytes`: One byte per tile in row-major order, exactly `linear_buffer_size()` long; nonzero sets the tile.

### import_raw_buffer

```cpp
void import_raw_buffer(std::span<const std::uint8_t> bytes)
```

Copy an engine-chunked buffer into this object.

- `bytes`: Engine-chunked bytes, exactly `raw_buffer_size()` long.

### is_empty

```cpp
bool is_empty() const
```

Check whether all map tiles are clear.

### is_set

```cpp
bool is_set(vec2 p) const
```

Read a tile; throws if it is outside the map.

- `p`: Tile to query.

### linear_buffer_size

```cpp
static std::size_t linear_buffer_size()
```

Get the size of the packed row-major buffer in bytes.

### operator&

```cpp
friend bitboard operator&(bitboard&& a, const bitboard& b)
```

Tiles set in both masks, reusing a's storage.

### operator&

```cpp
friend bitboard operator&(const bitboard& a, const bitboard& b)
```

Tiles set in both masks.

### operator&=

```cpp
bitboard& operator&=(const bitboard& b)
```

Keep only tiles also set in b.

### operator^

```cpp
friend bitboard operator^(bitboard&& a, const bitboard& b)
```

Tiles set in exactly one mask, reusing a's storage.

### operator^

```cpp
friend bitboard operator^(const bitboard& a, const bitboard& b)
```

Tiles set in exactly one mask.

### operator^=

```cpp
bitboard& operator^=(const bitboard& b)
```

Toggle every tile set in b.

### operator=

```cpp
bitboard& operator=(bitboard&&) noexcept = default
```

Take over another mask's storage.

### operator=

```cpp
bitboard& operator=(const bitboard& other)
```

Copy another mask's tiles.

### operator==

```cpp
friend bool operator==(const bitboard& a, const bitboard& b)
```

Check whether both masks contain the same map tiles.

### operator|

```cpp
friend bitboard operator|(bitboard&& a, const bitboard& b)
```

(bitboard&& a|Tiles set in either mask, reusing a's storage.

### operator|

```cpp
friend bitboard operator|(const bitboard& a, const bitboard& b)
```

(const bitboard& a|Tiles set in either mask.

### operator|=

```cpp
bitboard& operator|=(const bitboard& b)
```

Combine map tiles in place.

### operator~

```cpp
bitboard operator~() const
```

Return the complement of the map tiles.

### positions

```cpp
std::vector<vec2> positions() const
```

Get the positions of all set map tiles.

### positions_into

```cpp
std::uint32_t positions_into(std::span<vec2> out) const
```

Write the positions of set map tiles into `out` and return how many were written.

- `out`: Destination buffer; at most `out.size()` positions are written.

### print

```cpp
void print() const
```

Print the buffer through the engine.

### ptr

```cpp
const std::uint64_t* ptr() const noexcept
```

Access contiguous backing storage; preserve its layout when passing it to the host.

### ptr

```cpp
std::uint64_t* ptr() noexcept
```

Access aligned raw storage for SDK imports.

### raw_buffer_size

```cpp
static std::size_t raw_buffer_size()
```

Get the size of the engine-chunked buffer in bytes.

### reachable_tiles

```cpp
bitboard reachable_tiles(vec2 origin, std::uint16_t distance, bitboard& frontier, bitboard& scratch) const
```

Get reachable tiles using caller-provided working buffers.

- `origin`: Start tile.
- `distance`: Maximum number of 8-directional steps from `origin`.
- `frontier`: Working buffer; its contents are overwritten.
- `scratch`: Working buffer; its contents are overwritten.

### reachable_tiles

```cpp
bitboard reachable_tiles(vec2 origin, std::uint16_t distance) const
```

Get reachable tiles using this board as walls.

- `origin`: Start tile.
- `distance`: Maximum number of 8-directional steps from `origin`.

### reachable_tiles_into

```cpp
void reachable_tiles_into(vec2 origin, std::uint16_t distance, bitboard& frontier, bitboard& scratch, bitboard& out) const
```

Like `reachable_tiles`, but writes into `out` instead of returning a new board.

- `origin`: Start tile.
- `distance`: Maximum number of 8-directional steps from `origin`.
- `frontier`: Working buffer; its contents are overwritten.
- `scratch`: Working buffer; its contents are overwritten.
- `out`: Destination; its previous contents are overwritten.

### reachable_tiles_into

```cpp
void reachable_tiles_into(vec2 origin, std::uint16_t distance, bitboard& out) const
```

Like `reachable_tiles`, but writes into `out` instead of returning a new board.

- `origin`: Start tile.
- `distance`: Maximum number of 8-directional steps from `origin`.
- `out`: Destination; its previous contents are overwritten.

### reflect

```cpp
bitboard reflect(symmetry value) const
```

Return a reflected copy using the requested map symmetry.

- `value`: Map symmetry to apply.

### reflect_horizontal

```cpp
bitboard reflect_horizontal() const
```

Reflect across the map horizontally, reversing tile x coordinates.

### reflect_horizontal_into

```cpp
void reflect_horizontal_into(bitboard& out) const
```

Like `reflect_horizontal`, but writes into `out`.

- `out`: Destination; its previous contents are overwritten.

### reflect_into

```cpp
void reflect_into(symmetry value, bitboard& out) const
```

Like `reflect`, but writes into `out` instead of returning a new board.

- `value`: Map symmetry to apply.
- `out`: Destination; its previous contents are overwritten.

### reflect_vertical

```cpp
bitboard reflect_vertical() const
```

Reflect across the map vertically, reversing tile y coordinates.

### reflect_vertical_into

```cpp
void reflect_vertical_into(bitboard& out) const
```

Like `reflect_vertical`, but writes into `out`.

- `out`: Destination; its previous contents are overwritten.

### rotate_180

```cpp
bitboard rotate_180() const
```

Rotate tiles 180 degrees within the map dimensions.

### rotate_180_into

```cpp
void rotate_180_into(bitboard& out) const
```

Like `rotate_180`, but writes into `out`.

- `out`: Destination; its previous contents are overwritten.

### set

```cpp
void set(vec2 p, bool value = true)
```

Set or clear a tile; throws if it is outside the map.

- `p`: Tile to update.
- `value`: `true` to set the tile, `false` to clear it.

### shadow_cast

```cpp
bitboard shadow_cast(vec2 origin, std::uint16_t distance) const
```

Get visible tiles using this board as opaque walls.

- `origin`: Viewer tile.
- `distance`: Maximum sight radius in tiles.

### shadow_cast_into

```cpp
void shadow_cast_into(vec2 origin, std::uint16_t distance, bitboard& out) const
```

Like `shadow_cast`, but writes into `out` instead of returning a new board.

- `origin`: Viewer tile.
- `distance`: Maximum sight radius in tiles.
- `out`: Destination; its previous contents are overwritten.

### shift_right

```cpp
bitboard shift_right(std::int32_t count) const
```

Shift tiles horizontally; negative counts shift left.

- `count`: Columns to shift; negative values shift left.

### shift_right_into

```cpp
void shift_right_into(std::int32_t count, bitboard& out) const
```

Like `shift_right`, but writes into `out` instead of returning a new board.

- `count`: Columns to shift; negative values shift left.
- `out`: Destination; its previous contents are overwritten.

### shift_up

```cpp
bitboard shift_up(std::int32_t count) const
```

Shift tiles vertically; negative counts shift down.

- `count`: Rows to shift; negative values shift down.

### shift_up_into

```cpp
void shift_up_into(std::int32_t count, bitboard& out) const
```

Like `shift_up`, but writes into `out` instead of returning a new board.

- `count`: Rows to shift; negative values shift down.
- `out`: Destination; its previous contents are overwritten.

### swap

```cpp
void swap(bitboard& other) noexcept
```

Exchange ownership of raw board storage without querying the host.

- `other`: Bitboard to exchange contents with.

### toggle

```cpp
void toggle(vec2 p)
```

Invert a tile; throws if it is outside the map.

- `p`: Tile to flip.

### width

```cpp
std::int32_t width() const
```

Get the map dimensions in tiles.

<a id="cambc-buff-collection"></a>

## cambc::buff_collection

### begin

```cpp
const_iterator begin() const
```

Iterate captured buffs without refreshing; the collection must outlive the iterator.

### const_iterator

```cpp
class const_iterator { public: using value_type = buff_t; using difference_type = std::ptrdiff_t; using iterator_category = std::forward_iterator_tag; using iterator_concept = std::forward_iterator_tag; using reference = const buff_t&; using pointer = const buff_t*; };
```

Forward iterator over captured buffs; references remain valid while the collection lives.

### end

```cpp
std::default_sentinel_t end() const noexcept
```

Get the past-the-end iterator for the stored values or owning snapshot.

### get

```cpp
buff_t get(buff_types kind) const
```

Get the requested buff snapshot; absent buffs throw std::out_of_range.

- `kind`: Buff kind to look up.

### get

```cpp
template <class T> T get() const
```

Get the requested buff snapshot; absent buffs throw std::out_of_range.

### has

```cpp
bool has(buff_types kind) const
```

Check the captured collection for this buff kind without querying the host.

- `kind`: Buff kind to test for.

### has

```cpp
template <class T> bool has() const
```

Check the captured collection for the selected buff payload type.

### has_enhanced_attack

```cpp
bool has_enhanced_attack() const
```

Check whether the captured collection has an enhanced-attack buff.

### has_shield

```cpp
bool has_shield() const
```

Check whether the captured collection has a shield buff.

### has_stun

```cpp
bool has_stun() const
```

Check whether the captured collection has a stun buff.

### is_empty

```cpp
bool is_empty() const
```

Check whether the captured collection has no active buffs.

### operator==

```cpp
friend bool operator==(const buff_collection&, const buff_collection&) = default
```

Compare every captured buff.

### size

```cpp
std::size_t size() const
```

Get the number of entries in this container.

<a id="cambc-buff-collection-const-iterator"></a>

## cambc::buff_collection::const_iterator

### const_iterator

```cpp
const_iterator() = default
```

Construct an iterator that compares equal to the end sentinel.

### const_iterator

```cpp
explicit const_iterator(const storage_type& values)
```

Iterate the captured buffs in values.

### difference_type

```cpp
using difference_type = std::ptrdiff_t;
```

Iterator distance type.

### iterator_category

```cpp
using iterator_category = std::forward_iterator_tag;
```

Standard iterator category.

### iterator_concept

```cpp
using iterator_concept = std::forward_iterator_tag;
```

C++20 iterator concept.

### operator->

```cpp
pointer operator->() const
```

Access the current buff.

### operator*

```cpp
reference operator*() const
```

Access the current buff.

### operator++

```cpp
const_iterator operator++(int)
```

Advance to the next captured buff, returning the previous position.

### operator++

```cpp
const_iterator& operator++()
```

Advance to the next captured buff.

### operator==

```cpp
bool operator==(const const_iterator&) const = default
```

Compare iterator positions.

### operator==

```cpp
bool operator==(std::default_sentinel_t) const
```

Check whether every captured buff has been visited.

### pointer

```cpp
using pointer = const buff_t*;
```

Pointer to a captured buff.

### reference

```cpp
using reference = const buff_t&;
```

Reference to a captured buff.

### value_type

```cpp
using value_type = buff_t;
```

Iterated buff snapshot type.

<a id="cambc-buff-enhanced-attack"></a>

## cambc::buff_enhanced_attack

### operator==

```cpp
friend bool operator==(const buff_enhanced_attack&, const buff_enhanced_attack&) = default
```

Compare every field.

<a id="cambc-buff-restrictions"></a>

## cambc::buff_restrictions

### all

```cpp
static constexpr buff_restrictions all() noexcept
```

Construct a mask with every known flag set.

### begin

```cpp
constexpr iterator begin() const noexcept
```

### bits

```cpp
constexpr std::uint8_t bits() const noexcept
```

Return the underlying engine bit pattern, including unknown flags.

### buff_restrictions

```cpp
constexpr buff_restrictions() noexcept = default
```

Construct a mask with no restrictions.

### contains

```cpp
constexpr bool contains(buff_restrictions flags) const noexcept
```

Check that all selected bits are present; an empty mask is always contained.

- `flags`: Flags to test.

### empty

```cpp
static constexpr buff_restrictions empty() noexcept
```

Construct an empty mask.

### end

```cpp
constexpr iterator end() const noexcept
```

### from_bits

```cpp
static constexpr std::optional<buff_restrictions> from_bits(std::uint8_t bits) noexcept
```

Decode raw engine bits, or return nullopt if any bit is not a known flag.

- `bits`: Raw flag bits.

### from_bits_retain

```cpp
static constexpr buff_restrictions from_bits_retain(std::uint8_t bits) noexcept
```

Decode raw engine bits without discarding unknown future flags.

- `bits`: Raw flag bits, kept as is including unnamed bits.

### from_bits_truncate

```cpp
static constexpr buff_restrictions from_bits_truncate(std::uint8_t bits) noexcept
```

Decode raw engine bits, discarding unknown flags.

- `bits`: Raw flag bits; unnamed bits are dropped.

### insert

```cpp
constexpr void insert(buff_restrictions flags) noexcept
```

Set selected flags.

- `flags`: Flags to set.

### intersects

```cpp
constexpr bool intersects(buff_restrictions flags) const noexcept
```

Check whether any selected bit is present.

- `flags`: Flags to test.

### is_all

```cpp
constexpr bool is_all() const noexcept
```

Check whether every known flag is set.

### is_empty

```cpp
constexpr bool is_empty() const noexcept
```

Check whether no bits, known or unknown, are set.

### operator-

```cpp
friend constexpr buff_restrictions operator-(buff_restrictions a, buff_restrictions b) noexcept
```

Return the flags in a that are not in b.

### operator-=

```cpp
constexpr buff_restrictions& operator-=(buff_restrictions flags) noexcept
```

Remove selected flags.

### operator&

```cpp
friend constexpr buff_restrictions operator&(buff_restrictions a, buff_restrictions b) noexcept
```

Intersect bitmasks.

### operator&=

```cpp
constexpr buff_restrictions& operator&=(buff_restrictions flags) noexcept
```

Retain only selected flags.

### operator^

```cpp
friend constexpr buff_restrictions operator^(buff_restrictions a, buff_restrictions b) noexcept
```

Toggle selected bits.

### operator^=

```cpp
constexpr buff_restrictions& operator^=(buff_restrictions flags) noexcept
```

Toggle selected flags.

### operator==

```cpp
friend constexpr bool operator==(buff_restrictions a, buff_restrictions b) noexcept
```

Compare every bit, including unknown flags.

### operator|

```cpp
friend constexpr buff_restrictions operator|(buff_restrictions a, buff_restrictions b) noexcept
```

Compose bitmasks without discarding unknown flags.

### operator|=

```cpp
constexpr buff_restrictions& operator|=(buff_restrictions flags) noexcept
```

Insert selected flags.

### operator~

```cpp
friend constexpr buff_restrictions operator~(buff_restrictions value) noexcept
```

Complement known flags; unknown flags are discarded.

### remove

```cpp
constexpr void remove(buff_restrictions flags) noexcept
```

Clear selected flags.

- `flags`: Flags to clear.

### set

```cpp
constexpr void set(buff_restrictions flags, bool value) noexcept
```

Insert selected flags when value is true, otherwise remove them.

- `flags`: Flags to update.
- `value`: `true` to set the flags, `false` to clear them.

### toggle

```cpp
constexpr void toggle(buff_restrictions flags) noexcept
```

Toggle selected flags.

- `flags`: Flags to flip.

<a id="cambc-buff-shield"></a>

## cambc::buff_shield

### operator==

```cpp
friend bool operator==(const buff_shield&, const buff_shield&) = default
```

Compare every field.

<a id="cambc-buff-stun"></a>

## cambc::buff_stun

### operator==

```cpp
friend bool operator==(const buff_stun&, const buff_stun&) = default
```

Compare every field.

<a id="cambc-camp"></a>

## cambc::camp

### attack_range

```cpp
std::int32_t attack_range() const override
```

Get attack range from this camp's design; melee camps have range 1.

### base_stats

```cpp
camp_stats base_stats() const
```

Get an owning snapshot of the camp's engine-provided design stats.

### camp_group

```cpp
map::camp_group camp_group() const
```

Query this camp's group from the engine on every call; invalid identities throw.

### focus

```cpp
float focus() const override
```

Query current focus for this visible unit.

### health

```cpp
float health() const override
```

Query current health; live state requires a visible runtime identity.

### is_alive

```cpp
bool is_alive() const
```

Query whether this camp is living (awake or asleep); uses the same visibility checks as state().

### is_asleep

```cpp
bool is_asleep() const
```

Query whether this camp is living but dormant; uses the same visibility checks as state().

### is_awake

```cpp
bool is_awake() const
```

Query whether this camp is awake; uses the same visibility checks as state().

### is_dead

```cpp
bool is_dead() const
```

Query whether this camp is dead; uses the same visibility checks as state().

### is_elk

```cpp
bool is_elk() const noexcept
```

Check whether this camp is an elk.

### is_gem_cluster

```cpp
bool is_gem_cluster() const noexcept
```

Check whether this camp is a gem cluster.

### is_gold_cluster

```cpp
bool is_gold_cluster() const noexcept
```

Check whether this camp is a gold cluster.

### is_golem

```cpp
bool is_golem() const noexcept
```

Check whether this camp is a golem.

### is_monolith

```cpp
bool is_monolith() const noexcept
```

Check whether this camp is a monolith.

### is_visible

```cpp
bool is_visible() const override
```

Check whether live state is available; hidden units and design-only views return false.

### is_wolf

```cpp
bool is_wolf() const noexcept
```

Check whether this camp is a wolf.

### kind

```cpp
camp_type kind() const noexcept
```

Get the entity or inventory entry kind.

### max_health

```cpp
float max_health() const override
```

Query current maximum health; live state requires a visible runtime identity.

### operator handle_camp_t

```cpp
operator handle_camp_t() const noexcept
```

Convert to the strong camp identity.

### operator==

```cpp
friend bool operator==(const camp& a, const camp& b) noexcept
```

Compare camp identities.

### position

```cpp
vec2 position() const override
```

Get the tile position; live entity views query current engine state.

### spawn_position

```cpp
vec2 spawn_position() const noexcept
```

Get the camp's original spawn tile, not its current live position.

### state

```cpp
camp_state state() const
```

Query dead, alive (awake), or asleep. The current tile, or last occupied tile when dead, must be in vision; hidden camps throw api_not_in_vision. This is separate from the camp-group state.

### strength

```cpp
float strength() const override
```

Query current strength for this visible unit.

<a id="cambc-camp-state"></a>

## cambc::camp_state

### camp_state

```cpp
constexpr camp_state() noexcept = default
```

Construct the dead state.

### camp_state

```cpp
constexpr camp_state(enum_type state) noexcept
```

Wrap an underlying enum value without changing its identity.

### enum_type

```cpp
enum class enum_type : std::uint32_t { dead = 0, alive = 1, asleep = 2 };
```

Underlying mutually exclusive engine values; alive means awake.

### is_alive

```cpp
constexpr bool is_alive() const noexcept
```

Check whether the captured state is living, including asleep camps.

### is_asleep

```cpp
constexpr bool is_asleep() const noexcept
```

Check whether the captured state is living but dormant.

### is_awake

```cpp
constexpr bool is_awake() const noexcept
```

Check whether the captured state is awake (the alive enum value).

### is_dead

```cpp
constexpr bool is_dead() const noexcept
```

Check whether the captured state is dead.

### operator enum_type

```cpp
constexpr operator enum_type() const noexcept
```

Convert to the underlying engine enum.

### operator T

```cpp
template <class T> requires std::is_integral_v<T> constexpr explicit operator T() const noexcept
```

Explicit integer conversion for host ABI values.

<a id="cambc-champion"></a>

## cambc::champion

### abilities

```cpp
std::array<ability, 2> abilities() const
```

Return a copy of the two champion-bound ability views with immutable cached metadata.

### attack

```cpp
void attack(const altar_lock& target) const
```

Attack an altar lock; requires the authenticated self and host-validated action availability.

- `target`: Visible altar lock within attack range.

### attack

```cpp
void attack(const unit& target) const
```

Attack a champion or camp view; requires the authenticated self and host-validated action availability.

- `target`: Visible champion or camp within attack range.

### attack_range

```cpp
std::int32_t attack_range() const override
```

Get the unit's attack range in tiles; champion state is queried live.

### base_stats

```cpp
champion_stats base_stats() const
```

Get the champion design base stats.

### buy

```cpp
void buy(consumable_type type) const
```

Buy a consumable for self.

- `type`: Consumable to buy.

### buy

```cpp
void buy(item_type type, std::uint32_t count = 1) const
```

Buy items for self.

- `type`: Item to buy.
- `count`: Number of copies to buy.

### can_attack

```cpp
bool can_attack() const
```

Check whether this champion can attack.

*Example: Check the action allowance before spending fuel to choose an attack target.*

```cpp
const auto me = bc::self();
const bool action_available = me.can_attack();
```

### can_buy

```cpp
bool can_buy(consumable_type consumable) const
```

Check whether a consumable can be bought in the current state.

- `consumable`: Consumable to buy.

### can_buy

```cpp
bool can_buy(item_type item, std::uint32_t count = 1) const
```

Check whether an item can be bought in the current state.

- `item`: Item to buy.
- `count`: Number of copies to buy.

### can_cast

```cpp
bool can_cast() const
```

Check whether this champion can cast.

*Example: Check the action allowance before spending fuel to evaluate ready abilities.*

```cpp
const auto me = bc::self();
const bool action_available = me.can_cast();
```

### can_move

```cpp
bool can_move() const
```

Check whether this champion can move.

*Example: Check the action allowance before spending fuel to plan a path.*

```cpp
const auto me = bc::self();
const bool action_available = me.can_move();
```

### can_sell

```cpp
bool can_sell() const
```

Check whether the authenticated self currently has permission to sell.

### cancel_recall

```cpp
void cancel_recall() const
```

Cancel an active recall.

### cancel_submit_gems

```cpp
void cancel_submit_gems() const
```

Cancel an active gem submission.

### champion

```cpp
explicit champion(champion_type type)
```

A design-only champion: immutable properties are available, live queries require vision.

### champion_name

```cpp
champion_type champion_name() const
```

Get the entity or inventory entry kind; live champions read it without vision.

### consumables

```cpp
const enum_map<consumable_type, consumable>& consumables() const noexcept
```

Action wrappers by consumable type; each count is queried live.

### end_turn

```cpp
void end_turn() const
```

Yield the current champion turn.

### focus

```cpp
float focus() const override
```

Query current focus for this visible unit.

### gem_count

```cpp
std::uint32_t gem_count() const
```

Get carried gems.

### gold_count

```cpp
std::uint32_t gold_count() const
```

Get gold; this query requires self.

### has_completed_turn

```cpp
bool has_completed_turn() const
```

Check whether this champion has completed its turn.

### health

```cpp
float health() const override
```

Get current and maximum health.

*Example: Recall when badly injured and safe from interruption.*

```cpp
auto me = bc::self();
if (safe_to_recall && me.health() < me.max_health() * 0.3f) {
    me.recall();
}
```

### is_alive

```cpp
bool is_alive() const
```

Check whether the champion is alive.

### is_ally

```cpp
bool is_ally() const
```

Check whether this champion belongs to the observing team.

### is_enemy

```cpp
bool is_enemy() const
```

Check whether this champion belongs to the opposing team.

### is_recalling

```cpp
bool is_recalling() const
```

Check whether this champion is recalling.

### is_submitting_gems

```cpp
bool is_submitting_gems() const
```

Check whether this champion is submitting gems.

### is_teleporting

```cpp
bool is_teleporting() const
```

Check whether this champion is teleporting.

### is_visible

```cpp
bool is_visible() const override
```

Check whether the champion can be inspected from this perspective.

### item_count

```cpp
enum_map<item_type> item_count() const
```

Get item counts indexed by item type.

### max_health

```cpp
float max_health() const override
```

Query current maximum health; live state requires a visible runtime identity.

*Example: Recall when badly injured and safe from interruption.*

```cpp
auto me = bc::self();
if (safe_to_recall && me.health() < me.max_health() * 0.3f) {
    me.recall();
}
```

### move

```cpp
bool move(vec2 delta) const
```

Attempt to move by a delta from the current position. Returns false for a newly revealed hidden obstruction; known invalid destinations throw.

- `delta`: Displacement from the current position.

*Example: Take a planned step; false means no movement occurred.*

```cpp
auto me = bc::self();
if (me.can_move()) {
    const bool moved = me.move(direction);
}
```

### move_absolute

```cpp
bool move_absolute(vec2 destination) const
```

Attempt to move to an absolute destination tile. Returns false for a newly revealed hidden obstruction; known invalid destinations throw.

- `destination`: Map tile to move to.

*Example: Take a planned step; false means no movement occurred.*

```cpp
auto me = bc::self();
if (me.can_move()) {
    const bool moved = me.move_absolute(destination);
}
```

### move_towards

```cpp
bool move_towards(vec2 target) const
```

Move to the reachable tile on a shortest path to `target`. Always treat the target as free for pathfinding, while avoiding other walls, holes, altars, enemy spawn tiles, visible units and teleport reservations. Returns false when already there, unable to move, no route exists, or a hidden obstruction is revealed. The engine still validates the chosen landing tile: trying to enter a known blocked target throws.

- `target`: Map tile to approach.

*Example: Path towards a target even when its tile is blocked. Stop at the desired range: the engine still rejects landing on a known blocked tile.*

```cpp
auto me = bc::self();
if (me.can_move()) {
    const bool moved = me.move_towards(destination);
}
```

### operator handle_champion_t

```cpp
operator handle_champion_t() const noexcept
```

Access the underlying engine handle.

### operator==

```cpp
friend bool operator==(const champion& a, const champion& b) noexcept
```

Compare champion identities.

### passive

```cpp
passive_type passive() const
```

Get the passive effect tag from the champion's immutable design.

### place_ward

```cpp
bool place_ward(vec2 destination) const
```

Place a ward at a destination tile. Returns false for a newly revealed hidden obstruction; known invalid destinations throw.

- `destination`: Tile to place the ward on.

### position

```cpp
vec2 position() const override
```

Get the tile position; live entity views query current engine state.

### prev_priority

```cpp
std::int32_t prev_priority() const
```

Get the scheduling priority used for the current round.

### priority

```cpp
std::int32_t priority() const
```

Get the scheduling priority for the next round.

### recall

```cpp
void recall() const
```

Start recalling to spawn.

*Example: Recall when badly injured and safe from interruption.*

```cpp
auto me = bc::self();
if (safe_to_recall && me.health() < me.max_health() * 0.3f) {
    me.recall();
}
```

### remaining_channel_time

```cpp
std::int32_t remaining_channel_time() const
```

Query the visible champion's remaining channel rounds; no active channel throws.

### restrictions

```cpp
buff_restrictions restrictions() const
```

Union of active buff restrictions; requires visibility.

### sell

```cpp
void sell(item_type type, std::uint32_t count = 1) const
```

Sell items for self; the engine validates champion and shop restrictions.

- `type`: Item to sell.
- `count`: Number of copies to sell.

### set_priority

```cpp
void set_priority(std::int32_t priority) const
```

Set the scheduling priority for the next round.

- `priority`: New scheduling priority; takes effect from the next round and persists.

### state

```cpp
champion_state state() const
```

Get current state and action availability.

### strength

```cpp
float strength() const override
```

Query current strength for this visible unit.

### submit_gems

```cpp
void submit_gems(vec2 altar) const
```

Start submitting gems at an altar.

- `altar`: Altar tile to tribute at.

### team

```cpp
team team() const
```

Get the owning team relative to the authenticated bot; live champions read it without vision.

### visible_tiles

```cpp
bitboard visible_tiles() const
```

Get tiles visible to this champion.

### visible_tiles_from

```cpp
bitboard visible_tiles_from(vec2 position) const
```

Vision at a hypothetical position, using this champion's design.

- `position`: Hypothetical tile to see from.

### visible_tiles_from_into

```cpp
void visible_tiles_from_into(vec2 position, bitboard& out) const
```

Like `visible_tiles_from`, but writes into `out` instead of returning a new board.

- `position`: Hypothetical tile to see from.
- `out`: Destination; its previous contents are overwritten.

### visible_tiles_into

```cpp
void visible_tiles_into(bitboard& out) const
```

Like `visible_tiles`, but writes into `out` instead of returning a new board.

- `out`: Destination; its previous contents are overwritten.

### ward_cooldown

```cpp
std::int32_t ward_cooldown() const
```

Query the authenticated champion's remaining ward recharge rounds.

### ward_placement_tiles

```cpp
bitboard ward_placement_tiles() const
```

Compute self-only ward placement range from current position and engine settings.

### ward_placement_tiles_into

```cpp
void ward_placement_tiles_into(bitboard& out) const
```

Like `ward_placement_tiles`, but writes into `out` instead of returning a new board.

- `out`: Destination; its previous contents are overwritten.

### ward_positions

```cpp
std::vector<vec2> ward_positions() const
```

Query an owning list of wards placed by the authenticated self champion.

<a id="cambc-champion-state"></a>

## cambc::champion_state

### all

```cpp
static constexpr champion_state all() noexcept
```

Construct a mask with every known flag set.

### begin

```cpp
constexpr iterator begin() const noexcept
```

### bits

```cpp
constexpr std::uint32_t bits() const noexcept
```

Return the underlying engine bit pattern, including unknown flags.

### champion_state

```cpp
constexpr champion_state() noexcept = default
```

Construct a state with no flags set.

### contains

```cpp
constexpr bool contains(champion_state flags) const noexcept
```

Check that all selected bits are present; an empty mask is always contained.

- `flags`: Flags to test.

### empty

```cpp
static constexpr champion_state empty() noexcept
```

Construct an empty mask.

### end

```cpp
constexpr iterator end() const noexcept
```

### from_bits

```cpp
static constexpr std::optional<champion_state> from_bits(std::uint32_t bits) noexcept
```

Decode raw engine bits, or return nullopt if any bit is not a known flag.

- `bits`: Raw flag bits.

### from_bits_retain

```cpp
static constexpr champion_state from_bits_retain(std::uint32_t bits) noexcept
```

Decode raw engine bits without discarding unknown future flags.

- `bits`: Raw flag bits, kept as is including unnamed bits.

### from_bits_truncate

```cpp
static constexpr champion_state from_bits_truncate(std::uint32_t bits) noexcept
```

Decode raw engine bits, discarding unknown flags.

- `bits`: Raw flag bits; unnamed bits are dropped.

### insert

```cpp
constexpr void insert(champion_state flags) noexcept
```

Set selected flags.

- `flags`: Flags to set.

### intersects

```cpp
constexpr bool intersects(champion_state flags) const noexcept
```

Check whether any selected bit is present.

- `flags`: Flags to test.

### is_all

```cpp
constexpr bool is_all() const noexcept
```

Check whether every known flag is set.

### is_dead

```cpp
constexpr bool is_dead() const noexcept
```

Check whether the alive flag is clear.

### is_empty

```cpp
constexpr bool is_empty() const noexcept
```

Check whether no bits, known or unknown, are set.

### operator-

```cpp
friend constexpr champion_state operator-(champion_state a, champion_state b) noexcept
```

Return the flags in a that are not in b.

### operator-=

```cpp
constexpr champion_state& operator-=(champion_state flags) noexcept
```

Remove selected flags.

### operator&

```cpp
friend constexpr champion_state operator&(champion_state a, champion_state b) noexcept
```

Intersect bitmasks.

### operator&=

```cpp
constexpr champion_state& operator&=(champion_state flags) noexcept
```

Retain only selected flags.

### operator^

```cpp
friend constexpr champion_state operator^(champion_state a, champion_state b) noexcept
```

Toggle selected bits.

### operator^=

```cpp
constexpr champion_state& operator^=(champion_state flags) noexcept
```

Toggle selected flags.

### operator==

```cpp
friend constexpr bool operator==(champion_state a, champion_state b) noexcept
```

Compare every bit, including unknown flags.

### operator|

```cpp
friend constexpr champion_state operator|(champion_state a, champion_state b) noexcept
```

Compose bitmasks without discarding unknown flags.

### operator|=

```cpp
constexpr champion_state& operator|=(champion_state flags) noexcept
```

Insert selected flags.

### operator~

```cpp
friend constexpr champion_state operator~(champion_state value) noexcept
```

Complement known flags; unknown flags are discarded.

### remove

```cpp
constexpr void remove(champion_state flags) noexcept
```

Clear selected flags.

- `flags`: Flags to clear.

### set

```cpp
constexpr void set(champion_state flags, bool value) noexcept
```

Insert selected flags when value is true, otherwise remove them.

- `flags`: Flags to update.
- `value`: `true` to set the flags, `false` to clear them.

### toggle

```cpp
constexpr void toggle(champion_state flags) noexcept
```

Toggle selected flags.

- `flags`: Flags to flip.

<a id="cambc-consumable"></a>

## cambc::consumable

### consumable

```cpp
consumable() = default
```

Create an inventory entry; live queries require a champion-bound entry.

### count

```cpp
std::uint32_t count() const
```

Get the number currently owned.

### kind

```cpp
consumable_type kind() const noexcept
```

Get the entity or inventory entry kind.

### use

```cpp
bool use() const
```

Use the entry on a target or tile, if required; the host validates the self-only action. Returns false for a newly revealed hidden obstruction; known invalid destinations throw.

### use

```cpp
bool use(vec2 destination) const
```

Use the entry on a target or tile, if required; the host validates the self-only action. Returns false for a newly revealed hidden obstruction; known invalid destinations throw.

- `destination`: Tile to use the consumable at.

<a id="cambc-consumable-info"></a>

## cambc::consumable_info

### operator==

```cpp
friend bool operator==(const consumable_info&, const consumable_info&) = default
```

Compare every field.

<a id="cambc-consumable-type"></a>

## cambc::consumable_type

### carry_limit

```cpp
std::uint32_t carry_limit() const
```

Get the maximum carried inventory count.

### consumable_type

```cpp
constexpr consumable_type() noexcept = default
```

Construct the first enum value.

### consumable_type

```cpp
constexpr consumable_type(enum_type value) noexcept
```

Wrap an underlying enum value without changing its identity.

### consumable_type

```cpp
explicit constexpr consumable_type(std::uint32_t value) noexcept
```

Explicitly decode an ABI integer; metadata queries reject invalid values.

### cost

```cpp
std::uint32_t cost() const
```

Get the purchase cost in gold.

### enum_type

```cpp
enum class enum_type : std::uint32_t { tp_crystal, altar_lock, count };
```

Underlying engine enum; wrapper values convert to it implicitly.

### info

```cpp
consumable_info info() const
```

Get an owning metadata value; invalid kinds and host failures throw.

### operator enum_type

```cpp
constexpr operator enum_type() const noexcept
```

Preserve compatibility with functions expecting the underlying enum.

### operator T

```cpp
template <class T> requires std::is_integral_v<T> constexpr explicit operator T() const noexcept
```

Explicit integer conversion for indexing and host ABI calls.

<a id="cambc-debug"></a>

## cambc::debug

### draw_dot

```cpp
void draw_dot(vec2 position, std::uint32_t rgb)
```

Emit a debug dot on a tile using a packed 0xRRGGBB colour.

- `position`: Tile to mark.
- `rgb`: Packed `0xRRGGBB` colour.

*Example: Mark a decision in your replay debug overlay to understand the bot's route or target.*

```cpp
bc::debug::draw_dot(position, rgb);
```

### draw_line

```cpp
void draw_line(vec2 from, vec2 to, std::uint32_t rgb)
```

Emit a debug line between tiles using a packed 0xRRGGBB colour.

- `from`: Start tile.
- `to`: End tile.
- `rgb`: Packed `0xRRGGBB` colour.

*Example: Mark a decision in your replay debug overlay to understand the bot's route or target.*

```cpp
bc::debug::draw_line(from, to, rgb);
```

<a id="cambc-distance-field"></a>

## cambc::distance_field

### compute

```cpp
void compute(const bitboard& walls, const bitboard& roots, bitboard& visited, std::uint16_t max_distance = unreachable)
```

Compute distances from roots, reusing the visited buffer.

- `walls`: Impassable tiles.
- `roots`: Tiles at distance zero.
- `visited`: Receives the tiles the search reached.
- `max_distance`: Tiles farther than this are left unreached.

*Example: Find a step towards the goal tiles. The result is a direction for move.*

```cpp
bc::distance_field field;
bc::bitboard visited;
field.compute(blocked, goals, visited);
auto direction = field.next_move_from(bc::self().position());
```

### compute_to

```cpp
void compute_to(const bitboard& walls, const bitboard& roots, const bitboard& destinations, bitboard& visited, std::uint16_t max_distance = unreachable)
```

Compute distances until destinations are reached or the search is exhausted.

- `walls`: Impassable tiles.
- `roots`: Tiles at distance zero.
- `destinations`: The search stops once these tiles are reached.
- `visited`: Receives the tiles the search reached.
- `max_distance`: Tiles farther than this are left unreached.

### compute_to_with_expansion_count

```cpp
std::uint16_t compute_to_with_expansion_count(const bitboard& walls, const bitboard& roots, const bitboard& destinations, bitboard& visited, std::uint16_t max_distance = unreachable)
```

Compute towards destinations and return the number of expansion steps.

- `walls`: Impassable tiles.
- `roots`: Tiles at distance zero.
- `destinations`: The search stops once these tiles are reached.
- `visited`: Receives the tiles the search reached.
- `max_distance`: Tiles farther than this are left unreached.

### compute_with_expansion_count

```cpp
std::uint16_t compute_with_expansion_count(const bitboard& walls, const bitboard& roots, bitboard& visited, std::uint16_t max_distance = unreachable)
```

Compute distances and return the number of expansion steps.

- `walls`: Impassable tiles.
- `roots`: Tiles at distance zero.
- `visited`: Receives the tiles the search reached.
- `max_distance`: Tiles farther than this are left unreached.

### copy_from

```cpp
void copy_from(const distance_field& source, const bitboard& mask)
```

Copy only tiles selected by mask, preserving every unselected value in this field. Mask padding is ignored. Reuses this field's storage; self-copy is a no-op.

- `source`: Field to copy from.
- `mask`: Tiles to copy.

*Example: Update selected tiles while preserving the rest of an existing distance field.*

```cpp
destination.copy_from(source, mask);
```

### copy_from

```cpp
void copy_from(const distance_field& source)
```

Copy all distances from source into this field, reusing its storage. Self-copy is a no-op.

- `source`: Field to copy from.

*Example: Replace an existing distance field while reusing its storage.*

```cpp
destination.copy_from(source);
```

### distance_field

```cpp
distance_field()
```

Allocate a distance buffer that reads as zero until written.

### distance_field

```cpp
distance_field(const distance_field& other)
```

Copy another field's distances.

### distance_field

```cpp
distance_field(distance_field&&) noexcept = default
```

Take over another field's storage.

### export_linear_buffer

```cpp
std::vector<std::uint16_t> export_linear_buffer() const
```

Return a row-major copy of the distances.

### export_linear_buffer

```cpp
void export_linear_buffer(std::span<std::uint16_t> values) const
```

Export to a caller-provided row-major buffer.

- `values`: Destination with one distance per tile in row-major order.

### export_raw_buffer

```cpp
std::vector<std::uint8_t> export_raw_buffer() const
```

Return a copy of raw storage.

### export_raw_buffer

```cpp
void export_raw_buffer(std::span<std::uint8_t> bytes) const
```

Copy raw storage to a caller-provided buffer.

- `bytes`: Destination, exactly `raw_buffer_size()` long.

### get

```cpp
std::uint16_t get(vec2 p) const
```

Read a tile distance; throws if it is outside the map.

- `p`: Tile to query.

### height

```cpp
std::int32_t height() const
```

Get the map height in tiles.

### import_linear_buffer

```cpp
void import_linear_buffer(std::span<const std::uint16_t> values)
```

Import a packed row-major buffer.

- `values`: One distance per tile in row-major order.

### import_raw_buffer

```cpp
void import_raw_buffer(std::span<const std::uint8_t> bytes)
```

Copy an engine-chunked buffer into this object.

- `bytes`: Engine-chunked bytes, exactly `raw_buffer_size()` long.

### linear_buffer_size

```cpp
static std::size_t linear_buffer_size()
```

Get the size of the packed row-major buffer in bytes.

### next_move_from

```cpp
std::optional<vec2> next_move_from(vec2 from) const
```

First optimal step from `from` towards a root, as a direction delta in compass order from north. Returns nullopt at a root or unreached tile; throws if `from` is outside the map.

- `from`: Tile to step from.

*Example: Find a step towards the goal tiles. The result is a direction for move.*

```cpp
bc::distance_field field;
bc::bitboard visited;
field.compute(blocked, goals, visited);
auto direction = field.next_move_from(bc::self().position());
```

### next_moves_from

```cpp
std::vector<vec2> next_moves_from(vec2 from) const
```

Every optimal step from `from` towards a root, as direction deltas in compass order from north.

- `from`: Tile to step from.

### operator=

```cpp
distance_field& operator=(const distance_field& other)
```

Copy another field's distances.

### operator=

```cpp
distance_field& operator=(distance_field&&) noexcept = default
```

Take over another field's storage.

### print

```cpp
void print() const
```

Print the buffer through the engine.

### ptr

```cpp
const std::uint16_t* ptr() const noexcept
```

Access contiguous backing storage; preserve its layout when passing it to the host.

### ptr

```cpp
std::uint16_t* ptr() noexcept
```

Access raw distance storage for SDK imports.

### raw_buffer_size

```cpp
static std::size_t raw_buffer_size()
```

Get the size of the engine-chunked buffer in bytes.

### set

```cpp
void set(vec2 p, std::uint16_t value)
```

Write a tile distance; throws if it is outside the map.

- `p`: Tile to update.
- `value`: Distance to store.

### width

```cpp
std::int32_t width() const
```

Get the map dimensions in tiles.

<a id="cambc-draft"></a>

## cambc::draft

### current_draft

```cpp
std::vector<champion_draft> current_draft(team side)
```

Get an owning list of completed draft picks, recomputed each call.

- `side`: Team whose picks to return.

*Example: Choose your team's roster during the draft phase.*

```cpp
auto result = bc::draft::current_draft(side);
```

### pick

```cpp
void pick(champion_draft pick)
```

Submit a champion pick for the current draft round.

- `pick`: Champion to pick.

*Example: Choose your team's roster during the draft phase.*

```cpp
bc::draft::pick(pick);
```

### team_size

```cpp
std::uint32_t team_size()
```

Query the number of champions per team; gameplay perspectives propagate engine errors.

*Example: Choose your team's roster during the draft phase.*

```cpp
auto result = bc::draft::team_size();
```

<a id="cambc-draft-memory-buffer"></a>

## cambc::draft_memory_buffer

### begin

```cpp
auto begin() const
```

Iterate over read-only captured bytes without querying the host.

### data

```cpp
const std::byte* data() const
```

Borrow bytes captured at startup; assignment does not change this snapshot.

### draft_memory_buffer

```cpp
draft_memory_buffer()
```

Load the current draft bytes into owning, read-only storage.

### draft_memory_buffer

```cpp
draft_memory_buffer(const draft_memory_buffer&) = default
```

Copy the captured bytes without querying or submitting to the engine.

### end

```cpp
auto end() const
```

Get the end of the read-only captured bytes.

### is_empty

```cpp
bool is_empty() const
```

Check whether the captured buffer is empty.

### operator[]

```cpp
const std::byte& operator[](std::size_t offset) const
```

Read one startup-snapshot byte; an out-of-range offset throws std::out_of_range.

### operator=

```cpp
draft_memory_buffer& operator=(const draft_memory_buffer& other)
```

Submit another buffer's captured bytes, including self-assignment.

### operator=

```cpp
draft_memory_buffer& operator=(std::initializer_list<std::byte> bytes)
```

Submit byte initialiser lists; an empty list submits no data.

### operator=

```cpp
draft_memory_buffer& operator=(std::span<const std::byte> bytes)
```

Submit bytes immediately; errors throw and leave captured bytes unchanged. Oversized input is truncated to capacity; shorter input leaves the remaining engine bytes unchanged.

### operator=

```cpp
template <std::ranges::contiguous_range Range> requires (std::ranges::sized_range<Range> && std::is_trivially_copyable_v<std::ranges::range_value_t<Range>>) draft_memory_buffer& operator=(Range&& values)
```

Submit contiguous arrays, vectors or spans of trivially copyable values using native layout.

### size

```cpp
std::size_t size() const
```

Get the captured byte count without querying the host.

<a id="cambc-enum-map"></a>

## cambc::enum_map

### begin

```cpp
auto begin() const noexcept
```

Get a const iterator to the first enum-indexed value.

### begin

```cpp
auto begin() noexcept
```

Get an iterator to the first enum-indexed value.

### end

```cpp
auto end() const noexcept
```

Get the const past-the-end iterator for enum-indexed values.

### end

```cpp
auto end() noexcept
```

Get the past-the-end iterator for enum-indexed values.

### operator[]

```cpp
const Value& operator[](T key) const
```

Access the value for key; throws std::out_of_range for an invalid key.

### operator[]

```cpp
Value& operator[](T key)
```

Access the value for key; throws std::out_of_range for an invalid key.

### operator==

```cpp
friend bool operator==(const enum_map&, const enum_map&) = default
```

Compare every value.

### ptr

```cpp
const Value* ptr() const noexcept
```

Access contiguous backing storage; preserve its layout when passing it to the host.

### ptr

```cpp
Value* ptr() noexcept
```

Access contiguous backing storage; preserve its layout when passing it to the host.

### size

```cpp
constexpr std::size_t size() const noexcept
```

Get the number of entries in this container.

<a id="cambc-error"></a>

## cambc::error

### code

```cpp
error_code code() const noexcept
```

Get the engine error code.

### error

```cpp
error(error_code code, std::string message)
```

Construct an error with an explicit code and message.

### error

```cpp
explicit error(error_code code)
```

Construct an engine error with its code and diagnostic message.

### error

```cpp
explicit error(std::int32_t code)
```

Capture the engine diagnostic before another SDK call changes it.

### message

```cpp
const std::string& message() const noexcept
```

Get the engine diagnostic captured when this error was created.

<a id="cambc-item-info"></a>

## cambc::item_info

### operator==

```cpp
friend bool operator==(const item_info&, const item_info&) = default
```

Compare every field.

<a id="cambc-item-type"></a>

## cambc::item_type

### combine_count

```cpp
std::uint32_t combine_count() const
```

Get the ingredient count needed to create the result item.

### cost

```cpp
std::uint32_t cost() const
```

Get the full value in gold: the purchase price, refunded in full when sold.

### enum_type

```cpp
enum class enum_type : std::uint32_t { monster_shard_of_strength, monster_emblem_of_strength, monster_shard_of_focus, monster_emblem_of_focus, monster_shard_of_health, monster_emblem_of_health, power_shard_of_strength, power_emblem_of_strength, power_shard_of_focus, power_emblem_of_focus, power_shard_of_health, power_emblem_of_health, durability_shard_of_strength, durability_emblem_of_strength, durability_shard_of_focus, durability_emblem_of_focus, durability_shard_of_health, durability_emblem_of_health, treasure_shard_of_strength, treasure_emblem_of_strength, treasure_shard_of_focus, treasure_emblem_of_focus, treasure_shard_of_health, treasure_emblem_of_health, jungle_shard_of_strength, jungle_emblem_of_strength, jungle_shard_of_focus, jungle_emblem_of_focus, jungle_shard_of_health, jungle_emblem_of_health, home_shard_of_strength, home_emblem_of_strength, home_shard_of_focus, home_emblem_of_focus, home_shard_of_health, home_emblem_of_health, bruiser_shard_of_strength, bruiser_emblem_of_strength, bruiser_shard_of_focus, bruiser_emblem_of_focus, bruiser_shard_of_health, bruiser_emblem_of_health, tribute_shard_of_strength, tribute_emblem_of_strength, tribute_shard_of_focus, tribute_emblem_of_focus, tribute_shard_of_health, tribute_emblem_of_health, capture_shard_of_strength, capture_emblem_of_strength, capture_shard_of_focus, capture_emblem_of_focus, capture_shard_of_health, capture_emblem_of_health, prospector_shard_of_strength, prospector_emblem_of_strength, prospector_shard_of_focus, prospector_emblem_of_focus, prospector_shard_of_health, prospector_emblem_of_health, hunter_shard_of_strength, hunter_emblem_of_strength, hunter_shard_of_focus, hunter_emblem_of_focus, hunter_shard_of_health, hunter_emblem_of_health, skirmish_shard_of_strength, skirmish_emblem_of_strength, skirmish_shard_of_focus, skirmish_emblem_of_focus, skirmish_shard_of_health, skirmish_emblem_of_health, greed_shard_of_strength, greed_emblem_of_strength, greed_shard_of_focus, greed_emblem_of_focus, greed_shard_of_health, greed_emblem_of_health, collectors_shard_of_strength, collectors_emblem_of_strength, collectors_shard_of_focus, collectors_emblem_of_focus, collectors_shard_of_health, collectors_emblem_of_health, count };
```

Underlying engine enum; wrapper values convert to it implicitly.

### focus_points

```cpp
std::int32_t focus_points() const
```

Get the focus bonus.

### health_points

```cpp
std::int32_t health_points() const
```

Get the health bonus.

### info

```cpp
item_info info() const
```

Get an owning metadata value; invalid kinds and host failures throw.

### is_purchasable

```cpp
bool is_purchasable() const
```

Whether the item can be bought directly; emblems must be combined.

### item_type

```cpp
constexpr item_type() noexcept = default
```

Construct the first enum value.

### item_type

```cpp
constexpr item_type(enum_type value) noexcept
```

Wrap an underlying enum value without changing its identity.

### item_type

```cpp
explicit constexpr item_type(std::uint32_t value) noexcept
```

Explicitly decode an ABI integer; metadata queries reject invalid values.

### operator enum_type

```cpp
constexpr operator enum_type() const noexcept
```

Preserve compatibility with functions expecting the underlying enum.

### operator T

```cpp
template <class T> requires std::is_integral_v<T> constexpr explicit operator T() const noexcept
```

Explicit integer conversion for indexing and host ABI calls.

### passive

```cpp
std::optional<item_passive> passive() const
```

Get the optional passive effect.

### passive_magnitude

```cpp
float passive_magnitude() const
```

Get the passive magnitude.

### result

```cpp
std::optional<item_type> result() const
```

Get the combination result, if this item can be combined.

### strength_points

```cpp
std::int32_t strength_points() const
```

Get the strength bonus.

<a id="cambc-map"></a>

## cambc::map

### altars

```cpp
const bitboard& altars()
```

Get the immutable altar mask; the reference lasts for the bot lifetime.

*Example: Build a terrain-only walking mask. Also exclude occupied tiles and the enemy spawn when selecting a legal step.*

```cpp
auto blocked = bc::map::walls() | bc::map::holes() | bc::map::altars();
auto walkable = ~blocked;
```

### bushes

```cpp
const bitboard& bushes()
```

Get the immutable bush mask; the reference lasts for the bot lifetime.

### camp

```cpp
cambc::camp camp(vec2 position)
```

Find a camp by spawn tile, querying the engine on every call; throws if there is no camp.

- `position`: Spawn tile of the camp.

### camp_group

```cpp
class camp_group { };
```

A physical camp cluster and its rewards.

### camp_group_alive

```cpp
struct camp_group_alive {};
```

The group still contains living camps; this state has no respawn countdown.

### camp_group_capture_state

```cpp
struct camp_group_capture_state { std::int32_t timer; camp_group_capture_type state; };
```

Capture countdown and status; timer is the configured maximum when not capturing.

*Example: Read the visible group's capture state, even when its occupants are hidden. AllyCapturing and EnemyCapturing carry the remaining countdown; all other states carry the configured maximum (five turns).*

```cpp
auto capture = group.capture_state();
if (capture.state == bc::map::camp_group_capture_type::contested) {
}
auto turns = capture.timer;
```

### camp_group_capture_type

```cpp
enum class camp_group_capture_type : std::int32_t { no_capture_available, ally_capturing, contested, enemy_capturing, capture_available };
```

Capture status relative to the querying champion's team.

*Example: Read the visible group's capture state, even when its occupants are hidden. AllyCapturing and EnemyCapturing carry the remaining countdown; all other states carry the configured maximum (five turns).*

```cpp
auto capture = group.capture_state();
if (capture.state == bc::map::camp_group_capture_type::contested) {
}
auto turns = capture.timer;
```

### camp_group_respawning

```cpp
struct camp_group_respawning { std::int32_t timer; };
```

The group is waiting to respawn. The timer is the remaining round countdown; zero means respawning is currently blocked by occupied spawn tiles.

### camp_group_reward_available

```cpp
struct camp_group_reward_available {};
```

All camps are defeated and the reward is available. The respawn countdown begins after the reward is captured.

### camp_group_state

```cpp
using camp_group_state = std::variant<camp_group_alive, camp_group_reward_available, camp_group_respawning>;
```

Returned by camp_group.state(). Inspect camp_group_respawning.timer when the variant is respawning. Reading state requires at least one original camp spawn tile in current vision; otherwise the SDK reports a visibility error. max_respawn_timer gives the configured full duration, not the remaining countdown.

### camp_groups

```cpp
std::vector<camp_group> camp_groups()
```

Query physical camp groups from the engine on every call; also available in draft.

### height

```cpp
std::int32_t height()
```

Get the map height in tiles.

### holes

```cpp
const bitboard& holes()
```

Get the immutable hole mask; the reference lasts for the bot lifetime.

*Example: Build a terrain-only walking mask. Also exclude occupied tiles and the enemy spawn when selecting a legal step.*

```cpp
auto blocked = bc::map::walls() | bc::map::holes() | bc::map::altars();
auto walkable = ~blocked;
```

### is_in_bounds

```cpp
bool is_in_bounds(vec2 position)
```

Check whether a tile is within the map dimensions.

- `position`: Position to check.

### reflect_horizontal

```cpp
vec2 reflect_horizontal(vec2 p)
```

Reflect across the map horizontally, reversing tile x coordinates.

- `p`: Map position to reflect.

### reflect_vertical

```cpp
vec2 reflect_vertical(vec2 p)
```

Reflect across the map vertically, reversing tile y coordinates.

- `p`: Map position to reflect.

### rotate_180

```cpp
vec2 rotate_180(vec2 p)
```

Rotate tiles 180 degrees within the map dimensions.

- `p`: Map position to rotate.

### spawn_region

```cpp
const bitboard& spawn_region(team value)
```

Get the cached spawn mask for a team.

- `value`: Team whose spawn region to return.

### symmetry

```cpp
symmetry symmetry()
```

Get the map symmetry.

### walls

```cpp
const bitboard& walls()
```

Get cached terrain masks; references remain valid for the bot lifetime.

*Example: Build a terrain-only walking mask. Also exclude occupied tiles and the enemy spawn when selecting a legal step.*

```cpp
auto blocked = bc::map::walls() | bc::map::holes() | bc::map::altars();
auto walkable = ~blocked;
```

### width

```cpp
std::int32_t width()
```

Get the map width in tiles.

<a id="cambc-map-camp-group"></a>

## cambc::map::camp_group

### begin

```cpp
auto begin() const noexcept
```

Iterate immutable camp members stored in this physical group.

### camps

```cpp
std::span<const camp> camps() const noexcept
```

Get the camp members stored in this physical group.

### capture_state

```cpp
camp_group_capture_state capture_state() const
```

Read current capture progress; group visibility is required, champion visibility is not.

*Example: Read the visible group's capture state, even when its occupants are hidden. AllyCapturing and EnemyCapturing carry the remaining countdown; all other states carry the configured maximum (five turns).*

```cpp
auto capture = group.capture_state();
if (capture.state == bc::map::camp_group_capture_type::contested) {
}
auto turns = capture.timer;
```

### end

```cpp
auto end() const noexcept
```

Get the past-the-end iterator for this group's camp members.

### gem_value

```cpp
std::uint32_t gem_value() const noexcept
```

Get the gem reward for capturing this camp group.

### gold_value

```cpp
std::uint32_t gold_value() const noexcept
```

Get the gold reward for capturing this camp group.

### max_respawn_timer

```cpp
std::int32_t max_respawn_timer() const noexcept
```

Get the configured camp-group respawn duration in rounds.

### operator handle_camp_group_t

```cpp
operator handle_camp_group_t() const noexcept
```

Convert to the strong camp-group identity.

### operator==

```cpp
friend bool operator==(const camp_group& a, const camp_group& b) noexcept
```

Compare camp-group identities.

### spawn_tiles

```cpp
bitboard spawn_tiles() const
```

Build the mask of original camp spawn tiles in this group; computed on every call.

### spawn_tiles_into

```cpp
void spawn_tiles_into(bitboard& out) const
```

Like `spawn_tiles`, but writes into `out` instead of returning a new board.

- `out`: Destination; its previous contents are overwritten.

### state

```cpp
camp_group_state state() const
```

Current lifecycle state; remembered state outside current vision is not exposed.

<a id="cambc-shared-memory-buffer"></a>

## cambc::shared_memory_buffer

### operator[]

```cpp
reference operator[](std::size_t offset) const
```

Access one byte; throws if the offset is outside the buffer.

### read

```cpp
template <class T, std::size_t Extent> requires (std::is_trivially_copyable_v<T> && !std::is_const_v<T>) void read(std::size_t offset, std::span<T, Extent> values) const
```

Read a checked byte range into trivially copyable values.

- `offset`: Byte offset into shared memory.
- `values`: Receives the values; its size sets how many are read.

### read

```cpp
void read(std::size_t offset, std::span<std::byte> bytes) const
```

Read a checked byte range into caller-owned storage.

- `offset`: Byte offset into shared memory.
- `bytes`: Receives the bytes; its size sets how many are read.

*Example: Reserve byte zero in your team's memory layout for a shared objective ID. All allied bots must agree on its meaning.*

```cpp
std::byte objective_id{};
bc::shared_memory.read(0, std::span<std::byte>{&objective_id, 1});
```

### reference

```cpp
class reference { };
```

Byte proxy that reads and writes through SDK imports.

### size

```cpp
static std::size_t size()
```

Get the shared-memory capacity in bytes.

### write

```cpp
template <class T, std::size_t Extent> requires std::is_trivially_copyable_v<T> void write(std::size_t offset, std::span<T, Extent> values) const
```

Write the object representations of trivially copyable values to a checked byte range.

### write

```cpp
void write(std::size_t offset, std::span<const std::byte> bytes) const
```

Write bytes at an offset; the entire range must fit.

- `offset`: Byte offset into shared memory.
- `bytes`: Bytes to write.

*Example: Reserve byte zero in your team's memory layout for a shared objective ID. All allied bots must agree on its meaning.*

```cpp
const std::byte objective_id{2};
bc::shared_memory.write(0, std::span<const std::byte>{&objective_id, 1});
```

<a id="cambc-shared-memory-buffer-reference"></a>

## cambc::shared_memory_buffer::reference

### operator std::uint8_t

```cpp
operator std::uint8_t() const
```

Read the current byte at this proxy's checked offset.

### operator=

```cpp
reference& operator=(const reference& other)
```

### operator=

```cpp
reference& operator=(std::byte value)
```

### operator=

```cpp
reference& operator=(std::uint8_t value)
```

Write one byte at this proxy's checked offset.

### reference

```cpp
reference(const reference&) = default
```

<a id="cambc-teleport"></a>

## cambc::teleport

### champion

```cpp
cambc::champion champion() const
```

Construct a live view of the champion in the teleport reservation.

### is_ally

```cpp
bool is_ally() const
```

Check whether this teleport belongs to the observing team.

### is_enemy

```cpp
bool is_enemy() const
```

Check whether this teleport belongs to the opposing team.

### operator==

```cpp
friend bool operator==(const teleport&, const teleport&) = default
```

Compare every captured field.

### position

```cpp
vec2 position() const noexcept
```

Get the destination tile captured in this teleport reservation.

### remaining_time

```cpp
std::int32_t remaining_time() const noexcept
```

Get the remaining round count captured in this observation.

### team

```cpp
team team() const
```

Get the owning team relative to the authenticated bot.

### teleport

```cpp
explicit teleport(detail::teleport_info value)
```

Copy a visible teleport reservation; its metadata remains a snapshot.

### visible_tiles

```cpp
bitboard visible_tiles() const
```

Hypothetical caster vision after arriving at the reserved destination, not current visibility.

### visible_tiles_into

```cpp
void visible_tiles_into(bitboard& out) const
```

Like `visible_tiles`, but writes into `out` instead of returning a new board.

- `out`: Destination; its previous contents are overwritten.

<a id="cambc-type-tag-t"></a>

## cambc::type_tag_t

### type

```cpp
using type = T;
```

The tagged type.

<a id="cambc-uninitialized-t"></a>

## cambc::uninitialized_t

### uninitialized_t

```cpp
explicit uninitialized_t() = default
```

Explicit so that `{}` cannot select the tag by accident.

<a id="cambc-unit"></a>

## cambc::unit

### ~unit

```cpp
virtual ~unit() = default
```

Destroy a derived unit view through the shared interface.

### attack_range

```cpp
virtual std::int32_t attack_range() const = 0
```

Attack range in Chebyshev tiles; melee units have range 1.

### attack_tiles

```cpp
bitboard attack_tiles() const
```

Build the live unit's Chebyshev attack-range mask; does not filter targets or attack availability. Hidden units and design-only champions propagate position/range query errors.

### attack_tiles_into

```cpp
void attack_tiles_into(bitboard& out) const
```

Like `attack_tiles`, but writes into `out` instead of returning a new board.

- `out`: Destination; its previous contents are overwritten.

### buffs

```cpp
buff_collection buffs() const
```

Construct a fresh owning buff collection; previous collections retain their captured values.

### focus

```cpp
virtual float focus() const = 0
```

Query current focus for this visible unit.

### health

```cpp
virtual float health() const = 0
```

Query current health; live state requires a visible runtime identity.

### is_visible

```cpp
virtual bool is_visible() const = 0
```

Check whether live state is available; hidden units and design-only views return false.

### max_health

```cpp
virtual float max_health() const = 0
```

Query current maximum health; live state requires a visible runtime identity.

### position

```cpp
virtual vec2 position() const = 0
```

Get the tile position; live entity views query current engine state.

### strength

```cpp
virtual float strength() const = 0
```

Query current strength for this visible unit.

<a id="cambc-vec2"></a>

## cambc::vec2

### chebyshev_distance

```cpp
constexpr std::int64_t chebyshev_distance(vec2 b) const
```

Get the largest absolute coordinate difference.

- `b`: Other vector.

### cross

```cpp
constexpr std::int64_t cross(vec2 b) const
```

Get the signed two-dimensional cross product with a 64-bit result.

- `b`: Other vector.

### dot

```cpp
constexpr std::int64_t dot(vec2 b) const
```

Dot and cross products use 64-bit arithmetic.

- `b`: Other vector.

### length_squared

```cpp
constexpr std::int64_t length_squared() const
```

Get the squared Euclidean length.

### operator-

```cpp
constexpr vec2 operator-() const
```

Negate both components.

### operator-

```cpp
friend constexpr vec2 operator-(vec2 a, vec2 b)
```

Subtract b from a.

### operator-=

```cpp
constexpr vec2& operator-=(vec2 b)
```

Subtract a displacement in place.

### operator*

```cpp
friend constexpr vec2 operator*(std::int32_t n, vec2 a)
```

Scale a vector by an integer.

### operator*

```cpp
friend constexpr vec2 operator*(vec2 a, std::int32_t n)
```

Scale a vector by an integer.

### operator*=

```cpp
constexpr vec2& operator*=(std::int32_t n)
```

Scale both components in place.

### operator/

```cpp
friend constexpr vec2 operator/(vec2 a, std::int32_t n)
```

Divide both components, truncating towards zero. Throws std::invalid_argument when n is zero.

### operator/=

```cpp
constexpr vec2& operator/=(std::int32_t n)
```

Divide both components in place, truncating towards zero. Throws std::invalid_argument when n is zero.

### operator+

```cpp
constexpr vec2 operator+() const
```

Return the vector unchanged.

### operator+

```cpp
friend constexpr vec2 operator+(vec2 a, vec2 b)
```

Add two vectors.

### operator+=

```cpp
constexpr vec2& operator+=(vec2 b)
```

Add a displacement in place.

### operator<=>

```cpp
constexpr auto operator<=>(const vec2&) const = default
```

Compare by x, then by y.

### reflect_horizontal

```cpp
constexpr vec2 reflect_horizontal() const
```

Reflect the vector horizontally across the origin.

### reflect_vertical

```cpp
constexpr vec2 reflect_vertical() const
```

Reflect the vector vertically across the origin.

### rotate_180

```cpp
constexpr vec2 rotate_180() const
```

Rotate the vector 180 degrees about the origin.

### rotate_ccw

```cpp
constexpr vec2 rotate_ccw() const
```

Rotate the vector 90 degrees counterclockwise about the origin.

### rotate_cw

```cpp
constexpr vec2 rotate_cw() const
```

Rotate a displacement by a quarter turn.

### vec2

```cpp
constexpr vec2() = default
```

Construct an integer tile vector; the default value is the origin.

### vec2

```cpp
constexpr vec2(std::int32_t x, std::int32_t y)
```

Construct an integer tile vector; the default value is the origin.

<a id="cambc-vision"></a>

## cambc::vision

### altar_lock_at

```cpp
cambc::altar_lock altar_lock_at(vec2 position)
```

Prefer the allied lock if both teams have a lock on this altar.

- `position`: Tile to query.

### altar_lock_tiles

```cpp
bitboard altar_lock_tiles()
```

Query current altar-lock occupancy for the selected team or both teams.

### altar_lock_tiles

```cpp
bitboard altar_lock_tiles(team side)
```

Query current altar-lock occupancy for the selected team or both teams.

- `side`: Team to include.

### altar_lock_tiles_into

```cpp
void altar_lock_tiles_into(bitboard& out)
```

Like `altar_lock_tiles()`, but writes into `out`.

- `out`: Destination; its previous contents are overwritten.

### altar_lock_tiles_into

```cpp
void altar_lock_tiles_into(team side, bitboard& out)
```

Like `altar_lock_tiles`, but writes into `out` instead of returning a new board.

- `side`: Team to include.
- `out`: Destination; its previous contents are overwritten.

### altar_locks

```cpp
std::vector<cambc::altar_lock> altar_locks()
```

Get fresh, owning visible altar-lock snapshots, optionally filtered by team.

### altar_locks

```cpp
std::vector<cambc::altar_lock> altar_locks(team side)
```

Get fresh, owning visible altar-lock snapshots, optionally filtered by team.

- `side`: Team to include.

### asleep_camp_tiles

```cpp
bitboard asleep_camp_tiles()
```

Get the tiles of visible asleep camps. Dead camps are excluded.

### asleep_camp_tiles_into

```cpp
void asleep_camp_tiles_into(bitboard& out)
```

Like `asleep_camp_tiles`, but writes into `out`.

- `out`: Destination; its previous contents are overwritten.

### awake_camp_tiles

```cpp
bitboard awake_camp_tiles()
```

Get the tiles of visible awake camps. Dead camps are excluded.

### awake_camp_tiles_into

```cpp
void awake_camp_tiles_into(bitboard& out)
```

Like `awake_camp_tiles`, but writes into `out`.

- `out`: Destination; its previous contents are overwritten.

### camp_at

```cpp
cambc::camp camp_at(vec2 position)
```

Find a currently visible camp.

- `position`: Current tile of the camp.

### camp_groups

```cpp
std::vector<map::camp_group> camp_groups()
```

A group is currently visible when any original spawn tile is in effective vision, even if empty.

### camp_tiles

```cpp
bitboard camp_tiles()
```

Get camp occupancy from the current perspective.

### camp_tiles_into

```cpp
void camp_tiles_into(bitboard& out)
```

Like `camp_tiles`, but writes into `out` instead of returning a new board.

- `out`: Destination; its previous contents are overwritten.

### camps

```cpp
std::vector<cambc::camp> camps()
```

Get an owning list of currently visible camps, recomputed each call.

### champion_at

```cpp
cambc::champion champion_at(vec2 position)
```

Create a fresh view of the currently visible champion at a position.

- `position`: Tile to query.

### champion_tiles

```cpp
bitboard champion_tiles()
```

Get visible champion occupancy for both sides.

### champion_tiles

```cpp
bitboard champion_tiles(team side)
```

Get visible champion occupancy for one side.

- `side`: Team to include.

### champion_tiles_into

```cpp
void champion_tiles_into(bitboard& out)
```

Like `champion_tiles()`, but writes into `out`.

- `out`: Destination; its previous contents are overwritten.

### champion_tiles_into

```cpp
void champion_tiles_into(team side, bitboard& out)
```

Like `champion_tiles`, but writes into `out` instead of returning a new board.

- `side`: Team to include.
- `out`: Destination; its previous contents are overwritten.

### champions

```cpp
std::vector<cambc::champion> champions()
```

Get a fresh champion list for the current view and optional team filter.

### champions

```cpp
std::vector<cambc::champion> champions(team side)
```

Get an owning list of currently visible champions, recomputed each call.

- `side`: Team to include.

### has_altar_lock

```cpp
bool has_altar_lock(vec2 position)
```

Check for a visible altar lock for either team; missing or hidden locks return false.

- `position`: Tile to query.

### has_camp

```cpp
bool has_camp(vec2 position)
```

False on hidden or empty tiles; invalid positions retain the engine's error.

- `position`: Tile to query.

### has_champion

```cpp
bool has_champion(vec2 position)
```

Check visible champion occupancy at a tile; invalid positions retain engine errors.

- `position`: Tile to query.

### has_teleport

```cpp
bool has_teleport(vec2 position)
```

Check whether a tile is occupied by a visible teleport reservation.

- `position`: Tile to query.

### has_ward

```cpp
bool has_ward(vec2 position, team side)
```

Check ward occupancy for `side`; hidden or absent wards return false.

- `position`: Tile to query.
- `side`: Team the ward must belong to.

### has_ward

```cpp
bool has_ward(vec2 position)
```

Check ward occupancy at a tile; hidden or absent wards return false.

- `position`: Tile to query.

### in_vision

```cpp
bool in_vision(vec2 position)
```

Check current self vision, including owned ward vision, whether or not the tile is occupied. Hidden tiles return false; out-of-bounds positions throw api_bad_position.

- `position`: Tile to query.

### teleport_at

```cpp
teleport teleport_at(vec2 position)
```

Get the visible teleport reservation on a tile.

- `position`: Tile to query.

### teleport_tiles

```cpp
bitboard teleport_tiles()
```

Query current visible teleport-reservation occupancy.

### teleport_tiles_into

```cpp
void teleport_tiles_into(bitboard& out)
```

Like `teleport_tiles`, but writes into `out` instead of returning a new board.

- `out`: Destination; its previous contents are overwritten.

### teleports

```cpp
std::vector<teleport> teleports()
```

Get fresh, owning visible teleport-reservation snapshots.

### visible_tiles

```cpp
bitboard visible_tiles()
```

Query current visible tiles.

### visible_tiles_into

```cpp
void visible_tiles_into(bitboard& out)
```

Like `visible_tiles`, but writes into `out` instead of returning a new board.

- `out`: Destination; its previous contents are overwritten.

### ward_at

```cpp
cambc::ward ward_at(vec2 position, team side)
```

Get the ordinary ward at a tile for one team.

- `position`: Tile to query.
- `side`: Team the ward must belong to.

### ward_at

```cpp
cambc::ward ward_at(vec2 position)
```

Get the ordinary ward at a tile.

- `position`: Tile to query.

### ward_tiles

```cpp
bitboard ward_tiles()
```

Query visible ordinary-ward occupancy for both teams.

### ward_tiles

```cpp
bitboard ward_tiles(team side)
```

Query visible ordinary-ward occupancy for one team.

- `side`: Team to include.

### ward_tiles_into

```cpp
void ward_tiles_into(bitboard& out)
```

Like `ward_tiles()`, but writes into `out`.

- `out`: Destination; its previous contents are overwritten.

### ward_tiles_into

```cpp
void ward_tiles_into(team side, bitboard& out)
```

Like `ward_tiles`, but writes into `out` instead of returning a new board.

- `side`: Team to include.
- `out`: Destination; its previous contents are overwritten.

### wards

```cpp
std::vector<cambc::ward> wards()
```

Fresh visible ordinary-ward observations; overlapping records remain distinct.

### wards

```cpp
std::vector<cambc::ward> wards(team side)
```

Get fresh ordinary-ward observations filtered by team.

- `side`: Team to include.

<a id="cambc-ward"></a>

## cambc::ward

### is_ally

```cpp
bool is_ally() const noexcept
```

Check whether this ward belongs to the observing team.

### is_enemy

```cpp
bool is_enemy() const noexcept
```

Check whether this ward belongs to the opposing team.

### operator==

```cpp
friend bool operator==(const ward&, const ward&) = default
```

Compare every captured field.

### owner

```cpp
cambc::champion owner() const
```

Return the owning champion captured when this ward was visible, even if the owner is hidden. Live champion state still requires the champion to be in vision.

### position

```cpp
vec2 position() const noexcept
```

Get the ward's tile.

### remaining_time

```cpp
std::optional<std::int32_t> remaining_time() const noexcept
```

Get the remaining lifetime in rounds; empty for an unlimited lifetime.

### team

```cpp
cambc::team team() const noexcept
```

Get the owning team relative to the authenticated bot.

### visible_tiles

```cpp
bitboard visible_tiles() const
```

Hypothetical vision from this ward's position, ignoring current team visibility.

### visible_tiles_from

```cpp
static bitboard visible_tiles_from(vec2 position)
```

Query the mask for ordinary-ward vision at a placement tile.

- `position`: Hypothetical ward tile.

### visible_tiles_from_into

```cpp
static void visible_tiles_from_into(vec2 position, bitboard& out)
```

Like `visible_tiles_from`, but writes into `out` instead of returning a new board.

- `position`: Hypothetical ward tile.
- `out`: Destination; its previous contents are overwritten.

### visible_tiles_into

```cpp
void visible_tiles_into(bitboard& out) const
```

Like `visible_tiles`, but writes into `out`.

- `out`: Destination; its previous contents are overwritten.

<a id="std"></a>

## std

### operator()

```cpp
std::size_t operator()(cambc::vec2 v) const noexcept
```

Hash a tile position.

### operator()

```cpp
std::size_t operator()(const cambc::camp& c) const noexcept
```

Hash a camp identity.

### operator()

```cpp
std::size_t operator()(const cambc::champion& c) const noexcept
```

Hash a champion identity.

### operator()

```cpp
std::size_t operator()(const cambc::map::camp_group& g) const noexcept
```

Hash a camp-group identity.
