# Which fight model predicts real ladder fights?

Files in this directory:
- `fightmodel.py`: Python port of morgana's `Safety` trade sim and the variants.
- `fm_eval.py`: scoring.
- `fightmodel.pkl`: per-fight predictions.
- `fm_present.md`, `fm_part.md`: every table, including the subsets left out here.

## Data

- **Games:** 1,274 games since 2026-10-16 08:00Z with a top-6 team or us (ladder groups, plus `replays/mine` for PTN Hyperion).
- **Engagements:** 32,787 found by `tools/replay/analysis/fights.engagements()`. These are champion-damage instances that share a champion within 3 rounds and 16 tiles, or are within 1 round and 8 tiles; clusters longer than 25 rounds are split.
- **Labels:**
  - Kills label: the side with more kills in the engagement won. Only decisive engagements count: 9,756 fights in 285 ladder groups. Team A won 47% of them.
  - Swing label: the sign of the net swing (kill gems − own bags lost + 0.25 × kill gold); 9,947 fights. It gives the same picture.
- **Start state:** read at the start of the engagement's first round r0, from `rounds.json`: HP, max HP, effective Strength and Focus, and cooldowns (cd = turns until ready). The champion's current shield is ignored, because `join()` doesn't copy it. Two participant sets:
  - **present:** alive champions within 8 of the first round's damage centroid. This is the set known before the fight.
  - **part:** only the champions that actually dealt or took damage in the engagement. This uses hindsight, since it includes reinforcements and drops bystanders.
- **CIs:** 95% intervals from 300 resamples of whole ladder groups. "Δ vs b" is paired within the same resamples.

## The port (faithful to safety.cpp)

- **Turns:** each side acts as a block and the sides alternate. Every member's basic attack (Strength) and its most valuable ready cast are summed.
  - Cast value: stuns add Strength; attack_reset adds Strength; damage and shield add mult × Focus; heal adds mult × Focus when the side has more than one member; dash is worth 0.
  - Slot choice goes by value, ties to slot 0. A cast sets the slot's cooldown to turn + 8. Reset and damage casts count as 2 hits, everything else as 1.
- **Focus:** the summed damage goes to the other side's weakest member (health + shield), shield first, and the excess spills over to the next weakest.
- **Stuns:** each stun makes the other side's strongest-Strength, non-Marcella member skip its next turn.
- **Ren:** hits back hits × 0.2 Focus onto the attacking side's weakest member.
- **Cassi/Issac:** both bodies die together.
- **Shields and heals:** a shield lasts 5 of its owner's turns; a heal goes to the weakest hurt ally other than the caster.
- **Horizon:** 24 turns per side. "Lost" means our side is wiped first.
- **Not modelled (as in morgana):** Varg's splash, Vendetta's reset on kill, items, positions and reach.

## Models

| model | description |
|---|---|
| (a) | morgana as is: the enemy strikes first, from each side's point of view. The fight-level call is the side that does not lose when struck first. If both lose when struck first (11% of present fights, 7% of part), the call counts as half right. The AUC score is A's health margin minus B's. |
| (b) | Block sim with the true first striker: the side that dealt the engagement's first damage. |
| b_wrong | Block sim with the other side first. This is a control for how much turn order matters. |
| (c) | Champion-level turn order. In round r, team A starts odd rounds, teams alternate one champion at a time, and within a team higher priority then lower id goes first. Each champion's action uses the same rules as above, applied immediately. Order is taken from the start of round r0. |
| c2 | As (c), but round r0 starts at the true first striker's slot. |
| (d) | Block sim with the true first striker and Smith's-rule targeting: hit the enemy with the highest D / (health + shield) first, where D = Strength + Σ damage-spell mult × Focus / 8 + Strength / 8 if it has a reset. |
| cd, c2+d | The ordering and targeting variants combined. |
| (e) | Lanchester: H_A·D_A against H_B·D_B, with D = Strength + Σ damage-spell mult × Focus / 8. |

Baselines: HP-sum ratio, headcount difference, and "the first striker wins".

## Results (kills label)

