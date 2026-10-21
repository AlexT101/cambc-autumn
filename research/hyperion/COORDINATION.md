# hyperion: coordination (workstream D)

How allies combine, and which group rules can be derived instead of named. Code refs are `bots/hyperion/src` at main
07c414f. Data: the 360 distinct v32 ladder games (245 won, 68%); scripts and tables in
`replays/orch/research/ddata_*.py` and `ddata_agg.txt`. Reviewed adversarially before queueing (section at the end).

## Answer in short

- **The biggest coordination loss is one sealed altar, not outnumbered fights.** On 01boss-battle we went 0/15 and
  tributed 0 gems in every game; 8 of the 15 ended 0-0 and were lost on gold, so any banked bag wins those.
- **Tie-breaks are already right.** `pick_up`, `capture_taken` and `turn_order.cpp:side_damage` use "nearest ally
  I see takes it, ties to the lower index", so allies who see the same scene agree. Keep them.
- **Several ally rules use a fixed radius as a stand-in for arrival time** (fights 4, pack 5, help 8 steps, partner
  12). Farm's crew value is the opposite error: every claimer counts as already hitting, however far away.
- **Head count is a weak lever.** Initiative moves fight outcomes more than numbers (table below), so more exact
  ally counting in fights is expected to be level. Only the farm-side version is queued.

## Findings

**Deaths and bags.** 2,278 deaths (6.3 a game) lost 26,629 carried gems. 72% of deaths carried nothing.
00contest (9,000) and 01boss-battle (8,769) account for 67% of the gems lost.

**01boss-battle: 0/15.** The only tile in tribute range of the only altar is a Monolith camp tile, (24, 20)
(CHANGES 27). Camps block walking, so nothing can bank until that member dies, and its tile then stays in the other
Monolith's reach (5, 200 a phase). In 8 games it was 0-0 at round 2000; in 7 the opponent killed the pair
(r1023-1890). 145 of our 397 deaths with a bag of 20+ were on this map. CHANGES 27 (sieging the key member, all
bags held back until it fell) went 2/2 against the pre-change bot but 1/2 against v31 and was reverted: the 400-875
bags it had held back could not bank under the second Monolith's fire, while v31 banked 19-49 bags there.

**Carrier deaths elsewhere (bag 20+, boss-battle excluded): 252 deaths, 16,084 gems.** A champion killed 216 of
them, camps 36 (1,002 gems). In 95% of the 216 the killer was within 4 at the start of the death round and in 91%
it had been seen in the previous 10 rounds. At the first hit of the run-up, 74 had no ally within 8, 30 were
outnumbered and 112 even or better (all units within 8). So most carrier deaths happen with allies nearby: this is
a cost for Workstream A's search (bag and life in a seen enemy's reach), not missing allies. (Hp at the start of the
death round, ≤50% in 89%, says little; at the first hit it was ≤50% in 42%, and 35% died in the round of the first
hit.)

**Fights (15,584 engagements; "present" = within 8 of the first hit; won = of fights with a kill):**

| | we initiated | they initiated |
|---|---|---|
| we were outnumbered | +4.7 swing a fight, won 69% | −3.1, won 40% |
| we outnumbered them | +9.0, won 83% | −0.5, won 55% |

Matches EXPERIMENTS "General": with HP fraction, gold and initiative in, head count adds little. Initiative is a
choice made from position, so this is correlation, not a lever by itself.

**Ambushes are minor.** In 11% of champion kills the first attacker was unseen for the 5 rounds before the first
hit (55% of those from a bush); 72% of killers were seen 6+ rounds earlier.

**Code facts checked.** The rally bit (`comms.cpp` `sight_fight`, bit 31) is read only by `send` to protect the slot;
the rally's only effect is that the enemy we fight takes the sighting slot over the rotation. `partner_output`
requires `a.visible`, and an ally is visible only within our vision (8) or ward (6), so `rally_radius` 12 binds only
for ward-seen allies.

## Proposals, ranked

### 1. Open a sealed altar (M)

