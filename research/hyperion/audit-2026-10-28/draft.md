# Audit: draft (`bots/astraeus/src/draft/draft.cc`, `draft.h`)

## Changed

Commit `astraeus audit (draft): cleanup`. Bench (00ambush, 00lanes, 01hooks, 00interlock, both
sides, no `--test-draft`, against a HEAD copy): **8/8 replays byte-identical**, same drafted teams.
Fuel: play turns unchanged (mean 50985 -> 50985); champion round-1 turns +56 (+0.03%, from
code layout and the shared decode helper); total +0.0004%.

- **`body_tile`** now reads `map.landing_tiles[b]`. It used to sort the spawn tiles again on every
  call (team B: A's tiles sorted, then mirrored). `StaticMap::build` already sorts `landing_tiles`
  into the same order: B's tiles sorted by their mirror image are A's sorted order, mirrored.
- **`body_spawn_index`**: the "find the body's tile in `ally_spawn_tiles`" code that `rank_body`
  and `dash_entry` both had.
- **`best_rice(codes)`**: the Rice-parameter search that `write_steps` and `dash_entry` both had.
- **`tribute_tiles(map)`**: the tribute-goal board was built in three places.
- **`uncounted_field`**: the save/make/restore of `max_field_layers` / `costliest_field` that
  `check_dash_steps` and `dash_entry` both had. It now carries one comment saying why these fields
  are left out of the plan's reported layers.
- **`decode_bounded`** (always_inline): `decode_steps`' lambda and `decode_enemy_steps`' copy of it
  are now one function.
- **`TileBox::none()` / `add()`**: `TileBox::of` and `ward_box` both had the min/max loop.
- **`unzigzag`** is now in the header, and `index_steps` uses it instead of an inline copy.
- **`expected_bodies`** is now one pass over the order. The old code did "add the first missing
  pick" repeatedly, with a `picked_round` special case that did the same thing as the loop's first
  pass. Its unused `state` parameter (and `make_leads`') is gone.
- **`tributes_walked`**: the camp-overlap test used to reuse the board named `walls` as scratch; it
  now has its own board, `on_camps`.
- **`write_index`**: renamed the decoded-steps variable from `rice` to `coded`.
- **Comments**:
  - Removed the "v61" references (`vesper_allowed`, `choose_table_draft`).
  - Moved the Analysis description from `draft_reserve` onto `struct Analysis`.
  - Clarified `map_hash` (it is keyed on our team), `model_draft` (rewrapped) and the order-caching
    comment in `play_draft`.

## Considered, not changed

- **`pick_first_available`'s try/catch** (~3.9k fuel per rejected pick). Our own repeats and
  Vesper are already filtered out, and both teams may pick the same champion, so the catch only
  fires on unexpected engine errors. A pre-check would add nothing.
- **Splitting `analyse`** (~110 lines) into per-phase functions. Its resumable `for (; a.x < ...)`
  loops share the `afford`/return protocol, and splitting them would need every phase to report
  "stopped for fuel". That is mostly noise for a function read top to bottom.
- **`write_index` and `write_steps` re-encode codes that `write_steps` also builds** (fixed-width
  vs Rice codes). Sharing a `codes` builder is possible but the two differ in the mirrored and
  unreachable cases; I left it.
- **`ward_sight = 2 + 6`** could use `ward_range() + ward_vision_radius`. It needs a constexpr
  context in a static; I left it as the commented literal.

## Suggestions

1. **Later draft turns can never afford some ward sites** (`draft.cc:711`, severity low,
   effort small). The cost is `5000 + 2000 * ward_box area`, on top of the 40k `draft_reserve`:
   - A two-member group's box (e.g. 6x5 = 30) needs 105k.
   - An altar site's box (7x7 = 49) needs 143k.

   Both exceed a 100k draft turn. If the first (10M) turn does not finish the ward search, no later
   turn ever does: `analyse` returns at that site every turn, and the index section is never
   written. Today the first turn always finishes, so it is latent. Fix: estimate per candidate
   tile (or split a site's candidates across turns) so the bound is under the 60k a turn has free.
   That removes a stall rather than adding a gate.
2. **`type_facts`' heal walk is a Chebyshev guess where the exact steps are known**
   (`draft.cc:200`, severity low, behaviour change). It uses
   `dist(map.landing_tiles[0], group.centre)`, but `a.steps[g][0]` (the walk from our spawn) is
   already computed when `type_facts` runs. Farm's opening uses the Chebyshev distance from the
   spawn centre (`economy/farm.cc:658`), so the two already differ slightly. Either match farm
   exactly, or use the exact steps in both. It only changes lead ranking, so it needs an A/B.
3. **Dash entries can go stale if the expected team changes** (`draft.cc:673`, severity very
   low). `make_leads` resets `leads_made` when `lead_for` changes, but `dash_bodies` and
   `dash_kind` are not reset. `dash_entry`'s early returns also leave an earlier `dash_kind` in
   place. The dash section is written once, in the same `analyse` pass, so this only bites if fuel
   runs out between the two. Fix: reset `dash_bodies` and `dash_kind` together with `leads_made`.
4. **`write_steps` leaves `header.mirrored` and `rice` set when it fails** (`draft.cc:~262`,
   cosmetic). `header.steps` stays false, so champions ignore them, but the written header
   carries stale flags. Clearing them on failure would make the header self-consistent.
5. **`mirrored_enemy_steps`' cursor is a function-local static** (`draft.cc:881`). It assumes one
   plan per instance, which holds today. A member of `DraftSteps` would make that explicit and
   safe if a second decode ever appears. Low value.
6. **Kiting is modelled only for ranged champions**, both in `type_facts` (`spells` needs
   `f.ranged`) and in farm (`economy/farm.cc:662`). Melee champions with a unit-target damage spell
   (Marcella 2x, Ren 1.1x, range 4) out-range wolves (range 3) just as well; the rules allow a melee
   champion to cast without walking into range. This is a modelling gap that belongs to farm
   first; the draft should follow whatever farm does. Medium effort; needs an A/B.
7. **`best_ward`'s "own sight" is measured from the group centre** (`draft.cc:~475`). Champions
   working a group stand on its camp tiles, and for an altar, on a tribute tile rather than the
   altar. Scoring the union of sight from the camp tiles (or the likely stand tile) would rate
   wards against what the worker actually sees. Judgement call, draft-only fuel.
8. **Header docs** (`draft.h`, the section comment on `DraftPlan`) are accurate but dense. No
   error found; I checked each section's layout against the writers and readers.