| model | present: accuracy | CI | AUC | Δ accuracy vs (b) [CI] | part: accuracy | AUC | Δ vs (b) [CI] |
|---|---|---|---|---|---|---|---|
| (a) enemy-first | 78.6% | 77.4-79.9 | 0.865 | **−1.9 [−2.3, −1.6]** | 85.0% | 0.921 | −1.3 [−1.6, −1.0] |
| (b) true first striker | **80.5%** | 79.4-81.8 | 0.876 | 0 | **86.3%** | 0.924 | 0 |
| b_wrong (other side first) | 76.6% | 75.2-77.9 | 0.808 | −3.9 [−4.7, −3.3] | 83.7% | 0.877 | −2.6 |
| (c) slot order from start of round | 79.3% | 78.1-80.6 | 0.856 | −1.3 [−1.7, −0.7] | 85.5% | 0.909 | −0.8 [−1.2, −0.4] |
| c2 slot order from first striker | 80.6% | 79.6-81.8 | **0.880** | +0.1 [−0.2, +0.4] | 86.5% | **0.927** | +0.2 [−0.1, +0.5] |
| (d) Smith targeting | 80.4% | 79.3-81.7 | 0.875 | −0.1 [−0.4, +0.2] | 86.7% | 0.924 | **+0.4 [+0.2, +0.6]** |
| c2 + Smith | 80.5% | 79.3-81.8 | 0.878 | −0.0 [−0.4, +0.4] | 86.7% | 0.927 | +0.4 [+0.1, +0.7] |
| (e) Lanchester | 74.9% | 73.6-76.3 | 0.827 | −5.6 [−6.3, −4.9] | 82.4% | 0.900 | −3.8 [−4.5, −3.2] |
| HP ratio | 72.1% | | 0.795 | −8.4 | 76.8% | 0.846 | −9.5 |
| first striker wins | 69.3% | | 0.697 | −11.2 | 69.3% | 0.697 | −17.0 |
| headcount | 62.2% | | 0.675 | −18.3 | 61.2% | 0.672 | −25.1 |

### Subsets (present set, Δ vs (b))

| subset | n | (b) accuracy | (a) | c2 | (d) |
|---|---|---|---|---|---|
| 1v1 | 916 | 93.2% | −1.7 | −0.2 | 0 |
| 2+ champions on each side | 5,378 | 77.7% | −2.2 | 0.0 | −0.2 |
| uneven numbers | 7,102 | 79.1% | −1.5 | +0.5 [+0.1, +0.8] | −0.1 |
| top-6 team on both sides | 2,829 (69 groups) | 81.1% | −2.5 | −0.2 | −0.3 |
| games with us | 3,520 (141 groups) | 82.1% | −1.9 | 0.0 | 0.0 |

In the part set, Smith targeting helps most in 2v2+ fights: +0.9 [+0.2, +1.5] (2,808 fights).

### How often (a) calls a fight lost for a side that actually won it

Each fight is counted from both sides; kills label.

| side group | present: winners called LOST | present: losers called LOST | present: precision of LOST | part: winners called LOST | part: precision |
|---|---|---|---|---|---|
| all sides | **27%** (of 9,756 winners) | 84% | 76% | 18% | 83% |
| TOP6 sides | 27% | 84% | 70% | 20% | 77% |
| PTN Hyperion sides | 20% | 78% | 65% | 14% | 75% |
| other teams | 33% | 85% | 86% | 21% | 91% |

## Conclusions

1. **The block sim is a strong predictor.** It reaches 80.5% accuracy and AUC 0.88 on the pre-fight participant set, and 86% / 0.92 when the participants are known. That is far ahead of Lanchester (−4 to −6 points), the HP ratio (−8 to −10) and "the first striker wins" (−11 to −17).
2. **The enemy-first assumption costs about 2 points of accuracy** (−1.9 [−2.3, −1.6] present, −1.3 part).
   - It calls 27% of the sides that went on to win the fight "lost" (18% in the part set), and leaves 11% of fights undecided because both sides lose when struck first.
   - It is still more accurate than assuming the wrong side strikes first (b_wrong: −3.9). Turn order is worth about 4 points in total, and the pessimistic assumption gives up about half of it.
3. **Champion-level turn order (c) does not improve on block alternation.**
   - Started at the top of the round, it is worse (−1.3 [−1.7, −0.7]): it lets champions who weren't in reach act first.
   - Started at the true first striker's slot (c2), it is level: +0.1 [−0.2, +0.4]. The exception is fights with uneven numbers, at +0.5 [+0.1, +0.8], with AUC +0.004.
   - What matters is which side strikes first, not the interleaving.
4. **Smith's-rule targeting (d) is level with weakest-first.** It is −0.1 [−0.4, +0.2] in the present set and +0.4 [+0.2, +0.6] in the part set (+0.9 in 2v2+ fights). That is too small to matter for prediction. For a bot's own target choice, Smith targeting costs nothing in predictive accuracy.

## Caveats

- **Only fights with a winner by kills are scored** (about 30% of engagements). Pokes that end 0-0 are excluded, so absolute accuracies are inflated for lopsided fights; 1v1 reaches 93-96%.
- **The sim always plays to a wipe,** but real engagements end at the first kill or a retreat. The label is kill difference, not a wipe.
- **The "first striker" is the first damage instance in the engagement.** That is known to the side choosing to strike, but not to a defender in advance.
- **Present vs part:** the present set is a proxy for what a bot could see, without vision limits or unseen enemies. The part set uses outcome information (who joined).
- **Participants differ from morgana's own fight().** Morgana uses allies within 4 and the enemies that can hit the tile; here participants are everyone within 8 of the fight.
- **Morgana-only simplifications** (shield ignored at join, no splash, no reset on kill) are kept in every variant, so the comparisons isolate ordering and targeting only.
