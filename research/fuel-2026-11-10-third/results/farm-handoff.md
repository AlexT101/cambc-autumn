# Handoff: farm-loop fuel reserve sweep (from the "nooof" fuel-prover agent, paused 2026-11-10 07:45 UTC)

User: "the fuel work can be paused cuz usage ... you can just dump what it was gonna do on it have it do it instead."
Take it over only if it fits what you're doing; your own work comes first.

## What it found (committed: 5f77c9805, b0eeff17e; EXPERIMENTS "farm-loop reserve")
- Fuel ceiling: more fuel per turn helps (~+0.45 pts per extra 1k); the gain is fuel-gated work doing more, not fewer out-of-fuel turns.
- Farm-loop reserve is loose: on cut turns, 9 in 10 the rest of the decision spends ~11.6k less than held back.
- Out-of-fuel turns miss by <3.9k half the time, mostly fight turns (strike search ~36k).
- Reserve sweep on ocean-16d6f78 + q1 (fgate vs ocean-16d6f78, Flp4/Mt3q): rs2 -0.27, rs4 -0.04, rs6 -0.03, rs8 +0.15, rs12 +0.21, re8 +0.13, re6 -0.20 (all ±0.25; ladder +0.2..+0.55). All level; rs8 is live as v106.
- ss1 (strike search below 25k) -0.36 ±0.54, rejected. `-mllvm -inline-threshold` gain can't ship (ladder builds src/ with its own flags).

## What it was doing when stopped (partial, killed mid-fgate)
Larger reserves 16k/20k/24k (variants/oc16-rs16/20/24; chain ~/tmp-offload/nooof/tools/chain-rsbig.sh; logs fgate-oc16-rs*.log, boc16-rs*.log):
- rs16: fresh +0.05 ±0.52 of 9.7k units, ladder +0.40; out-of-fuel play turns 986
- rs20: fresh -0.43 ±0.56 of 8.7k, ladder +0.58; oof 1441
- rs24: fresh -0.12 ±0.60 of 7.4k, ladder +0.84; oof 1850
Reading: nothing beats rs8/rs12; out-of-fuel grows with reserve. Plan was: queue live only if one clearly beat rs8/rs12 (none does so far).

## Open next steps it had
- Spend the loose reserve better (the 11.6k slack) without raising out-of-fuel turns.
- Patches/tools: research/fuelcap-2026-11-09/ (oc16-q1/ss1/rs .patch, tools/), ~/tmp-offload/nooof/tools/.
