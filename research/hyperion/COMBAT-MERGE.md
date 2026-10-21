The 2026-10-21 session plan for merging the combat logic into one system, as written.

# Hyperion: one combat system, waves 1-5 (revised)

Basis: cambc-rules.yaml read. Code checked on claude/dazzling-mccarthy-4kawix f25159f (main 55e0bdc + wave 0: w0/removals, w0/phase-instr, ab.py --phases). Owners are given as function names; line numbers are hints only.
Wave 1 starts from the wave-0 integration after its A/B. Call it `w0`.

## 0. Judgement on the inputs

- Shape: lazy per-turn tile table in Safety, one unseen rule, one camp model with exit rounds, memoised duplicate sims (W1); one fight engine with a per-mode rule table plus a lazy guard (W2); one search per turn with flee/chase modes (W3); remaining readers (W4).
- Rejected from the handoff:
  - Recommendation 1 (shield as extra health, 25-40k): EXPERIMENTS.md:211 measured -1% for the plain-side loop, :645 no gain. Measure-first version only in W5.
  - The step_guard "union key over all exposed tiles" shortcut: needs every tile's exposure up front, the eager cost being deleted. Dominance + memo replace it.
- Corrected handoff claims:
  - The search executes its own start-tile ground casts (plan.cpp grow). The removals mismatch was only `valued.any` counting unseen centres; w0 fixed it.
  - Phase 4a was A/B'd: 40.8% of 1094, OOF +135%, 52.6% at 100M (EXPERIMENTS.md:167). W3 has a fuel gate because of this.
  - "Searches start with 65-73k" is unverified; strike-notes say 40-60k.

## 1. Claims checked in code

