# Replay micro analysis (replay subagent, saved by main investigator)

Full tables: TABLES.md in this folder; scripts measure.py, aggregate.py, prio.py; raw rows measure.pkl.
Sample: top-6 teams ~40-51 ladder groups each since 2026-10-16 08:00Z (Nyxius since 10-15); us = replays/mine since
10-16 (605 games, 140 groups); 'others' = non-top opponents (75 groups). Turn order rebuilt from priorities: 99.9% match.
Brackets = 95% cluster bootstrap over ladder groups.

1. Kiting/spacing. Top ranged in fights end 88% [87-89] of turns outside a melee enemy's basic reach, but only 25% exactly
   at d=3 (mostly 4-5). Ranged attacks from range 3: 73%. Vs a dasher with dash ready only 45% (melee) / 59% (ranged) of turns
   end outside reach. Melee attack turns: walk-then-attack 43%, attack-then-walk 32% (Univ 50%), stationary 25%. Within 2-8
   points of others and us: spacing is not what separates teams.
2. Retreat. Soft own-HP threshold: break-off rate 36% at .4-.5 HP, 47% at .3-.4, 63-66% below .3 (procless steps at .5).
   AUC own HP fraction 0.70 vs threat-based rounds-to-die 0.64 (Mite .74/.58, procless .77/.67; Nyxius: local health ratio .73).
   Threat adds on top (at .4-.5 HP: 66% if could die within a round vs 38%). Recalls with enemy in sight: median .32 HP, 70%
   with no enemy able to reach that turn (step out, then recall). Carried gems: no effect (AUC .51).
3. Abilities. 88% of damage/stun casts on the first turn an enemy is in range (SBC/Univ 94, Mite 92, procless 90, Fish 84,
   Nyxius 72, us 87). Stuns hit a channeller in 8% of casts; when one is in range it is stunned 95%. Stunned target dies within
   2 rounds 8% (vs 20% after non-stun damage spells). attack_reset used on 67% of ready champion-attack turns (procless 90,
   Nyxius 45) and 85% on camps (ours 72%). Ground AoE: 65% of casts hit no champion; hits average 1.17 champions.
4. Focus fire. Kills average 1.61 distinct attackers (3 rounds), 53% solo. Victim was the lowest-HP enemy in view in 85% of
   kills with >= 2 visible (random 40%; partly mechanical). Bags not targeted (largest bag 36%).
5. Wards (clearest difference). Top teams: 96% of wards on bush tiles (four teams 100%), 2.2 per 100 alive rounds. Us: 34% on
   bushes, 7.0 per 100. Mite/SBC: 50-60% within 3 of a camp/altar; ~1% on chokes. Wards do not foreshadow kills (14% vs 12%).
6. Bushes. Top champions 6% of rounds on bushes, 12% of champion attacks from bushes; 3% of kills by a never-seen killer.
7. Priority. No common rule: Mite recomputes constantly (335 changes/champion-game), procless melee first + low HP first,
   Univ fixed order, Fish nearest-enemy first, SBC/Nyxius unused. Us: nearest enemy first.
8. Camps. Wolf groups 45% solo (Fish/Mite 31/25%, procless/SBC 66/59%), elk 26% solo (Fish/Mite 5-8%), monolith 4.7 participants.
   Clear time vs basic-attack minimum: SBC .65, Univ .68, top .79, others .81, us .88. Tanking (mixed melee+ranged clears):
   melee takes 86% of camp damage while dealing 54%; highest-HP champion takes 60% (us 77% / 42%). Camp damage per gem similar
   (top 10.2, us 9.4).
Caveats: clustering (judge by groups), one-day window, heuristic fight/threat definitions, 'lowest HP' confounded, our set mixes versions.
