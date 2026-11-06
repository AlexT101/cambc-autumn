# Kill assignment and the reactive Tribute emblem (2026-11-06)

The user's four ideas (who takes the kill, the kill-gold funnel, kill-gem routing, a reactive Tribute emblem), then
the user's refinement: a **refusal rule** as the primary design. Base `bots/variants/oc-retest-clean` (= `bots/ocean`
= live v78). Dev copy `bots/variants/oc-kill-dev`, knobs in `params::kill::` (all off = the base). Variants
`bots/variants/oc-kill-<name>`. Fresh ladder-mix suites 542000-542039 (`maps/suites/merged/kill-dev`), confirm
542100-542139 (`kill-confirm`). Scripts in `kill-tools/` (`killstats.py`: the counts below from extracted replays;
`obese.py`: obese bags; `mkvar.py`: a variant with knobs set; `paired.py`: a variant's games against base-vs-base's
on the same map and side, split by whether a trace line fired; `ab.sh`, `queue.sh`: the A/B queue).

## 1. How often it happens

### Live scrims (v78 against Fish, Mite, Ad Astra, Vvvvv; 425 distinct games)

`killstats.py` over every v78 scrim replay (`replays/ladder-scrims/`). "Own" is the killer's bag at the end of the
round before the kill; "v" the victim's bag it took.

- Our champions land 8.8 kills a game; 2.8 a game take a bag (v > 0).
- Kills taking a bag by a body that already carried:

  | own bag | per game | gems taken | an ally within 4 of the victim | killer later died with its bag | lost in those deaths | won |
  |---|---|---|---|---|---|---|
  | > 300 | 0.48 | 13,483 | 85 / 206 | 37 | 56,137 | 167 / 206 |
  | > 600 | 0.18 | 7,658 | 35 / 75 | 19 | 44,931 | 51 / 75 |
  | > 1000 | 0.07 | 2,979 | 14 / 29 | 11 | 33,178 | 13 / 29 |
  | own + v > 600 | 0.23 | 20,233 | 42 / 97 | 26 | 54,879 | 65 / 97 |
  | own + v > 1000 | 0.09 | 14,005 | 18 / 38 | 14 | 39,995 | 17 / 38 |
  | own + tributed >= 1000 (the bag already wins) | 0.24 | 7,373 | 62 / 102 | 19 | 36,970 | 82 / 102 |

  The rest of each row's bags were banked (115 of 206 above 300) or still carried at the game's end.
- Prism lands nearly all of them: 506 of the 556 kills (any v) with own > 300, and 182 of 232 with a winning bag;
  Vesper Vale most of the rest (30 of 50 with own > 1000). Its Focus grows with the bag, so the hoarder is also our
  best killer.
- So the issue is real but small in count: ~0.2-0.5 kills a game, where an ally is near in about 40% of them. The
  gems involved are large because the bags already are: the bags our carriers lose after such a kill (37-56k) dwarf
  what the kills added (3-13k).

### Tribute emblems and channel lengths (same games)

- We buy 268 Tribute emblems in 425 games: Vesper Vale 99, Issac 57, Vendetta 49, Marcella 22, **Prism 22**. The bag
  at purchase is almost always 0 (a respawn or a shopping trip, which `wants_shop` makes only without a bag).
- 11,279 tribute starts: 10,451 completed (median 3 turn ends, p90 5, longest 103); 771 cancelled (median 29, p90 72:
  371 by ourselves, 245 stuns, 123 locks, 32 deaths). By channel length:

  | channel turns | starts | completed | gems at start | gems banked |
  |---|---|---|---|---|
  | 1-5 | 9,807 | 98% | 198,915 | 192,551 |
  | 6-15 | 768 | 87% | 64,908 | 54,072 |
  | 16-30 | 146 | 62% | 32,592 | 20,004 |
  | 31-60 | 348 | 28% | 164,212 | 43,050 |
  | 61+ | 153 | 16% | 142,631 | 18,436 |

  (Restarts count each start.) A 33% shorter channel matters exactly in the last two rows.

### Local self-play

1,000 games of the kd0 A/B (candidate and oc-retest-clean, kill-dev suite; the refusal fired in ~3% of games, so
both columns read as the base). Kills taking a bag (v > 0) are 2.7 a game, as live; big bags kill more often locally:

| own bag | kills a game (any v) | with v > 0 | an ally within 4 | killer later died with its bag |
|---|---|---|---|---|
| >= 300 | 1.45-1.56 | 0.58-0.60 | 43-46% | 18-19% |
| >= 600 | 0.66-0.82 | 0.27-0.31 | 56-58% | 20-21% |
| own + tributed >= 1000 | 0.95-1.11 | 0.40-0.43 | 56-58% | 17-18% |

Tribute emblems: 650-660 bought in 1,000 games (Vesper 270, Issac 120, Vendetta 110, Marcella 60-66, Prism 54-60),
nearly all at bag 0. Channels as live: 92-93% complete, cancelled ones median 22-29 turns (p90 105-108).

