# macro5: the Prism as the team's bank (2026-11-11)

Lead: one orchestrator agent, implementation by subagents (each audited by a read-only subagent).
Worktree `/home/ubuntu/wt/macro5`, branch `macro5-20261111`. Reference `bots/variants/ocean-ref-b7c87cf` (= `bots/ocean` at
the start). Every A/B: `tools/ab.py CAND variants/ocean-ref-b7c87cf --no-test-draft --fuel 200000`, fast runner,
own drafts, maps `/home/ubuntu/wt/macro5-maps/s-<seed>` (`--mix ladder-v2`, 256 maps a suite, both sides). Running log:
[macro5-log.md](macro5-log.md).

## Result

**bots/ocean = `bots/variants/macro5-hold-sole2` (commit e99ae435e): 57.0% (95% CI 56.5-57.5) over 39,936 games** against
ref at 2x fuel, in four ladder-v2 suite blocks (hold-safe, the previous best, on the same maps for comparison):

| Suites | Games | hold-sole2 win % (95% CI) | OOF cand vs ref | hold-safe |
|---|---|---|---|---|
| dev s-500001..020 | 10240 | 56.6 (55.6-57.5) | 575 vs 596 | 55.1 |
| held-out s-500101..120 | 10240 | 57.0 (56.0-57.9) | 487 vs 453 | 54.5 |
| block 3 s-500023..040 | 9216 | 57.8 (56.8-58.8) | 501 vs 472 | 55.1 |
| final s-500121..140 (reserved) | 10240 | 56.9 (55.9-57.8) | 588 vs 481 | 54.4 |
| **pooled** | **39936** | **57.0 (56.5-57.5)** | | 54.8 |
| `--mix varied` v-500201..210 | 5120 | 54.2 (52.8-55.6) | 553 vs 500 | 52.2 |

The 60% goal was not reached. The gain is all in games where the drafts include a Prism (~80%; the drafts mirror, so both
teams have one), and games without a Prism stay at exactly 50%; so the Prism games run at about 59%. It is three layers of
one idea, the gems the team captures landing on its Prism: prismhold (54.4% alone over 29,696 games), prismsafe (+0.5 on
top) and hold-sole/hold-sole2 (+2.2 on top). Out-of-fuel turns are up slightly (~+50 to +100 a 10k games at 2x fuel).

## Design

**A gem carried by the Prism is worth more than the same gem carried by anyone else.** It scores the same once
tributed, but while the Prism carries it, it is +1.5 Focus (the Prism's passive), and the Prism's stun (1.5 x Focus) and
ground hit (1 x Focus) scale with Focus. At the shop's price a Focus shard is 30 gold for +8 Focus, so a carried gem
is 1.5 / 8 x 30 = 5.625 gold of Focus on top of its score. Every number comes from the rules.

ref already lets a Prism standing on a cleared group hold it alone when no enemy is in sight (`sole_capture_holder`), but
its holder choice (`holder_value`) priced a gem the same on every champion. The Prism attacks from range 3-4, so it is
rarely on the tiles at the clear; the melee claimer holds and the Prism moves on. In ref-vs-ref games 28% of the
captures our team took on groups our Prism had damaged that cycle paid the Prism nothing: 46% as many gems as the
Prism's whole capture income.

prismhold (economy/capture.cc, economy/farm.cc, +68/-25 lines):
- `holder_value` adds `price x focus_gold_per_gem x gems` for a Prism holder (`focus_gold_per_gem` = 1.5 / Focus growth
  x shard price), so `value_holder` / `outvalues_holders` name the Prism the holder of gem groups; `multiplies` counts
  it, so the comparison runs on pure gem groups too.
- `focus_holder` factors out `sole_capture_holder`'s endgame exemptions (the bag would win; no time left to bank) and
  applies them on every path.
- `pick_up`: the Prism also takes over a cleared gem group in view within `pick_up_radius` that an ally holds, if it
  outvalues the holder and arrives a round before payout (the incumbent steps off only when it sees the Prism on a
  tile, and only with no threat and no camp damage there; under threat they share). Off on crew, siege and Monolith
  operations.
- Nothing else: no farm pricing, banking, retreat or fight change. Nobody walks anywhere new except the Prism's short
  pick-up walks; the team captures what it did, and the gems land on the Prism.

Effect (1200 extracted games): our Prism's bag at r100/200/300/400/600 is 41/96/160/231/305 against ref's
29/74/127/182/259; Prism-kills-Prism 475 vs 352; gems lost to kills -13 a game; captures +4 own, +2 mid, +7 enemy side.

prismsafe (new combat/stun_lock.cc; hooks in want_home, retreat_step, retreat, guard.cc, bank.cc) adds ~+0.5: our Prism
leaves, and keeps its work steps off, tiles where an enemy's stun and its next turn would kill it; unseen stunners are
remembered for one ability cooldown.

hold-sole and hold-sole2 (economy/capture.cc, economy/bank.cc, model/pathing.cc) finish the reallocation. Allies on the
tiles at payout split the gems, but extra holders add no contest protection (one enemy on any tile stops the count however
many of ours stand there); they matter only if the Prism leaves or dies first. In hold-safe games our Prism still shared
11.6% of its captures, 33 gems a game to co-holders. Traces of those payouts: 48% were co-holders on a capture recall
(`continue_recall` keeps it, so the yield is never reached), ~36% allies walking across the Prism's tiles in transit, and
only ~4% the threat gate of `yield_capture`.
- hold-sole: when the holder is a fit focus_holder Prism whose hold is counting, a co-holder steps off even under threat,
  to a tile no more exposed than its own (mend_step's test), only if a tile is already free, no strike is possible, and
  the Prism cannot leave before payout.
- hold-sole2: a capture-recall co-holder of such a hold skips the capture_recall keep (only that keep) when it has a
  step-off tile: its feint recall cancels, it steps off, and next turn's keeps decide the recall as usual (it still goes
  home to shop or heal, without the share). Routes (`Pathing::route`, `closer_neighbours`) put steps onto a Prism-held
  hold's tiles last among equally short steps.
- Effect (smoke, 406 both-Prism games): shared Prism captures 11.8% -> 5.0%, gems to co-holders 33 -> 15 a game, Prism
  share of capture gems 40.6% -> 42.9%. hold-sole alone read level (54.9%); its rule fires only in the ~4% case.


## Why this and not the obvious levers

The programme started from the prior that macro gains come from time at work, and spent its first two hours confirming
that ref's macro is tuned against itself: every weight we moved (banking line, retreat ratios, enemy memory, stickiness,
gold price, home and mid weights, join weight, Prism-only caution) reads flat or down (44-50%). The structural attempts
fared no better: exclusive claims (36.7%) showed that co-claims are not waste (two bodies clear faster, gift less and die
less); a Lanchester force model on contested groups (49.9%), two-stop routes (49.0%) and a home weight scaled by the live
ratio (49.8%) changed little. Aggression (deny, 44.1%) costs farm time.

