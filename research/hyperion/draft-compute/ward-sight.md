# What champions do with ward sight

2026-10-26, branch `worktree-agent-a7d420b4f423ef566`: measured on df3b03e (CHANGES 159), shipped on 12c2e69f (CHANGES 160). Follows the ward plan
([wards.md](wards.md), CHANGES 159), whose note named the play side as the likely next gain.

## How ward sight flows today (code)

Everything reads the engine's vision, which is the champion's own tile plus its own ward (`vision.personal`). No
decision is self-sight only.

- `World::read_vision` takes `sdk_vision` (body and ward); `update_champion` marks an enemy `visible` from
  `engine::champion`, which answers for anything in that vision. A ward-seen enemy gets the same exact position,
  health, cooldowns, channel and `fix()` of `possible` as a self-seen one.
- Absence: `track()` prunes `possible` (and `undashed`) to `unseen_ = ~visible`, so a tile the ward watches already
  counts as evidence that the enemy is not there. Safety's unseen weights (`|square ∩ possible| / |possible|`) shrink
  with it.
- Safety's threats, `want_home` (`stand()` with visible enemies within `pursuit_steps` joining), `threatened()`
  (recall risk), `tribute_safe` (`turns_to_kill_idle` over visible enemies), the strike search and the farm all read
  `visible` / `seen_enemies()`: the ward's sightings are in every one.
- Comms (CHANGES 141): `send()` posts any `visible` enemy, ward-seen included, into one or two sighting slots;
  teammates `note_sighting()` it, which fixes `possible` there. Dead champions run the same update and send, so a
  dead champion's ward keeps posting.
- The only Chebyshev-8 rule is `prism_capture_holder`'s pressure test (`vision_radius + age`), about stale sightings.

So the ideas "count ward sight as evidence of absence" and "share a ward sighting" are already in the code.

## Measurements

Scripts in the session scratchpad (`ws.py`, `kc.py`, `deliv.py`, `rule.py`, `wt.py`); vision by
`tools/replay/narrative/vision.py`. "Own ward first": the victim's turn-start `sees` held the killer while it stood
outside the victim's own radius-8 cast, before its own cast did; "mate": a teammate's turn-start `sees` held it at a
turn whose post could reach the victim's last turn (teammate earlier in that round, or the round before).

### The ward A/B's games (1164, `replays/batch-20261026-043028-ab-wardplan1-*`), the ward plan's side

| | deaths by a champion | real recalls broken (≤3 turns left) | tributes stunned |
|---|---|---|---|
| n | 4413 | 2871 | 163 |
| own body saw the killer first | 83.5% | 80.9% | 86.5% |
| own ward saw it first | 10.9% | 11.8% | 9.2% |
| only a teammate saw it | 1.7% | 2.9% | 1.2% |
| nobody, 10 rounds back | 3.9% | 4.3% | 3.1% |
| killer unseen at the victim's last turn start | 12.0% | 16.6% | 14.7% |
| ... but a teammate saw it in time for comms | 5.3% | 8.9% | 9.8% |

- Own-ward-first deaths are not missed warnings. In 413 of 479 the body saw the killer later too, and most are
  bush fights: the ward first showed the killer at Chebyshev 1-6 (229) more often than beyond 8 (171). The victim
  fought knowing where it was; changing those is the fight model's work, not ward sight's.
- A ward placed in the same turn just before a tribute start revealed a new enemy 35 times in 1164 games (31 of
  those tributes completed): `submit_here` judging before its ward is not worth a change.

### Did comms deliver? (652 games, ladder + gen, CAND with `KC`/`KS` debug lines, vs astraeus-df3b03e)

- Delivery works: 95% of first-slot and 91% of second-slot posts reached each teammate that lacked the enemy
  (827k / 407k teammate-posts).
- Victims whose killer was unseen at their last turn but seen by a teammate in time: 190 deaths, 195 recall
  breaks. The killer was posted at some point between in 96%, but the victim knew its position at its last turn in
  only 69 deaths (36%) and 92 recalls (47%).
- The loss is in what gets posted. Of 173 teammate turns that saw a later killer in the rounds before the victim's
  last turn, the teammate posted the killer 40 times, another enemy 20 times and nothing 113 times: both slots were
  already taken that round by an earlier teammate's sighting, which a later poster never overwrites.
- With exact positions, "post the enemy nearest to a teammate who does not see it" picks the killer in 105 of those
  173 turns, and in at least one turn for 50 of the 121 unaware deaths and 41 of 103 unaware recall breaks.

The ceiling: ~50 deaths and ~40 recall breaks in 652 games (2% of deaths), before asking whether knowing would have
saved them.

## The change (shipped, level)

`comms` only; CHANGES 141's layout is untouched (commits 1efa1168, d763bb91, 5c78285c).