**Why the refusal seldom fires.** In a probe (kf600 with every exception logged, 256 ladder-map games) the bag rule
held 176 times and was refused 4 times: 164 had no able ally, 8 were denials of a winning bag, 4 threats. Of the
no-ally cases most had no visible ally within 4 of the victim at all; the rest had allies that had already acted, or
a victim acting before them, or not enough damage between them (counting the allies' strikes summed, `ally_sum`, did
not change it). A carrier with a big bag that lands a kill is usually alone or first: the kill bid (turn order) seats
the body that can kill first. So with `need_ally` the refusal changes few turns; its main lever is `gate_bids`, which
stops the carrier bidding the first seat when another ally can kill next round.

## 2. Where the killing blow is chosen

- **There is no team-level striker choice.** Each body runs its own strike search (`combat/plan.cc plan_strikes`,
  `Search`) on its own turn; the first body to act that can kill, does.
- **Within a search**, a kill is worth `kill_distance(health, full, bag)` (`combat/abilities.h`: chip + rest x
  sqrt(health share), rest = (1 - chip) full + `life_value` + `gem_value` x the victim's bag, both bags for C&I) plus
  `kill_stops` (a cancelled tribute; the whole win if it wins), added in `Search::die`. The plan is the end tile and
  leaf with the highest total (hits less `hit_given_reach` x each foe's blow at the end tile); ties keep the first
  candidate (`total > best_total`, tiles in their Strike-price order); `best_hit` ties go to the lower health.
  Nothing in it reads our own bag or another ally's ability to take the kill.
- **Across the team** the lever is turn order (`model/turn_order.cc offer_kills`): a body whose blow, with the
  allies acting before the victim, kills it bids the kill band at `turn_life_value + 15 x victim gems`; equal bids
  tie by champion id (lower first). A binding bid (`follow.h`) forces next turn's plan to keep it (`break_penalty`
  1e5). The other kill-valuing paths are `best_hit` (`strike_enemy`, retreat turns), `cast_at_enemies`
  (`abilities.cc`) and `self_abilities.cc`'s reset attack; all add `kill_stops` on a kill.

## 3. Design

All knobs in `params::kill::`, off by default. A killing blow of ours on e now adds `kill_stops_ours(e)` =
`kill_stops(e) - kill_refusal(e)` (`combat/kill_rule.cc`) at every kill-valuing site above, so a refused kill loses
`refuse_penalty` (5,000 enemy health points: more than any turn's hits, less than a binding bid's 1e5) whichever path
would take it, and a plan that only hits others or holds is chosen instead.

**Refusal** applies only to a victim carrying gems (v > 0: a bagless kill does not change our banking), and never:
- when v + their tributed >= 1000 (denial of a winning bag);
- when the victim's own blow on us before our next turn reaches `threat_share` (0.5) of our health and shield
  (threatened, or the kill is our escape);
- with `need_ally` (default), when no visible ally can take it: alive, not channelling, yet to act this round
  with the victim already acted (so before its next turn), and whose strike this round kills it alone.

Two rules (the user's refinement):
- **K-fixed** (`fixed_x`, `fixed_plus`): refuse when our bag (or our bag + v) exceeds X, and an able ally would not
  itself be over X.
- **K-dynamic** (`dyn_on`, `dyn_y`): a local projection of each side's win round. Each body (ours: our bag, visible
  allies' bags, the others' posted bags; theirs: last-seen bags) banks its whole bag after its walk (Chebyshev to the
  nearest altar - 1; 15 out of sight) and its channel (`tribute_turns`, with the Tribute emblem when owned), in
  parallel; the projected round is when the sorted banks reach 1000 - tributed, and short of it the rest comes at the
  side's mean gems a round so far. Margin = their round - ours. Taking the kill: our bag + v, their victim (both
  bodies of C&I) at 0. Alternatives: each able ally's kill (their side the same), and (without `need_ally`, or with
  no able ally) nobody's (they keep v). Refuse when the best alternative's margin beats taking it by more than Y.
- `gate_bids` (default on with a rule): a body that would refuse at its turn's end (with any visible ally whose next
  turn's strike kills the victim counting as able) makes no kill bid on that victim, so a bid never binds it to a
  kill it declines.

Secondary knobs:
- **Routing** (`route_w`, `route_gap`): a kill by us loses `route_w x gem_value x v` when an able ally carries at
  least `route_gap` fewer gems (idea 3, a soft version of the refusal).
- **Kill-gold funnel** (`funnel_bid`): our kill bid gains 7 value units (past an equal bid only: rank codes step at
  0/7/10 mod 15) while our gold efficiency (`relative_efficiency`, CHANGES 420) is the highest among the allies we
  see (idea 2). Equal bids otherwise tie by id.
- **Race refusal** (`race_on`, `race_y`; the coordinator's extra arm on `bots/variants/oc-race`'s model, copied in as
  `model/race.{h,cc}`): with an able ally, refuse when our kill delays our projected win (`if_kill(e).us - base.us`)
  by more than Y; without one (`need_ally` off), when it shrinks margin = P_them - P_us by more than Y.
