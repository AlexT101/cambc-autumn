# herbert and herbert_advcombat

Two bots by HerbertTheBird, added in e32257b (2026-10-18) and deleted in a1efff2 (2026-10-21). Read the code with `git show e32257b:bots/herbert/src/<file>`, or export it with `git archive e32257b bots/herbert bots/herbert_advcombat`.

In their comments, "Hyperion" (`namespace hyp`, "Hyperion:" tags) is the author's own name for the project. It is unrelated to our `bots/hyperion`, which was called hecate until 2026-10-21. "The user" in comments means the author.

## Base

The commit calls the base "Aph (the bot.zip I was given, a nemesis-family build)". In git terms, Aph is **nemesis 5ef5601** ("Update Nemesis to Khaos v22") plus the **v17 farm code**:
- `params.h`, `world.*`, `champions.*`, `comms.*`, `abilities.*`, `self_abilities.*` and `safety.h` match 5ef5601 byte for byte, so the draft is nemesis's (Cassi, Varg, Stellar, Ryth, Tavi). Every other difference in the shared files is one of the author's tagged changes below.
- The v17 farm code is `local_spell_plan`, `collect_local_reward` and `FarmEvaluationReserve`. hecate ported the same code in 6381814 and replaced it in 048fd12. herbert's copy differs only by the no-memory and fuel changes below.

## herbert: new systems

New files: `bands.*`, `kit.*`, `linefight.*`, `micro.*` and `sim_core.h`. Changes to Aph are in `bot.cpp`, `turn_order.cpp`, `pathing.*`, `util.h`, `draft.*` and `main.cpp`.

1. **Two-band turn order with double turns** (`bands.*`, `turn_order.cpp`, `DraftPlan::prio_split`).
   - **Bands.** Higher priority acts first, and a change applies from the next round. LAST values lie in [1, M) and FIRST values in [M, 2M).
   - **Double turn and forfeit.** Going from LAST to FIRST gives us two actions back to back (a double turn). Going from FIRST to LAST gives the enemy two in a row (a forfeit) and banks a double turn for later.
   - **Secret split.** The draft bot draws M per game from the clock and the map, and each value is random within its band. Enemies can read priorities, but they cannot tell which band a value is in.
   - **Resting band.** A champion with neither a dash nor a stun that allows walking rests LAST, with a double turn ready. The others rest FIRST. If every ally has a dash or such a stun, the ranged champions rest LAST.
   - **Each turn:** a request from the micro wins (herbert_advcombat only). Otherwise, Aph's turn-order needs at `protect` or above go FIRST (a kill, or a channel to protect or stop). Otherwise the band holds while an enemy is in sight, because drifting mid-fight would hand them a double turn. Once no enemy is in sight, it drifts back to rest.
2. **Line-model fight sim** (`sim_core.h`, `linefight.*`).
   - **`sim_core.h`** was carried over from the author's earlier bot, Helios. It uses fixed-point integers and fixed arrays with no allocation, and its fast paths are bit-exact against a round-by-round reference. It contains a camp-clear sim, a positional champion fight, and `Battle::run_line`.
   - **The line model.** Each unit fights its focus 1v1 at a distance on a line, and damage on a unit is summed over everyone focusing it. Units act one after another, so first strikes, kills and double turns are modelled. Movement, dashes and stuns follow fixed rules for each pairing (melee or ranged against melee or ranged). Each unit makes one cast a turn, the ready ability worth the most as a fraction of max health. Rounds where nothing changes are skipped in one step.
   - **`line::evaluate`** pits us and the 4 nearest visible allies within 5 against the 5 nearest credible threats. A threat counts if it is visible within 7, or if it is unseen and its tracked position could be within its reach + 1 of us. The default horizon is 8.
   - **`line::at`** runs one cached sim per turn and tile, with horizon 10, counting our saved double turn.
   - **Uses.** It replaces nemesis's `safety.fight` in `want_home`: leave a lethal tile where we die, or a visible threat's fight we don't win. The ladder (item 3) also uses it.
3. **Helios ladder for picking fights** (`micro::choose`, called from `prey`). Every turn it scores each enemy and takes the best:

   | Score | Take the fight when |
   |---|---|
   | 95 | a channelling enemy (recall, tribute or teleport) is in reach and we survive |
   | 85 | our burst kills it now and we survive |
   | 72 | the line model says we win and I live (ranged: holding for 2 rounds is safe) |
   | 70 | retreat: no fight to take, the fight is not ours, and an enemy can hit us next turn |

   - **Chase reach:** melee 4 (6 with a dash, Varg 3). A ranged champion goes as far as it reaches from here, plus up to 3 more depending on the matchup.
   - **Limits:** an enemy on or next to its spawn is taken only for a kill. A target whose every in-reach tile is in Aph's pack zone is skipped. Ties go to more gems, then lower health.
   - **Execution:** Aph's chase movement plays the chosen fight, and it runs before the opportunistic attack. Aph's gates still apply: not while holding a capture or saving a stun for a tributer, and with a bag only when it cannot be tributed safely.
   - **Matchup micro not used:** the author measured the ladder with Aph's moves at 21/34 and +50 gems a game against Aph. With the author's own matchup micro moving (`micro::engage` / `retreat`, still in `micro.cpp`), it was 17/34 and -68.