- **Change.** Start from ff50c99 (CHANGES 27, reverted in ef452e3) and fix the two causes of its loss:
  - *Bags.* Hold a bag back only while no altar is usable for it: a tile within 1 of it reachable on foot with live
    camps as walls, where `camp_damage` over `tribute_turns(b)` stays below the carrier's health (`tribute_safe`'s
    test). Once the key falls, bags small enough to survive the covering Monolith's fire bank at once, as v31's did;
    larger bags keep farming until the cover is gone too.
  - *Siege set.* The siege candidate is every live member that blocks every walk to an access tile *or* whose reach
    covers it, not only the key; all of it is cleared, key first. Same Monolith-only siege limits.
- **Rests on.** Rules `map.occupancy`, `camps.attack`, `gems.tribute`; replays: 0/15 on the ladder, ladder teams that
  score there kill both Monoliths and hold the tile.
- **General?** Yes: derived from occupancy and reach, it fires on any map whose every altar is sealed, and on no
  other. No generated map has one, so gen results are fuel noise.
- **A/B.** boss-battle both sides against hecate-v8 and against v31 (the version that beat 27); then ladder +
  gen must be level. The ladder is the real judge (4% of ladder games are this map).

### 2. Delete the rally (S)

- Remove `comms::post_rally`, `State::fighting`, `sight_fight` and chase's call (bot.cpp ~2221). Sightings then
  rotate as on any other turn. Following a rally was level (50.0%) and nothing reads the bit. Bundle it with TODO's
  other removals; keep if level. STRIKE-SEARCH 4b's "the rally post stays" becomes "goes".

### 3. Crew output from each claimer's arrival (M)

- **Change, farm only, no comms.** In `farm`'s claimed branch, `health_left = H − others × working` becomes
  `H − Σ out_i × max(0, working − eta_i)`, where `eta_i` for a visible claimer is the group's centre field at its
  tile (`GroupFacts::centre`, one lookup) and 0 for an unseen one (today's assumption). `rounds` is then solved
  piecewise over the ≤4 arrivals. The same arrival replaces two constants:
  - `help_radius`: help a `struggling` ally when our steps are fewer than the rounds until it would breach its
    recall line (its `min_camp_damage` clear, scaled to that line), not when steps ≤ 8;
  - `rally_radius`: a visible unclaimed partner joins from its own arrival in the joint-clear value; delete the
    radius (vision bounds it).
- **Screen first.** Before the A/B, count in a `debug_block` over 6 games how often the chosen group changes. If it
  is under ~1% of farm turns, park it as a level cleanup.
- **EXPERIMENTS.** Pooled crew health (−3), capture-round crews (48.0%), earlier-index crews (44.5% gen) and one
  champion per camp (38-45%) lost. This keeps the crew rule and first-claimer ownership and changes only when a
  walking claimer's output starts. It does not touch corridors' flips, which come from claims arriving a turn late.
- **A/B.** ladder + gen ≥ 47%; deaths with no ally within 6 not up.

## Not queued

- **Fight allies by arrival turn** (`fighting_allies`, `pack_boxes`). "Symmetric fight arrivals" lost on nemesis,
  ally assist was level, the table above predicts level, and it adds simulation work on fight turns, where fuel runs
  out. The draft also measured arrival to striking reach of our tile rather than of the enemies. Hand it to
  STRIKE-SEARCH phase 5 (one danger model) as an input, not a separate change.
- **Siege commit and `kite` folded into the crew clear (old 2b).** Large, and both are on TODO's don't-remove list
  with evidence (gen-monolith-only 9/24 -> 17/24). Revisit only after 3 is measured.
- **Arrival times in comms** (3 bits beside the claim). Only needed if the screen in 3 shows unseen walking claimers
  matter.

## Review (D-critic)

Spot-checked against `ddata_deaths.pkl`, `ddata_carry.pkl` and main: 0/15 on boss-battle, 145/397 and 252/16,084
carriers, 216 champion kills, 74 with no ally within 8, 95% killer within 4, 91% seen, and the initiative table
all reproduce; the rally's single reader and the radii are as stated. Corrected: the outnumbered/even
split (30/112, not 72/76) and the hp claim (a death-round measure, near tautological). Cut from the queue: fight
arrivals (lost before, predicted level, fuel), 2b (don't-remove items), the comms bits (replaced by visible-only
arrival).
