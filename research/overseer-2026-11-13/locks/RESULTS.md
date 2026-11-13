# Altar-lock policy family (charybdis, 2026-11-13)

Question: under which map features and game states do charybdis's altar locks pay? Every variant below is
`bots/variants/lockpol-<tag>`. Each is a copy of `lockpol-base` that differs only in `params::lock_policy` (params.h).
Each played charybdis at normal fuel with its own draft, on `maps/suites/overseer-nyx` (20,480 maps, 40,960 games).
The best was then confirmed on the fresh `maps/suites/overseer-lockconf` (seeds 148100-148179, 40,960 games).

## Policy layer (lockpol-base)

- `params::lock_policy` sets the buy gates: altars, enemy altar options, round, the enemy threat (tributed gems,
  optionally plus its largest live bag seen since its score last rose), and gold spent on shards.
- It also sets the cancel rules: on/off, game-ending only, a minimum bag, and safe-only. "Safe" is
  `tribute_safe`'s kill test over `tribute_window`.
- It sets the pre-emptive rules: on/off, a maximum altar count, contested-only, and, on maps with 3 or fewer
  altars, the enemy's side or the enemy's only option.
- `hard_stop` controls whether a carried lock counts as a sure stop. It covers `holds_hard_stop`, `intercept_steps`,
  `ally_stops` and `stop_game_ender`'s goal tiles and `hard`, and it only applies while cancels are on.
- Static features are computed once per altar: `enemy_side` is `our_side` from the enemy's spawn.
- **Identity:** with every switch at its default, lockpol-base equals charybdis. `tools/fuel/bench.py --set wide`
  gave 52/52 byte-identical replays with own drafts and 52/52 with `--test-draft`, at 100M fuel, fuel +0.01%. It
  was rechecked after the last layer change, with the same result.
- **Audit:** a read-only auditor found two problems, both fixed before any full run:
  - `preempt_contested` could never fire. Contested altars are already on our side, so the `contest` flag was
    redefined as the enemy's side.
  - In `win` and `bag20`, a lock counted as a hard stop that `place_lock` then refused to place. Those cancels now
    also accept any `enemy_tribute_wins` ender, and the hard stop needs cancels on.
- **Smokes:** every variant played 256 ladder games: 0 errors, no DRAFT-UNFINISHED or PLAN-CHECK.

## Results on overseer-nyx (vs charybdis, 40,960 games each)

The CI is ab.py's, over games. The split columns give the CAND win % on map pairs, and their CIs are about
±0.6-1.4. Game length is post-treatment, so it only suggests where an effect lands. OOF is out-of-fuel turns over
the whole A/B.