| Claim | Verdict | Evidence |
|---|---|---|
| Fight memo can survive invalidate() | TRUE except cut fights | Beliefs fixed per Safety (world.observe only in decide's ward block, which rebuilds Safety). invalidate() zeroes fight_count_, keeps made_. trade() stores fight-cut results (lost=self_falls=true) in the memo via new_fight. refresh() invalidates only on a death. |
| Camps absent from fight() | TRUE | new_fight fills us/them only. pursuit and turns_to_kill_idle set us.camp = camp_damage(p,false). |
| Sim charges camp every their-turn for the whole horizon | TRUE | simulate(): `us.hurt(us.camp)` each their turn, fight_horizon = 17; play_quiet/outlives/overwhelmed multiply by `theirs`. Elk 60 → 1020 over 17 turns. |
| step_guard eager with fuel gates | TRUE | 3 "step-guard" gates, static `costliest`, all ≤24 tiles, union key first. |
| Retreat is unguarded today | TRUE | decide returns at `leave` before set_guard; carry_bag and stop_game_ender set_guard(nullptr). |
| Search bans guarded tiles for walk and end | TRUE | read_geometry ORs pathing.guard() into blocked (plan.cpp ~673). dist-3 lethal in plan_strikes; capped fallback skips dist 3. |
| set_guard has 4 call sites | TRUE | decide, act, stop_game_ender, carry_bag. |
| travel_dash uses threats_near/danger | TRUE | self_abilities.cpp travel_dash (outside the old W3-C range). |
| farm has no Safety | TRUE | farm(world, pathing, memory); dash calls in farm and take_hop. |
| chase calls dash_to_attack(pointer) | TRUE | chase; p4b changes it to a reference. |
| p4b KeptRoute keys on the guard pointer | TRUE | p4b pathing.h KeptRoute{goals, avoid, guard,...}. |
| reset hold reads shield_wanted without Safety | TRUE | reset_and_attack_enemy(world, stunning_only). |
| prey simulates at e.pos | TRUE | prey: fight(order[i].second->pos); gated by prey-cut-short. |
| prey key at an attack tile can drop e | TRUE | fight_key keeps only threats whose blow hits p; a melee e cannot reach a range-3 tile. |
| want_home reruns on tribute and ward turns | TRUE | continue_tribute calls want_home without filling home; ward block resets home. |
| Ward reobserve can keep `home` | FALSE | home depends on unseen beliefs (lethal, fight_key) which the ward changes; list_enemies' listed_ must also reset. |
| flee_camps charge | camp_worst × (walk_out-1 or -2) on top of damage_bound | damage_bound already includes the hit at p. |
| bench.py run takes a bot dir, not a ref; debug_phases costs ~1% fuel | TRUE | bench.py `run bot`, ab.py --phases help text. |
| TODO "Don't remove step_guard, pursuit, threat_strike" | Binding | Their rules move into Safety (verdict, Engage pursue), not deleted. |

## 2. End state: one combat system

Inputs (unchanged): World beliefs; Strike (Chebyshev bound per enemy); Reach (map-exact visible blows, memoised); capped threat fields for unseen enemies; camp members.

Safety, the one enemy model per turn:
- `TileDanger tile(p)`: lazy row, stamped by generation, 7×7 window around the turn-start tile plus a 4-slot ring outside. Columns: vis/stun/unseen masks, vis sum, vis_unacted, unseen sum (field rule), camp_exp, camp_worst; lazy exit_rounds, unseen_chance, verdict.
- `engage(p, Engage)`: the one sim entry, with an explicit per-mode rule table (below), memoised by FightKey across invalidate, dominance between stand keys.
- `guarded(q)`: step_guard's rule computed lazily, within radius 3.

Per-mode rule table (pinned, W2-A):

| Mode | Us | Them | Arrivals | First | Camp charge |
|---|---|---|---|---|---|
| stand (fight) | fighting_allies(p) | visible in vis_mask + credible unseen in unseen_mask | 0 | they | camp_exp(p) minus claimed group, for exit_rounds(p) of their turns |
| pursue (pursuit) | fighting_allies(p) | visible, not on near_enemy_spawn, approach ≤ a | approach() | we | same as stand |
| idle (turns_to_kill_idle) | self only, never acts | visible within horizon | approach() | they | camp_exp(p), full horizon (a channel cannot walk) |

One search per turn: `prepare_strikes` once (read+grow), `price_strikes` in normal, flee or chase mode. End tile must pass guarded() in normal and chase; flee prices danger and death instead (retreat stays unguarded).

Readers: want_home (low, outmatched, camp_trapped via exit_rounds, engage stand(here), pursue only when stand does not settle it); prey (engage stand at the attack tile, prey always in the key); Pathing (guarded lazily, only while guarding); retreat/carry_bag altar-hit (price_strikes flee, else retreat_home by table cost); tribute_safe (engage idle); recall checks (tile(here)); dashes (tile worst, depth, guarded); shield/heal (one valuer at the final tile); turn_order (tile(end)).

Deleted by the end:
- bot.cpp: step_guard, open_bits, the 3 step-guard gates, camp_exit_rounds, flee_camps, retreat_step, want_home's home-no-fight-sim/home-no-pursuit gates, prey-cut-short, chase's dash/attack/reset/cast tail on searched turns, the destroy/construct ward rebuild (kept only when reobserve fails).
- self_abilities: dash_away, threats_near, Hazard, danger(), shield_wanted, shield_if_needed's bool test.
- plan.cpp: camp_at and camps[24], the duplicate shield formula, the guard OR in read_geometry, the dist-3 lethal special.
- safety.cpp: each_threat's d0 rule, the threats_at bisection, CampMemo, Foe::asked/near, damage_ceiling (kept only as lethal's early-out until W5).
- abilities.cpp: hit_worth and duplicate target loops. turn_order: the gate.

## 3. Rules for every wave

