# Round 1's farm evaluation and the draft (2026-10-26, astraeus)

Round 1's farm evaluation loop was the biggest round-1 cost after first-turn pass 3: 46.2k mean, 129k max, on the
wide bench (26 maps, test drafts, both sides, 241 champion instances). This pass asked whether the draft can carry
what makes it cheap or exact. It cannot carry the result exactly (below), so the loop now visits the draft's guesses
first and prunes with bounds that are valid in any visiting order, which makes the guesses fuel-only. Plan v7 adds
two small sections: each body's leads and a dasher's steps from its spawn tile.

Baseline: main at ca1139bd (CHANGES 161), frozen as `bots/variants/astraeus-m161`. Bench:
`tools/fuel/bench.py run <bot> --set wide --test-draft --per-map --jobs 7`, at 100M and at the real budget
(`--fuel 0`). Profiles: first-turn.md's profiler (laps, a `MAND` line per instance); the loop's parts with laps of two
`fuel()` reads. **52/52 replays identical at 100M**; play turns after round 1 +0.01% in total.

## What round 1's evaluation depends on

For one body (`farm`, bot.cpp), in round 1:

| Input | Source | Known to the draft |
|---|---|---|
| Strength (floored output), Ren's reflection, spare health, range, spell and basic output | the type, base stats, full health, no items | at the write of the body's pick |
| Gold rate (Vesper Vale), gold-farmer weight (Cassi), Marcella's tribute gold | the type | same |
| `per_gold` | `prices(world)`: `best_emblem` over the upkeep model, the main stat, and the gems share (1000 over the bodies alive) | only by running the champion's World; it varied 0.09-1.46 by type and map |
| Our tile | team A's bodies fill its spawn row by row from the bottom left; team B's take the mirror tiles of A's (seen on every bench instance) | yes |
| Steps to each group | the plan's walking steps from that tile; a dasher on a map with crossable tiles (and no `dash_spawn_steps`) builds a dash field from its tile (55 of 241 instances) | yes (the field is the draft's to compute) |
| Group facts, clears | static, every camp asleep at full health | yes, per type |
| Camp state | as above, unless a champion acting earlier in round 1 hit a camp in our sight | no |
| Allies' claims | earlier bodies' round-1 choices, posted at their turn end (lost if they ran out of fuel) | only as a guess |
| Unclaimed partner | the strongest ally in sight within 12 with no claim: the later bodies, so the whole composition | at the last write |
| Allies' positions | earlier bodies' round-1 moves: crew work, `struggling`, `ally_engaged` | no |
| Enemies | nothing in the loop; they only decide whether `decide` gets to farm (the strike search) and can hit a camp first | n/a |
| Turn order | which allies have acted (claims, moves); team A or B only through enemy actions before us | yes |
| Fuel | the loop's gate (`farm-partial-evaluation`), the field-from-here gate, earlier allies finishing | no |

What each write knows: round r's write comes before pick r, but the draft knows pick r (the first available in its
order) and the enemy's picks of rounds before r. The last write therefore knows our whole team but not the enemy's
last pick, which the loop does not read. Only round 0 has 10M fuel; later rounds have 100k, of which the draft used
~2k before this pass.

**Exact carrying (candidate a) does not fit.** The loop's per-group facts are floats (fastest clear, camp damage,
clear rounds, spell clear): 4 x 32 bits a group a body, 3-6 KB for 40 groups and 5 bodies against ~800 free bytes.
The final choice, or the set of groups that change the loop's state (median 3-4 a body, measured), depends on
`per_gold`, on allies' claims that are posted only if their turn ends, and on allies' positions after their first
move. The draft cannot reproduce those, and the champion cannot check them for less than the work saved.

**Ordering (candidate b) can be exact.** Every prune skips only a group whose value is strictly below the best so
far, by bounds that hold whatever the visiting order (below). The choice is then the best value, ties to the earlier
group in the usual order; with the leads visited first, acceptance breaks ties by that order (`earlier`). So the
leads change only fuel. A stress copy that visited two arbitrary groups first was also 52/52 identical.

## What was built