| variant | rule | win % (95% CI) | OOF turns cand / ref | altars 1 / 2 / 3-4 / 5+ | rounds <600 / 600-899 / 900-1499 / 1500+ |
|---|---|---|---|---|---|
| nolock-100k | never buy (chy-nolock) | 51.0 (50.5-51.5) | 248,720 / 253,135 | 51.0 / 51.4 / 50.5 / 51.0 | 49.7 / 50.3 / 52.7 / 53.4 |
| cancel | cancels only, no pre-emptive locks | 50.0 (49.5-50.5) | 251,559 / 253,870 | 49.1 / 50.2 / 50.2 / 50.7 | 50.1 / 50.6 / 49.5 / 48.5 |
| preempt | pre-emptive only, no cancels, not a hard stop | 49.8 (49.3-50.2) | 253,361 / 254,609 | 50.1 / 49.9 / 49.3 / 49.4 | 48.8 / 48.9 / 51.2 / 52.0 |
| win | cancel only game-ending tributes, no pre-emptive | 49.7 (49.2-50.2) | 251,457 / 253,188 | 48.4 / 50.0 / 50.0 / 50.6 | 50.4 / 49.9 / 49.3 / 47.5 |
| nohard | full policy, lock never a hard stop | 49.8 (49.3-50.3) | 253,545 / 253,880 | 50.1 / 50.0 / 49.4 / 49.6 | 48.9 / 49.2 / 50.9 / 52.2 |
| alt2 | buy only on <= 2 altars | 50.2 (49.7-50.7) | 252,127 / 252,906 | 50.0 / 50.0 / 50.4 / 50.9 | 50.0 / 50.2 / 50.4 / 50.4 |
| alt3 | buy only on <= 3 altars | 50.1 (49.6-50.6) | 252,688 / 253,282 | 50.0 / 50.0 / 50.1 / 50.9 | 49.8 / 50.1 / 50.4 / 50.4 |
| eopt1 | buy only when the enemy has <= 1 altar option | 50.3 (49.8-50.8) | 251,679 / 251,861 | 49.7 / 50.4 / 50.5 / 50.6 | 49.8 / 50.0 / 50.6 / 51.7 |
| alt2-else-cancel | full on <= 2 altars, cancel-only elsewhere | 50.1 (49.6-50.6) | 253,169 / 253,584 | 50.0 / 50.0 / 50.2 / 50.7 | 50.0 / 50.3 / 50.0 / 49.7 |
| **end500** | buy once enemy score >= 500, full policy | **51.1 (50.6-51.6)** | 249,149 / 251,826 | 51.3 / 51.4 / 50.4 / 50.7 | 49.7 / 50.4 / 52.4 / 54.1 |
| end700 | buy once enemy score + largest seen bag >= 700 | 50.8 (50.3-51.3) | 251,510 / 251,999 | 50.7 / 50.9 / 51.4 / 49.2 | 50.2 / 50.8 / 51.3 / 51.1 |
| contest | full, plus on <= 3 altars the enemy's side pre-emptively | 50.1 (49.6-50.6) | 255,521 / 255,376 | 50.0 / 50.2 / 50.0 / 50.0 | 50.0 / 50.0 / 50.1 / 50.6 |
| precontest | pre-emptive only on contested (and guarded) altars | 50.1 (49.6-50.5) | 254,744 / 254,746 | 50.0 / 50.1 / 50.2 / 49.7 | 49.9 / 50.3 / 50.1 / 49.3 |
| rich | buy once this body spent 300+ gold on shards | 50.4 (49.9-50.9) | 253,992 / 252,855 | 50.5 / 50.3 / 50.1 / 51.5 | 49.9 / 50.5 / 50.8 / 50.5 |
| bag20 | cancel only bags of 20+ (winning always), no pre-emptive | 49.9 (49.4-50.4) | 251,329 / 253,244 | 48.9 / 50.2 / 50.2 / 50.7 | 50.3 / 50.4 / 49.5 / 48.0 |
| cancel-nohard | cancels only, not a hard stop | 49.8 (49.3-50.3) | 252,692 / 255,313 | 49.3 / 50.0 / 49.9 / 50.3 | 49.0 / 49.4 / 51.0 / 50.9 |
| win-nohard | cancel only game-ending, not a hard stop | 49.8 (49.3-50.2) | 251,005 / 255,474 | 49.1 / 50.0 / 49.9 / 50.2 | 49.0 / 49.2 / 51.2 / 50.2 |
| safe | full; non-winning cancels only where we cannot be killed within tribute_window | 49.9 (49.4-50.4) | 255,053 / 255,444 | 49.9 / 49.9 / 50.0 / 49.9 | 50.0 / 50.0 / 49.8 / 49.6 |
| safe-cancel | safe cancels only, no pre-emptive | 50.0 (49.5-50.4) | 252,689 / 253,455 | 48.9 / 50.2 / 50.3 / 50.8 | 50.5 / 50.4 / 49.4 / 48.3 |
| inert | buy and carry, never place, never a hard stop | 49.7 (48.8-50.6), stopped at 11,935 games | n/a (stopped early) | | |

None of the variants had a failed game, an early loss or a capped draft. Enemy-option and contested splits
(`splits-all.json`) are flat for every variant: no bucket moves more than its CI, and nolock is 51.4 / 50.5 / 51.0
on 1 / 2 / 3+ enemy options.

## Confirmation on overseer-lockconf (fresh, 40,960 games each)

| A/B | win % (95% CI) | OOF cand / ref | altars 1 / 2 / 3-4 / 5+ |
|---|---|---|---|
| end500 vs charybdis | **50.85 (50.36-51.33)** | 249,429 / 253,679 | 50.7 / 51.0 / 50.5 / 51.2 |
| end500 vs chy-nolock | **50.00 (49.52-50.48)** | 250,149 / 249,359 | 50.1 / 50.1 / 49.9 / 49.6 |

## What locks do in charybdis's games (replays)

Source: 3,000 random games of the nolock arm (charybdis vs chy-nolock), from `lockuse.py` on the extraction
(`lockuse-nolock-arm.txt`). Figures are per game; "L" is charybdis.

- **Buying and placing.** charybdis buys 7.3 locks a game and places 3.8. Of the placements, 3.2 are pre-emptive.
  The enemy destroys 2.6 of them, and they block 0 tribute attempts: the enemy breaks a lock or goes elsewhere.
- **Cancels.** charybdis cancels 0.75 enemy tributes a game, almost all of 20+ gems. In 1500+ round games the figure
  is 3.4 cancels, of game-ending bags averaging about 1,300 gems.
- **Fate of a cancelled bag.** The enemy later banks it 51% of the time. Its carrier is killed 8% of the time. In
  the rest (41%) the game ends with the bag still carried.