- **Interface commit first (`wN-iface`, integrator, ~15 min):** the wave's pinned headers plus stub bodies forwarding to the old code, so every builder worktree builds and smokes. Builders branch from `wN-iface`, not from wN-1. Stubs must keep the game byte-identical at 100M (check with bench.py compare before branching).
- Builders work in separate worktrees, leave out `.cambc/`, edit only owned functions. Header sections are assigned per item; the integrator resolves header merges.
- Builders build and run at most a 2-game smoke (`cambc run --map 00interlock`, then one `maps/gen/<file>.map26a`). Only the integrator runs bench.py or ab.py, one at a time.
- No new `fuel()` reads in decisions. Fixed counts are allowed. Diagnostics only inside `debug_block({ ... })`, one tag per line: TABLE-MISMATCH, VERDICT-MISMATCH, DOMINANCE-MISMATCH, PURSUIT-SKIP-MISMATCH, MEMO, SRCH, GUARD-RETRY, WANTHOME.
- Every new top-level helper gets `Phase phase{"name"}` (want_home, verdict, engage, prepare_strikes, price_strikes, retreat_home).
- Per-wave sequence (integrator):
  1. Merge builders in the listed order, build.
  2. Fuel-only commits: `bench.py compare` at 100M, byte-identical.
  3. Materialise wN to `bots/variants/wN` (no `.cambc/`), set `debug_phases = true` there, `bench.py run bots/variants/wN --fuel 0 --jobs 4 --out ...`, then `oof_phases.py`.
  4. `py tools/ab.py wN wN-1 --suites ladder,gen --threads 4` (582 games). Not with --phases (it costs ~1% fuel).
  5. Record in research/EXPERIMENTS.md and research/hyperion/CHANGES.md.
- A drop is a diagnosis task in the wave's follow-up (~30 min), not a revert.
- Time: ~100 min a wave (15 iface, 45 build, 15 integrate+bench, 20 A/B, 15-30 follow-up). W1-W4 fit in 8h; W5 stretch.

---

## Wave 1: one tile table, memoised sims (foundation)

Goal: every per-tile danger number within radius 3 comes from `Safety::tile(p)` under one unseen rule and one camp model; duplicate sims and the ward rebuild are memoised. Public Safety queries keep their signatures.

### Pinned interface (w1-iface)

```cpp
// safety.h public, W1-A
struct TileDanger {
    std::uint16_t vis_mask = 0, stun_mask = 0, unseen_mask = 0; // bit i: enemies[i]
    float vis = 0, vis_unacted = 0, unseen = 0, camp_exp = 0, camp_worst = 0;
    float worst() const { return vis + unseen + camp_worst; }
};
const TileDanger& tile(vec2 p);
float strike_sum(vec2 p, std::uint16_t* mask = nullptr); // visible Strike bound, no Reach build
int exit_rounds(vec2 p);      // rounds to leave camp_area(): any_within(standable & ~camp_area, p, r); 0 if no camp at p
float unseen_chance(vec2 p);  // 1 - prod(1 - near/tiles * hit_given_reach) over unseen_mask
// Readers kept: damage_bound, worst_damage, lethal, may_be_hit, threatened, camp_damage, threats_at.
// CampHit gains `std::int16_t group` (W2's claimed-group skip).

// safety.h public, W1-B
std::uint32_t generation() const; // bumped by invalidate() and reobserve()
bool reobserve();                 // after world.observe(): true = Safety kept
// Trade gains: bool cut = false; // set in trade() on fight-cut; never memoised
```

Stubs: tile() fills a row from the current functions; exit_rounds forwards to the camp_exit_rounds ring logic; reobserve() returns false; generation() returns a counter bumped in invalidate().

The one unseen rule: an unseen credible foe's blow at p is `Threat::at(p)` from its capped field. One `any_within(possible, origin, reach + 3)` per foe per generation; false → the foe adds nothing in the window; only otherwise build(). Outside the window the same rule is computed directly.

### Items