- Urgency of an enemy in sight: the Chebyshev distance to the nearest other live ally that may not see it, less the
  rounds since we saw that ally (a step a round), capped at `Strike::max_reach + 1`. An ally we see within 8 counts
  as seeing an enemy in the open (walls ignored), and one in a bush only from inside its cluster (`vision.personal`,
  `vision.occlusion`). Past the cap every enemy ties, so the old order (bush first, then the rotation) keeps the
  far ones fresh.
  On merge (CHANGES 162) the bush test grows the enemy's cluster on demand and tests the ally's tile against it,
  in place of comparing `found_bush_cluster` pointers, which are null until warm-up (spare fuel) finds them.
- `send()` picks the most urgent, then the old order. A teammate's sighting from this round (either slot, never a
  capture) is replaced when ours is strictly more urgent and of another enemy: teammates between it and us have
  read it, and those after us get the more urgent one.
- `receive()` works the urgencies out at the turn start, and send reuses them. Nothing moves during our turn, so
  they still hold. An enemy first seen after our move is worked out in send. Allies are listed only when an urgency
  is needed, so the first turn (no enemy in sight) does no extra work. No observe is added and nothing is fuel-gated.

## A/B

All against `bots/variants/astraeus-m160` (12c2e69f), both on their own drafts, `--no-test-draft`, 7 threads. Each
candidate is the committed code plus the `KC`/`KS` `debug_block` lines, which compile out in release. With those
lines alone against its own base, the bot read 50.0% of 652 (`kcmeasure`).

| Run | Code | All (1164) | ladder | gen | gen-s1 | OOF CAND / REF |
|---|---|---|---|---|---|---|
| `wardcomms` | shadow cast per enemy, urgencies in send | 48.7% (45.8-51.6) | 45.0 | 49.8 | 48.6 | 4546 / 4087 |
| `wardcomms2` | no cast, urgencies at the turn start | 50.0% (47.1-52.9) | 45.0 | 51.4 | 50.0 | 4383 / 4458 |
| **`wardcomms4`** | **+ cap at a strike's reach, lazy allies (committed)** | **49.4% (46.5-52.3)** | 47.1 | 49.0 | 50.4 | 4558 / 5716 |

What each fix was for:

- `wardcomms`: 658 of CAND's out-of-fuel turns came from `send()`. Measured on gen-arena-120102600, the send cost
  2.4k on average against 1.0k for the base (p90 4.3k against 2.1k), and it runs with only `late_floor` (1500) to
  spare. The stdout labels these "prepare", the phase set when the resumed turn ended. Moving the work to the turn
  start and dropping the cast brought send to 1.2k on average, with p90 the same as the base.
- `wardcomms2`: ladder deaths were 842 against 642, 105 of the extra 200 on boss-battle and 56 on
  mut-boss-battle, about 60 deaths a game in a loop of walking into the centre. That was not comms. Champion 4's
  first turn (200k) runs out of fuel in both bots on boss-battle. The extra turn-start work made it run out earlier,
  before it posted its claim, and from there the game went another way. With allies listed lazily, the candidate
  replays the base's boss-battle game exactly (1318-0 as team A).
- `wardcomms4`, in its 652 ladder+gen games: deaths 2482 against 2563 (SE ~144); killer unseen at the last turn but
  seen by a teammate in time, 191 deaths; victim knew it by comms then, 79 (41%, against 36% in `kcmeasure`);
  unaware deaths 112 against 121. The mechanism moves the way it should, but within noise. Delivery is unchanged
  (93% / 90% of posts reach each teammate lacking the enemy).

Kept by the keep rule: level, 49.4% of 1164. It is a small, rules-derived refinement with no measurable gain, which
matches the ~2% ceiling above.

## Out-of-fuel turns (the ward plan's +7%)

- The ward plan's fresh suite (`batch-20261026-050013-ab-wardplan1-confirm-suite-ward`): 2090 against 1952, all but
  ~30 a side in `decide`, with no new phase. Across 196 maps with any, the per-map difference sums to +138 with an SE
  of ~80 (z ~1.7). The main A/B read +0.5%.
- The same REF (`astraeus-m160`) read 4087, 4458 and 5716 out-of-fuel turns in the three A/Bs above, against
  candidates whose play hardly differs. A few points of out-of-fuel difference between two A/Bs is game-to-game
  spread, not cost. The ward plan's +7% is most likely that spread. Only a new phase (like `send()` above) or a
  paired replay shows a real cost.

## Not done, and why

- Leaving camps early on ward sight: `want_home` already reads ward-seen enemies (`stand()` with walkers within
  `pursuit_steps`). The ward-first deaths are mostly informed bush fights. That is the fight model's work.
- Delaying a tribute on the altar ward's sight: `tribute_safe` already reads it. A ward placed just before a tribute
  revealed a new enemy only 35 times in 1164 games.
- Evidence of absence from ward sight: already in `track()`.
