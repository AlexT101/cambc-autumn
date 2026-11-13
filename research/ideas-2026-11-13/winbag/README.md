# Winning-bag escort and Tribute emblem (2026-11-13)

`chy-winbag.diff` is `bots/variants/chy-winbag/src` against `bots/baselines/v132/src` (charybdis 525): the Tribute emblem from a
score + bag of 900, the all-in escort at the safest altar, and the carrier held to that altar. `params::winbag_tribute`,
`winbag_escort` and `winbag_carrier_altar` switch each part. The ablation variants `wb-trib`, `wb-escort` and `wb-escort-free`
are this patch with those switches set. To rebuild one: `./copybot baselines/v132 variants/chy-winbag`, then
`patch -p4 -d bots/variants/chy-winbag/src < research/ideas-2026-11-13/winbag/chy-winbag.diff`.
Results: [EXPERIMENTS.md](../../EXPERIMENTS.md), "All-in escort of a winning bag at the safest altar".