4. **Banking rules** (`bot.cpp`).
   - **Bag size:** a bag of at least min(150, max(75, gems still needed / 2)) goes in.
   - **Awake camps:** no tribute (`submit_here`) and no recall start within 3 of a live fighter in an awake or possibly awake group.
   - **Route to the altar:** banking steps may pass through camp range (only enemies are routed around), but never end in an awake camp's range. If every tribute tile is in range, it waits.
   - **Stun-aware safety:** a tribute is unsafe if a credible enemy with a ready stun can get within the stun's reach before the tribute lands.
5. **One-shot camp walls** (`pathing.cpp`). Any tile within camp attack range of an awake (or possibly awake) fighter whose single hit would kill us (health plus shield) is blocked for every route that turn, except our own tile.
   - Camp range was 3 for every monster then. Since the week-2 patch it depends on the monster type (cambc-rules.yaml `camps.types`).
6. **No decision memory.** Each turn starts by resetting banking, farm group, claim, crew, siege and staging. The only thing remembered is the last farm target, which keeps Aph's 1.2 stickiness. Consequences:
   - **Farm claims form a hierarchy:** a champion defers only to lower-index allies' claims. The lowest index decides alone, so claims can't cycle.
   - **Siege commitment** comes from the current state: an ally claims the group, or someone is already fighting it while it is awake.
   - **Spell clears** are planned from this turn's farm choice, not last turn's.
7. **Fixed-work fuel rule** (`util.h`: `budget()`, `Precompute`).
   - **Decisions never read fuel:** outside precompute, `fuel_ok` sees 2^40. Searches run to a fixed depth.
   - **Only lossless precompute reads real fuel:** draft analysis, next turn's walk, the static fields, and a new `warm_farm` that fills each group's clear-estimate cache.
   - **Lossless farm-loop prune:** an empty-handed champion skips a group whose best possible value per round can't beat the best so far. The author found the same result with about 8% less fuel in `decide`.
   - **Cost:** about 21 lost turns a game on the ladder maps, against none for Aph. Rule 1 of our FUEL-GATES.md is the same principle; it pairs the rule with bounded work so turns stay within budget.
8. **Kits from the engine** (`kit.*`). Champion stats and abilities are read once from the engine's designs, not transcribed. The micro and the line model use them.

## herbert_advcombat: the author's attack rules

This is herbert with every fight played by rules taken from the author's recorded 1v1 duels ("Duel Lab"). The ladder still picks the fight and the line model still decides retreats. `rules::attack` replaces Aph's chase moves.

- **Enemy reach next turn:**
  - melee: 2 (walk + attack), 4 with a ready dash;
  - ranged: 3; walk, reset, attack 4; dash + attack 5;
  - damage spells: their cast range, +1 if the caster can walk first;
  - stuns are not counted.
- **Is it coming?** `note_enemies` records each visible enemy's tile at our turn's end. An enemy counts as coming if it got closer since then, or if it was stunned or unseen.
- **Ranged movement:** the ranged champion holds outside the enemy's reach.
  - With our stun ready: one tile outside.
  - With our stun down: at 4 against ranged, so they walk to 3 for one hit while we hit twice.
  - Against a melee with a ready dash: at its dash reach, to bait the dash.
  - Against other melee: one tile outside.
- **Melee movement:**
  - Against ranged: hold one tile outside its reach and dash in as it steps closer, when our dash covers its reach. Otherwise walk straight up.
  - Against melee with our stun ready: hold one tile outside and stun it as it steps in. Otherwise close to 3, keeping the dash.
- Holds last only while the target is coming. Otherwise Aph's chase step closes in.
- **Casts:**
  - a damage + stun spell the first turn an enemy is within its reach of us;
  - a pure stun once an enemy is in our attack range;
  - damage spells whenever in range;
  - attack + reset + attack whenever the reset is up;
  - the shield the turn before our first attack.
  - `cast_at_enemies` takes a slot mask so the rules choose the ability.
- **Turn order:** approach in the LAST band, request the double turn on contact, and forfeit back when ahead and out of reach.
- **Dash trick** (we hold a dash, theirs is down): on the double turn, hit once, dash out of reach, walk on and forfeit back. Then hit it when it walks back in.

## Results

The author's numbers, from cambc 2.2.5 before the week-2 patch, with `--release` and every map played from both sides:

| | 17 ladder maps | 84 maps (17 ladder + 67 custom) | 33 edge maps |
|---|---|---|---|
| herbert vs Aph | 21/34, +50 gems | 81/168, +4 gems | 31/66, +44 gems |
| advcombat vs Aph | 16/34, -38 gems | 80/168, -4 gems | 28/66, -34 gems |
| advcombat vs herbert | 22/34, +145 | 93/168, +45 | 34/66, +55 |

- **Against Aph,** over all 234 games the two bots tie within noise (herbert 112 wins, herbert_advcombat 108). On the 17 ladder maps alone, herbert is the stronger.
- **Head to head,** herbert_advcombat wins 127/234 (54%, +48 gems a game).
- **Fuel:** both lose turns to fuel, about 21 (herbert) and 16 (advcombat) a game on the ladder maps, against none for Aph.
- **Never A/B'd here:** neither bot was played against hecate or hyperion in this repo.

## Not in hyperion (2026-10-21)

hyperion's turn order uses fixed bands and has no double turns or forfeits. So item 1, and herbert_advcombat's turn-order rules and dash trick, have not been tried here. The fixed-work fuel rule (item 7) is already hyperion's direction.
