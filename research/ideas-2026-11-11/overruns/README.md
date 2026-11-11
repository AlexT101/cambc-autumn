# One-site overruns (2026-11-11)

Brief: the 38 "overrun" losses of live v115 (= `oc-dfuel-506`) against Fish and Mite
([badmaps](../badmaps/README.md): 15+ deaths, twice theirs, captures under 60%). What happens in the real replays, is
there a root cause that holds on fresh maps, and if so a fix.

**Answer: no fix built.** The overruns are the losing tail of a snowball that runs both ways, and we are on the
winning end of it more often than the losing end. What decides them is the early champion fights, where real Fish
(and less so Mite) converts numbers into kills and the local bodies do not. The only change the replays point at
(give way to packs sooner) has the opposite sign against the bodies by construction, so no local gate can read it,
and its ceiling is about a point against Fish alone. No gate was run.

## Data and tools

- Live: v115's 520 decoded scrims against Fish r2 and Mite r6 (`~/tmp-offload/badmaps/ext`, classes in
  `an/lossclass.pkl`). Local: 506 against `spar-dvn1-Flp4` / `-Mt3q` on the 128 ladder maps, 512 games (`extl`).
- [tools/](tools/) (working copies and pickles in `~/tmp-offload/overruns/an/`): `deaths.py` / `deaths_local.py`
  build the per-death table (numbers within 6, distance to spawn and altar, rounds since respawn); `engage.py`
  cuts champion-on-champion damage into engagements (gap of 6 rounds, bodies within 8 at the first hit);
  `init.py`, `theyinit.py`, `weinit.py`, `flee.py` read them by who hit first and who had the numbers;
  `firstdeath.py` reads each side's first death; `alpha.py`, `cohesion.py`, `tgt.py`, `fb.py` are the fidelity
  reads; `trace2.py PKL MAP OPP SIDE R0 R1` prints a fight round by round.
- Early = rounds up to 250 (300 in `alpha.py` and `tgt.py`). A kill of Cassi or Issac counts once.

## What happens in the 38 games

41 games carry the class (three cells were played twice).

- Our first champion dies at round 86 (median), in 35 of the 41 before any of theirs. By round 300 we have lost
  4.0 champions to their 0.7 and earned 1,018 gold to their 2,087; over the game 20.8 deaths to 3.6.
- Kill gold is about a third of that gold gap. The rest is the site: after the first fight they hold it and we
  walk back in short-handed (71% of our bodies alive on average after round 150, 95% of theirs).
- 41% of our deaths are within 8 tiles of our own spawn and 18% within 30 rounds of a respawn. It is not one
  pattern: on ribs, dunes and pilgrimage every death is at the site, 40-70 tiles out; on elk_arena, swirl,
  horseshoes, lines and sunburst most are at our door.
- The first fights, traced: one of ours engages alone while the teammates beside it keep hitting a camp or walk
  off (hooks: Issac dashes into three, three allies stay on a cluster 5 tiles away; ribs: Heart of Ruin dives a
  four-stack while Cassi, Issac and Willow back away, Marcella fights two alone and Prism has recalled;
  gold_rush: Vesper pokes a three-stack, Vendetta dashes away). Or a full-health pack arrives on a group of ours
  (stampede: Fish's six bodies kill Cassi from full health in two rounds at round 146, then Willow, Vesper and
  Marcella one at a time over the next 17 rounds; oasis: Mite's five arrive on four of ours hurt by a camp).

## It runs both ways

Games with 12+ deaths on one side and at most half as many on the other (15+ in brackets):

| | we are overrun | we overrun them |
|---|---|---|
| live Fish (260) | 30 (22) | 35 (26) |
| live Mite (260) | 24 (21) | 35 (23) |
| local Flp4 (256) | 8 (6) | 69 (51) |
| local Mt3q (256) | 11 (8) | 52 (35) |

- The first champion death by round 150, live: ours first in 83 games against Fish (54% won) and theirs first in
  54 (87%); Mite 65 (46%) and 48 (75%). Locally the counts are reversed: 52 and 82, 58 and 87.
- No map feature marks the class. Live win rate is 70% on one-altar maps, 67% on two, 57% on four; by spawn
  distance and size the overrun share moves between 1% and 21% with no level effect on wins.
- About half of the 38 sit in map-and-opponent cells lost in every version (v105-v115 scrims: gold_rush against
  Fish 0 of 22, stampede against Mite 2 of 24, swirl against Mite 2 of 24, fragment against Mite 2 of 24,
  boss_battle against Mite 3 of 26, crater against Fish 3 of 22, ribs and sunburst against Fish 6 of 22). The
  same maps are won against the other team (gold_rush against Mite 22 of 24, swirl against Fish 18 of 22, hooks
  22 of 22 against Fish and 9 of 24 against Mite). The other half are cells we usually win (dunes, gemfight,
  pilgrimage, stalactites, elk_arena).
- On the Fish cells the body plays Fish's exact picks and the local result is the mirror image: stampede live 33
  deaths to 3 and 20 to 8, locally 7 to 9 and 5 to 4 with two wins; guardians live 27 to 7 and 20 to 13, locally
  6 to 17 and 1 to 18; adgato_gemcombat5 live 30 to 4 and 26 to 3, locally two wins; crater side b live 26 to 10,
  locally 2 to 19. Ribs is split locally (2 to 18 and 15 to 4). Only gold_rush is lost locally too (a draft
  matchup, already in badmaps). Against Mite the body's picks differ on most of these maps; it is overrun on
  hooks (1 to 18, 1 to 19), oasis (4 to 16, 2 to 10), fragment (same picks; 4 to 24, 1 to 16) and boss_battle,
  and swirl and horseshoes are split.

## Where the early fights are lost

Engagements up to round 250, net champion kills for us per engagement:

| who hit first, who had more bodies within 8 | live Fish | live Mite | local Flp4 | local Mt3q |
|---|---|---|---|---|
| they did, they had | -0.40 of 136 | -0.06 of 122 | +0.03 of 141 | -0.07 of 116 |
| they did, level | +0.02 of 102 | -0.14 of 105 | +0.10 of 124 | +0.08 of 130 |
| we did, they had | -0.03 of 439 | +0.02 of 338 | +0.16 of 373 | +0.20 of 338 |
| we did, we had | +0.14 of 190 | +0.12 of 211 | +0.16 of 143 | +0.19 of 201 |
| any, they had | -0.12 of 575 | 0.00 of 457 | +0.13 of 511 | +0.14 of 453 |

- **Fish's pack finishes what it starts and its body does not.** When Fish hits first with the numbers (3.8 bodies
  to our 2.0): 2.62 of them attack, 650 damage lands on the first target and it dies 38% of the time. The Flp4
  body from the same position: 2.14 attackers, 457 damage, 16%. Ours in the mirrored case against Fish (3.6 to
  2.0): 2.18, 459, 16%. The first target is our Cassi or Issac in 48% of Fish's cases; ours is their Heart of
  Ruin, Vendetta or Marcella in 66%, which their Willow heals (856, 764 and 448 health a game by round 300).
