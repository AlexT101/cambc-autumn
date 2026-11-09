# G3b: peeling for a teammate whose retreat is lost (notes, 2026-11-08)

Copy: `bots/variants/cl2-peel` (from `variants/cl2-belief` = oc-cl2-base + the belief fix). Reference for every A/B:
`variants/oc-cl2-base`, `--no-test-draft`, suite `maps/suites/merged/cl2-dev`, fast runner.

## 1. Measurement (1,000 kept games of the cl2-belief-v1 A/B, both sides ~ the base)

Script: session scratchpad `g3b/peel.py` (flee.py's episodes: a champion under 50% health steps homeward with an
enemy within 5; at most one per champion per 15 rounds; outcome within 20 rounds). "Healthy ally": the nearest other
teammate at 60%+ health within 8 of the fleer at the episode's start. "Pursuers": enemies within 5 of the fleer then.
"Engaged": the ally damaged (attack or cast) or unit-cast at a pursuer within 5 rounds. Behaviour over 3 rounds
otherwise: fled (its spawn distance fell by 2+), followed (closer to the pursuers or the fleer), stayed.
"Reach": the ally within its attack range + 1 of a pursuer in some round of the first 4.

| | a side-game | caught |
|---|---|---|
| flee episodes | 11.9 | 27% |
| healthy ally within 8 / none | 9.1 / 2.8 | 23% / 39% |
| caught fleers | 3.20 | |
| ... with a healthy ally within 8 (66%; within 6: 59%) | 2.10 | |
| ... ally engaged a pursuer | 0.79 | |
| ... ally did not: stayed 0.44, followed 0.40, fled 0.34, died 0.16 | 1.31 | |
| ... not engaging, but the pursuer within its range + 1 (strict peel chance) | **0.30** | |
| ... not engaging, could walk into range before the fleer died (gap - 1 <= rounds left) | **0.81** | |

Of those 0.81: 46% of the allies carried gems, 18% were hitting camps, 13% were the fleer's own Cassi/Issac partner;
types Issac 21%, Cassi 20%, Vesper 17%, Willow 11%, Prism 8%, HoR 8%. Fleer 16+ steps from home in 54%.
Gap at the start (ally to nearest pursuer, less its range), not engaging: mostly 1-5 tiles.

Engaged vs not, where a peel was possible (healthy ally within 8, gap at the start <= 3, fleer alive 2 rounds later,
not the linked partner), stratified by enemies within 5 of the fleer (1/2/3+), gap (<=1 / 2-3) and ally carrying:
engaged by +2 rounds 14.1% caught against 17.7% not engaged within +5 (standardised over the strata).
Selection bias: the ally engages when its own fight model says it wins (prey's won fights, the strike search's
plans), and an ally with the pursuer already in range engages more; stratifying removes the enemy count, the gap and
the bag, not the fight model. So 3.6 points is an upper bound on what engaging does for the fleer; reverse
causation (fleer dying fast leaves no time to engage) is handled by requiring the fleer alive at +2.

Reading: peel chances in reach are rare (0.30 a side-game, under the brief's 0.5), but chances a walk of 1-5 tiles
opens are 0.81. Even an effect at the upper bound (3.6 points of catch rate over ~2.2 opportunity episodes a
side-game, caught or not) saves ~0.08 lives a side-game: a small lever, +1 point at best. Worth one targeted try.

## 2. Design (v1)

Base behaviour: a helper joins a teammate's fight only through prey(): its own pressed fight, team_pressed (an
ally striking an enemy hurter than itself: never a fleer, which is the hurter one), or a candidate whose chase_trade
is not lost. A fleer in the roster is our side's first fall, so the trade reads lost and prey declines; and preyable
drops a healthy enemy out of range off its own ground, which the pursuer nearly always is. So the base never walks
to a pursuer unless it would win the fight anyway.

