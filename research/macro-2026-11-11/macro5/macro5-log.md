# macro5 running log (lead)

Brief: macro5-brief.md. Worktree /home/ubuntu/wt/macro5, branch macro5-20261111. Ref: bots/variants/ocean-ref-b7c87cf.
Every A/B: `--no-test-draft --fuel 200000`, against the ref only. Maps: /home/ubuntu/wt/macro5-maps/s-<seed> (ladder-v2).

## Suites
- s-500001..500040: dev pool (generated 01:40 UTC 2026-11-11).
- Held-out confirmation seeds: 500101+ (not yet generated).

## Timeline
- 01:40 start. Read brief, AGENTS, rules. Copied ref -> variants/macro5-base (identical; for mirror replays).

## Priors (from EXPERIMENTS macro programmes, 2026-10-30 on astraeus)
- Champions walk 51-55% of time; camps abundant; champion time & health bind.
- Gains came from time-at-work (give way less, later recalls, recall as travel, no waiting at respawns).
- Coordination toward fights (hunts, bursts, distress/assist, tank formation, team ops) lost every time.
- Shared info (capture record, claims) worth ~6 points; enemy sightings in comms hurt (-2).

## Plan / hypotheses
(filled below)
- (log times up to here were estimates; real clock: start 01:40, 02:46 at the claims launch)
- 01:45 mirror macro5-base vs ref: exactly 50.0% of 10240 (deterministic: identical bots split every map). 10k games take ~3 min
  (0.3 s a game native at 2x fuel). Out-of-fuel 500 turns per side in 10k games at 2x. Median game 753 rounds; 2% reach 2000.
  => testing is cheap; implementation is the bottleneck.
- 01:50 architecture survey (Explore agent). Key facts:
  - decide() is a strict priority cascade (bot.cc:366-519): channels > shop-on-spawn > game_ender > mend/want_home(retreat)
    > support > capture join/yield/handoff > strike search > hold > banks_bag/carry_bag > wants_shop > guard_turn > chase
    > contest > kite/siege > willow_follow > farm. Scores only inside branches.
  - Farm: rate(worth, r) = worth / (r (1 + r/H)), H = 100 max(1, side/50). worth = home_ground^1.89 x mid-band exposure (up to 1.36)
    x stickiness 1.2 x (gems + per_gold gold). Claims (comms) price claimed groups as a share; not exclusive.
    Crews for strong groups (plan_crew), 4-round bail, 26-round ban.
  - Comms 8 bytes: per-ally claim field, one bag slot, one capture record, healer-follow position. No enemy sightings.
  - Enemy memory dies after track_horizon=3 rounds. No model of where the enemy farms; denial is local/opportunistic
    (contest_capture in vision, cooked-mode x1.5).
  - Banking/shop/retreat fully individual. want_home pre-empts all macro.
  - Plug points: farm.cc:1792-1817 weight block (beware max_exposure prune bounds farm.cc:371-583); deterministic team
    plans as in siege_candidate/guarding(); open_plan is already a team assignment solver (draft time, r<=100).
- 01:58 probes (10240 games, s-500001..020): bigbank 49.5 (48.5-50.4), bold 49.7 (48.8-50.7), timid 49.3 (48.3-50.2). Flat.
- 02:05 probes: track10 48.4, stick1.6 48.7, gold x2 48.0, gold x0.5 49.7. All flat or slightly down: tuned knobs sit on a flat optimum vs ref.
- 02:12 probes: nohome (home_power 0) 48.1, mid2 48.2, deny (cooked mode all game: enemy-side x1.5, mirror pull, accept_lost) 44.1 (43.1-45.0). Aggression toward the enemy side loses clearly. Auditor note: ref's opening-plan x1.5 weight breaks the weight<=1 prune bounds (farm.cc:1797) for r<=100.
- 02:15 idle supply (mirror, r1-600, gems/round per side at nominal rate gems/respawn; idle = group up and asleep):
  own side: clusters idle 31% of time, wolf groups 48%, elk groups 45%, golem 65%, Monolith 93%. Idle own-side supply
  ~2.7 gems/round per side vs a team income of ~1.3: supply is not binding; power (DPS, health) and time are.