The mirror replays then pointed at the Prism. The team whose Prism dies first loses 85%; Prisms die mostly to the other
Prism (53%), and the killer had the bigger bag 81% of the time. Within a close total, the team with the bigger Prism bag wins
66-67%, while a team 60+ gems ahead with the smaller Prism bag wins only 32-54%. So the bag on the Prism is power, not
risk: banking it to protect it (duel1, 46.4%) or making the Prism more careful (prismtimid, 47.0%) loses, and the Prism
dies from full health to the bigger enemy Prism, not to health lines. And 28% of the captures on groups our Prism had
helped clear paid it nothing, because the melee claimer stands on the tiles.

That made the lever a reallocation: the captures the team takes anyway, landed on the Prism. prismhold does only that, and
every attempt to also change where the Prism goes or what it fights lost or stayed level: pricing Focus into its farm and
kill values (prismhold2, 52.2%), preying on weaker enemy Prisms (prismhunt, 54.5%), a bolder Prism (hold-bold, 53.9%),
avoiding stronger ones (hold-yield, 55.1%), allies leaving groups for the Prism (hold-anchor, 55.3%), Prism kill-steals by
turn order (hold-kb). In hold-safe games where both teams have a Prism (about 80% of games; the drafts mirror), our Prism dies
first in 27.9% (we win 15%) and theirs in 33.8% (we win 88%); with no Prism death the game is level (51.9%). The gain is the
duel, and the duel is the bag: in 342 of 725 Prism-kills-Prism the victim struck first and still died, the killer's bag
bigger in 321 of them.


## Every A/B

All against `variants/ocean-ref-b7c87cf`, 2x fuel, own drafts. "dev" = s-500001..020 (10240 games), "held-out" =
s-500101..120 (10240), "block 3" = s-500023..040 (9216), "varied" = v-500201..210 (`--mix varied`, 5120), "final" =
s-500121..140 (10240, untouched until the final candidate). 95% CI in brackets. OOF = out-of-fuel turns, cand vs ref.