**Who peels, when (peel_target, fight.cc):**
- The helper: alive, not a healer (Willow's heal bid and support already cover it), at 60%+ health, not leaving
  (want_home false: peel never overrides a stand the helper itself loses), reaching the decision through prey()
  (the chase branch, the carrier's chase, the altar guard; a capture hold keeps holding).
- The mate: a visible ally under hurt_health_fraction (0.45), off its spawn, 2+ steps from it
  (from_ally_spawn), within 8 of us.
- Doom from the helper's view (cheap stand-in for the cl2-ret rollout): visible pursuers off their spawn's edge,
  each in its one-turn reach + 1 of the mate, deal their burst now (strike at its distance) plus one basic a turn
  (half for a ranged champion, whose walk spends its attack) for min(steps home, 3) turns, after the mate's
  Durability; doomed when that reaches its health and shield.
- The pursuer we peel: the doomed mate's pursuer nearest us, within our attack range + 3 (+2 with a ready dash).
- Our own risk: chase_trade of the fight at the pursuer (the same roster prey builds, with our fall settling it);
  we peel while we do not fall in it (self_falls false), whether or not the mate does (the "lost" prey reads).
  Not into a pack's zone (pack_covers). Linked Cassi/Issac: our fall is our pair's, same rule.

**What peeling is:** prey returns the pursuer, so the existing chase walks into range (dash when far) and hits;
chase_aim gives the strike search the same aim, so a search turn walks there and strikes. In the mirror the
pursuer's own prey/chase_trade and stand_lost_at re-price a fight that now holds a healthy helper: the threat alone
can turn it. Body-blocking (a step onto the line pursuer-mate) is not built: the chase's nearest in-range tile is
usually that side anyway, and a block for melee is not worth a step it cannot price.

**Fleer told?** Not in v1. Earlier fleer-side changes (retreat toward a healthy ally, havens) were level; the fleer
already flees, and a covered fleer that stops to fight was the doomed_commit loss.

**Turn order:** not in v1. A peel pays most when the helper acts before the pursuer next round; turn_order already
bids "protect" for escapes and heals, so a peel bid (hit the pursuer before its turn) is the round-2 lever if v1
fires but does not save.

**Economy:** it fires only on a doomed mate within 8 and a pursuer within range + 3, so a few times a game; a carrier
reaches it only where carry_bag already chases (not safe, not close to an altar). A capture hold is untouched.

**Two peelers:** both may peel; each judges its own fall, and two healthy helpers on one pursuer is the best case.

**Second order:** once the mate is home or dead, peel_target lapses; the helper is then near the pursuers with high
health, and its own want_home / pressed / prey take over as usual (pressed keeps a fight only while the enemy is
hurter than us). A pursuer turned by the threat walks off: prey then drops it (not preyable), so no long chase.

**Fuel:** peel_target is a few hundred fuel (allies x enemies, cached strikes); one chase_trade (~fight_cost_estimate)
only when a peel candidate exists, cached for the turn (prey runs up to three times a turn), behind the same fuel
gate prey's loop uses.

## 3. Building it

- First risk test (prey's chase_trade with our fall settling it: peel while we do not fall): 512 debug games on
  maps/gen, 2.4 candidate turns a game, 88% rejected (the fight is simulated to the end with them striking first, so a
  helper at full health "falls" to a 2v1 it would leave after two turns). Accepted 0.32 turns a game: inert.
- Replaced by a short-horizon test: every visible enemy that could hit us beside the pursuer (its reach + our range)
  lands its best one-turn strike twice, after our Durability, and that stays under our health and shield. The prey
  refactor went back out; peel_prey costs no simulation now (a strike per visible enemy, cached), so no fuel gate.
- Debug, 512 games on maps/gen (cl2-peel-dbg1): accepted 1.77 turns / 1.54 episodes a game (rejected 0.96 turns),
  decisions on accepted turns chase 67%, farm 24% (chase_aim's aim without a chase turn), bank 2%, hold 4%.
  Over 747 accepted episodes: helper hit the pursuer within 3 rounds 45%, the gap to it closed by +2 23%, the
  pursuer hit the helper 21%; the mate died within 5 rounds 27% (12% to the peeled pursuer), the helper 4%, the
  pursuer 3% (1% to the helper). Pursuer-mate distance grew by +2 in 59%.
- Same games, flee episodes by side: caught 3.01 a side-game (cand) vs 3.02 (ref), engaged 4.10 vs 4.06: no visible
  change in what happens to fleers on 512 games.

## 4. A/B rounds (cl2-dev, 20,480 games each, release, fast runner, `--no-test-draft`, ref oc-cl2-base)

| Round | Mechanism | Win % (95% CI) | OOF cand / ref |
|---|---|---|---|
| v1 | peel_target + peel_prey (two-turn risk test) as prey's last resort and chase_aim's fallback | 49.9 (49.2-50.6) | 213,381 / 208,317 (+2.4%) |
| v2 | v1 + the mate's main threat (most damage over its walk, among those we reach) instead of the pursuer nearest us + a turn-order bid (protect band, half a life + the mate's bag) to strike that pursuer before its next turn | 49.8 (49.1-50.4) | 211,642 / 207,558 (+2.0%) |
| v3 | v2 + stun_worth adds half a life (+ bag) when the stunned enemy's lost turn would kill the teammate nearest it (off its spawn) | 49.8 (49.1-50.5) | 211,537 / 207,678 (+1.9%) |

Why they moved (or did not):
- v1: fleers' outcomes did not change. On its 1,000 kept games, flee episodes 12.58 vs 12.35 a side-game, caught
  3.33 vs 3.27 (26.5% both); fight_metrics deaths 6.24 vs 6.07, kills 5.79 vs 5.99, gems 761 vs 790 (short games,
  within noise). The peel fires ~1.5 episodes a game; in them the helper hits the pursuer 45% of the time, but the
  mate still dies 27%, most often to another enemy or within the first 1-2 rounds (30% of caught fleers die within
  2 rounds of the episode's start), before a walk of 2-5 tiles brings a hit. In the mirror the pursuer's own prey
  already prices helpers walking in (Safety::late), so threatening adds no new information to its decision.
- v2: the bid and the target choice change who acts first on a handful of turns a game; level, as v1.
- v3: the stun bonus applies on 0.17 helper-turns a game (debug, 512 games, PSTUN traces): a stun-ready helper in
  cast range of a mate's killer at the moment of the kill is rare. Debug gen 52.5% on 512 games (noise).

## 5. Verdict

- Three rounds, all level (49.9 / 49.8 / 49.8, CIs about ±0.7), OOF +2% each. Nothing to ship or stack. The
  variant directory `bots/variants/cl2-peel` holds round 3 (v1 and v2 differ only by the edits above).
- Peeling as built does not move what happens to fleers. The measurement already bounded it small: stratified,
  allies that engaged saw 14.1% caught against 17.7%, an upper bound under the fight model's selection, worth
  ~0.08 lives a side-game even if all of it were causal. In the games the cand's catch rate matched the ref's.
- Where the kills are decided: 30% of caught fleers die within 2 rounds of the episode's start, often to an enemy
  other than the nearest pursuer; a helper 2-5 tiles away arrives after the kill. A helper already in reach engages
  in the base (the strike search hits a pursuer in range). The pursuer, being ocean, prices walking helpers
  already (Safety::late), so a threat alone changes nothing; only damage or a stun before its turn could, and a
  stun-ready helper in cast range at that moment is rare (0.17 helper-turns a game).
- Not tried: body-blocking the pursuer's line; peeling that overrides the helper's own want_home (the 'fled'
  allies, 0.34 a side-game of caught fleers, catch rate 28% vs ~21%), which risks the helper; and the mate's side,
  told it is covered (earlier fleer-side changes were level).
- Tools (session scratchpad, not kept): `g3b/peel.py` (the measurement table, per side), `g3b/peel_dbg.py` and
  `g3b/peel_eps.py` (PEEL traces joined with deaths and hits), PEEL / PSTUN debug traces in the copy.