- 02:30 replay study (546 decisive mirror games; scratch study/ dir). Failure modes:
  M1 bag carrier caught 25% (Prism hoard: Prism mean bag 110 vs Vesper 15; Prism deaths = 64% of gems lost to kills; team whose Prism
     dies first loses 85% (n=1079), even with a 0-19 bag; Prism kills Prism in 53% of Prism deaths, killer had the bigger bag 80%).
  M2 outnumbered in the middle 36%: enemies converge on the victim (within 6: 0.5 -> 2.1 over 20 rounds), victim's allies stay at 1.5.
  M3 contested mid group lost 31%: more bodies take 82% of contested captures, more health 77%, first arriver 61%; losers gift 5.4% of
     camp damage to the enemy (winners 2.5%); team that gifts less wins 69%.
  M4 own-side tempo 4%. Walking is equal on both sides (52-53%).
  r300 gem lead +232 = mid/enemy captures +125, bag swings +82, own captures +21.
- 02:35 Prism in 81% of games per team (Cassi/Issac 97%). retaining_gems (bank.cc:780): Prism keeps its whole bag unless winning/closing.
  Launched two implementation tracks:
  A) macro5-contest: Lanchester local force (Σhp x Σdmg like the pack zone) per contested group over arrival+clear+capture window;
     farm worth x P_win, joining value + marginal P_win gain (reinforcement emerges from valuation). Targets M3/M2.
  B) macro5-duel1: Prism retains its bag only while its bag >= the enemy Prism's last-known bag (persistent profile), else banks.
     macro5-duel2: + dominant Prism treats a visible weaker enemy Prism as preferred prey. Targets M1.
- 02:45 deny diag (1200 games): cand enemy-side caps +26 gems, mid +7, but own-side -82, camp damage -10%, capture gold -370,
  deaths +0.5. Aggression costs farm time (walking); ref's own-side take even rises. Any macro that adds walking loses.
  Tools: scratchpad/ab.sh (launch), waitab.sh, brk.py (by map metrics), diag.sh + an/cmp.py (per-bot diagnostics).
- 03:05 duel1 (Prism retains only while it out-Focuses the enemy Prism, else banks) 46.4% (45.4-47.3) of 10240; duel2 (+ hunt a
  one-shottable enemy Prism) 46.4%, same (duel_prey rarely fires). Diag: Prism gems lost -9, but captures down everywhere
  (own -12, mid -9, enemy -12), camp damage -2%: banking costs trips and Focus. The bag is power; ceding it loses. Dropped.
  Lesson: the duel is won by having the bigger bag, not by protecting a smaller one.
