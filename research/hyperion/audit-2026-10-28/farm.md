# Audit: `bots/astraeus/src/economy/farm.cc` (farm)

## Changed

### Cleanup (commit 1, byte-identical bench replays)

The bench used 4 maps (00ambush, 00lanes, 01hooks, 00interlock) with `--test-draft`. All 8 replays were byte-identical. Total fuel fell 2,211,802,776 to 2,198,297,713 (-0.61%), with mean per turn 50161 to 49854. The bench builds without `--release`, so most of that saving comes from the removed debug traces. A release build saves less.

- **Experiment traces removed:** FPARTIAL (the whole `partial_trace` lambda and its reason strings), FCDELAY, FCWINDOW and FCPARTNER (all three `round <= 5` old-vs-new checks), FSEED and DASH-FOLLOW. No tool parses them. Without them `prefer_partial` drops to about half its length and reads as plain early returns.
- **`prefer_partial`:**
  - The `decision != 'F' || banking || siege || siege_group()` re-check is gone. Its only caller (`attack_in_range`) calls it only when `ordinary` already holds exactly that.
  - `harmless` is gone. It is implied by `H.strength <= 0`, since group strength is the members' sum.
  - It now has a header comment saying what it does.
- **`claimed_by_ally(g)`:** this lambda replaces three copies of the `g < 256 && (ally_claims[g >> 6] >> (g & 63) & 1)` mask test (in `taken`, `struggling` and `prefer_partial`).
- **`ally_spawn_box(map)`:** our spawn's bounding box is now read once, not rebuilt every farm turn.
- **`capture_rounds(world)`:** read once into `capture` / `cap_rounds`. Before, about 12 inline calls in the group loop plus two duplicate hoisted copies (`cap_rounds`, `capture`).
- **`crew_work`:** its unused `group` local is gone. In the partner loop, `camp_output(a)` is now read only for a partner that arrives together with us.
- **Comments:**
  - Removed transient references: "v61", "~0.4% dearer", "distances.md / draft walk orders", "so near the cap each step turned us back", and "This admission tier must share any future farm-wide cleanup-delegation exclusion".
  - Reflowed the `GroupFacts` header.
  - Moved the short-of-fuel comment and `previous` next to `walk_on`, which uses them.
  - Added a line on how `first` is seeded.

### Fix (commit 2, behaviour-changing)

- **The crew flag was lost on a cut-short turn** (`farm.cc`, the `best < 0` tail of `farm_turn`). Before the loop, `memory.claim`/`memory.crew` are reset to `best`/false. When the loop weighed nothing (`k == 0`), the code still walks on towards last turn's choice and sets `memory.claim = memory.farm_group`, but leaves `crew = false`. This happens after a fight's strike search (`evaluated == 0`) or when fuel ran short before the first group.
  - Effect: a champion that was crew on an ally's claim silently becomes its rival. On the next turn `taken()` and `is_claimed()` treat the group as ours, so we value the full reward rather than our share, and we hit it in passing as our own.
  - Fix: keep `crew` when last turn's claim was the same group (`crew_of_choice`).
  - Bench against the cleanup: 3 of 8 replays differ (00interlock b, 01hooks a and b). Fuel on the 5 identical games rose +0.01%, from the extra bool. Not A/B tested: it needs an `ab.py` run to judge.

## Considered, not changed

- **`opening ? engaged(g) : ally_engaged(world, g)`:** `engaged` is an exact prefilter of `ally_engaged`, so using it on later turns too would give the same choices. It was left alone because the per-turn cost of building the box was presumably measured, and the difference is fuel only.
- **`step_onto_cleared`'s try/catch around `camp(i).is_alive()`:** rules say a camp's alive state is readable out of vision, so it should never throw. It is harmless, though, and costs nothing unless it throws.
- **`rated_below` duplicating `rate()`'s horizon formula:** it is the inlined form of `rate()`, kept so the hoisted constants avoid a call. Left in place.
- **The `pick_up` radius of 4:** this is a bare magic number. I had no basis to change it (see Suggestions).