| Variant | What it changes | Suite | Win % | OOF |
|---|---|---|---|---|
| macro5-base | copy of ref (mirror) | dev | 50.0 (49.0-51.0) | equal |
| p-bigbank / p-bold / p-timid | banking line; retreat ratios x1.5 / x2/3 | dev | 49.5 / 49.7 / 49.3 | ~equal |
| p-track / p-stick / p-gold2 / p-gold05 | enemy memory 10 rounds; stickiness 1.6; gold price x2 / x0.5 | dev | 48.4 / 48.7 / 48.0 / 49.7 | ~equal |
| p-nohome / p-mid2 | home-ground weight off; mid-band exposure x2 | dev | 48.1 / 48.2 | ~equal |
| p-deny | cooked mode all game (enemy side x1.5, accept losses) | dev | 44.1 (43.1-45.0) | 673 vs 567 |
| duel1 / duel2 | Prism banks unless it out-Focuses the enemy Prism; + hunts a weak enemy Prism | dev | 46.4 / 46.4 | ~equal |
| contest | Lanchester P(win) on contested groups' worth and joins | dev | 49.9 (49.0-50.9) | 702 vs 529 |
| route | two-stop route rate on the top-4 farm candidates | dev | 49.0 (48.0-50.0) | 710 vs 475 |
| alive | home weight x live-pick ratio | dev | 49.8 (48.8-50.7) | ~equal |
| claims | exclusive solo claim ownership by seniority | dev | **36.7 (35.7-37.6)** | ~equal |
| p-join067 / p-join15 / p-join2 | join value x0.67 / x1.5 / x2 | dev | 45.9 / 49.6 / 45.5 | ~equal |
| p-prismtimid / p-prismbold | Prism-only retreat ratios and recall line x2/3 / x1.5 | dev | 47.0 / 49.6 | ~equal |
| prismsafe | our Prism avoids tiles where a stun plus the next turn kills it | dev | 50.7 (49.7-51.7) | 527 vs 512 |
| **prismhold** | a gem on the Prism priced at +5.625 gold of Focus in the holder choice; Prism pick-up | dev | **54.6 (53.6-55.6)** | 476 vs 477 |
| prismhold | | held-out | 53.8 (52.8-54.8) | 464 vs 463 |
| prismhold | | block 3 | 54.7 (53.7-55.7) | 493 vs 469 |
| prismhold | | varied | 51.8 (50.4-53.1) | 494 vs 498 |
| ph-f05 / ph-f2 | prismhold, Focus premium x0.5 / x2 | dev | 52.7 / 55.0 (54.1-56.0) | ~equal |
| prismhold2 | + Focus premium in the Prism's farm worth and kill values | dev | 52.2 (51.3-53.2) | 436 vs 475 |
| prismhunt | + our Prism preys on an enemy Prism it out-Focuses | dev | 54.5 (53.6-55.5) | ~equal |
| prismbig | + Prism sole holder of Monolith / multi-holder groups | dev | 54.6 (53.7-55.6) | ~equal |
| hold-bold | prismhold + p-prismbold | dev | 53.9 (52.9-54.9) | ~equal |
| **hold-safe** | prismhold + prismsafe | dev | **55.1 (54.2-56.1)** | 526 vs 498 |
| hold-safe | | held-out | 54.5 (53.5-55.5) | 480 vs 463 |
| hold-safe | | block 3 | 55.1 (54.1-56.1) | 521 vs 465 |
| hold-safe | | varied | 52.2 (50.8-53.5) | 543 vs 498 |
| hold-yield | hold-safe + avoid any out-Focusing enemy Prism's stun reach | dev | 55.1 (54.1-56.1) | ~equal |
| hold-anchor | hold-safe + allies price a group the Prism will take over at the Prism's walk | dev | 55.3 (54.4-56.3) | 520 vs 496 |
| hold-kb | hold-safe + the Prism's turn-order kill bid values a solo kill's bag at 2.69 gem-equivalents | dev | 55.0 (54.0-56.0) | 528 vs 504 |
| **hold-safe** | | **final** | **54.4 (53.4-55.4)** | 587 vs 514 |
| hold-sole | hold-safe + co-holder steps off a Prism-held hold under threat | dev | 54.9 (53.9-55.8) | 512 vs 489 |
| hold-duel | hold-safe + hunt a Prism we out-Focus, yield to one that out-Focuses us | dev | 55.1 (54.2-56.1) | 524 vs 476 |
| **hold-sole2** | hold-sole + capture-recall co-holders step off; routes avoid a Prism-held hold's tiles | dev | **56.6 (55.6-57.5)** | 575 vs 596 |
| hold-sole2 | | held-out | 57.0 (56.0-57.9) | 487 vs 453 |
| hold-sole2 | | block 3 | 57.8 (56.8-58.8) | 501 vs 472 |
| **hold-sole2** | | **final** | **56.9 (55.9-57.8)** | 588 vs 481 |
| hold-sole2 | | varied | 54.2 (52.8-55.6) | 553 vs 500 |
MORE_ROWS


## Lessons

- **Tuning is saturated against a tuned self.** Every ref weight sits on its optimum; +-50% moves read 44-50%. 60% needs a
  capability ref lacks, not a re-weighting.
- **Reallocate, don't redirect.** The one large gain moved rewards the team already captures (who holds) without changing
  where anyone walks. Every variant that changed where the Prism goes or what it fights read level or lost, even when its
  own metrics (bag size, Prism deaths) moved the intended way.
- **The bag is power.** Banking or caution to protect the Prism's bag lost: in the duel the bigger bag wins regardless of who
  strikes first. Derive values from the rules (1.5 Focus per gem at the Focus shard's price, 5.625 gold); the slope probes
  (x0.5 52.7, x1 54.6, x2 55.0) show the premium acts as a switch, so the derived value is enough.
- **Co-claims are not waste.** Exclusive claims cost 13 points: concentration has a steep slope.
- **Measure who wins and why before designing.** The decisive diagnostics were mirror-replay splits (first Prism death,
  bag gap at close totals, captures the Prism helped clear but took no share of), not the A/B win rates of probes.
- **Gains are draft-bound.** With mirror drafts, games without Prisms (~20%) stay at exactly 50%: the design moves only Prism
  games (~56% there). Off the ladder mix (--mix varied) it shrinks to ~52%.

