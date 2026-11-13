# Study S2 (read-only): what decides the first Prism duel, and what the loser's team could have done

You are a read-only study agent for PHOEBE, who owns a macro refactor of our Cambridge Battlecode bot `charybdis`.
**Do not edit, create or delete any file in the repository** (scratch files only under `/tmp/phoebe-s2/`). Do not
run A/Bs or games. Work from `/home/ubuntu/wt/mx-phoebe` (read `AGENTS.md` and `cambc-rules.yaml` first; never
look at other worktrees under `/home/ubuntu/wt/`).

## Data
- 1,360 distinct charybdis mirror games (both copies of the bot identical; each map played twice, identical
  replays), extracted per game in `replays/.mxp-mirror/<hash>/` (`meta.json`, `rounds.json.gz` with per-round
  per-champion x, y, hp, maxHp, alive, gems, gold, foc, cd0/cd1 (ability cooldowns), str, ...; `events.jsonl.gz`
  with attack / cast (with `dmg`, `stun` lists) / move / capture / death / tribute / recall events). The raw debug
  replays with per-turn `D` trace lines (branch letters: see `bots/variants/chy-ref/src/bot_parts.h` enum Branch) are in
  `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study/*.repl26a` (zip: `team-a.stdout`, `team-b.stdout`; map from
  `meta.json` `sources`). Tools: `tools/replay/README.md`; existing scripts in `research/mx-phoebe/scripts/` (pduel.py,
  firstcast.py, gclass.py, pincome.py show how to read the data).
- Known facts: 618 games have a first Prism-on-Prism kill (median r435); the killer's team then wins 94%. 10 rounds
  before, the killer had more Focus 70%, more HP 72%, more allies within 8 in 47% (fewer 26%). The richer Prism got
  richer by its own captures (it died less early, held more, its team took more mid and enemy-side groups). The first
  damaging spell between the two Prisms came from the eventual killer 58% of the time. Prisms spend ~70 rounds a game
  5-8 tiles apart (standoffs). A Prism cannot cast after walking; its stun reaches 4 tiles (1.5x Focus, removes the
  target's next turn), its ground spell 5 (1x Focus); one cast a turn.

## Question
Reconstruct the 60 rounds before the first Prism-on-Prism kill in ~40 games (a mix: 15 where the richer Prism
lost, 25 where it won), and measure across all 618: what *macro* situation the loser's Prism and team were in, and
what the winner's side did to create the kill. Specifically:
1. How the encounter began: who walked toward whom, from what activity (farming which group, holding, walking to an
   altar, chasing a third body, answering a fight), whose side of the map, near which camps (camp damage on either
   Prism), and each Prism's HP fraction, cooldowns and Focus at first sight (within 8).
2. The standoff: how many rounds within 5-8; what each Prism did then (kept farming, waited, approached, retreated);
   when and why the distance closed; who had which spells ready at that moment.
3. The other bodies: where each team's other champions were (within 8, 9-16, farther), whether any joined, whether
   the loser's allies were busy elsewhere (holding, banking, dead), and whether the winner had a body that stunned or
   damaged the loser's Prism first (Cassi's stun, Vesper, Willow's heals on the winner).
4. Avoidability: in how many cases did the loser's Prism see the danger early enough (killer's burst over its HP)
   and have a safe alternative (walk away keeping 6+ tiles), and what did it do instead (branch letters from the
   D lines of the loser's team stdout)?
Classify the 618 by the main pattern with counts and the loser team's win rate impact, and name 2-4 concrete
**macro** behaviour changes (where to be, when to engage or leave, what the team does around a Prism encounter)
with the evidence for each, largest expected effect first. Separate what is measured from what is guessed.

## Report
Deliver the report via SubagentHandback: the patterns with counts, 6-10 example game hashes and rounds, the measured
hazards, the recommendations with their evidence, and caveats. Keep scratch scripts in /tmp/phoebe-s2/ and name them.