- **Reactive Tribute emblem** (`trib_mode`):
  - T1 (1): `passive_saved`'s Tribute value adds the cut on our current bag (every gem held is tributed some day),
    `(b - (b - floor(0.33 b)))` turns over `max(horizon, 20)` rounds, to the history-based rate;
  - T2 (2): T1 with each turn weighed `1 + trib_lambda x channel turns / 50`;
  - T3 (3): T1 with each turn of a winning bag weighed `trib_win_w` (a turn of our projected win round).
  - In every mode `best_emblem` prices the Tribute emblem in its best stat against the learned (emblab) choice and
    buys it when it saves more, never over a begun emblem, so the learned order holds elsewhere; and a restarted
    channel (no tribute of its size since the last start) adds only the cut of the gems it adds (the history
    double-count the coordinator found at bank.cc:772).

**Obese bags** (the user's later idea; `obese`, `obese_bank`, `obese_m`, `obese_f`). A tribute scores the whole bag
(no partial tributes, cambc-rules.yaml `tribute`) and a kill only grows the killer's bag, so a bag whose quickest
channel, begun this round with a Tribute emblem (b - floor(0.33 b), b = ceil(g / 10)), ends past round 2000
(more turn ends than rounds left + 1) can never score: X(R) is the smallest such bag, with a walk of 0 (proof for any
holder). The bot already never starts such a channel (`tribute_ok`: turns <= rounds left), but `bankable_bag` still
counts the bag, so the carrier walks to an altar and waits there.
- V0 (`obese` 1): `kill_gems` (model/world.h) counts such bags 0 in every kill-valuing site (search board, strikes,
  `best_hit`, the reset attack, the prey order, the kill bid) and `protect_gems` in the protect bids; kill gold and
  life value stay. Not when a Prism holds the bag (Focus per carried gem) or is the killer (ours), or, for protect,
  when the enemy has a Prism. `obese` 2 also halves a bag whose kill would make ours obese (they lose it, we cannot
  score it).
- `obese_bank`: a non-Prism body of ours with an obese bag has `bankable_bag` 0, so it farms, fights or guards.
- V1 (`obese_m`, `obese_f`): a kill's gems count `obese_f` of themselves when `race::if_kill` leaves the projected
  winner unchanged and both margins exceed m rounds (not for Prism, killer or victim; memo per victim and turn).

## 4. Tests

- Identity: all knobs off, `tools/fuel/bench.py` replays at 100M equal oc-retest-clean's, default and wide sets.
- Fires: debug builds print `KREF round type rule v own able tributed` (once per round and victim) and `KTRIB` (an
  emblem choice turned to Tribute); counted from local games' stdout.
- A/B: each arm against oc-retest-clean on kill-dev, at 2x fuel first (200k a turn, 400k the first; both sides), SPRT
  0.50/0.51, full runs and kill-confirm for an SPRT pass; the real budget only for an arm good at 2x. Bar for the live
  gate: an SPRT pass or a held-out win over 20k games. Obese arms also on `kill-late` (the 662 kill-dev maps where a
  base-vs-base game reached round 1700, 1,324 games) and `kill-latec` (503 kill-confirm maps, 1,006 games).

## 5. Results

**No arm is significant: nothing goes to the live gate.** With every knob off, `bench.py` replays equal
oc-retest-clean's at 100M (16/16 default, 52/52 wide; fuel +0.00%), checked on the final dev copy.

### Kill refusal

At 2x fuel (SPRT 0.50/0.51 on kill-dev unless noted):

| arm | knobs | result | out-of-fuel turns cand / ref |
|---|---|---|---|
| kr0h | race, Y 0, no ally needed | SPRT H1 at 400 games (52.2%); **full: 50.0% of 20,480 (CI 49.3-50.7); kill-confirm 50.0% of 20,480 (49.3-50.6)** | 1825 / 1313; 1685 / 1096 |
| kr0 | race, Y 0, allies summed | H0, 50.1% of 883 | 51 / 48 |
| kd0s | dynamic, Y 0, allies summed | H0, 50.2% of 1,294 | 57 / 60 |
| kd0h | dynamic, Y 0, no ally needed | H0, 49.7% of 996 | 90 / 45 |
| kf600c / kfp600c | own (own + v) > 600, allies summed | H0, 50.0% of 216 / 202 | level |
| kf600h | own > 600, no ally needed | H0, 48.9% of 223 | level |
| rt | routing 0.5, allies summed | H0, 50.2% of 400 | level |
| fn | kill-gold funnel bid 7 | H0, 49.8% of 1,022 | level |
| base | oc-retest-clean copy | 50.0% of 20,480 (base vs base) | equal |

At the real budget (before the 2x-first order; kill-dev): kf600s 49.7% of 20,480 (49.0-50.4), kd0s 49.8% of 20,480
(49.1-50.5), kfp600s 49.7% of 20,480 (49.1-50.4); SPRT stops for kf300 / kf600 / kf1000 / kfp600 / kd0 / kd5 / rt at
49.6-49.7% of ~2,600, kd0h 48.1% of 1,656, kfp1000h 49.5% of 2,407; out-of-fuel turns +5-6% for the arms that run
the rule at every kill site (+33% for kd0h).

- **How often they fire.** kr0h refuses in 962 of 20,480 games (4.7%; 5,205 rounds); the fixed rules at 600 fire in
  7% of games (kf600s, real budget), kd0s in 3.5%, kfp600s in 15.6%. The probe in section 1: with an ally needed, the
  rule holds 176 times and refuses 4.
- **Paired forensics** (each game against base-vs-base on the same map and side, 2x, where play is equal until a rule
  fires): kr0h's fired games read 78.8% against base's 77.8% on the same games (+10 of 962: 55 turned to wins, 45 to
  losses); its other 19,518 games are level (-0.08 points). At the real budget the variants' extra fuel shifts every
  game, so the same split there (kf600s +8.5 points on fired games, -0.9 on the rest) is selection, not an effect.
- **Why it does nothing.** The rule fires where we already win four games in five: a carrier with a big bag landing
  a kill. Flips both ways are single games where the refused victim later banked or killed back (e.g. kr0h refusing a
  498-gem victim with own 1,500 at round 629, then losing at 1,633 a game base won at 2,000). Even +10 points on the
  fired 5% would be +0.5 overall, inside the full runs' CI.
- **Race model's sign (on real kills, 35,017 KRACE lines in 382 games).** A kill speeds our projected win with a
  small bag (own < 300: 30,208 of 32,972 sooner) and delays it with a big one (own >= 600: 121 of 166 later, median
  +4 rounds); their side is always later (mean +113 to +182 rounds). So `if_kill`'s delta has the expected sign.
- kr0h costs out-of-fuel turns (+39% at 2x on kill-dev, +54% on kill-confirm: `if_kill` is ~1.7k a call); no
  real-budget run since it is level at 2x.

### Reactive Tribute emblem

- 2x: T1b (`trib_mode` 1, from a bag of 100) H0 at 50.1% of 8,569; T3b H0 at 50.2% of 8,509. Real budget: T1b 50.3%
  of 14,422 (49.5-51.1), T3b 50.3% of 14,444, T2b 49.8% of 4,812; without the 100-gem floor T1 47.8%, T2 48.4%, T3 47.9%
  (it buys Tribute on small bags over the learned emblem); forward pricing for Prism (T1f/T2f/T3f) 42-45%.
- **Prism does buy it before big channels under T1b:** 400 Tribute emblems by Prism in 800 games (base 39), bags at
  purchase often 130-390; channels of 61+ turns fall from 383 to 162 starts and 31-60 from 411 to 326. Completion
  per length is unchanged (9% for 61+, 34-38% for 31-60): shorter channels still get stunned or locked.

### Obese bags

- **How often:** a bag >= X(R) exists in 1.4% of local self-play games (0.8% held by a non-Prism; 1,000 games), 1.5% in
  800 more, and 4 of 435 live scrims. About 2% of games reach round 2000. Nearly all of it is in the last 20 rounds
  (X(R) is ~760 gems at 50 rounds left and ~150 at 10).
- **V0 on the late-round suites (2x):** ob1 (kill values) 50.1% of 1,324 on kill-late, 49.6% of 1,006 on kill-latec;
  ob1b (+ `obese_bank`) 50.2% / 49.7%; ob2b (`obese` 2 + bank) 50.2% / 49.9%; obb (bank only) 50.0% / 50.0%. Fired in
  84 (ob1), 244 (ob1b), 369 (ob2b), 188 (obb) of the 2,330 late games, but against base-vs-base on the same maps no
  fired game changed winner but one (ob2b, +1). A bag that dead comes when the tributed score has already decided the
  game; the tiebreaks behind it (gold, kills) keep kill gold. No combination with a refusal winner, as there is none.
- **V1, by the race (2x, kill-dev SPRT):** m 50 / 150 / 300 with gems at 0: 49.1% of 2,550, 49.2% of 2,782, 49.6% of
  3,869; m 50 / 150 at half: 49.6% of 2,928, 49.9% of 4,907; all H0. It fires in ~93% of games (593k rounds in 2,382
  games for m 50): the race's margin is wide for most of a game, and a kill's gems still matter there (denial, the
  projection's error). Weaker discounts read closer to 50%; none above.

## 6. Long channel forensics

Every tribute channel of 10+ turns, from two sources:
- self-play: oc-retest-clean mirror, 1,024 games on every tenth kill-dev map, at the real budget, both teams counted;
- live: v78 scrims, 425 games (Fish 156, Mite 189, Ad Astra 40, Vvvvv 40).

Scripts are in `kill-tools/`: `chanforensics.py` (rows), `chansummary.py`, `chanfate.py` and `chancut.py` (tables),
and `mirror_race.py` (race margins for self-play, using the race agent's fog replica). The rows are in
`/home/ubuntu/tmp-offload/kill/chan/`.

How each channel ended, as % of starts (each restart counts as a start):

| channels | n | done | died | stunned | enemy lock | we cancelled | game end |
|---|---|---|---|---|---|---|---|
| ours, mirror, >= 10 turns | 3,850 | 44 | 0 | 16 | 10 | 26 | 3 |
| ours, mirror, >= 30 | 2,420 | 23 | 0 | 22 | 14 | 36 | 4 |
| ours, mirror, >= 60 | 1,200 | 8 | 1 | 28 | 19 | 41 | 3 |
| ours, live, >= 10 | 878 | 43 | 1 | 11 | 7 | 36 | 2 |
| ours, live, >= 30 | 523 | 24 | 1 | 14 | 9 | 50 | 2 |
| ours, live, >= 60 | 164 | 16 | 0 | 11 | 7 | 65 | 1 |
| Fish's, live, >= 30 | 95 | 26 | 0 | 16 | 25 | 27 | 5 |
| Fish's, live, >= 60 | 49 | 8 | 0 | 18 | 35 | 35 | 4 |

Completion by channel length, and by whether an enemy saw the channeller at the start (ours):

| turns | mirror: all | seen | unseen | we see no enemy | live: all | seen | unseen | we see no enemy |
|---|---|---|---|---|---|---|---|---|
| 10-19 | 87% | 78% | 92% | 91% | 74% | 58% | 93% | 86% |
| 20-29 | 66% | 53% | 78% | 73% | 62% | 50% | 76% | 67% |
| 30-59 | 37% | 24% | 55% | 47% | 28% | 17% | 60% | 35% |
| 60-99 | 12% | 6% | 23% | 15% | 21% | 14% | 43% | 28% |
| 100+ | 1% | 1% | 2% | 2% | 3% | 3% | 0% | 0% |

### Findings

- **Who channels.** Prism holds 89% (live) and 93% (mirror) of our 30+ turn channels.
- **Deaths are rare.** Our channeller dies in under 1% of long channels: Vesper Vale or a Prism, with one enemy within
  6.
- **We are already ahead.** Our lock is on the altar at the start of 88-93% of these channels, and the race margin
  is +100 or more in 86-91% of them.
- **We cancel most of them ourselves.**
  - Self-cancel is the largest end: 36-50% of 30+ turn channels, 41-65% of 60+.
  - It is `continue_tribute`: `tribute_ok` turns false because `tribute_safe` finds a kill on us within the window.
  - We were seen at the cancel 90-96% of the time, yet no enemy was within 6 in 37% (live) and 48% (mirror).
  - 63% (mirror) to 64% (live) of self-cancels start again within 3 rounds, and every restart is a whole new channel
    (80% after a stun).
  - So a hoard that is being watched cycles: start, cancel, start. Its gems then wait a median ~100 rounds to bank,
    if they bank at all.
- **Where the gems go.** Of the gems that start 60+ turn channels in the mirror, 24% are ever banked by that body, 13%
  are lost at its death and 63% are still carried at the game's end. Live: 34% banked, 24% lost, 43% carried.
- **What it costs.** Most of these are games we win anyway: the channeller's side wins 88% (mirror) and 87% (live)
  of them. The loss is concentrated in failed winning bags:
  - A "winning bag" is one where bag + tributed >= 1000. These complete only 14-15% of the time: 251 of 1,749 in the
    mirror, 51 of 343 live.
  - A side with one fail lost 37 mirror games (3.6% of games) and 11 live scrims (of the 60 losses that had a 10+
    turn channel).
  - Those live losses had a median channel of 77 turns. 31 of the 41 failed channels were self-cancelled, and 30 of
    the 41 bags were later lost.
  - The bags are oversized. For winning bags with 30+ turn channels, the median need was ~390 gems but the bag
    carried 169 (live) and 380 (mirror) more than that; in the mirror, half were at least twice the need.
  - Examples: a Vesper Vale bag of 2,690 needing 988 (181 turns), a Prism bag of 998 needing 829 (100 turns), a Prism
    bag of 600 needing 400 (60 turns). Each was cancelled again and again, and the game was lost.
- **Fish's hoarder** is Vesper Vale, with 57 of Fish's 95 channels of 30+ turns. Those channels complete 26% of the
  time (60+: 8%). We stop them mostly with locks (25%; 35% at 60+). Next are their own cancels when we come close
  (27-35%; one of ours is within 6 at 21 of their 26 such cancels) and stuns (16-18%). They die in channel 0%, so we never
  catch the channeller.

### What would have saved them

- **Banking smaller and earlier, which here means not letting a winning bag grow.** This is the largest lever.
  - Completion falls steeply with length: 87% at 10-19 turns, 66% at 20-29, 37% at 30-59, 12% at 60-99, 1% at 100+
    (mirror). A tribute takes the whole bag, so a bag past its need only adds turns.
  - The failed winning bags carried a median 169-380 gems over the need, which is 17-38 extra turns.
  - A winning bag already heads for an altar (`winning_bag`). But a long winning channel waits for a safe window
    (`any_risk`), and while it waits the bag keeps growing from kills and capture shares. That lengthens the channel
    and makes a safe window rarer.
  - Candidate fixes:
    - While a winning bag waits, refuse gem-gaining kills and camps unless a kill denies their win.
    - Cap Prism's Focus retention at a channel length that still completes (about 300 gems, 20-30 turns, which is
      66-87% completion).
- **A safer start.** An enemy seeing us at the start halves completion or worse at every length (30-59 turns: 24%
  against 55% in the mirror, 17% against 60% live). "We see no enemy", which the bot can read, recovers most of that
  (47% / 35%). So a long channel should start only when no enemy is in sight, and otherwise move to an unwatched
  altar or wait out of sight.
- **No cancel-restart cycling.**
  - About half of the self-cancels have no enemy within 6, and about two thirds restart within 3 rounds.
  - Cancelling only when a stun, lock or kill can land before the channel ends, rather than `tribute_safe`'s window
    on a long channel, would keep the channels that are already part done.
  - This is the one fix the data points at directly. An A/B would decide it.
- **More bodies or a perma-lock: no.**
  - Channels with 2+ allies within 6 complete less often than lone ones (mirror 30+: 17% against 33%). That is
    confounded: escorts gather where the fight is. But the escort does not stop stuns (26% of those channels).
  - Our lock is already up at the start of 88-93% of long channels. The 14-19% enemy-lock cancels come after they
    break it with 5 hits, so a guard on the lock could save only that slice.
  - So oc-lock-dev's perma-lock machinery would add little here.
- **Not channelling and fighting with the hoard instead.** In won games this already happens in effect: 63% of the
  60+ channel gems in the mirror are still carried at the end. In lost games the hoard is what loses (30 of 41 failed
  winning bags lost at death live). So for a bag that wins the game, fighting on with it is the wrong choice.
- The paired base-vs-base data adds nothing here, since no variant was run. Any fix above needs its own 2x-first A/B.

## 7. Long channel fixes (C1-C4)

The coordinator's four fixes from section 6, built in `oc-kill-dev` as `params::kill::` knobs:
- **C1** (`c1`, `c1_min_left` 5): a channel with 5+ turns left is cancelled only for a kill on us within w turns
  (`turns_to_kill_idle`, or the damage taken last turn). w is 1 (strict), 2 (a turn's slack), or 3 (restart cost:
  `tribute_window` scaled by the share of the channel left). There is no pre-emptive cancel for a stun or lock: either
  cancels the channel anyway, and the gems stay carried.
- **C2** (`c2`, `c2_slack`): a winning bag refuses kills that add gems, through the kill-refusal penalty at every
  kill site and the kill bid. The denial and threat exceptions stay. Variants: all carriers, Prism only, or bag +
  tributed >= 1100. Camp payouts are already refused: `may_chain` never chains a capture with a winning bag.
- **C3** (`c3_turns`, `c3_switch`): a channel of T+ turns (20 or 30) starts only with no enemy in sight, except in
  the endgame's any-risk cases. With the switch, the usual altar wait ends with a walk to another altar; without it,
  the body waits on.
- **C4** (`c4_win_turns`, `c4_cap`, `c4_round`): a winning bag's channel of up to 30 or 45 turns is taken at any risk
  (the window is otherwise 10); or Prism keeps no bag of 300 or more from round 1200 (450 from round 1500).

With every knob off, bench replays are identical at 100M fuel (16/16, 52/52).

At 2x fuel, against oc-retest-clean on kill-dev:

| arm | SPRT (seed 0) | full run, 20,480 games | 95% CI |
|---|---|---|---|
| C1 strict | H0, 48.7% of 729 | **48.8%** | 48.1-49.4 (loss) |
| C1 slack | H0, 49.5% of 645; seed 11: H0, 48.6% of 923 | not run | |
| C1 restart cost | H0, 50.0% of 1,221 | 49.9% | 49.2-50.6 |
| C2 all carriers | H0, 48.7% of 374 | **49.1%** | 48.5-49.8 (loss) |
| C2 Prism only | H0, 49.0% of 384 | **49.2%** | 48.5-49.9 (loss) |
| C2 slack 100 | H0, 49.8% of 213; seed 12: H0, 49.8% of 305 | not run | |
| C3 T 20, switch | H0, 50.0% of 240 | 49.9% | 49.2-50.6 |
| C3 T 20, wait | H0, 50.0% of 354 | 49.9% | 49.2-50.6 |
| C3 T 30, switch / wait | H0, 50.2% / 49.8%; seeds 13 / 14: H0, 49.8% of 418 / 49.4% of 247 | not run | |
| C4 winning any-risk to 30 | H0, 49.8% of 233 | 49.3% | 48.6-50.0 |
| C4 winning any-risk to 45 | H0, 48.9% of 262; seed 15: H0, 48.4% of 543 | not run | |
| C4 Prism cap 300 from 1200 | H0, 49.6% of 264 | 49.9% | 49.2-50.6 |
| C4 Prism cap 450 from 1500 | H0, 50.4% of 274; seed 16: H0, 50.2% of 255 | not run | |

Out-of-fuel turns are level in every arm (+0-2%).

The seed-0 SPRT screens all played the same first games (ab.py's fixed `--sprt-seed`), so their stops are
correlated. The eight main arms were therefore run in full, and the other six were screened again with seeds 11-16:
H0 again.

**Mechanism.** Channel fates for every eighth game of each full run (2,560 games). CAND and REF here are the two
sides of the same A/B: REF is the before, CAND the after. "Lost" is a 30+ turn bag that failed and was later lost at
a death, in gems per game.

| arm | side | 30+ starts | done | stun | lock | self | 60+ done | winning bags done | lost / game |
|---|---|---|---|---|---|---|---|---|---|
| C1 strict | REF | 3,014 | 24% | 17% | 16% | 38% | 8% | 17% | 155 |
| | CAND | 2,176 | 31% | 31% | 22% | 9% | 10% | 18% | **256** |
| C1 restart cost | REF | 2,948 | 24% | 17% | 16% | 38% | 9% | 18% | 117 |
| | CAND | 2,667 | 27% | 24% | 18% | 27% | 9% | 17% | 133 |
| C2 Prism only | REF | 3,046 | 24% | 17% | 16% | 38% | 9% | 17% | 160 |
| | CAND | 2,799 | 24% | 20% | 16% | 36% | 9% | 17% | 150 |
| C3 T 20 | REF | 2,912 | 25% | 17% | 16% | 38% | 9% | 18% | 108 |
| | CAND | 2,747 | 25% | 22% | 16% | 33% | 9% | 18% | 110 |

**Why none wins.**
- **C1 works as built but costs games.** Strict C1 cuts self-cancels from 38% to 9% and restarts by 28%, and per-start
  completion rises from 24% to 31%. But the cancels turn into stuns (17% to 31%) and enemy locks (16% to 22%). The bags
  later lost at a death rise by 65%, so winning bags complete no more often.
  - The self-cancel that looked wasteful was the bot leaving before the stun-and-kill reached it.
  - Even with no enemy within 6, `tribute_safe`'s 10-turn window sees an approach that a 1-turn check does not.
- **C2 costs kills.** Refusing kills while holding a winning bag rarely changes how a channel ends. It gives up kills
  that also remove threats and kill gold, and it loses 0.8-0.9 points.
- **C3 moves the failure later.** Waiting for an unseen start (fired in 15-30% of games) leaves fates and winning-bag
  completion unchanged: stuns rise, self-cancels fall, and the start comes no safer.
- **C4 is level or slightly down.** Taking a winning bag's 30-45 turn channel at any risk reads 48.4-49.3%. A late Prism
  cap fires in about 5% of games and is level.
- **Conclusion.** A long channel watched by the enemy fails one way or another. Neither keeping it, refusing kills nor
  waiting for sight changes that, and the self-cancel is the cheapest of its failures. The lever left is not having a
  long channel in a watched spot: a winning bag banked before it gets long, which section 6 found is mostly the need
  shrinking while Prism holds the bag. The macro agent found a fixed early cap loses (39.5%), and C4's gated caps are
  level.

**Not run:**
- Combinations: there is no winner to combine.
- Real-budget runs: the 2x-first order holds.

## 8. Obese round 2: negative value (2026-11-06)

The user's refinement of V0: an obese bag is not just worth 0 but slightly negative. Inheriting one disables the
killer (it can neither farm towards nor make a tribute with it) and makes it a walking target; an ally holding one is
partly disabled. Base `bots/variants/oc-base10`; dev copy `bots/variants/oc-obese-dev`, knobs in `params::obese::`
(all off = the base); variants `oc-obese-<arm>`. Scripts in `obese2-tools/` (`mkvar.py`; `ab.sh`; `obstat.py`: the
census and firings per game; `pair2.py`: an arm's games against the base mirror's on the same map and side).
Fresh ladder-mix suites: dev 600100-600139 (`maps/suites/merged/obese-dev`, 20,480 games), held out 600200-600239
(`obese-confirm`, unused: no winner). `obese-late`: the 300 obese-dev maps where a base mirror game at 2x reached
round 1900.

### Design

- The proof is V0's. A bag is dead when its quickest channel, begun now with a Tribute emblem (b - floor(0.33 b),
  b = ceil(g / 10)), needs more turn ends than rounds left + 1. Tributes take the whole bag and a kill only grows
  one, so it never scores. New in this round: a tribute of it already under way that ends by round 2001
  (`channel_end_round`) keeps the bag live. V0 would have zeroed a 300-gem channel begun at round 1970 once
  round 1990 came. Prism (Focus per gem) is excluded as holder and as killer; for protect, so is any enemy Prism.
- `on`, `mult` m: kill values (search board, strikes, `best_hit`, the reset attack, the prey order, the kill bid)
  and protect bids count an obese bag as m x its gems. Kill gold and life value stay.
- `disable_pen`: gems taken off for the disabled body, both a victim's and one of ours whose bag the kill makes
  obese.
- Bids count whole gems and never fewer than 0 (rank codes). The prey order's divisor is floored at 1.
- `bank`: our own obese bag is not carried to an altar (V0's `obese_bank`).
- The enemy's in-progress tribute stop (`kill_stops`, the stun's tribute delay, the stun bid) is unchanged.
- Identity: knobs off, `bench.py` at 100M equals oc-base10's, 16/16 default and 52/52 wide.
- Debug builds print `OBESEC round side+index gems [P]` for every dead bag in sight (P: a Prism's, or a channel
  ending in time) and `KOBESE` when a value changed. Both print only with `on`.

### How often it fires

- **Rarely.** At 2x on obese-dev (20,480 games) a dead bag was in sight in 250 games (1.2%), a non-Prism one in 163
  (0.8%). The gate changed a value in 144 (0.70%): kill values in 59, the bank in 104.
- **Late.** Every one of those games is on obese-late. The first obese round is 1802-2000, median 1999. The
  fired games' median largest bag is 36 gems: a small bag in the last rounds, when X(R) is small.
- **Where.** By family: gen-ladder 51, ultrastarvation 13, lines 12, boss-battle 9, shared-gems 7.
- **Real budget, obese-late:** dead bags in 123 of 600 games, non-Prism in 95, fired in 85.

### A/B

- **The SPRT screen is degenerate here.** All four m arms "accepted H0" at 200-634 games on obese-dev (2x,
  0.50/0.51, seeds 600001-600004). An arm plays exactly as oc-base10 until a bag goes obese, so nearly every map
  scores 0.5. The variance falls to the 0.001 floor and the LLR drops ~0.05 a map pair whatever the effect. So the
  arms were run in full on obese-late instead (which holds every game the gate can touch) and paired against a base
  mirror on the same maps.

| arm (bank on) | obese-late 2x | fired games (2x): arm / mirror | real budget obese-late | fired (real): arm / mirror |
|---|---|---|---|---|
| m0 (the old V0) | 50.5% of 600 | 50.7 / 50.0 (144; 1 flip) | 48.5% of 600 | 47.1 / 49.4 (85; +9 / -11) |
| m -0.1 | 50.5%, game for game m0's | same | not run | |
| m -0.25 | 50.5%, game for game m0's | same | not run | |
| m -0.5 | 50.5%, game for game m0's | same | 48.5%, game for game m0's | same |
| m -0.25, pen 50 | 50.7% | 45.5 / 44.9 (176; 1 flip) | not run | |

- **m changes play but never a result.** m -0.1, -0.25 and -0.5 each change 15 of the 600 late games against m0
  (the same 15), and no winner. Each of those 15 was decided on tributed gems, by 45 or more. An obese bag
  cannot move that total: m only moves late kills, and with them kill gold and kill counts (by 1-3). Those are
  tiebreaks after a tied tributed score, which none of the 600 had.
- **The arms' noise is fuel, not the gate.** m0 against the mirror flips 7 games at 2x and 97 at real budget, nearly
  all where the gate never fired. The debug census and the new code shift fuel-gated searches. m -0.25 + pen
  diverges from m0 in 586 of 600 games from round 1, a new constant's codegen alone.
- **Full-suite bound:** the fired games are 0.7% of a ladder-like suite. If each fired game flipped one way, that
  would be ±0.7 points; the measured paired effect there is 0.
- **Not run:** the held-out confirm, `--mix varied` and the panel (no winner), and the tiered race gate. V1 read
  49.1-49.9% last round and needs a winning m to stack on.

### Replays (the 15 games m -0.5 changed, 2x)

- m0 and m -0.5 both bank, so they differ only in kill values. In each game play diverged in the last 0-170
  rounds (rounds 1831-2000): a late kill taken or passed up.
- Kill counts moved by 1-3 either way. In 2 games the opponent's tributed total fell (539 -> 320, 533 -> 462),
  through the divergence that followed, never enough to change the result.
- **Were the decisions right?** By the rules, yes and irrelevantly so. The bag could not score for either side, so
  denying or inheriting it was worth nothing. Only kill gold (tiebreak 2) and kills (tiebreak 3) remain, and those
  argue for killing (m >= 0), not against. A negative m trades away tiebreak value for a "disabled" cost that doesn't
  exist in the last rounds: nothing is left to farm towards.

**Verdict: level, and structurally so.** A bag provably dead by round 2000 only appears once the tributed score has
decided the game. Its kill value, at any sign, moves only tiebreaks that never come into play. Don't merge; don't
retry with other m.