## Suggestions

1. **`spell_clear`'s kite tile ignores other groups' reach** (farm.cc `spell_clear`, where `reach` is drawn only from `G`'s members). The goal tiles must be out of the chosen group's attacker reach, but a neighbouring awake group can still hit us there. `spell_clear_rounds` then values the clear as costing no health. Kites near camp clusters may stand under fire every turn without the farm valuation knowing.
   - Exact version: also draw the reach of awake, live strikers of groups near the goal set (`groups_near`), or at least drop goals in `Safety`'s camp threat.
   - Severity: medium on dense camp maps, only for ranged champions with damage spells (Prism, Stellar, Cassi, Tavi). Effort: small.
2. **Melee damage spells never kite** (`const float spells = world.me().facts().ranged ? spell_output(...) : 0`). Marcella (slot 1: damage 2, unit, range 4), Ren (slot 0: 1.1 stun, unit) and Heart of Ruin's dash landing all deal spell damage from beyond a wolf's reach of 3. They are excluded from both `spell_clear_rounds` and `beyond_spare`'s `kites`. The rates are low (Marcella about 15 a round at base), so the main loss is the zero-health clear for a hurt melee champion.
   - The gate looks arbitrary rather than modelled. Let `spell_clear_rounds` decide; it already returns -1 when no spell reaches.
   - Severity: low. Effort: small, but it changes behaviour, so it needs an A/B.
3. **A hop group's recall-out time is added to `steps`** (loop: `steps = walk + tp_crystal_time + inner + (centre_to_altar(g) == unreachable ? recall_turns : 0)`). That recall belongs to banking (after the capture), not the approach. Counted in `steps` it shrinks the respawn `wait` by up to `recall_turns`, and so admits groups that will still be respawning on arrival. It also inflates `help_steps`, `best_steps` and the search cap.
   - Fix: add it to `bank` / `cycle_bank` instead.
   - Severity: low (crystal-region maps only). Effort: small.
4. **`struggling` overstates an ally's danger** (`a.health - min_camp_damage(...)`). It ignores the ally's damage-taken emblems (Jungle, Durability), its self-shield (Varg, Heart of Ruin; `shielded_clear`) and any heals. We help more often than the ally needs, which is "one champion per camp otherwise" broken. The ally's emblems are known (`camp_dealt` is read for allies, so a `camp_taken` equivalent likely exists in `world.cc`).
   - Severity: low. Effort: small.
5. **Ren's partner clear ignores reflection.** The main loop's `min_camp_damage(world, g, strength + partner_output, &joint_rounds)` passes no `reflect`, and `beyond_spare`'s `shared` matches it. The joint clear is therefore overcosted for Ren, so a partnered group can be wrongly called risky. The prune and the main loop agree, so this is a modelling gap, not an inconsistency.
   - Severity: low. Effort: small, but `min_camp_damage`'s reflect path is single-clearer.
6. **The partial-evaluation fuel gate** (`room()`, `farm-partial-evaluation`, `fuel_ok(full_field_cost_estimate ...)` break, `farm-kept-target`, `crow-flies-farm`). Each group's value depends on facts kept across turns (`GroupFacts`, version-keyed) plus our position and `best_value`. The loop could resume where it stopped last turn, or re-weigh only groups whose belief or context changed, instead of restarting from `first`. That would make a full evaluation bounded across turns rather than gated within one.
   - Severity: medium (the bench shows about 0.8% of turns over 100k, some of them farm). Effort: large.
7. **The `pick_up` radius of 4** (`if (steps > 4) continue;`) is an unexplained constant. It reads as "a step or two before the capture count matters". It should be a named `params::` value or derived, for example from `capture_rounds`, since a pickup further than that loses to the claimer anyway.
   - Severity: cosmetic. Effort: trivial.
8. **`engaged`'s threat bound** uses `members.size() - 1 + reach`. `CampGroup::threat_radius()` is exact (and `ally_engaged` itself uses it). The two give the same result; whether the switch saves fuel depends on whether `threat_radius()` is already warm. Fuel only.