- 03:25 contest (Lanchester P_win on contested groups' worth + marginal join gain) 49.9% (49.0-50.9) of 10240; OOF 702 vs 529.
  Diag: gifted -74, mid caps -5, deaths -0.2, prism lost -6: the force model barely changes outcomes. Level -> park.
  Launched macro5-route (two-stop route rate lookahead on top-4 solo/crew candidates) and macro5-alive (home_power x live ratio).
- 03:55 debug mirror (512 games, s-500021/22, D lines; an/trips.py, an/switch*.py): claim trips that yield the team a capture
  of that group 47.6% of body-turns; abandoned trips 31.8%: farm re-pricing switch before any hit 10.4% (158/game, 6 turns),
  retreat before any hit 5.5% (125/game, 4 turns), retreat after hitting 4.5%, switch after hitting 3.4%, enemy took it 3.4%.
  Of 195 switches/game away from an uncaptured claim: 43% while an ally claims the same group (21% of all: both drop it, no
  capture; 20%: we claimed first and still yielded), 32% A-B-A within 20 rounds. Claim coordination is a measurable waste.
- 04:00 alive (home_power x live-pick ratio) 49.8% (48.8-50.7). Level.
- 02:55 (real clock) retreat starts (debug mirror): 245/game, 77% last <=2 turns, 58% at hp >= 0.85, nearest enemy <= 8 in 92%,
  60% in the mid band; 25% with 4+ of ours vs 3 of theirs within 8 (fight rosters count visible allies within 4, 7 if chasing).
  Died within 15 rounds after only 6%. Mostly give-way flickers.
  Elasticity reading: deny's -10% camp damage cost ~6 points, so recovering a third of the 31.8% abandoned-trip time could be
  worth ~+10 if it costs nothing elsewhere. Abandoned trips are the main lever.
- 02:47 launched macro5-claims (exclusive solo ownership by claim seniority; owner never yields to later claimers).
- 03:05 route (two-stop route rate on top-4 solo/crew) 49.0% (48.0-50.0); OOF 710 vs 475. Level/down.
- 03:10 kills: first kill by r150 in 35% of games, killer team wins 65%; kill diff at r150 +1 -> 66%, +2 -> 70%, +3 -> 79%.
  Early cohesion (ally within 3, r5-200, 58% of body-rounds) gap > 0.05: more cohesive team +0.13 kills by r200, wins 53.1%.
  C&I are 38.5% of deaths, but not more separated at death (10.7) than on average (12.7): separation is not the cause.
- 03:22 claims (exclusive solo ownership by claim seniority; ally-owned non-crew groups skipped) **36.7% (35.7-37.6) of 10240**: -13.3.
  Diag (1200): captures own -55, mid -29, enemy -20; camp damage -4%; gifted +977 (+26%); deaths +0.7; tributes -2.5.
  The "wasted" co-claims are not waste: two bodies on one group clear faster, give away less and die less. Concentration has
  a steep slope. Next: measure the join's weight slope (probes join x0.67 / x1.5 / x2) before designing a team-marginal join value.
- 03:16 debug branch shares (dbg mirror): F farm 57.6% of body-turns (moving 67%, hitting a camp 28%), B bank 8.3% (moving 88%),
  dead/none 7.2%, R retreat 5.7%, h willow 5.7%, P hold 5.1%. Bodies hit camps on ~17% of all turns.
- 03:24 switch traces (macro5-trace = ref + debug-only SW lines; release replays byte-identical to ref; debug mirror 1024 games
  s-500021/22, 50.0%): 87 switches/game per team away from a live uncaptured group. Old's code: S solo 46%, Q "its claimers clear
  it before we arrive" 26%, J 11%. Flags vs the previous pricing turn: an ally claims old 38+7%, old's health fell 27%, new's state
  changed 22%, old's state 13%, none 28%. new/old value: old unvalued 32%, >=2x 20%, <1.1x only 12%. A-B-A within 20 rounds 17%.
  Mostly reasoned re-pricing (an ally will finish it, states change), not noise: hysteresis has little to recover.
- Capture cycles by our hitters (mirror): 1 body 99k cycles 92.1% ours; 2 bodies 94.4%; 3+ 95.1%. Gifted damage share ~4.5% each.
- 03:34 join-weight probes (J value and its bounds x w): x0.67 45.9% (45.0-46.9), x1.5 49.6% (48.6-50.6), x2 45.5% (44.5-46.4).
  The join is at its optimum too; claims' -13 is joins removed. Every weight we have moved sits on a tuned optimum against
  itself: 60% needs a capability ref lacks, not a re-weighting.
- 03:45 endgame (mirror, 1962 decided games): the first team to hold a winning total (tributed + carried >= 1000) wins 91.5%;
  it takes a median 30 rounds (quartiles 15-64) from that moment to the win (2.1 carriers needed, max bag median 195 = a
  20-turn channel). Losers held a winning total at the end in 13% of games. First-but-lost (8.5%): bags 315, 17 from an
  altar, 2.1 carriers killed. Endgame execution is worth a few points at most.
- 03:50 Prism deaths to champions (2322 in 2000 mirror games): killer Prism 53%, Vesper 21%, Cassi 6%. By a Prism: killer's
  bag bigger 81%, victim saw the killer within the last 12 rounds 90% (when it first came within 8: 45%), at full health
  12 rounds before; victim bag median 40, death round median 550, victim team won 15%.
  Launched probes macro5-p-prismtimid / prismbold (Prism-only retreat ratios and recall line) to read the slope.
- 03:52 Prism-only caution probes: prismtimid (retreat ratios x2/3, recall line room x2/3: 0.32 -> 0.54) 47.0% (46.0-47.9);
  prismbold (x1.5, recall line at the 0.05 floor) 49.6% (48.6-50.5). Diag timid: Prism deaths unchanged (0.5/game), captures
  down everywhere, gifted +362. Health lines don't protect the Prism: it dies from full health to bursts (stun-locks).
  macro5-prismsafe (stun-lock lethal reach avoidance for our Prism) is being built.
- 03:55 Prism bag vs team total (mirror, both Prisms alive): with totals within 60 at r200/r300, the team whose Prism carries
  40+ more gems wins 66% / 67%; a team 60+ ahead in total but with the smaller Prism bag wins only 32% (r200, n25) / 54% (r300)
  against 76-79% for any 60+ lead. Prism takes 34% of capture gems (r<=400) and shares only 12% of the captures it attends.
- 04:00 captures our Prism damaged in that cycle but took no share of: 18.4k of 66.2k (28%), gems = 46% of the Prism's capture
  gems (it hits from range 3-4; the melee claimer holds). Launched macro5-prismhold: the Prism is the preferred holder of
  gem captures via holder_value (a gem on the Prism also buys 1.5 Focus = 1.5/8 of a 30-gold Focus shard, ~5.6 gold) and
  pick_up of groups it helped clear.
- 04:25 prismsafe (our Prism leaves/avoids tiles where an enemy's stun plus its next turn kills it; unseen lockers remembered
  for one cooldown) 50.7% (49.7-51.7) of 10240; OOF 527 vs 512. Fires ~1.5 turns a game; diag: Prism deaths 0.5 vs 0.5, nothing
  else moves. Stun-locks are not how Prisms die (only 26% of Prism deaths follow a stun in the last 5 rounds). Parked.
- 04:29 **prismhold 54.6% (53.6-55.6) of 10240** (s-500001..020); OOF 476 vs 477. First real gain.
  Design: holder_value prices a gem on the Prism at +1.5 Focus = 1.5/8 of a 30-gold Focus shard (5.625 gold), so value_holder /
  outvalues_holders / pick_up make our Prism the holder of gem captures it can reach before payout (incumbent steps off when
  no threat; endgame exemptions kept). Smoke: Prism share of capture gems 39.5% vs 33.9%, r300 Prism bag 134 vs 108.
  Diag (1200): enemy caps +7, mid +2, own +4, camp damage +0.9%, deaths -0.3, gems lost to kills -13 (Prism -10), gifted -62.
  Broad over map classes (picks 3/4/5: 52.0/53.2/55.6). Held-out s-500101..120 launched.
- 04:36 prismhold held-out (s-500101..120): **53.8% (52.8-54.8) of 10240**; OOF 464 vs 463. Confirmed. Copied to bots/ocean.
- 04:40 prismhold games (1200 extracted): Prism bag cand/ref r100 41/29, r200 96/74, r300 160/127, r400 231/182, r600 305/259;
  Prism-kills-Prism 475 cand vs 352 ref. Launched prismhold2 (Prism farm worth and kill value include the Focus premium)
  and slope probes ph-f2 / ph-f05 (premium x2 / x0.5).
- 04:44 premium slope on prismhold: x0.5 52.7% (51.7-53.7), x1 54.6%, x2 55.0% (54.1-56.0). Monotone, flattening above the
  derived value: the premium acts mostly as a switch (the Prism wins the holder comparison); keep the rule-derived 5.625.
- Mechanics audit (Explore agent, read-only): ref covers nearly every rule. Untried: camp fire on enemies in fight trades,
  holding back an enemy group's respawn by standing on it, touch-resets of enemy holds. ref also publishes its claim, rank and
  chase bit unencoded in its priority payload; decoding it would be self-play overfit, not pursued.
- 04:58 launched macro5-prismhunt (on prismhold: our Prism treats a visible enemy Prism it out-Focuses as prey; every fight gate kept).
- 05:08 prismhold2 (prismhold + the Prism's farm worth of groups it holds and its kill bag values include the Focus premium,
  all prune bounds scaled) **52.2% (51.3-53.2)**: -2.4 vs prismhold. Smoke: r300 bag +8-11 but capture share flat and Prism deaths
  up (0.88-0.97 vs 0.73). Pricing Focus into where the Prism goes/fights loses; pricing it into who holds what is already
  reached wins. Dropped.
- 05:13 prismhunt (prismhold + our Prism preys on a visible enemy Prism it out-Focuses, all fight gates kept) 54.5% (53.6-55.5): level with prismhold. Fires ~0.5/game, mostly on empty-bag Prisms. Dropped.
- 05:17 hold-safe (prismhold + prismsafe merged cleanly) 55.1% (54.2-56.1) of 10240 dev; OOF 526 vs 498. +0.5 over prismhold, inside noise; held-out run launched.
- 05:21 hold-safe held-out (s-500101..120) 54.5% (53.5-55.5) vs prismhold's 53.8% there; pooled 20480: hold-safe 54.8, prismhold
  54.2 (+0.6, not significant). Launched macro5-prismbig (Prism sole holder of Monolith / multi-holder groups) and
  macro5-hold-bold (prismhold + the prismbold probe: does a bigger Prism want to stand more?).
- 05:26 hold-bold (prismhold + prismbold) 53.9% (52.9-54.9): -0.7 vs prismhold. A bigger Prism still doesn't want to stand more. Dropped.
- 05:28 endgame in prismhold games: cand first to a winning total in 54% of games, converts 90.7% (lag median 37 rounds)
  vs ref 91.0% (lag 30): the bigger bag converts as often but slower.
- 05:30 launched macro5-hold-yield (hold-safe + our Prism treats any enemy Prism that out-Focuses it as a locker: out of its stun reach).
- 05:51 hold-yield (hold-safe + yield to any out-Focusing enemy Prism) 55.1% (54.1-56.1): level with hold-safe; smoke Prism deaths -0.12/game but capture -13 gems. Dropped.
- 05:56 third block (s-500023..040, 9216 games): prismhold 54.7% (53.7-55.7), hold-safe 55.1% (54.1-56.1). Over 29,696 games each:
  prismhold 54.4%, hold-safe 54.9%; hold-safe ahead in all three blocks (+0.5, +0.7, +0.4).
- 05:59 launched macro5-hold-anchor (hold-safe + non-Prism allies waive the capture rounds of gem groups our Prism will take over).
- 06:04 prismbig (Prism sole holder of Monolith/multi-holder groups) 54.6% (53.7-55.6): identical to prismhold; the win/closing exemption blocks it (Prism bag + Monolith usually wins). Dropped.
- 06:08 varied stress mix (v-500201..210, 5120 games): hold-safe 52.2% (50.8-53.5), prismhold 51.8% (50.4-53.1). Positive but smaller off the ladder-v2 mix.
- 06:34 hold-safe diag (1200): captures enemy +10, mid +6, own +9; gems lost -10 (Prism -8.5); Prism deaths 0.4 vs 0.6;
  gifted -198. By drafts (mirror drafts: both teams have a Prism or neither): no-Prism games 50.0% (n244), Prism games 53.7% (n956).
  The whole gain is in the ~80% of games with Prisms (~56% there).
- 06:34 hold-anchor (hold-safe + non-Prism allies price a gem group our Prism will take over at the Prism's walk, not
  the full capture) 55.3% (54.4-56.3): level with hold-safe (55.1) on the same suites; smoke changed 16/192 games. Dropped (adds code, no gain).
- 06:36 hold-safe Prism games (956): our Prism dies first 27.9% (we win 15.0%), theirs first 33.8% (we win 87.6%),
  neither 38.3% (51.9%). The gain is the duel: no-death games are near level. Prism-kills-Prism (725): the victim struck
  first in 342 and still died, the killer's bag bigger in 321 of those. The duel is decided by the bag, not first strike or
  spacing: the only lever there is the bag itself.
- 06:49 hold-kb (hold-safe + the Prism's turn-order kill bid values the victim's bag at 2.69 gem-equivalents when its
  own blow kills alone) 55.0% (54.0-56.0): level. Smoke: 43/768 games differ; Prism kill-gem share 60.6% vs 61.2%. Kills the
  Prism could land alone that only turn order decides are ~0.5 a game. Dropped.
- 06:49 launched macro5-hold-sole (hold-safe + a co-holder steps off a Prism-held group even under threat, when its
  step is no more threatened): our Prism shares 12.9% of its captures, ~20 gems a game per team to others. Final
  confirmation of hold-safe on the reserved s-500121..140 running.
- 06:51 **hold-safe final confirmation (reserved s-500121..140): 54.4% (53.4-55.4) of 10240**; OOF 587 vs 514.
  Over four suites blocks (39,936 games): 21,878 wins = **54.8% (54.3-55.3)**. bots/ocean = hold-safe (139d4d9aa).
- 07:15 hold-sole (hold-safe + a co-holder steps off a Prism-held group under threat too, to a no-more-exposed tile)
  54.9% (53.9-55.8): level. Smoke traces of the shared Prism payouts: 48% are co-holders on a capture recall (yield never
  reached), ~36% allies walking onto the Prism's hold that turn, only ~4% the threat-gated yield. Launched hold-sole2
  (recall co-holders step off; paths treat a Prism-held hold as taken).
- 07:25 hold-duel (hold-safe + one Focus comparison: hunt a Prism we out-Focus, yield to one that out-Focuses us;
  the yield's ready-stun bug fixed) 55.1% (54.2-56.1): identical to hold-safe. Smoke: their Prism killed ours 68 vs 89 on
  ladder maps, no change on gen; results differ in 4-7% of games. Dropped: once the bag is bigger, moving the Prism toward or
  away from the duel adds nothing.
- 07:46 **hold-sole2** (hold-sole + a capture-recall co-holder cancels its feint recall to step off a Prism-held hold;
  routes put steps onto a Prism-held hold's tiles last among equally short steps): dev **56.6% (55.6-57.5)**, held-out
  s-500101..120 **57.0% (56.0-57.9)**, block 3 **57.8% (56.8-58.8)**; +1.5/+2.5/+2.7 over hold-safe on the same maps. Smoke:
  shared Prism captures 11.8% -> 5.0%, gems to co-holders 33 -> 15 a game, Prism share of capture gems 40.6 -> 42.9%.
  Final s-500121..140 and varied launched.
- 07:49 **hold-sole2 final (reserved s-500121..140): 56.9% (55.9-57.8)**; OOF 588 vs 481. Over four blocks (39,936 games):
  22,776 wins = **57.0% (56.5-57.5)**, +2.2 over hold-safe on the same maps. bots/ocean = hold-sole2 (e99ae435e).
  Launched hold-sole3 (payout-round transit detours; higher-id co-holders kept by bank/shop keeps).
- 07:49 hold-sole2 varied (v-500201..210, 5120): 54.2% (52.8-55.6) vs hold-safe 52.2%: the gain holds off the ladder mix.