1. **Leads (draft).** For each body of the team the draft expects (picks so far, this round's, then the rest of its
   order; Cassi and Issac as two bodies), a cheaper copy of farm's round-1 valuation from the body's spawn tile:
   clear alone (spells kiting where farm would), a clear too costly alone shared with the strongest later body, gold
   at 0.2 a gem (x the type's gold rate, x4 for Cassi), rated as farm rates. Each body's two best, past every earlier
   body's first lead (its likely claim). Per-type facts are made in round 0; each later write remakes the leads only
   if the expected team changed.
2. **Leads first (champion).** On the first turn the loop visits the body's leads, then the usual order without
   them. Not for Ren or in a pocket (below).
3. **Rated bounds.** `value = rate(worth, cycle)` falls with the cycle, and no clear is quicker than the fastest:
   `rate(gems + gold, trip + capture + fastest)` bounds the value, and with an unclaimed partner `rate(worth x part,
   trip + capture + fastest x part)` bounds a shared clear. The bound uses the Chebyshev distance before the steps
   are read (a walk, a dash path or a crystal hop is never shorter; a recall out of a pocket can be, so not there),
   with a 1e-4 slack for float rounding. Ren's reflection clears faster than its output, so Ren keeps the old
   bounds. Where pruned:
   - before the steps, when no centre field gives them (every turn; it saves the drafted step lookup);
   - first turn only, before the group's facts (`unweighed_beaten`: empty-handed and short of the win no altar
     walk is in the trip, and the weight is at most 1) and after the steps in place of the plain bound.
4. **Beyond spare (first turn).** A live group that no spell kites (an attacker reaches 4, or no spells), whose
   attackers each strike at least until their own kill (`sum strength x (ceil(hp / output) - 1)`), alone and with
   the partner, for more than the spare health, and with no ally on its threat tiles, can only be risky: skipped
   once a best exists. 78% of the groups the rated bound left were such groups.
