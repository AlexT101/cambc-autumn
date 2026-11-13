# Brief C: price the local balance of force into the team's work (implementation subagent)

You implement one macro change to our Cambridge Battlecode bot charybdis, in C++, and measure it. Work only in
`/home/ubuntu/wt/mx-crius` (a git worktree on branch `mx-crius-20261113`). Do not commit, push or touch any other
worktree or `/home/ubuntu/cambc-autumn`. Do not edit `bots/variants/chy-ref` (the frozen reference), `bots/charybdis`,
or any other variant. Other subagents may be working in `bots/variants/a-collect` (Prism capture hand-overs) and `bots/variants/b-crew` (crew staging on Elk/Golem); stay out of those topics.

## Read first
- `AGENTS.md` (repo rules: fuel, debug_block tracing, testing), `cambc-rules.yaml` (engine-verified rules: combat,
  death, vision), `docs/api/cpp.md` as needed.
- Source: `bot.cc` `decide()` (the turn), `economy/farm.cc` farm_turn (the group choice: worth, `rate`, the exposure
  terms `exposure` / `mid_exposure` / `max_exposure`, home_ground, the prunes and their bounds), `economy/camps.cc`
  (`rate`, home_ground), `model/safety.{h,cc}` (threat model: seen enemies, unseen ones through `possible` sets),
  `model/enemy_reach.{h,cc}`, `model/comms.{h,cc}` (allies' claims and posted positions), `combat/fight.cc`
  (want_home, stand_lost_at), `combat/guard.cc` (guard_work), `economy/capture.cc` (prism_premium).
- `research/fish-farm-2026-11-02.md` (the top ladder team packs and dies half as often).

## Why (measured on 1,700 mirror games of chy-ref vs itself, `replays/an-mirror`)
- Fights are instant: from a victim's first champion damage to its death, quartiles 0 / 1 / 3 rounds (p90 7). Allies
  7-14 tiles away close by 0.1 tiles on average meanwhile. So what decides a fight is who is near at contact.
- Deaths come with warning: the victim saw its killer the round before in 78% of kills, for 10+ rounds in 33% and 4+
  in 55%, first seen ~7 tiles away at 90%+ health in two thirds. Over the victim's last 10 turns (excluding lost
  endgames) it was retreating 40% and farming 36%: long standoffs and chases, not ambushes.