| id | owner | change | deletes |
|---|---|---|---|
| W1-A table | safety.cpp query section (damage_bound…threats_at, lethal), find_members (camp_memo_ reset, CampHit.group), strike_foe (asked), safety.h public table block + private `table` section + Foe/CampMemo decls | Rows with generation stamps, never cleared eagerly. Readers rewritten on tile(). exit_rounds by any_within over standable minus camp_area (no tile() reads), memo in the row. | each_threat d0 rule, Foe::asked/near, CampMemo, threats_at bisection |
| W1-B memo lifecycle | safety.cpp invalidate/refresh/gone/list_enemies, memo/fight_of/new_fight, pursuit, turns_to_kill_idle, trade() (cut flag only), act() (debug counters only); safety.h Trade, generation member/accessor, private memo members | invalidate keeps fights_ and bumps generation; no `cut` Trade stored; pursuit/idle 2-entry memo keyed (p, arg, generation). reobserve(): compare visible enemy set+positions, visible ally set, camp states with construction; unchanged → reset unseen-derived state (built_, threat_count_, threat_mask_, unseen counted_ bits, enemy_area_), listed_ = false, drop memo keys with an unseen bit, keep Reach/Strike/made_/visible-only memos, bump generation, return true. Debug `MEMO round sims hits kept idle_hits pursuit_hits` and act() branch split (quiet/plain/general). | — |
| W1-C turn start + camp consumers | bot.cpp continue_tribute, decide's ward block and shard reset, camp_trapped, camp_exit_rounds, flee_camps, retreat_step | continue_tribute takes `std::optional<bool>& home` and fills it; decide passes `home`. Ward: `if (!safety.reobserve()) { destroy_at; construct_at; }` and ALWAYS `home.reset()`. camp_trapped reads exit_rounds. flee_camps/retreat_step cost = tile(q).worst() + camp_worst × max(0, exit_rounds(q) - 1). | camp_exit_rounds |
| W1-D search pricing | plan.cpp shield_worth, Search::shield_at, read_mates heal value, plan_strikes pricing + capped fallback | camp_at/camps[24] → tile(p).camp_exp. One `shield_cap(Safety&, vec2, amount, duration)` = min(amount, duration × damage_bound(p)) in plan.h. dist-3 check → tile(p).worst() >= health. max_exact_queries counts threats_at calls and dist-3 row reads. Capped fallback computes per-striker share once per tile. | camp_at, camps[24], duplicate shield formula |