5. **Dash steps (draft).** For each expected body with a dash, on maps where a dash's steps differ from walking's,
   the steps of its dash (`dash_walls`, or `landing_dash_walls` for Heart of Ruin) from its spawn tile to every
   group. The champion decodes its entry on first ask in place of building a field from its tile; on a small map
   (`150 x groups` at least the field's estimate) it keeps the field.
6. **Two copies of farm.** `farm_turn<opening>`: the first-turn prunes and leads compiled into the first turn's copy
   only. With them in the one loop behind runtime flags, every farm call after round 1 was ~0.4% dearer (~19 fuel
   a group checked); the caches farm keeps across turns moved to `FarmMemo`, one set for both copies.

### Plan v7 layout

`PlanHeader` is 80 bits: v6's 79 with `schedule_at` renamed `leads_at` (13 bits) and one flag, `dash_steps`.

| Section | Where | Bits |
|---|---|---|
| Leads | `leads_at`, where the attack tiles end | 6 bodies x 2 leads x `bit_width(groups)`: 0 none, else group + 1 (72 bits at 40 groups, 96 at 255) |
| Dash steps (with `dash_steps`) | after the leads | per body: kind 2 (0: none); with a kind, spawn tile 4, Rice parameter 3, codes' length 13, then per group a Rice code, 0 unreachable, else steps + 1 less their Chebyshev distance |
| Wards | `wards_at`, after the dash steps (else the leads) | as v6 |

The leads are rewritten at every draft write, the dash steps written once. A champion uses an entry only for its
own index, kind and tile. Both sections are placed only once the attack tiles are done and only if the whole ward
section still fits after them (merge review): a ward site cut from the plan changes play (`ward_planned` falls back to
`ward_bushes`), where the leads and dash steps change only fuel.

Bytes on the wide bench (last write; "free" is what the ward section leaves):

| | leads | dash steps | free |
|---|---:|---:|---:|
| 26 wide-bench maps | 4.5-10.5 | 0 on 16 maps; 8-49 on the 10 with a dasher whose dash steps differ from walking (ambush 23.5, pilgrimage 48.8, dense-camps 35.4) | 747-984 |
| gen-dense-camps-120105502 (98 groups, 3 dashers) | 10.5 | 235.4 | 82 |
| gen-tiny-groups-120105300 (80 groups) | 10.5 | 46.5 | 610 |

### Draft fuel

Round 0: 1.61M -> 1.73M mean (+117k: per-type facts, the leads and up to one field per dasher; +27k to +294k by
map, max 3.23M of the 10M). Later draft turns: 1.7k -> 7.0k mean, 8.2k max (the expected team and rewriting the
leads), far inside their 100k with `draft_reserve` (40k) untouched; a later write remakes leads with half the
reserve kept.

## Results

| | before (m161) | after |
|---|---:|---:|
| Mandatory round-1 work at 100M (profiled): mean / p50 / p90 / max | 188.5k / 186.7k / 249.1k / 300.8k | 173.6k / 169.8k / 226.4k / 302.5k |
| Mandatory work over 200k, of 241 | 93 | 56 |
| Farm loop at 100M (profiled): mean / max | 46.2k / 129.4k | 28.1k / 112.7k |
| camp damage + spell clears in it | 14.4k | 5.5k |
| field from here | 1.7k (55 instances, max 27k) | 0.2k (15, max 3.8k) |
| Round 1 at 100M, mean (warm-up included) | 513.8k | 500.1k |
| Play turns after round 1 at 100M, total | | +0.01% |
| Round 1, real budget: mean / p50 / p90 | 193.0k / 192.9k / 199.7k | 192.5k / 192.8k / 199.3k |
| Round-1 turns at 200000 (ran out), of 241 | 21 | 20 |
| Round-1 turns that ran out in `decide` | 21 | 18 |
| Round-1 turns whose `decide` finished (`D 1` line) | 222 | 224 |
| Round-1 `farm-partial-evaluation`, real budget | 81 | 51 |

The heaviest maps (gen-dense-camps-120105500/502, gen-tiny-groups-120105300/302; 8 games, 34 instances, 8/8
identical at 100M): mandatory work 322.7k -> 303.1k mean, farm loop 81.4k -> 54.5k, field from here 4.9k -> 0. Their
round 1 is far past 200k either way (27 of 34 instances), and at the real budget 22 and 23 of the 34 ran out.

Leads: 197 of the 241 bodies had leads to use (not Ren, 35; a few bodies with no affordable group). The first lead
was the loop's choice for 146 of them (74%), the second for 9 more. Per loop, groups whose steps were read went from
22.7 to 8.8 a body and full clears from 10.8 to 4.7 (lead traces, before the beyond-spare prune).

### At the real budget

The freed fuel mostly goes to round-1 work that was gated before: `farm-partial-evaluation` 81 -> 51,
`ward-no-bushes-fuel` 84 -> 53, `turn-order` 54 -> 31, `farm-no-route` 23 -> 17, `crow-flies-farm` 20 -> 14. The
turns that still run out are where the mandatory work is still over 200k (56 at 100M, from 93: lanes 10, the
68-group hourglass 10, boss-battle 7, classic 5, ambush and expanse 4 each; by type Ren 18, Heart of Ruin 13, Issac
9), so the count falls only from 21 to 18. Games diverge at this budget, so play-turn out-of-fuel counts (597 -> 651) are not comparable.

## What did not work

- **Rated bound after the steps on every turn:** +0.7% on play turns. Later loops start from last turn's choice and
  the plain bound already prunes most groups; the rated one costs two `rate` calls.
- **Runtime flags for the first-turn prunes in the shared loop:** +0.4-0.5% on play turns (~19 fuel a group
  checked, the conditions' instructions). Out-of-line helpers did not help (+0.37%), nor marking the bound
  `noinline` (+0.53%: its captures become memory), nor two copies of the loop inside one farm (+0.41%). Two farm
  functions with shared caches: +0.01%.
- **Dash steps read through the plan per lookup:** ~350 fuel a lookup (skipping Rice codes past a parameter above 0
  is ~50 a code, O(groups^2) a turn); decoded once per body, and kept off small maps where the field is cheaper.
- **Leads alone** (no rated bounds) saved little: the plain bound `W / (trip + capture + fastest)` prunes 57% of
  the non-best groups even with the true best first; the rated one 85%.
- **The S-set (only the groups that change the loop's state, median 3-4) with a hash of the loop's inputs:** the
  draft would have to reproduce `per_gold` (a World), allies' moves and posted claims; not built.

## Left

- The first-turn loop still evaluates claimed groups in full (1.5 a body): their value has no cheap bound before
  the steps (the crew's share depends on the allies' arrival).
- Ren keeps the plain bounds (reflection): its loop is the dearest left (60-75k on many-group maps).
- A group pruned before its facts still costs ~330 (the rated check, its fastest clear and the loop's
  bookkeeping): 11-12k on 35 groups. Facts ~265 and steps ~350 for those that pass.

## Merge review (2026-10-26)

Merged onto main ea5c1302 (CHANGES 162) as CHANGES 163. The bound was rechecked against every value the loop computes:
`rate` is non-increasing in the rounds; clears alone (`min_camp_damage` sums `ceil(hp / output)`), kiting
(`spell_clear_rounds` is at least the health over basic plus spell output, which `output` covers) and shared
(`min_camp_damage` at the joint output) are never under the fastest clear; `home_ground` is at most 1; every steps
source is at least the Chebyshev distance (centre fields and fields from here walk; drafted spawn steps decode only
when exact; dash steps are coded as the excess over it). The exception is a crystal hop (its nearest source and
landing need not pair), safe only because group hops are made after every centre field, so the pre-steps prune never
sees one; noted in the code. Every prune is strict, and each acceptance (best, risky, shared, help) breaks ties by
`earlier`. Fixes: the ward-section guard above, and no leads past 256 groups (the visiting order is bytes, as
`nearest_groups`'s, which returns none there). Checks: wide bench 52/52 identical (round 1 -2.7%, play turns +0.01%);
12 unbenched gen-s1 maps 24/24; a copy visiting every group in reverse order on round 1 52/52; leads remade in full on
every later draft turn (forced) on gen-dense-camps-120105502 and gen-tiny-groups-120105300 still picked with 52-54k
left.