- Contact onsets (an enemy within 6, none in the 3 rounds before; `research/mx-crius/scripts/contact.py`): 4.4% die
  within 10 rounds. By allies minus enemies within 10 at onset: -4: 13.9%, -3: 12.2%, -2: 8.9%, -1: 5.2%, 0: 3.6%,
  +1: 2.7%, +2: 2.4%, +3: 1.5%. With 3 allies within 6 against 3 enemies 7.4%, alone 21%. (Observational: being near
  allies also means being on our own ground; derive, don't copy, any curve you use.)
- Victims were outnumbered by 2+ within 6 in 40% of kills, with an ally 7-14 tiles away in 58% of those.
- The Fish study: its nearest teammate is 4-5 tiles away against our 7, only 21% of its deaths come outnumbered
  against our 56%. Its finding: our farm's rate never makes working near allies better than an equal job alone,
  because what company buys (deaths avoided, local strength, camps not lost) is left out of the price. Earlier
  constant cohesion bonuses read level, and forced packing (pack, squad, escort, convoy) lost 5-13 points because it
  took farm time. The fix is a consistent price, not a pull.

## Design
Every job the farm prices (a group to clear, hold or collect, for every body, the Prism included) carries its expected
loss from contact over the job's rounds, in the same gem units as its worth:
  expected loss = P(contact during the job) x P(death | contact, local balance at the job) x cost of our death,
- **P(contact)**: from what we know of enemies: a visible enemy within reach of the job over its rounds is near
  certain; unseen ones through the Safety model's `possible` sets / enemy_reach over the job's window (they walk a
  tile a round; their dash; time since seen).
- **Local balance**: the fighting strength of allies that will be within support distance of the job at contact (an
  ally's posted claim and position: allies working nearby count; allies far away do not) against the enemies that can
  be there. Use fight strength the bot already models (the strike/blow model, raw output, health), not head counts.
- **Cost of our death**: our bag (to the killer: priced at the killer's premium when the killer is a Prism, since it
  feeds its duel), the kill gold to the enemy, our respawn rounds at our farm rate, and for the Cassi & Issac pair
  both bodies; a Prism's own premium on its bag.
- Use it where the farm compares jobs (the worth or the rate), so champions take jobs near allies where contact is
  likely, take the best job anywhere where it is not, and leave jobs (re-choose) when an enemy force they cannot match
  stands in sight of them, instead of working on in a standoff. Keep the prunes sound (any term that lowers a value
  must keep the prune bounds valid, or the prunes go and the fuel blows up: CASTOR's C8 lost that way).
- Where the existing exposure / home_ground weights already stand in for this, replace them rather than stacking a
  second risk term on top (or show they measure something else). In farm.cc: `exposure_of` (~line 1322) weighs a
  middle-band group by up to `params::mid_exposure` (1.361, a tuned weight: middle groups are *worth more*, the
  opposite sign of a risk term), cached in `exposure_kept`; `exposed` (~line 1882) multiplies it with Ren's
  `pull.deny_scale`; the pre-facts prunes bound the weight by `params::max_exposure` (1.215) and `exposure_most`.
  Understand what that weight captures (contest value of middle groups, denial) before replacing or keeping it.
- Every allied body must be able to compute the same numbers from shared information where they coordinate.
Leave alone: `draft/`, which emblems champions build (`economy/shop.cc` emblem choice), and fuel optimisation (we
test at 2x fuel; a guard against runaway loops is fine). No magic numbers or map-specific cases: quantities from the
rules or measured.

## How to work
- `./copybot variants/chy-ref variants/c-balance` (never copy `.cambc/`) and work in `bots/variants/c-balance`. `unity.cpp`
  includes every `.cc`: a new one goes there.
- Win rate: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-crius && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c-balance variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx/train --name mx-crius-c-<tag>`
  (10,200 games, ~3-8 min; `replays/ab/<name>/summary.md`). Run long commands in the background
  (`run_in_background`), never a foreground sleep loop. Use only `train` for A/Bs and `study` for `--debug` traces
  (`debug_block({ printf(...); })`, output in replays' `team-?.stdout`); never `dev`, `hold`, `x1`, `x2`, `x3`, `scr`
  or `fin`. Farm speed vs idle (should not fall much): `py tools/solo.py variants/c-balance variants/chy-ref --suites maps/suites/mx/study --one-side --fuel 200000 --name mx-crius-c-solo-<tag>`.
  Delete replay batches you no longer need.
- Check it moved what it should: deaths a game, deaths outnumbered, nearest-ally distance, Prism deaths
  (`research/mx-crius/scripts/killnum.py`, `contact.py`, `cohesion.py`, `py tools/replay/fight_metrics.py DIR` on
  extracts: `node tools/replay/extract.mjs BATCH --out DIR`), and that farm income did not collapse.
- Iterate at most ~4 full train A/Bs on the design (fix bugs and missing companion pieces; do not sweep constants).
- Before returning: spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) to check the
  change against this design and the rules for bugs (prune soundness above all); fix what it finds; make sure the bot
  builds; play a smoke `py tools/ab.py variants/c-balance variants/chy-ref --no-test-draft --fuel 200000` (256 ladder
  games: no failed games, no DRAFT-UNFINISHED / PLAN-CHECK).
- Stop when: built, audited and smoked with its best train A/B; or after ~4 train A/Bs; or if the premise proves wrong.

## Report back (concisely)
Variant path; what you built; each train A/B (win %, CI, OOF both sides) and what changed between them; the death /
cohesion / farm metrics before and after; the auditor's findings and fixes; the smoke; what you would try next. Save
the final diff against its base: `diff -ruN bots/variants/chy-ref/src bots/variants/c-balance/src > research/mx-crius/patches/c-balance.diff`.
