# Brief s2: why does our Prism convert so few of its kill chances? (study, no bot change kept)

A bounded measurement study for the orchestrator of a macro refactor of the C++ bot `charybdis`. Read
`/home/ubuntu/wt/mac13-kronos/AGENTS.md` and `cambc-rules.yaml` first. Work ONLY in `/home/ubuntu/wt/mac13-kronos`
(do not touch `/home/ubuntu/cambc-autumn` or other worktrees; do not commit).

## The observation
In 1,024 debug mirror games of charybdis (`maps/suites/mac13/study`), our Prism sees an enemy non-Prism champion
within 6 tiles whose current health is below 2.5x our Prism's Focus (its stun 1.5x + ground 1.0x burst) about 14.6
times a team-game (deduplicated per target per 10 rounds). Only ~2.6 of these end with that enemy dead within 8
rounds (2.1 by our Prism). Most chances are at distance 5-6 with our stun ready and no enemy Prism within 8
(~3.2 a team-game, 25% converted) or with an enemy Prism within 8 (~3.6, 11%). About a third happen while our Prism
channels a tribute. Kills decide games (the side with more kills wins 91%), so each extra kill matters.
Mechanics to keep in mind: Prism spells exclude walking (cast or walk, not both); unit spells need the target
visible; teams alternate champions within a round and priority orders a team (a champion may get two turns in a
row against a given enemy across a round boundary); attacking from a bush does not reveal the attacker.

## Method
1. `./copybot variants/chy-ref variants/s2-trace`. Add ONLY debug-only output (`debug_block`, printf; release
   builds unchanged) on our Prism's turns when such a chance exists (a visible enemy non-Prism within 6 with health
   below 2.5x our Focus, after Durability/shields as the code models them if easy): round, our id, target id,
   distance, our stun/ground cooldowns, the branch taken (`decision`), whether the strike search ran and what it
   chose, the chase gate's verdict on that target (`prey()` or whatever decides a chase, with the reason it
   declined if it did: fight sim lost, lethal tile, enemy Prism, channel, fuel...), and whether the target will act
   before our next turn (the turn-order windows the code computes). Name the line `PK ...`.
2. Play a debug mirror on `maps/suites/mac13/study512` (512 maps, 1,024 games):
   `source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-kronos && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH python tools/ab.py variants/s2-trace variants/chy-ref --no-test-draft --fuel 200000 --debug --keep-replays 0 --suites maps/suites/mac13/study512 --name mac13-kronos-s2`
   then `node tools/replay/extract.mjs <batch dir>`; join the PK lines (in the replay zips' team-a/team-b.stdout, the
   s2-trace side) with what happened next (the target's moves, damage, death, its distance next turn).
3. Classify the missed chances by cause and give each cause's count per team-game, with what our Prism did instead
   and what the target did (fled out of reach, was shielded/healed, the burst was not lethal after all, our Prism
   was channelling, the gate declined for which reason). Then estimate for the top 2-3 causes how many kills a
   team-game a fix could add, and point to the code that decides (file, function).
4. Scripts and a short README.md with the tables under `/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/s2/`.

## Stop condition
Return the findings (causes with counts per team-game, the code locations, and the 2-3 most promising fixes with
their estimated size). Delete the s2 batch replays when done; keep scripts and README. No other A/Bs.
