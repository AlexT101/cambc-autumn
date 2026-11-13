# Camp-death gem denial (2026-11-13): abandoned before building; a camp can land the blow on 0-3 of 78 live hoard kills

**Idea.** A champion killed by a camp loses its carried gems, and the killer gets no kill gold. Camps attack at the
start of each round, before champion turns. So a hoarding Prism whose death is certain could end its turn where an
awake camp lands the last blow at the next camp phase, before Fish's killer acts. The bag would be destroyed
instead of handed to Vesper.

**The test.** The camp must deal the Prism's remaining health in one camp phase. That health is the health at the
end of round D-1, where D is the death round. Two more conditions:
- the Prism must be each monster's strictly nearest champion;
- the monster must be awake, or one the Prism wakes by hitting it, which costs its walk (a Prism's walk, attack and
  casts are mutually exclusive).

**Data.** The 244 extracted live Fish r8 games (`~/tmp-offload/fishr8/live/ext`, `rows-r8-all.json`). There are 78
deaths of our champions with a bag of 100+ gems at a Fish champion's hands, 24,172 gems in all. 68 of them are the
Prism's, and 55 are kills by Vesper.

| | hoard deaths (bag 100+) | gems |
|---|---|---|
| all | 78 | 24,172 |
| health at that camp phase ≤ 60 / ≤ 120 / ≤ 200 | 16 / 26 / 31 | 5,088 / 7,495 / 8,642 |
| a live monster's range covers the victim's tile at the end of D-1 | 19 (9 awake) | |
| that monster's Strength ≥ the victim's health | 2 | 787 |
| **feasible:** one step, awake monsters only, victim strictly nearest | **0** | 0 |
| one step, waking allowed, victim strictly nearest (`feas.py`) | 2 | 883 |
| two steps, any wake state, no nearest test (the loosest bound, `relax.py`) | 5 | 1,786 |

- **Health is not the binding constraint: Strength and placement are.** The Prism is often low at the last camp
  phase (median 259 health, 40% at 200 or less).
  - The live camps beside hoard kills are mostly wolves (Strength 20) and elks (60), against the Prism's usual
    100-500 health.
  - The awake cases fall just short: a Monolith hit of 200 left the Prism at 206, and a wolf plus an elk (80) met 114.
  - Fights over captures happen on cleared groups, whose monsters are dead.
- **The ideation's "20 within reach" is the 19 above.** It did not compare camp Strength with the Prism's health.
- **The wider form, denying kill gold on any certain death, is small too.** Of all 1,320 deaths to Fish champions,
  the realistic bound is 14 (1.1%) and the loosest is 184 (13.9%). That is about 50 gold a game at most, against
  Fish's 4,600 by r600.
- **Expected effect.** Two feasible events in 244 games, one of them in a game we won anyway. The upper bound is
  under 0.5 points even if every event flipped a game. A "death is certain" trigger would also add false positives
  that kill a hoarding Prism outright. It cannot reach the 50.5% bar, and no gate could measure it.

**Verdict:** abandoned, not built or gated.

Scripts (each reads `EXT ROWS.json`):
- `hoardhp.py`: health at the camp phase before the kill, and monsters in reach.
- `feas.py`: the one-step feasibility, with the nearest and wake tests.
- `relax.py`: the relaxed bounds for 0, 1 and 2 steps.

Working output is in `~/tmp-offload/camp-death-gem-denial/`.