- In the four rounds before Fish's first hit our target moved towards the pack 61% of the time and away 21%
  (the body's games: 52% and 22%). 61 of the 136 are nearer our spawn than theirs, ground where the pack zone
  already applies at `home_retreat_ratio`, and those lose most (-0.52 each). The zone is the members' one-turn
  reach (`pack_radius` = 5), so a pack still closing is outside it until the round it strikes: on stampede only
  their Heart of Ruin stood within 5 of our Cassi at round 144, one body hit her at 146, three more at 147, and
  she and Issac were dead at 148.
- Our first deaths by round 150: 102 in fights the victim or its pair started and 77 in fights the enemy started.
  Locally 72 and 81. The whole live excess is fights we started with a pack near (3.3 enemies within 8 against 2.6
  locally; 3.2 end up attacking the victim against 2.8).
- Focus and stuns are not the gap: the top target takes 92-93% of a multi-attacker round's damage for live Fish,
  live Mite and both bodies alike (ours 86-89%, wider because of our area casts), and our first victim spends
  1.3-1.4 rounds stunned in all four.
- Mite's edge is spread thinner (fights it starts at level numbers or outnumbered, -0.11 to -0.14 each) and the
  Mt3q body matches it only where Mite has the numbers.

## Body fidelity for fights (the reason no gate was run)

Per game, rounds up to 300:

| | live Fish | Flp4 | live Mite | Mt3q |
|---|---|---|---|---|
| rounds with 4+ of them hitting one of ours | 0.38 | 0.19 | 0.17 | 0.12 |
| rounds with 3+ of them hitting one of ours | 1.53 | 1.15 | 1.26 | 0.82 |
| one of ours loses half its base health in a round | 0.59 | 0.34 | 0.45 | 0.30 |
| rounds with 4+ of ours hitting one of them | 0.16 | 0.47 | 0.12 | 0.18 |
| their Heart of Ruin: damage taken, early deaths a game | 1,133, 0.24 | 1,722, 0.55 | 1,215, 0.27 | 1,638, 0.46 |
| largest group within 5 of each other, 5-pick maps, rounds 30-100 (ours 3.4) | 4.5 | 3.9 | 4.1 | 3.1 |

- Against the bodies, an engagement entered outnumbered gains us 0.13-0.14 kills; against real Fish it costs
  0.12. Every "give way less" step won locally (CHANGES 240, the SPSA ratios) and every caution or cohesion arm
  lost or was level (EXPERIMENTS: fc1/fc2-coh75, home_retreat_ratio 1.5, squads, packs, rally). Those reads
  measured the bodies, not Fish.
- A wider pack zone or a give-way rule off our own half would therefore read negative locally whatever it does
  live. Its live ceiling, from the table: Fish's outnumbered engagements cost us about 70 kills in 260 games
  (0.27 a game); avoiding a third of them at no farm cost is about +1 point against Fish and nothing against
  Mite. Not built: no local evidence is possible and the size does not justify a live group on its own.

## Results against oc-dfuel-506

| gate | result |
|---|---|
| none | no candidate built, no games played |

Verdict: the one-site overruns have no cause of their own; they are early fights lost to real packs, on maps where
one lost fight costs the site, and the local bodies cannot show a fix for that.

## Carry forward

- A fight-faithful Fish body is the missing tool. Targets, all from `theyinit.py` and `alpha.py` on
  `deaths.pkl` against `deaths_local.pkl`: enemy-started outnumbering engagements at -0.40 kills each for us
  (now +0.03), the first target dying 38% of the time (16%), 2.6 attackers (2.1), 0.38 four-attacker rounds a game
  (0.19), and our own four-attacker rounds down to 0.16 (0.47). Cohesion alone (Flp4) moved none of these.
- With such a body, the first arm to try is the pack zone's margin: members that reach us in two turns counted
  as well as those that reach us in one, and the zone applied off our own half.
- The Fish cells where live and local disagree with identical picks (stampede, guardians, crater,
  adgato_gemcombat5) are the cheapest check of any new body: 506 should lose them.
