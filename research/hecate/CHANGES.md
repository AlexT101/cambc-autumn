# hecate change log

hecate starts as nemesis 2dba924 (frozen as bots/baselines/nemesis-v2). Results are hecate's win rate vs
nemesis-v2, all maps both sides (main = replays/allmaps 390 games; fresh = replays/fresh 356 games).

1. Camp stuns and Monolith range-4 sieges (from bots/variants/hx-casts5b).
   - abilities.cpp camp_cast: a stun is worth the member's Strength when any visible ally is within its reach;
     a damage-free stun that keeps the walk (Cassi) is cast at value >= 1.
   - bot.cpp siege(): a ranged caster with no melee ally next to the Monolith casts from range 4, out of reach.
   - Monolith-only maps 70.7% (184 games); elsewhere level (main 54.4%, fresh 52.2%, extra fresh 46.1%).
2. Shared-gem maps: kite the shared block (from bots/variants/hx-maps2).
   - bot.cpp shared_gems_map() (every gem source a big non-Monolith group or a Monolith); kite() replaces siege()
     there: everyone to tiles within 4 of the block's hitting monsters but out of their reach, casters cast on
     cooldown (cast_at_camp any_value), ranged basic-attack harmless clusters safely, set out for a respawning
     block within kite_early 10 rounds of arrival, nearest 3 capture, contest an enemy hold (contesting()).
   - Spell users build Focus and skip Jungle there (spell_builds).
   - Shared-gem maps 77.3% (132 games), fresh shared seeds 73.3% (60); all maps 55.1% vs nemesis, 60.5% vs rival.
3. Farming throughput (from bots/variants/hx-farm8b, merged by patch).
   - emblem_gain_rounds(): rounds the next emblem saves before the race ends; capture_recall shops with a bag only
     if that beats the bag's extra walk via spawn; wants_shop goes empty-handed only if it beats recall + walk back,
     or below shop_heal_fraction 0.6 health.
   - A capture holder hits other harmless or already-awake groups in reach; a melee champion whose hit clears a group
     steps onto its tile the same turn.
   - On plain nemesis: 55.6% main, 56.2% fresh, 55.7% extra suite vs nemesis; 63.6% vs rival; captured gems +2.9%.
4. Camp stun edit (1) limited to Monolith groups: on other camps it cost ~2.5% (hecate 55.3% -> 57.9% on main+fresh+
   fresh-hf without it). hx-c4: 57.0% over 1366 games (main 56.9, fresh 58.1, fresh-hf 58.0, hx-fresh2 55.3).
5. Death avoidance (from bots/variants/hx-s3t, merged by patch; hx-c5 = merged state).
   - step_guard(): tiles a step or ready dash could end on where want_home would leave at once (fight lost with
     them striking first, lethal and we fall, or a Cassi/Issac body falls) are off limits to pathing (set_guard).
   - Safety::pursuit(): we strike first, visible enemies within pursuit_steps 3 of their reach join as they arrive,
     camp damage counts; lost (or a linked body falls) -> want_home, except healthy on own ground or paying soon.
   - threat_strike(): an enemy with two turns before our next gets one more step of reach or a second basic attack
     (Strike::max_reach 5 -> 6; pack-zone radius kept at 7).
   - On plain nemesis: 55.2% over 1102 games, our deaths ~-29%. Merged hecate (hx-c5): 60.0% over 1366 games
     (main 59.7, fresh 58.7, fresh-hf 60.2, hx-fresh2 61.5); vs rival 66.9%.
6. Contest enemy captures (from bots/variants/hx-mid2; hx-c6 = merged state).
   - contest_capture(): a cleared group of contest_gems 40+ in sight that the enemy holds or stands on, reachable
     before the hold pays: step onto a free tile of it; contesting() keeps us there for any such group.
   - 60.3% over 1722 games (6 suites incl. fresh3 seeds 7301/7302) vs 59.0% before, no suite worse.
7. Teammate's nemesis fixes 1-3 (commit 5ef5601 "Khaos v22"): bag_at_stake() for the farm pack zone and the pack
   brake, no emblem capture-recall while closing(), no siege heal trip while holding a capture. Level (59.6% vs
   60.3% over 1722 games; with fix 4, the funded siege route, also 59.6%); kept as sound fixes matching nemesis.
8. Finish a kill before retreating (from bots/variants/hx-kill2).
   - killable_now(): a visible enemy our basic attack + best ready cast kills this turn, after which the rest and the
     camps could not kill us before our next turn. It overrides the low-health retreat, and the fight-lost retreat is
     judged with that enemy left out (Safety::fight exclude); then no pursuit retreat that turn.
   - Fires ~0.15 times a game (390 games: 51 low-health bypasses, target killed 37, we died within 3 rounds 4;
     9 fight bypasses, all 9 kills). Level on win rate (60.5% main); kept as sound.
9. Fuel (from bots/variants/hx-fuel, hand-merged with item 8's exclude parameter; hx-c7 = merged state):
   Safety::strike_of (per-turn strike cache) in step_guard and visible_threat, cheap tile tests first, known_fight
   memo lookup before the fuel gate, lethal() only when it decides, one-pass fight_key. 100M bench: 16/16 identical,
   mean -0.5%, p99 -1.9%.
10. Ladder-driven changes from the Intercontinental Fish analysis ([../LADDER-FISH.md](../LADDER-FISH.md)); frozen
   baseline before them: bots/baselines/hecate-v1. Submitted as version 19.
   - Draft copied from the top ladder teams: Ren, Stellar, Cassi, Ryth, Varg (Tavi last). Ren builds Focus (its
     stun and retaliation scale with it), and solo camp estimates count its retaliation on each monster that hits it.
   - From v17: spell-station clears for ranged champions and pickup of a freshly cleared group in sight
     (local_spell_plan, collect_local_reward), with the farm evaluation's fuel kept clear of the pickup.
   - Cassi farms gold: gold_farmer_weight 4 on its gold value, and it hits harmless gold-only groups in passing.
   - Cassi and Issac: basic attacks pick the pair with the weakest body, and damage only counts once it takes a body
     below its partner (useful_damage).
   - Locally all level: 48.7% vs hecate-v1; without the v17 port and gold farmer 46.2%; hecate-v1 plus only the
     Cassi/Issac targeting 51.3%. Ladder scrims vs the top 5 on the same maps: 27-48, against 20-55 for version 18.