Merge order: B (bench byte-identical), C's tribute+ward commit (byte-identical), A, C's camp commit, D.
A/B: `ab.py w1 w0`. Bench `--fuel 0`: OOF total, oof_phases split for want_home and step_guard.
Verify: TABLE-MISMATCH (bound, lethal, threatened, threats_at) on the bench, expect only unseen-rule flips; `WANTHOME round n` ≤ 1 per turn; SRCH-EXH and SRCH-DOM stay 0 on 00packs, gen shared-gems, gen huge.
On a drop below ~47%: TABLE-MISMATCH per losing map (lethal/threatened flips first, then retreat_step's lower unseen bound); camp deaths ≈ 1 per 16 games.

---

## Wave 2: one fight engine and one verdict (step_guard moves into Safety)

Goal: "Can I end on q?" has one lazy answer, guarded(q). All sims go through engage() with the per-mode rule table. The eager step_guard is deleted.

### Pinned interface (w2-iface)

```cpp
// safety.h, W2-A
struct Engage {
    enum class Mode : std::uint8_t { stand, pursue, idle };
    Mode mode = Mode::stand;
    int approach = 0;          // pursue/idle
    int horizon = fight_horizon;
    int with_enemy = -1;       // always in the key (prey); never no_fight
};
Trade engage(vec2 p, Engage e);
int idle_turns(vec2 p, int horizon);
void set_claimed(int group);  // camp group our farm/siege budgets; skipped in stand/pursue camp charge
struct Verdict { bool lost = false, falls = false; };
Verdict verdict(vec2 q);
bool guarded(vec2 q);          // false if no visible foe reaches q (strike_sum) or q no worse than here (mask ⊆, damage ≤);
                               // else v.lost || (v.falls && (linked || tile(q).worst() >= health)). Radius 3 only.
const bitboard* guarded_board();
std::uint32_t guard_stamp() const; // generation << 8 | guarded count (KeptRoute key)
// fight/pursuit/turns_to_kill_idle stay as wrappers until W4.

// pathing.h, W2-B
void set_safety(Safety* s);    // play_turn: &safety at start, nullptr at end
Safety* safety() const;
void set_guarding(bool on);    // replaces set_guard; per-tile tests: guarding_ && safety_ && safety_->guarded(p)
bool guarding() const;
// set_guard(nullptr) stays as an alias of set_guarding(false) until W2-D lands.
```

Stubs: engage forwards to fight/pursuit/turns_to_kill_idle; verdict = fight(q); guarded = today's per-tile rule on fight(); guarded_board = nullptr; set_guarding(true) keeps calling step_guard internally via a callback set by decide.

FightKey (private, W2-A): {who uint32, arrive 3 bits/enemy uint64, camp_q = round(camp charge/8) clamped uint16, camp_turns uint8, mode uint8, horizon uint8}. 48 slots, survives invalidate (no cut entries). Dominance only between stand keys with equal camp_q and camp_turns: a won key settles ⊆ enemies ⊇ allies; a lost key the reverse. reobserve (W2-A now owns its memo rule) drops every key with an unseen bit, all modes.

Camp cap: Side gains `camp_until` (their-turn index); sim core camp terms (play_quiet, outlives, overwhelmed, simulate) charge min(theirs, camp_until - them.turn) × camp. W2-A owns those four sites.

### Items

| id | owner | change | deletes |
|---|---|---|---|
| W2-A engine + verdict | safety.cpp fight API (fight_key*, memo, fight, fight_of, new_fight, pursuit, turns_to_kill_idle, cost estimates), sim-core camp terms only, reobserve memo rule, new verdict section; safety.h block above | engage per rule table; FightKey; dominance (covers list moves from step_guard, per generation); verdict/guarded/guarded_board; claimed-group skip from CampHit.group. Debug: `VERDICT round asked sims memo dom`, DOMINANCE-MISMATCH (re-sim dominated keys) must be 0. | separate pursuit/idle Side assembly (wrappers stay) |
| W2-B Pathing | pathing.cpp/.h guard_ sites (neighbour scans, route, try_move, dash_landings), step_towards/make_way attempt loop | Per-tile sites ask guarded() while guarding. route ORs guarded_board(). The guarded() check of chosen first steps and retry lives in step_towards' attempt loop, one shared cap of 8 (if all first steps guarded: route once without guard). dash_landings filters per tile. Debug GUARD-RETRY, assert no guarded end tile. | set_guard/guard() |
| W2-C search | plan.cpp read_geometry, plan_strikes accept step + capped fallback, plan execution (step "act") | Stop ORing the guard into blocked. At `total > best_total` for dist 1..3 skip p if guarded(p) (replaces dist-3 lethal). Capped fallback asks guarded() only for a tile about to be chosen. Execution runs with guarding off (RAII flip), since intermediate tiles are never stood on between turns. Leaves judged on the turn-start key. Debug `SRCH-GUARD round asked skipped`. | guard OR, dist-3 lethal |
| W2-D bot.cpp | step_guard, open_bits, want_home, prey, play_turn (set_safety, set_claimed), all 4 set_guard sites (decide, act, stop_game_ender, carry_bag) and want_home calls in continue_* | Delete step_guard/open_bits/gates. play_turn: set_safety(&safety), set_claimed(memory.claim), set_safety(nullptr) at end; ward rebuild re-calls set_claimed. decide: set_guarding(true) after the leave branch; others set_guarding(false). want_home: s = engage(here); home if (worst ≥ health && s.self_falls) or (visible_threat && s.lost); skip pursue only if !s.lost && !s.self_falls and every pursue enemy is in s's key (debug PURSUIT-SKIP-MISMATCH re-runs pursue); else pursue as today. prey: attack tile = open tile within range of e nearest us; verdict through engage(tile, {with_enemy = e}); fixed cap 3 sims. Debug WANTHOME-PURSUIT-SKIPPED, PREY-FLIP. | step_guard, open_bits, step-guard gates, home-no-fight-sim, home-no-pursuit, prey-cut-short |

Merge order: A, B, C, D.
Gate before A/B: bench `--fuel 0` OOF ≤ W1's; oof_phases shows step_guard gone (EXPERIMENTS.md:189: dropping gates without cutting cost raised OOF 8 → 100-200).
A/B: `ab.py w2 w1`.
On a drop: deaths within 2 rounds of stepping onto a tile (w1 vs w2 replays); VERDICT-MISMATCH by cause (camp, unseen, other); if camp-in-stand dominates, diagnostic A/B with stand camp charge 0; retreat counts (D-line R); PREY-FLIP.

---

## Wave 3: one search per turn (retreat and chase are modes)

Goal: one read+grow per turn; retreat (4a) and chase (4b) are pricing modes over the table. flee_camps, retreat_step, dash_away, threats_near, danger() deleted.

### Pinned interface (w3-iface)

```cpp
// plan.h, W3-A
struct Intent {
    bool walks = false, anchored = false, to_altar = false;
    int group = -1;
    float step_value = 0;
    bool flee = false;   // weights: visible 1.0, unseen hit_given_reach, camp_worst × max(0, exit_rounds(p) - 1) on top of the hit at p,
                         // death (life_value + bag) when tile(p).worst() >= health; no guarded() ban
    const cambc::distance_field* field = nullptr;
};
struct Prepared;
Prepared* prepare_strikes(const World&, Pathing&, Safety&, const Intent&);
Planned price_strikes(Prepared&, const Intent&); // second call only if the first returned !acted
Planned plan_strikes(const World&, Pathing&, Safety&, const Intent&);

// pathing.h, W3-C: route_field + KeptRoute from p4b; KeptRoute keyed on safety()->guard_stamp(), not a pointer.
// self_abilities.h, W3-C: dash signatures unchanged (Safety read through pathing.safety()), except
bool dash_to_attack(const World&, Pathing&, const ChampionBelief& target);
```

Stubs: prepare stores the intent; price calls plan_strikes; route_field ported in the iface commit (small); chase's call changed to `*target` in the iface.

### Items

| id | owner | change | deletes |
|---|---|---|---|
| W3-A search modes | plan.cpp/plan.h except strike_after and valued | Split prepare/price; port Pend groups and flee pricing from 80924f3 onto tile()/exit_rounds (4a's camp_at/camp_worst/dies and unseen_near loop replaced). guarded() end-tile ban in normal and chase only. Fixed caps: Pend ≤ 16, exact queries ≤ 10 incl. table/verdict reads. Debug `SRCH mode fuel`. | 4a's private camp/unseen code |
| W3-B bot.cpp flow | retreat, carry_bag, chase, decide strikes block, flee_camps, retreat_step, dash_away callers, step_safely | Port flee(), retreat_home(), note_search() from p4b. retreat: strike_possible or camp at here → price_strikes(prepare(flee)) with escape_step_value; else retreat_home by table cost (worst + camp_worst × max(0, exit_rounds - 1)), then home steps, then gap. Retreat and carry_bag altar-hit stay unguarded (set_guarding(false)). decide keeps Prepared*; chase reprices with prey's route field and farm_step_value when the first price neither acted nor was goal_free, and drops its dash/attack/reset/cast tail then. Retreat's cast_at_enemies deleted on search turns. Deletes dash_away together with its callers. | flee_camps, retreat_step, dash_away |
| W3-C dashes + pathing | self_abilities.cpp threats_near…dash_to_attack incl. travel_dash/ranked; pathing route_field/KeptRoute | Dashes read pathing.safety(). Landings: skip guarded() only while guarding; rank (tile worst, depth, home steps), depth = Σ (strike reach − dist + 1) over vis_mask + 2 per camp member in reach (local helper); escape dashes need strictly lower (worst, depth); dash_across compares vis + unseen only; travel_dash keep test worst(p) ≤ worst(here) && !wakes_camp. | threats_near, Hazard, danger() |

Merge order: A, C, B.
Gate before A/B (mandatory): at 100M retreat search mean < 12k, p99 < 40k; at `--fuel 0` OOF ≤ W2 + 10%. Fail → fixed caps (Pend expansion, priced tiles), no fuel reads.
A/B: `ab.py w3 w2`. On a drop: rerun at 100M; level at 100M → fuel, profile flee pricing by Phase; else split losses into retreat, chase, camp deaths (camp deaths ≤ 1 per 16 bench games).

---

## Wave 4: remaining readers and duplicate valuers

### Pinned interface (w4-iface)
- `shield_cap` (W1-D) is the only shield value.
- `struct Valued { int round; vec2 at; bool any; int slot = -1; int target = -1; vec2 ground{-1,-1}; };` (W4-B).
- `bool reset_and_attack_enemy(const World&, bool stunning_only = false, Safety* safety = nullptr);` null keeps today's shield_wanted rule.

| id | owner | change | deletes |
|---|---|---|---|
| W4-A shield/heal once | self_abilities shield_if_needed, shield_wanted, heal_ally, reset_and_attack_enemy; decide's pre/post-search heal/shield calls, act end; every reset_and_attack_enemy caller line (chase, stop_game_ender, retreat, decide) | One shield/heal call at act end at the final tile unless the search priced it there. Cast when shield_cap ≥ smallest real hit in tile(p), plus members in reach of groups we hit this turn (farmed group, or !my_can_attack()). Reset hold reads tile(here).vis_mask via the Safety* param. heal_ally once. | shield_wanted, shield_if_needed bool test |
| W4-B search owns casts | abilities.cpp enemy_cast/cast_at_enemies, hit_worth; plan.cpp valued + strike_after; cast_at_enemies call lines (mend, retreat, chase) | Search stores its start-tile cast in Valued; strike_after executes it. cast_at_enemies only on non-search turns. Shared target loop ORs add_unseen Ren tiles (retaliation ≥ health) into ground "off". Debug count wasted cast_at_enemies = 0. | abilities hit_worth, duplicate target loops |
| W4-C recall/tribute/turn order | tribute_safe, submit_here, continue_recall, recall_to_bank, capture_recall, wants_shop, siege_heal_trip, recall_outruns; turn_order offers + gate | tribute_safe → idle_turns (memoised). threatened() callers share one row read. recall_outruns keeps dist(here, e.pos) − reach for unseen (capped field cannot see 4-8 away). offer_escape/offer_channel read tile(self.pos), double_unacted from vis_unacted. | turn-order gate |

A/B: `ab.py w4 w3`. On a drop: recall cancels by damage, shield timing, tribute starts per game.

---

## Wave 5 (stretch)

- W5-A (safety.cpp sim core): only if W1-B's act-branch counters show the general path dominant. Event-driven quiet jumps; FIGHT-EXIT-MISMATCH clean, flips ≈ 0.
- W5-B (bot.cpp pack zone, outmatched): outmatched only when the here verdict is not won; pack zone stays a carrier's routing no-go. Own A/B.
- W5-C (safety.cpp enemy_area/avoid; docs): avoid uses guarded and rows within 3, fields beyond; delete the square model. Update STRIKE-SEARCH.md, FUEL-GATES.md, CHANGES.md.
- A/B w5 vs w4, then cumulative w5 vs w0 plus a fresh-seed suite (`mapgen.mjs suite --out DIR --seed S`, `--maps-dir DIR`).

## Risks

1. Fuel: W3 repeats 4a's OOF +135% unless W1-W2 save 15k+ on big turns. W3 gate mandatory.
2. Camps in stand/pursue (capped by exit_rounds, claimed group skipped) shift guard verdicts and want_home; exit_rounds near Monolith (reach 5) is the sensitive case.
3. Lazy guard: routes no longer bend around unasked radius-2 tiles; up to 8 retries per walk turn; a won multi-enemy turn may run 2-3 sims without the union key.
4. Stale state: rows and memos must follow generation (invalidate, refresh-with-change, reobserve); home is always reset after a ward.
5. Merge conflicts in bot.cpp and safety.h: iface commits pin signatures; builders stay inside owned functions; integrator resolves headers.