- **Own tributes.** A lock cancels one of our own tributes 0.004 times a game, which is negligible.
- **Deaths after a cancel.** Within 15 rounds and 4 tiles of a cancel, charybdis loses 0.54 bodies a game, against
  0.05 for the enemy. charybdis's bodies die 7.02 times a game, against 6.52 for chy-nolock. That +0.50 equals the
  post-cancel excess.
- **Deaths while approaching.** Deaths beside an enemy tribute are 0.12 against 0.06 a game.

The canceller stands within 2 of a carrier that has just been freed from its channel, and loses that fight. Even
so, the A/Bs show that removing the cancels or the hard-stop approach does not recover the loss. `cancel`, `win`,
`bag20`, `safe` and the `-nohard` variants all stay at 49.7-50.1. Only buying late does.

## Conclusions

1. **The cost of charybdis's locks is buying them early, not placing them.**
   - Every variant that buys from the first shop sits at 49.7-50.4, whatever its placement rules: no cancels, only
     game-ending cancels, safe cancels, no pre-emptive locks, pre-emptive on more altars, or no hard stop.
   - Gating the purchase on the game state recovers the whole no-lock gain. end500 reads 51.1 on nyx and 50.85 on
     the fresh suite, against no-lock's 51.0.
   - Gating on gold spent (rich) and on map features (alt2, alt3, eopt1) recovers part of it, roughly in proportion
     to how many games they keep from buying.
   - `inert` buys and carries locks but never places one. It reads 49.7 ±0.9 over 11,935 games, about where
     charybdis is and 1.3 below never-buying. It was stopped early because the shared pool gave it about 2.5k games
     an hour. So the purchase alone accounts for most of the deficit, and what charybdis's placements add is about
     0.3 ±1, which is nothing measurable.
   - The 10 gold is spent after the visit's shards. The cost comes on later visits: every body's first lock leaves
     it 10 gold short of the next emblem (`wants_shop` waits for `emblem_price`), so the next shopping trip comes
     later. This happens early in the game, when tempo matters most.
2. **No map feature makes locks pay** against this opponent.
   - No-lock beats charybdis in every altar bucket (51.0 / 51.4 / 50.5 / 51.0 on 1 / 2 / 3-4 / 5+), every
     enemy-option bucket and every contested bucket.
   - The one map signal is that pre-emptive locks matter on single-altar maps. Cancel-only variants lose about 1
     point there (48.4-49.3 against charybdis's 50). But never buying is still better on those maps (51.0), so
     there is nothing to build on.
3. **Late locks are neutral.** end500 against chy-nolock is 50.00% (49.52-50.48) over 40,960 fresh games, and its
   splits are flat. Cancelling the enemy's late tributes and locking our altars, once the enemy has 500 tributed,
   neither wins nor loses games here.
4. **The hard stop splits by game length.** Every `-nohard` variant reads about 1 point worse in games under 900
   rounds and 1-2 points better in games over 900. The two cancel out (49.8 overall). Game length is
   post-treatment, so this only suggests that the "whatever the risk" approach wins some short games and costs
   some long ones.
5. **Fuel:** end500 has 1-2% fewer out-of-fuel turns than charybdis (249k against 252-254k), the same as no-lock.

## Recommendation

**Buy altar locks only once the enemy's tributed score reaches 500 (`lockpol-end500`), with charybdis's placement
policy unchanged.**

- It beats charybdis by +1.1 (nyx) and +0.85 (fresh lockconf), with matching splits, and ties never-buying (50.00%
  on fresh maps).
- It removes the measured cost, which is early gold, and keeps the stop the rules make unique. Short of a kill, a
  lock is the only way to cancel a stun-immune Marcella's tribute, and the only stop that needs no ready ability.
  On this evidence that insurance costs nothing, and it may matter more against ladder bots' large endgame bags
  than against charybdis's own.
- 500 (half of `result.win`'s 1000) was one of the two endgame gates set before testing. The other, end700 (score
  plus the largest seen bag), reads 50.8. Both say the same thing: any late gate removes the cost. Treat the
  threshold as a convenient late point, not a tuned value.
- If the simpler code is preferred, never buying (chy-nolock) is statistically identical on these suites.
- Do not ship any placement-rule variant; none moved the result.

Files:
- `bots/variants/lockpol-*`: the variants. `lockpol-chy` is a frozen charybdis copy used for the identity bench.
- `make_variants.py`: the variant table. `split.py` and `table.py`: the splits. `altarsides.mjs`: the map features,
  in `replays/overseer/nyx-sides.json` and `replays/overseer/lockconf-sides.json`. `lockuse.py`: the replay
  measures.
- `splits-*.json`: the per-bucket reads.
