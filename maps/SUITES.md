# Map suites

Index of what is under `maps/` (2026-11-05). Everything below `maps/suites/` and every other folder except `fall-custom/` and `gen-bench/` is gitignored and can be remade from its seed with `tools/mapgen/mapgen.mjs`; `index.json` in each generated suite records its `seed` and `mix`.

## Top level

- The 128 ladder maps (`*.map26a`): `cambc run --map NAME` and the `ladder` suite only look directly under `maps/`, and mutation maps draw their source from them.
- `gen/` (seed 6001) and `gen-s1/` (6002): the standard `ab.py` suites (`gen`, `fresh` = every `maps/gen-s*`). Remake: `node tools/mapgen/mapgen.mjs suite --mix varied-v1` (`maps/gen`) and `--seed 6002 --mix varied-v1 --out maps/gen-s1`.
- `fall-custom/`, `gen-bench/`: tracked in git (`gen-bench` is `tools/fuel/bench.py`'s set).
- `suites/`: everything else, by family (below).

## suites/fresh/

Single-seed generated suites, `suites/fresh/fresh-<seed>/` (256 maps each, the directory name kept so `ab.py` labels and old notes still match). Remake a range with
`node tools/mapgen/mapgen.mjs suite --seed A-B --mix MIX --out 'maps/suites/fresh/fresh-{seed}'` (at most ~30k maps, about 117 suites, per command). MIX is `ladder` for `ladder` suites (calibration 2, from 2026-11-05) and `varied-v1` for `varied` ones (calibration 1, 2026-10-30 to 2026-11-05; byte for byte only while `maps/` holds the same ladder maps). Suites made before 2026-10-30 came from an older generator and cannot be remade exactly.

| seeds | suites | mix (index.json) | remake with | made |
|---|---|---|---|---|
| 4104 | 1 | varied | `--mix varied-v1` | 2026-11-04 |
| 6003-6040 | 38 | varied | `--mix varied-v1` | 2026-10-30 |
| 9001-9004 | 4 | varied | `--mix varied-v1` | 2026-10-30 |
| 9100-9280 | 181 | varied | `--mix varied-v1` | 2026-10-30 |
| 9300-9379 | 80 | varied | `--mix varied-v1` | 2026-10-30 |
| 9400-9419 | 20 | varied | `--mix varied-v1` | 2026-10-31 |
| 9501-9520 | 20 | varied | `--mix varied-v1` | 2026-10-30 |
| 9600-9719 | 120 | varied | `--mix varied-v1` | 2026-10-31 |
| 9800-10019 | 220 | varied | `--mix varied-v1` | 2026-10-31 |
| 10100-10139 | 40 | varied | `--mix varied-v1` | 2026-10-31 |
| 11000-11019 | 20 | varied | `--mix varied-v1` | 2026-11-01 |
| 11100-11109 | 10 | varied | `--mix varied-v1` | 2026-11-01 |
| 22000-22029 | 30 | varied | `--mix varied-v1` | 2026-11-01 |
| 24000-24039 | 40 | varied | `--mix varied-v1` | 2026-10-31 |
| 31300-31319 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 31400-31459 | 60 | varied | `--mix varied-v1` | 2026-11-02 |
| 52000-52019 | 20 | varied | `--mix varied-v1` | 2026-11-03 |
| 53000-53039 | 40 | varied | `--mix varied-v1` | 2026-11-03 |
| 66001-66040 | 40 | varied | `--mix varied-v1` | 2026-11-04 |
| 66101-66120 | 20 | varied | `--mix varied-v1` | 2026-11-04 |
| 66201-66220 | 20 | varied | `--mix varied-v1` | 2026-11-04 |
| 66301-66320 | 20 | varied | `--mix varied-v1` | 2026-11-04 |
| 66401-66420 | 20 | varied | `--mix varied-v1` | 2026-11-04 |
| 67101-67120 | 20 | varied | `--mix varied-v1` | 2026-11-04 |
| 67201-67220 | 20 | varied | `--mix varied-v1` | 2026-11-04 |
| 67301-67340 | 40 | varied | `--mix varied-v1` | 2026-11-04 |
| 67401-67420 | 20 | varied | `--mix varied-v1` | 2026-11-04 |
| 67501-67520 | 20 | varied | `--mix varied-v1` | 2026-11-04 |
| 67601-67640 | 40 | varied | `--mix varied-v1` | 2026-11-04 |
| 67701-67720 | 20 | varied | `--mix varied-v1` | 2026-11-04 |
| 67801-67820 | 20 | varied | `--mix varied-v1` | 2026-11-04 |
| 67901-67940 | 40 | varied | `--mix varied-v1` | 2026-11-04 |
| 68001-68020 | 20 | varied | `--mix varied-v1` | 2026-11-04 |
| 68101-68120 | 20 | varied | `--mix varied-v1` | 2026-11-04 |
| 68201-68220 | 20 | varied | `--mix varied-v1` | 2026-11-04 |
| 70001-70020 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 70101-70120 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 70201-70220 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 70301-70320 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 70401-70420 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 70501-70520 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 70601-70620 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 70701-70720 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 70801-70820 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 70901-70920 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 71201-71220 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 71301-71320 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 71401-71420 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 71501-71520 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 71601-71620 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 71701-71720 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 72001-72020 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 73001-73080 | 80 | varied | `--mix varied-v1` | 2026-11-02 |
| 73101-73180 | 80 | varied | `--mix varied-v1` | 2026-11-02 |
| 73201-73280 | 80 | varied | `--mix varied-v1` | 2026-11-02 |
| 73301-73380 | 80 | varied | `--mix varied-v1` | 2026-11-02 |
| 73401-73440 | 40 | varied | `--mix varied-v1` | 2026-11-02 |
| 77000-77195 | 196 | varied | `--mix varied-v1` | 2026-11-03 |
| 81001-81200 | 200 | varied | `--mix varied-v1` | 2026-11-02 |
| 82001-82040 | 40 | varied | `--mix varied-v1` | 2026-11-02 |
| 83001-83080 | 80 | varied | `--mix varied-v1` | 2026-11-02 |
| 84001-84040 | 40 | varied | `--mix varied-v1` | 2026-11-02 |
| 85000-85019 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 85100-85139 | 40 | varied | `--mix varied-v1` | 2026-11-02 |
| 85200-85239 | 40 | varied | `--mix varied-v1` | 2026-11-02 |
| 85300-85319 | 20 | varied | `--mix varied-v1` | 2026-11-02 |
| 85400-85458 | 59 | varied | `--mix varied-v1` | 2026-11-02 |
| 85500-85559 | 60 | varied | `--mix varied-v1` | 2026-11-02 |
| 85600-85659 | 60 | varied | `--mix varied-v1` | 2026-11-02 |
| 85700-85758 | 59 | varied | `--mix varied-v1` | 2026-11-02 |
| 85800-85859 | 60 | varied | `--mix varied-v1` | 2026-11-02 |
| 85900-85959 | 60 | varied | `--mix varied-v1` | 2026-11-02 |
| 86000-86059 | 60 | varied | `--mix varied-v1` | 2026-11-02 |
| 86100-86178 | 79 | varied | `--mix varied-v1` | 2026-11-03 |
| 88001-88040 | 40 | varied | `--mix varied-v1` | 2026-11-04 |
| 91001-91040 | 40 | varied | `--mix varied-v1` | 2026-11-03 to 2026-11-04 |
| 92001-92100 | 100 | varied | `--mix varied-v1` | 2026-11-03 |
| 93000-93059 | 60 | varied | `--mix varied-v1` | 2026-11-03 |
| 94001-94080 | 80 | varied | `--mix varied-v1` | 2026-11-03 |
| 95001-95040 | 40 | varied | `--mix varied-v1` | 2026-11-03 |
| 96001-96040 | 40 | varied | `--mix varied-v1` | 2026-11-03 |
| 96101-96140 | 40 | varied | `--mix varied-v1` | 2026-11-03 |
| 97001-97040 | 40 | varied | `--mix varied-v1` | 2026-11-03 |
| 98301-98340 | 40 | varied | `--mix varied-v1` | 2026-11-03 |
| 98501-98520 | 20 | varied | `--mix varied-v1` | 2026-11-03 |
| 98601-98640 | 40 | varied | `--mix varied-v1` | 2026-11-03 |
| 99001-99040 | 40 | varied | `--mix varied-v1` | 2026-11-03 |
| 99101-99357 | 257 | varied | `--mix varied-v1` | 2026-11-04 |
| 99401-99440 | 40 | varied | `--mix varied-v1` | 2026-11-04 |
| 99601-99640 | 40 | varied | `--mix varied-v1` | 2026-11-03 |
| 99701-99857 | 157 | varied | `--mix varied-v1` | 2026-11-04 |
| 147001-147120 | 120 | varied | `--mix varied-v1` | 2026-11-04 |
| 148001-148180 | 180 | varied | `--mix varied-v1` | 2026-11-04 |
| 149001-149180 | 180 | varied | `--mix varied-v1` | 2026-11-04 |
| 150001-150160 | 160 | varied | `--mix varied-v1` | 2026-11-05 |
| 150201-150480 | 280 | varied | `--mix varied-v1` | 2026-11-05 |
| 160000-160099 | 100 | varied | `--mix varied-v1` | 2026-11-05 |
| 161000-161039 | 40 | varied | `--mix varied-v1` | 2026-11-05 |
| 190001-190120 | 120 | varied | `--mix varied-v1` | 2026-11-05 |
| 191001-191320 | 320 | varied | `--mix varied-v1` | 2026-11-05 |
| 192001-192160 | 160 | varied | `--mix varied-v1` | 2026-11-05 |
| 192161-192360 | 200 | ladder | `--mix ladder` | 2026-11-05 |
| 192401-192440 | 40 | varied-v1 | no index.json | 2026-11-05 |
| 192441-192480 | 40 | ladder | `--mix ladder` | 2026-11-05 |
| 192481-192520 | 40 | varied | `--mix varied-v1` | 2026-11-05 |
| 192521-192560 | 40 | ladder | `--mix ladder` | 2026-11-05 |
| 192561-192580 | 20 | varied | `--mix varied-v1` | 2026-11-05 |
| 192581-192600 | 20 | ladder | `--mix ladder` | 2026-11-05 |
| 192601-192640 | 40 | varied | `--mix varied-v1` | 2026-11-05 |
| 192641-192680 | 40 | ladder | `--mix ladder` | 2026-11-05 |
| 192681-192760 | 80 | varied | `--mix varied-v1` | 2026-11-05 |
| 192761-192800 | 40 | ladder | `--mix ladder` | 2026-11-05 |
| 505001-505140 | 140 | varied | `--mix varied-v1` | 2026-11-05 |
| 506000-506599 | 600 | ladder | `--mix ladder` | 2026-11-05 |
| 506600-506639 | 40 | varied | `--mix varied-v1` | 2026-11-05 |
| 506900-506999 | 100 | ladder | `--mix ladder` | 2026-11-05 |
| 509100-509199 | 100 | ladder | `--mix ladder` | 2026-11-05 |
| 510001-510120 | 120 | ladder | `--mix ladder` | 2026-11-05 |
| 510121-510125 | 5 | varied | `--mix varied-v1` | 2026-11-05 |
| 510200-510379 | 180 | ladder | `--mix ladder` | 2026-11-05 |
| 511000-511119 | 120 | ladder | `--mix ladder` | 2026-11-05 |
| 511200-511239 | 40 | ladder | `--mix ladder` | 2026-11-05 |
| 511300-511779 | 480 | ladder | `--mix ladder` | 2026-11-05 |
| 511900-511909 | 10 | varied | `--mix varied-v1` | 2026-11-05 |
| 512000-512039 | 40 | ladder | `--mix ladder` | 2026-11-05 |
| 513000-513090 | 91 | ladder | `--mix ladder` | 2026-11-05 |
| 513091-513100 | 10 | varied | `--mix varied-v1` | 2026-11-05 |
| 513101-513120 | 20 | ladder | `--mix ladder` | 2026-11-05 |
| 514000-514039 | 40 | ladder | `--mix ladder` | 2026-11-05 |
| 514200-514279 | 80 | ladder | `--mix ladder` | 2026-11-05 |
| 514400-514439 | 40 | ladder | `--mix ladder` | 2026-11-05 |
| 514440-514449 | 10 | varied | `--mix varied-v1` | 2026-11-05 |
| 514500-514504 | 5 | ladder | `--mix ladder` | 2026-11-05 |
| 514510-514519 | 10 | ladder | `--mix ladder` | 2026-11-05 |
| 516001-516060 | 60 | ladder | `--mix ladder` | 2026-11-05 |
| 516061-516070 | 10 | varied | `--mix varied-v1` | 2026-11-05 |
| 516101-516180 | 80 | ladder | `--mix ladder` | 2026-11-05 |
| 517000-517019 | 20 | ladder | `--mix ladder` (SPSA oc3 tuning pool: never judge on them) | 2026-11-05 |
| 517100-517139 | 40 | ladder | `--mix ladder` (oc3-judge) | 2026-11-05 |
| 517200-517209 | 10 | varied | `--mix varied` (oc3-varied) | 2026-11-05 |
| 517210-517249 | 40 | ladder | `--mix ladder` | 2026-11-05 |
| 517300-517309 | 10 | ladder | `--mix ladder` (oc3-panel2) | 2026-11-05 |
| 517310-517349 | 40 | ladder | `--mix ladder` | 2026-11-05 |
| 517400-517409 | 10 | varied | `--mix varied` | 2026-11-05 |
| 521000-521039 | 40 | ladder | `--mix ladder` | 2026-11-05 |
| 521100-521139 | 40 | ladder | `--mix ladder` | 2026-11-05 |
| 521200-521209 | 10 | varied | `--mix varied` | 2026-11-05 |
| 518100-518139 | 40 | ladder | `--mix ladder` (oc3-confirm) | 2026-11-05 |
| 518140-518179 | 40 | ladder | `--mix ladder` (oc3-confirm2) | 2026-11-05 |
| 518200-518209 | 10 | varied | `--mix varied` (oc3-confirm-varied) | 2026-11-05 |
| 524000-524039 | 40 | ladder | `--mix ladder` (oc3-astr) | 2026-11-05 |
| 526000-526019 | 20 | ladder | `--mix ladder` (SPSA oc4 tuning pool: never judge on them) | 2026-11-05 |
| 526100-526139 | 40 | ladder | `--mix ladder` (oc4-sprt) | 2026-11-05 |
| 526500-526539 | 40 | ladder | `--mix ladder` (oc4-confirm) | 2026-11-05 |
| 526600-526609 | 10 | varied | `--mix varied` (oc4-varied) | 2026-11-05 |
| 526700-526709 | 10 | ladder | `--mix ladder` (oc4-panel2) | 2026-11-05 |
| 527000-527009 | 10 | ladder | `--mix ladder` (mirror pull 3rd pass: label pool, made in scratch; only used maps moved to suites/mp3) | 2026-11-05 |
| 527100-527104 | 5 | varied | `--mix varied` (mirror pull 3rd pass: label pool, scratch) | 2026-11-05 |
| 527500-527539 | 40 | ladder | `--mix ladder` (mirror pull 3rd pass: the gate's top 20% moved to suites/mp3/sel-ab; the rest scratch, not A/B-clean) | 2026-11-05 |
| 527600-527609 | 10 | varied | `--mix varied` (mirror pull 3rd pass: made in scratch, unused) | 2026-11-05 |
| 529000-529079 | 80 | ladder | `--mix ladder` (spawncamp round 2: dev; 529000-529039 is `df2-full`, the near subsets `df2-*` come from both halves) | 2026-11-06 |
| 529100-529139 | 40 | ladder | `--mix ladder` (spawncamp round 2 confirm: `df2-conf`) | 2026-11-06 |
| 529140-529149 | 10 | varied | `--mix varied` (spawncamp round 2 robustness: `df2-vary`) | 2026-11-06 |
| 528000-528039 | 40 | ladder | `--mix ladder` (fuel rounds 5-6 dev: `oc-fuel5-dev`) | 2026-11-05 |
| 528100-528139 | 40 | ladder | `--mix ladder` (fuel rounds 5-6 confirm: `oc-fuel5-conf`) | 2026-11-05 |
| 530000-530009 | 10 | varied | `--mix varied` (fuel round 6 robustness: `oc-fuel6-varied`) | 2026-11-06 |
| 531000-531039 | 40 | ladder | `--mix ladder` (oc-base4 merge check: `oc-base4-conf`) | 2026-11-06 |
| 550000-550156 | 157 | ladder | `--mix ladder` (ocean / ocean_tune3 against astraeus: `ast-ocean-40k`) | 2026-11-06 |
| 540000-540019 | 20 | ladder | `--mix ladder` (bots/fish dev suite: `fish-dev`; seeds 540000-540999 reserved for bots/fish) | 2026-11-06 |
| 535000-535039 | 40 | ladder | `--mix ladder` (ocean HER against astraeus 37e1eb64: `ocean-vs-astr-1106`) | 2026-11-06 |
| 536000-536039 | 40 | ladder | `--mix ladder` (astraeus changes ported to ocean: dev, `ap-dev`) | 2026-11-06 |
| 536100-536139 | 40 | ladder | `--mix ladder` (astraeus port confirm: `ap-conf`) | 2026-11-06 |
| 536200-536239 | 40 | ladder | `--mix ladder` (astraeus port combination confirm: `ap-combo`) | 2026-11-06 |
| 536300-536309 | 10 | varied | `--mix varied` (astraeus port robustness: `ap-varied`) | 2026-11-06 |
| 536400-536439 | 40 | ladder | `--mix ladder` (astraeus port second confirm: `ap-conf2`) | 2026-11-06 |
| 541000-541039 | 40 | ladder | `--mix ladder` (perma-lock confirm: `fresh-541000-541039`; research/ladder-scrims-2026-11-06/fix-lock.md) | 2026-11-06 |
| 541100-541119 | 20 | ladder | `--mix ladder` (perma-lock dev: its one-site maps are `lock-one-dev`, its multi-site maps `lock-multi-dev`) | 2026-11-06 |
| 544000-544039 | 40 | ladder | `--mix ladder` (cooked comebacks dev: `cb-e`; research/ideas-2026-11-05/comeback.md) | 2026-11-06 |
| 544100-544139 | 40 | ladder | `--mix ladder` (cooked comebacks confirm: `cb-c`) | 2026-11-06 |
| 544200-544209 | 10 | ladder | `--mix ladder` (cooked comebacks measurement: `cb-m`; `cb-smoke` is its first 40 maps) | 2026-11-06 |
| 544300-544339 | 40 | ladder | `--mix ladder` (cooked comebacks random gambit logger: `cb-L`) | 2026-11-06 |
| 544400-544439 | 40 | ladder | `--mix ladder` (cooked comebacks second confirm: `cb-d`) | 2026-11-06 |
| 544900-544909 | 10 | varied | `--mix varied` (cooked comebacks robustness: `cb-v`) | 2026-11-06 |
| 545000-545039 | 40 | ladder | `--mix ladder` (draft model features dev: `df-e`; research/ideas-2026-11-05/draftfeat.md; seeds 545000-545999 reserved for it) | 2026-11-06 |
| 545100-545139 | 40 | ladder | `--mix ladder` (draft model features confirm: `df-c`) | 2026-11-06 |
| 545200-545209 | 10 | varied | `--mix varied` (draft model features robustness: `df-v`) | 2026-11-06 |
| 547000-547039 | 40 | ladder | `--mix ladder` (ocean fuel round 8 confirm: `merged/fuel8-conf`; CHANGES 433) | 2026-11-06 |
| 547100-547139 | 40 | ladder | `--mix ladder` (ocean fuel round 9 confirm: `merged/fuel9-conf`; CHANGES 434) | 2026-11-06 |
| 547200-547239 | 40 | ladder | `--mix ladder` (ocean fuel round 10 confirm: `merged/fuel10-conf`; CHANGES 436) | 2026-11-06 |
| 548000-548099 | 100 | ladder | `--mix ladder` (draft6 lab pool, `replays/draftlab/draft6`; research/ideas-2026-11-05/draft6.md; seeds 548000-548999 reserved for it) | 2026-11-06 |
| 548200-548239 | 40 | ladder | `--mix ladder` (draft6 dev A/B: `d6-e`) | 2026-11-06 |
| 548300-548339 | 40 | ladder | `--mix ladder` (draft6 confirm: `d6-c`) | 2026-11-06 |
| 548400-548409 | 10 | varied | `--mix varied` (draft6 robustness: `d6-v`) | 2026-11-06 |
| 548500-548509 | 10 | ladder | `--mix ladder` (draft6 second panel set for astraeus and proteus: `d6-p2`) | 2026-11-06 |
| 590000-590099 | 100 | ladder | `--mix ladder` (draft7 lab pool, `replays/draftlab/draft7`; research/ideas-2026-11-06/draft7.md; seeds 590000-590999 reserved for it) | 2026-11-06 |
| 590200-590239 | 40 | ladder | `--mix ladder` (draft7 2x screen: `d7-e`) | 2026-11-06 |
| 590300-590339 | 40 | ladder | `--mix ladder` (draft7 held out: `d7-c`, half of `d7-held`) | 2026-11-06 |
| 590400-590419 | 20 | varied | `--mix varied` (draft7 robustness: `d7-v` is 590400-590409, `d7-varied` all 20) | 2026-11-06 |
| 590500-590529 | 30 | ladder | `--mix ladder` (draft7 panel: `d7-p2` is 590500-590509; `d7-panel` all 30 plus panel-check-514510) | 2026-11-07 |
| 590600-590639 | 40 | ladder | `--mix ladder` (draft7 held out: the other half of `d7-held`) | 2026-11-07 |
| 546000-546019 | 20 | ladder | `--mix ladder` (SPSA run oc5's pool, with the ladder x8: `replays/tune/oc5`) | 2026-11-06 |
| 546100-546139 | 40 | ladder | `--mix ladder` (SPSA oc5 confirm: `merged/oc5-confirm`) | 2026-11-06 |
| 546200-546209 | 10 | varied | `--mix varied` (SPSA oc5 robustness: `merged/oc5-varied`) | 2026-11-06 |
| 570000-570039 | 40 | ladder | `--mix ladder` (pooled level changes, 2x screen and ablations: `merged/pool-dev`) | 2026-11-06 |
| 570100-570139 | 40 | ladder | `--mix ladder` (pooled level changes, held-out real budget: `merged/pool-held`) | 2026-11-06 |
| 570200-570209 | 10 | varied | `--mix varied` (pooled level changes, robustness: `merged/pool-varied`) | 2026-11-06 |
| 570300-570309 | 10 | ladder | `--mix ladder` (pooled level changes, second panel set: `merged/pool-panel2`) | 2026-11-06 |
| 570400-570439 | 40 | ladder | `--mix ladder` (pooled level changes, second held-out set: `merged/pool-held2`) | 2026-11-06 |
| 546300-546309 | 10 | ladder | `--mix ladder` (SPSA oc5 second panel set for astraeus and proteus: `merged/oc5-panel2`) | 2026-11-06 |
| 546400-546439 | 40 | ladder | `--mix ladder` (map-conditioned constants screen at 2x fuel: `merged/mc2-screen`) | 2026-11-06 |
| 540200-540219 | 20 | ladder | `--mix ladder` (merged fish against astraeus: `merged/fish-af10k`) | 2026-11-06 |
| 580000-580039 | 40 | ladder | `--mix ladder` (fuel pass on oc-base10, exact step A/B: `merged/fuel11-a`) | 2026-11-06 |
| 580100-580139 | 40 | ladder | `--mix ladder` (fuel pass on oc-base10, SPRT screens: `merged/fuel11-b`) | 2026-11-06 |
| 580200-580239 | 40 | ladder | `--mix ladder` (fuel pass on oc-base10, held-out confirm: `merged/fuel11-c`) | 2026-11-06 |
| 910000-910019 | 20 | ladder | `--mix ladder` (fuel campaign 12, agent A's A/B: `merged/fc12-a`) | 2026-11-07 |
| 910100-910119 | 20 | ladder | `--mix ladder` (fuel campaign 12, agent B's A/B: `merged/fc12-b`) | 2026-11-07 |
| 910200-910239 | 40 | ladder | `--mix ladder` (fuel campaign 12, merge A/B: `merged/fc12-m`) | 2026-11-07 |
| 640000-640079 | 80 | ladder | `--mix ladder` (ocean against astraeus: `merged/ao-40k`) | 2026-11-06 |
| 741001-741040 | 40 | ladder | `--mix ladder` (astraeus goal field off spawn, gf2: `merged/gf2-741`) | 2026-11-06 |
| 742001-742040 | 40 | ladder | `--mix ladder` (astraeus camp damage by the nearest-champion rule, cd2: `merged/cd2-742`) | 2026-11-06 |
| 743001-743040 | 40 | ladder | `--mix ladder` (astraeus area hits and stuns in the camp-clear estimate, areaclear: `merged/ac-743`) | 2026-11-06 |
| 744001-744160 | 160 | ladder | `--mix ladder` (astraeus camp damage confirm, cd2-80k: `merged/cd2-744`) | 2026-11-06 |
| 745001-745040 | 40 | ladder | `--mix ladder` (astraeus turn-end feint fixes, feintfix: `merged/ff-745`) | 2026-11-06 |
| 746001-746040 | 40 | ladder | `--mix ladder` (astraeus feint fixes 2-4 alone, ff24: `merged/ff24-746`) | 2026-11-06 |
| 806001-806200 | 200 | ladder | `--mix ladder` (SPSA tc3/tc3ctl tuning pool, each map in one iteration: `merged/tc3-pool-806`; research/tune-combo3-2026-11-06.md; never judge on them) | 2026-11-06 |
| 807001-807040 | 40 | ladder | `--mix ladder` (combo3 untuned against astraeus 8c0343f: `merged/tc3-base-807`) | 2026-11-06 |
| 807101-807140 | 40 | ladder | `--mix ladder` (tuned combo3 against tuned astraeus: `merged/tc3-h2h-8071`) | 2026-11-06 |
| 807201-807240 | 40 | ladder | `--mix ladder` (each tuned bot against its untuned base: `merged/tc3-self-8072`) | 2026-11-06 |
| 807301-807340 | 40 | ladder | `--mix ladder` (tuned and untuned bots against ocean: `merged/tc3-ocean-8073`) | 2026-11-06 |
| 807401-807410 | 10 | ladder | `--mix ladder` (tc3 panel set: `merged/tc3-panel-8074`) | 2026-11-06 |
| 807501-807540 | 40 | ladder | `--mix ladder` (combo3 as merged, before the audit fixes: `merged/tc3-merge-8075`) | 2026-11-06 |
| 807601-807610 | 10 | varied | `--mix varied` (tc3 robustness, tuned against tuned: `merged/tc3-varied-8076`) | 2026-11-06 |
| lg 509001-509060 | 60 | ladder | `--mix ladder` | 2026-11-05 |
| oc-n1 508000-508039 | 40 | ladder | `--mix ladder` | 2026-11-05 |
| 791001-791600, 792001-792200 | 800 | ladder | `--mix ladder` | 2026-11-07 |
| 795001-795080, 796001-796080 | 160 | ladder | `--mix ladder` (fuel campaign 16: `merged/fuel16-795`, `merged/fuel16-796`) | 2026-11-07 |

## suites/merged/

Directories of relative symlinks (`../../fresh/fresh-<seed>/<map>`) merging many suites into one, so an A/B runs one suite instead of dozens (tools/README.md "Few suites per A/B"). Remake the targets, then link every map of them, e.g. `for s in $(seq A B); do ln -s ../../fresh/fresh-$s/*.map26a maps/suites/merged/NAME/; done`.

| set | maps | targets (fresh seeds) | purpose |
|---|---|---|---|
| `altar-c1` | 2560 | 510011-510020 |  |
| `altar-c2` | 2560 | 510021-510030 |  |
| `altar-c3` | 2560 | 510031-510040 |  |
| `altar-confirm` | 10240 | 510051-510060, 510081-510110 |  |
| `altar-multi-dev` | 1972 | 510001-510010 |  |
| `altar-multi-ident` | 395 | 510051-510052 |  |
| `altar-multi-smoke` | 150 | 510001-510010 |  |
| `altar-one-confirm` | 10250 | 510200-510379 |  |
| `altar-one-dev` | 588 | 510001-510010 |  |
| `altar-one-dev12` | 1181 | 510001-510010, 510041-510050 |  |
| `altar-one-dev2` | 593 | 510041-510050 |  |
| `altar-one-p3` | 1137 | 510061-510080 |  |
| `altar-one-sweep` | 4044 | 510001-510050, 510061-510080 |  |
| `altar-panel2` | 2560 | 510111-510120 |  |
| `altar-smoke` | 30 | 510001-510006, 510008, 510010 |  |
| `altar-varied` | 1280 | 510121-510125 |  |
| `bush-s1` | 5120 | 512000-512019 |  |
| `bush-s2` | 5120 | 512020-512039 |  |
| `df-c0` | 2560 | 514200-514209 |  |
| `df-c1` | 2560 | 514210-514219 |  |
| `df-c2` | 2560 | 514220-514229 |  |
| `df-c3` | 2560 | 514230-514239 |  |
| `df-c4` | 2560 | 514240-514249 |  |
| `df-c5` | 2560 | 514250-514259 |  |
| `df-c6` | 2560 | 514260-514269 |  |
| `df-c7` | 2560 | 514270-514279 |  |
| `df-conf` | 10240 | 514400-514439 |  |
| `df-lnear` | 16 |  |  |
| `df-mono` | 62 | 514001, 514005, 514008, 514011, 514018-514019, 514021-514024, 514026, 514030, 514036 |  |
| `df-monomix` | 60 |  |  |
| `df-near3` | 469 | 514000-514039 |  |
| `df-near4` | 395 | 514000-514039 |  |
| `df-vary` | 2559 | 514440-514449 |  |
| `df2-conf` | 10240 | 529100-529139 | spawncamp round 2 confirm |
| `df2-dev` | 1702 | 529000-529039, 514000-514039 | spawncamp round 2 dev subset: `df2-near` plus round 1's `df-near3`, `df-near4` |
| `df2-dev2` | 802 | 529040-529079 | spawncamp round 2: a striker within 4 of team A's spawn |
| `df2-devall` | 2504 | | `df2-dev` plus `df2-dev2` |
| `df2-full` | 10240 | 529000-529039 | spawncamp round 2 full suite |
| `df2-mono` | 122 | | `df-mono` plus `df-monomix` (78 maps with gems off Monoliths, 44 Monolith-only) |
| `df2-near` | 838 | 529000-529039 | a striker within 4 of team A's spawn (`df2-near3`: within 3, 460; `df2-near4`: at 4, 378) |
| `df2-vary` | 2560 | 529140-529149 (varied) | spawncamp round 2 robustness |
| `final-30k` | 29950 | 99121-99237 | final check of the oscillation work |
| `fresh-92all` | 25599 | 92001-92100 | fresh-92001..92100 in one suite |
| `fresh-95all` | 10240 | 95001-95040 | merge of a fresh seed range |
| `fresh-996all` | 10240 | 99601-99640 | merge of a fresh seed range |
| `fresh-997all-0` | 5120 | 99701, 99709, 99717, 99725, 99733, 99741, 99749, 99757, 99765, 99773, 99781, 99789, 99797, 99805, 99813, 99821, 99829, 99837, 99845, 99853 | merge of a fresh seed range |
| `fresh-997all-1` | 5120 | 99702, 99710, 99718, 99726, 99734, 99742, 99750, 99758, 99766, 99774, 99782, 99790, 99798, 99806, 99814, 99822, 99830, 99838, 99846, 99854 | merge of a fresh seed range |
| `fresh-997all-2` | 5120 | 99703, 99711, 99719, 99727, 99735, 99743, 99751, 99759, 99767, 99775, 99783, 99791, 99799, 99807, 99815, 99823, 99831, 99839, 99847, 99855 | merge of a fresh seed range |
| `fresh-997all-3` | 5120 | 99704, 99712, 99720, 99728, 99736, 99744, 99752, 99760, 99768, 99776, 99784, 99792, 99800, 99808, 99816, 99824, 99832, 99840, 99848, 99856 | merge of a fresh seed range |
| `fresh-997all-4` | 5120 | 99705, 99713, 99721, 99729, 99737, 99745, 99753, 99761, 99769, 99777, 99785, 99793, 99801, 99809, 99817, 99825, 99833, 99841, 99849, 99857 | merge of a fresh seed range |
| `fresh-997all-5` | 4864 | 99706, 99714, 99722, 99730, 99738, 99746, 99754, 99762, 99770, 99778, 99786, 99794, 99802, 99810, 99818, 99826, 99834, 99842, 99850 | merge of a fresh seed range |
| `fresh-997all-6` | 4864 | 99707, 99715, 99723, 99731, 99739, 99747, 99755, 99763, 99771, 99779, 99787, 99795, 99803, 99811, 99819, 99827, 99835, 99843, 99851 | merge of a fresh seed range |
| `fresh-997all-7` | 4864 | 99708, 99716, 99724, 99732, 99740, 99748, 99756, 99764, 99772, 99780, 99788, 99796, 99804, 99812, 99820, 99828, 99836, 99844, 99852 | merge of a fresh seed range |
| `fresh-99all` | 10240 | 99001-99040 | merge of a fresh seed range |
| `invade-a` | 5120 | 511000-511019 |  |
| `invade-ab` | 10240 | 511000-511039 |  |
| `invade-b` | 5120 | 511020-511039 |  |
| `invade-c` | 10240 | 511040-511079 |  |
| `invade-cd` | 20480 | 511040-511119 |  |
| `invade-d` | 10240 | 511080-511119 |  |
| `invade-fire12` | 933 | 511000-511039 |  |
| `invade-fire12cd` | 1835 | 511040-511119 |  |
| `invade-varied` | 2560 | 511900-511909 |  |
| `inv2-e` | 10240 | 511200-511239 | invade reopened (EXPERIMENTS "Invade / opening steal") |
| `inv2-fire-L0-conf` | 80 | 511540-511779 | invade reopened: maps where the strict L0 gate fires, unused-seed confirm |
| `inv2-fire-L0-fit` | 36 | 511300-511419 | invade reopened: L0 gate fire set |
| `inv2-fire-L0-val` | 35 | 511420-511539 | invade reopened: L0 gate fire set |
| `inv2-fire-L0b-{fit,val,conf}` | 42 / 44 / 92 | as L0 | invade reopened: L0 with worth >= 15 |
| `inv2-fire-L1-{fit,val,conf}` | 355 / 353 / 754 | as L0 | invade reopened: L1 gate fire set |
| `inv2-fire-L2-{fit,val,conf}` | 1899 / 1889 / 3852 | as L0 | invade reopened: the old margin-8 gate |
| `inv2-pool` | 61440 | 511300-511539 | invade reopened: fire-probe pool |
| `ac-c` | 10240 | 517310-517349 | area control around held camps: confirm |
| `ac-e` | 10240 | 517210-517249 | area control around held camps: dev sweep |
| `ac-v` | 2560 | 517400-517409 (varied) | area control around held camps: robustness |
| `ac-743` | 10240 | 743001-743040 | astraeus area hits and stuns in the camp-clear estimate (areaclear) |
| `inv2-pool2` | 61440 | 511540-511779 | invade reopened: fire-probe pool |
| `late-c` | 10240 | 521100-521139 | mirror pull (late invade): confirm / feature validation |
| `late-e` | 10240 | 521000-521039 | mirror pull (late invade): dev sweep / feature fit |
| `late-v` | 2560 | 521200-521209 (varied) | mirror pull (late invade): robustness |
| `fish-af10k` | 5120 | 540200-540219 | merged fish against astraeus, 10,240 games (2026-11-06) |
| `ao-40k` | 20480 | 640000-640079 | ocean against astraeus, 40,960 games (2026-11-06) |
| `noveto-20k` | 10240 | 99238-99277 | oscillation no-veto A/B |
| `noveto2-20k` | 10240 | 99278-99317 | oscillation no-veto A/B 2 |
| `noveto3-20k` | 10240 | 99318-99357 | oscillation no-veto A/B 3 |
| `oc-d1` | 10240 | 505021-505060 | ocean A/Bs (EXPERIMENTS "ocean") |
| `oc-h1` | 10240 | 505101-505140 | ocean A/Bs (EXPERIMENTS "ocean") |
| `oc-j1` | 5120 | 505001-505020 | ocean A/Bs (EXPERIMENTS "ocean") |
| `oc-lj1` | 10240 | lg 509001-509040 | ocean A/Bs (EXPERIMENTS "ocean") |
| `oc-lt1` | 5120 | lg 509041-509060 | ocean A/Bs (EXPERIMENTS "ocean") |
| `oc-n1` | 10240 | oc-n1 508000-508039 | ocean A/Bs (EXPERIMENTS "ocean") |
| `audit-p1` | 153600 | 791001-791600 | rejection audit reruns: SPRT screens, own `--sprt-seed` each (research/ideas-2026-11-07/rejection-audit.md) |
| `audit-p2a` | 20480 | 792001-792080 | rejection audit: real-budget held-out confirms (792081-792200 unused) |
| `audit-r1`..`audit-r24` | 6400 each | 791001-791600 in blocks of 25 | rejection audit: paired rare-gate chunks against a base mirror |
| `fuel16-795` | 20480 | 795001-795080 | fuel campaign 16: exact savings against oc-base16 (EXPERIMENTS "Fuel campaign 16") |
| `fuel16-796` | 20480 | 796001-796080 | fuel campaign 16: fuel-aware arms against the exact version |
| `oc-pool` | 5119 | 505081-505100 | ocean A/Bs (EXPERIMENTS "ocean") |
| `oc-t1` | 5120 | 505061-505080 | ocean A/Bs (EXPERIMENTS "ocean") |
| `oc3-astr` | 10240 | 524000-524039 | ocean oc-base3 vs astraeus-now-1105 and panel-astraeus |
| `ocint-b` | 2560 | 516051-516060 |  |
| `ocint-conf` | 10240 | 516001-516040 |  |
| `ocint-p2` | 2560 | 516041-516050 |  |
| `ocint-rw2` | 10240 | 516101-516140 |  |
| `ocint-rw3` | 10240 | 516141-516180 |  |
| `ocint-var` | 2560 | 516061-516070 |  |
| `oc3-confirm` | 10240 | 518100-518139 | SPSA oc3: oc-tuned3 vs oc-combo2 confirm (EXPERIMENTS "SPSA retune") |
| `oc3-confirm2` | 10240 | 518140-518179 | SPSA oc3: second confirm set |
| `oc3-confirm-varied` | 2560 | 518200-518209 (varied) | SPSA oc3: `--mix varied` check |
| `oc3-judge` | 10240 | 517100-517139 | SPSA oc3: made for judging, unused |
| `oc3-panel2` | 2560 | 517300-517309 | SPSA oc3: second panel set for astraeus and proteus |
| `oc3-varied` | 2560 | 517200-517209 (varied) | SPSA oc3: made for a varied check, unused |
| `oc4-sprt` | 10240 | 526100-526139 | SPSA oc4: oc-tuned4 vs oc-base4 SPRT (EXPERIMENTS "SPSA retune round oc4") |
| `oc4-confirm` | 10240 | 526500-526539 | SPSA oc4: confirm |
| `oc4-varied` | 2560 | 526600-526609 (varied) | SPSA oc4: `--mix varied` check |
| `oc4-panel2` | 2560 | 526700-526709 | SPSA oc4: second panel set for astraeus and proteus |
| `oc-fuel5-conf` | 10240 | 528100-528139 | fuel round 6 confirm (made in round 5, unused there) |
| `oc-fuel5-dev` | 10240 | 528000-528039 | fuel round 6 dev SPRTs (made in round 5, unused there) |
| `oc-base4-conf` | 10240 | 531000-531039 | oc-base4 (CHANGES 416 and 422) merge A/B against oc-fuel4 |
| `ast-ocean-40k` | 40192 | 550000-550156 | ocean and ocean_tune3 against astraeus 37e1eb64, 80k games each |
| `oc-fuel6-varied` | 2560 | 530000-530009 (varied) | fuel round 6 robustness |
| `ocr-c0` | 2560 | 506000-506009 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c1` | 2560 | 506010-506019 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c10` | 2560 | 506100-506109 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c11` | 2560 | 506110-506119 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c12` | 2560 | 506120-506129 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c13` | 2560 | 506130-506139 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c14` | 2560 | 506140-506149 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c15` | 2560 | 506150-506159 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c16` | 2560 | 506160-506169 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c17` | 2560 | 506170-506179 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c18` | 2560 | 506180-506189 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c19` | 2560 | 506190-506199 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c2` | 2560 | 506020-506029 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c20` | 2560 | 506200-506209 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c21` | 2560 | 506210-506219 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c22` | 2560 | 506220-506229 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c23` | 2560 | 506230-506239 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c24` | 2560 | 506240-506249 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c25` | 2560 | 506250-506259 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c26` | 2560 | 506260-506269 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c27` | 2560 | 506270-506279 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c28` | 2560 | 506280-506289 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c29` | 2560 | 506290-506299 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c3` | 2560 | 506030-506039 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c30` | 2560 | 506300-506309 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c31` | 2560 | 506310-506319 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c32` | 2560 | 506320-506329 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c33` | 2560 | 506330-506339 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c34` | 2560 | 506340-506349 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c35` | 2560 | 506350-506359 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c36` | 2560 | 506360-506369 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c37` | 2560 | 506370-506379 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c38` | 2560 | 506380-506389 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c39` | 2560 | 506390-506399 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c4` | 2560 | 506040-506049 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c40` | 2560 | 506400-506409 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c41` | 2560 | 506410-506419 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c42` | 2560 | 506420-506429 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c43` | 2560 | 506430-506439 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c44` | 2560 | 506440-506449 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c45` | 2560 | 506450-506459 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c46` | 2560 | 506460-506469 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c47` | 2560 | 506470-506479 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c48` | 2560 | 506480-506489 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c49` | 2560 | 506490-506499 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c5` | 2560 | 506050-506059 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c50` | 2560 | 506500-506509 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c51` | 2560 | 506510-506519 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c52` | 2560 | 506520-506529 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c53` | 2560 | 506530-506539 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c54` | 2560 | 506540-506549 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c55` | 2560 | 506550-506559 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c56` | 2560 | 506560-506569 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c57` | 2560 | 506570-506579 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c58` | 2560 | 506580-506589 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c59` | 2560 | 506590-506599 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c6` | 2560 | 506060-506069 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c7` | 2560 | 506070-506079 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c8` | 2560 | 506080-506089 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-c9` | 2560 | 506090-506099 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-v0` | 2560 | 506900-506909 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-v1` | 2560 | 506910-506919 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-v2` | 2560 | 506920-506929 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-v3` | 2560 | 506930-506939 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-v4` | 2560 | 506940-506949 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-v5` | 2560 | 506950-506959 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-v6` | 2560 | 506960-506969 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-v7` | 2560 | 506970-506979 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-v8` | 2560 | 506980-506989 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-v9` | 2560 | 506990-506999 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-varied0` | 2560 | 506600-506609 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-varied1` | 2560 | 506610-506619 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-varied2` | 2560 | 506620-506629 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `ocr-varied3` | 2560 | 506630-506639 | EXPERIMENTS "Farm routes via spawn (2026-11-05, ocean)" |
| `oct-a` | 10240 | 509100-509139 | EXPERIMENTS "SPSA retune (ocean, 2026-11-05)": oct-a tuned vs oc-base1, oct-b the panel |
| `oct-b` | 10240 | 509140-509179 | EXPERIMENTS "SPSA retune (ocean, 2026-11-05)": oct-a tuned vs oc-base1, oct-b the panel |
| `oct-c` | 5120 | 509180-509199 | EXPERIMENTS "SPSA retune (ocean, 2026-11-05)": oct-a tuned vs oc-base1, oct-b the panel |
| `osc-fix-10k` | 5120 | 88001-88020 | oscillation fix A/B |
| `osc-fix-20k` | 10240 | 88001-88040 | oscillation fix A/B |
| `osc-r2-10k` | 5120 | 91021-91040 | oscillation round 2 |
| `osc-r2-20k` | 10240 | 91021-91040, 99101-99120 | oscillation round 2 |
| `p1-total` | 20224 | 81001-81079 | Phase 1 total (EXPERIMENTS, used by no bundle's A/B) |
| `p1a-b1` | 5120 | 147001-147020 | EXPERIMENTS "Phase 1a" |
| `p1a-b2` | 5120 | 147021-147040 | EXPERIMENTS "Phase 1a" |
| `p1a-b3` | 5119 | 147041-147060 | EXPERIMENTS "Phase 1a" |
| `p1a-b4` | 5120 | 147061-147080 | EXPERIMENTS "Phase 1a" |
| `p1a-b5` | 5120 | 147081-147100 | EXPERIMENTS "Phase 1a" |
| `p1a-b6` | 5120 | 147101-147120 | EXPERIMENTS "Phase 1a" |
| `p1a-fix` | 5120 | 148121-148140 | EXPERIMENTS "Phase 1a" |
| `p1b-b1` | 5120 | 148001-148020 | EXPERIMENTS "Phase 1b" |
| `p1b-b2` | 5120 | 148021-148040 | EXPERIMENTS "Phase 1b" |
| `p1b-b3` | 5120 | 148041-148060 | EXPERIMENTS "Phase 1b" |
| `p1b-b4` | 5120 | 148061-148080 | EXPERIMENTS "Phase 1b" |
| `p1b-b5` | 5120 | 148081-148100 | EXPERIMENTS "Phase 1b" |
| `p1b-b6` | 5120 | 148101-148120 | EXPERIMENTS "Phase 1b" |
| `p1b-b7` | 5120 | 148141-148160 | EXPERIMENTS "Phase 1b" |
| `p1b-b8` | 5120 | 148161-148180 | EXPERIMENTS "Phase 1b" |
| `p1b-fix` | 5120 | 149121-149140 | EXPERIMENTS "Phase 1b" |
| `p2-b1` | 5120 | 149001-149020 | EXPERIMENTS "Phase 2" bundle set |
| `p2-b2` | 5120 | 149021-149040 | EXPERIMENTS "Phase 2" bundle set |
| `p2-b2r` | 5120 | 149141-149160 | EXPERIMENTS "Phase 2" bundle set |
| `p2-b3` | 5120 | 149041-149060 | EXPERIMENTS "Phase 2" bundle set |
| `p2-b4` | 5120 | 149061-149080 | EXPERIMENTS "Phase 2" bundle set |
| `p2-b5` | 5120 | 149081-149100 | EXPERIMENTS "Phase 2" bundle set |
| `p2-b6` | 5120 | 149101-149120 | EXPERIMENTS "Phase 2" bundle set |
| `p2-b6r` | 5120 | 149161-149180 | EXPERIMENTS "Phase 2" bundle set |
| `p3-b1` | 5120 | 150001-150020 | Phase 3 bundle set |
| `p3-b2` | 5119 | 150021-150040 | Phase 3 bundle set |
| `p3-b3` | 5120 | 150041-150060 | Phase 3 bundle set |
| `p3-b4` | 5120 | 150061-150080 | Phase 3 bundle set |
| `p3-b5` | 5120 | 150081-150100 | Phase 3 bundle set |
| `p3-b6` | 5120 | 150101-150120 | Phase 3 bundle set |
| `p3-b7` | 5120 | 150121-150140 | Phase 3 bundle set |
| `p3-b8` | 5120 | 150141-150160 | Phase 3 bundle set |
| `p4-b1` | 5120 | 150201-150220 | Phase 4 bundle set (EXPERIMENTS) |
| `p4-b10` | 5120 | 150381-150400 | Phase 4 bundle set (EXPERIMENTS) |
| `p4-b11` | 5120 | 150401-150420 | Phase 4 bundle set (EXPERIMENTS) |
| `p4-b2` | 5120 | 150221-150240 | Phase 4 bundle set (EXPERIMENTS) |
| `p4-b3` | 5120 | 150241-150260 | Phase 4 bundle set (EXPERIMENTS) |
| `p4-b4` | 5120 | 150261-150280 | Phase 4 bundle set (EXPERIMENTS) |
| `p4-b5` | 5120 | 150281-150300 | Phase 4 bundle set (EXPERIMENTS) |
| `p4-b6` | 5120 | 150301-150320 | Phase 4 bundle set (EXPERIMENTS) |
| `p4-b7` | 5120 | 150321-150340 | Phase 4 bundle set (EXPERIMENTS) |
| `p4-b8` | 5120 | 150341-150360 | Phase 4 bundle set (EXPERIMENTS) |
| `p4-b9` | 5120 | 150361-150380 | Phase 4 bundle set (EXPERIMENTS) |
| `panel-514500` | 1280 | 514500-514504 |  |
| `panel-check-514510` | 2560 | 514510-514519 |  |
| `port-a` | 10240 | 190001-190040 | CHANGES 398 port A/B (EXPERIMENTS) |
| `port-b` | 10240 | 190041-190080 | CHANGES 398 port A/B |
| `port-c` | 10240 | 190081-190120 | CHANGES 398 port A/B |
| `wa-30k` | 15360 | 150421-150480 | astraeus_wip vs astraeus, fuel (EXPERIMENTS) |
| `fish-dev` | 5120 | 540000-540019 | bots/fish development A/Bs (research/fish-bot-2026-11-06) |
| `rt-dev` | 10240 | 532000-532039 | near-miss retest dev (EXPERIMENTS "Near-miss retest on oc-base4"); the seeds were also ast-port1's |
| `rt-conf` | 10240 | 532100-532139 | near-miss retest confirm |
| `rt-combo` | 10240 | 532200-532239 | near-miss retest combo confirm |
| `rt-varied` | 2560 | 532300-532309 (`--mix varied`) | near-miss retest varied check |
| `ocean-vs-astr-1106` | 10240 | 535000-535039 | ocean (HER) against astraeus 37e1eb64, 1105 and oc-base3 (EXPERIMENTS "Ocean (HER) against astraeus 37e1eb64") |
| `fresh-541000-541039` | 10240 | 541000-541039 | perma-lock confirm (EXPERIMENTS "Perma-lock when ahead") |
| `gf2-741` | 10240 | 741001-741040 | astraeus goal field off spawn (gf2) A/B |
| `cd2-742` | 10240 | 742001-742040 | astraeus camp damage by the nearest-champion rule (cd2) A/B |
| `cd2-744` | 40960 | 744001-744160 | astraeus camp damage by the nearest-champion rule, 80k confirm A/B |
| `ff-745` | 10240 | 745001-745040 | astraeus turn-end feint fixes (feintfix) A/B |
| `ff24-746` | 10240 | 746001-746040 | astraeus feint fixes 2-4 (ff24) A/B |
| `tc3-pool-806` | 51200 | 806001-806200 | SPSA tc3/tc3ctl tuning pool (tune_fresh.py: 64 maps an iteration, none reused) |
| `tc3-base-807` | 10240 | 807001-807040 | combo3 untuned against astraeus 8c0343f |
| `tc3-h2h-8071` | 10240 | 807101-807140 | tuned combo3 against tuned astraeus |
| `tc3-self-8072` | 10240 | 807201-807240 | each tuned bot against its untuned base |
| `tc3-ocean-8073` | 10240 | 807301-807340 | tc3 bots against ocean |
| `tc3-panel-8074` | 2560 | 807401-807410 | tc3 panel set |
| `tc3-merge-8075` | 10240 | 807501-807540 | combo3 as merged, before the audit fixes |
| `tc3-varied-8076` | 2560 | 807601-807610 | tc3 robustness (`--mix varied`) |
| `lock-one-dev` | 1602 | 541100-541119 | one-site maps (altar tiles within 3, at most 2 tiles), by research/ladder-scrims-2026-11-06/lock-tools/sites.mjs |
| `lock-multi-dev` | 3376 | 541100-541119 | the multi-site maps of at most 8 altar tiles (perma-lock L4) |
| `lock-one-ladder` | 47 | ladder maps | the 32 one-tile and 15 one-site 2-tile ladder maps |
| `cb-e` | 10240 | 544000-544039 | cooked comebacks dev (research/ideas-2026-11-05/comeback.md) |
| `cb-c` | 10240 | 544100-544139 | cooked comebacks confirm |
| `cb-m` | 2560 | 544200-544209 | cooked comebacks measurement (self-play) |
| `cb-smoke` | 40 | 544200 | the first 40 maps of cb-m, smoke tests |
| `cb-L` | 10240 | 544300-544339 | cooked comebacks random gambit logger (selector data) |
| `cb-d` | 10240 | 544400-544439 | cooked comebacks second confirm |
| `cb-v` | 2560 | 544900-544909 (`--mix varied`) | cooked comebacks varied check |
| `df-e` | 10240 | 545000-545039 | draft model features (F92) dev (research/ideas-2026-11-05/draftfeat.md) |
| `df-c` | 10240 | 545100-545139 | draft model features confirm |
| `df-v` | 2560 | 545200-545209 (`--mix varied`) | draft model features varied check |
| `d6-e` | 10240 | 548200-548239 | draft6 dev A/B (research/ideas-2026-11-05/draft6.md) |
| `d6-c` | 10240 | 548300-548339 | draft6 confirm |
| `d6-v` | 2560 | 548400-548409 (`--mix varied`) | draft6 varied check |
| `d6-p2` | 2560 | 548500-548509 | draft6 second panel set (astraeus, proteus) |
| `d7-e` | 10240 | 590200-590239 | draft7 2x screen (research/ideas-2026-11-06/draft7.md) |
| `d7-c` | 10240 | 590300-590339 | draft7 held out (first half) |
| `d7-held` | 20480 | 590300-590339, 590600-590639 | draft7 held out, 40,960 games |
| `d7-v` | 2560 | 590400-590409 (`--mix varied`) | draft7 varied (first half) |
| `d7-varied` | 5119 | 590400-590419 (`--mix varied`) | draft7 varied, 10,238 games |
| `d7-p2` | 2560 | 590500-590509 | draft7 panel subset |
| `d7-panel` | 10240 | 590500-590529 + panel-check-514510 | draft7 panel, 20,480 games a member |
| `oc5-confirm` | 10240 | 546100-546139 | SPSA run oc5's held-out confirm (ocean) |
| `oc5-varied` | 2560 | 546200-546209 (`--mix varied`) | SPSA run oc5's varied check |
| `pool-dev` | 10240 | 570000-570039 | Pooled level changes: 2x screens and leave-one-out (research/ideas-2026-11-06/pool.md) |
| `pool-held` | 10240 | 570100-570139 | Pooled level changes: held-out real-budget confirm |
| `pool-varied` | 2560 | 570200-570209 (`--mix varied`) | Pooled level changes: varied check |
| `pool-panel2` | 2560 | 570300-570309 | Pooled level changes: second panel set (astraeus, proteus) |
| `pool-held2` | 10240 | 570400-570439 | Pooled level changes: second held-out set (oc-pool3t, oc-pool1t) |
| `fuel11-a` | 10240 | 580000-580039 | Fuel pass on oc-base10: exact step |
| `fuel11-b` | 10240 | 580100-580139 | Fuel pass on oc-base10: SPRT screens |
| `fuel11-c` | 10240 | 580200-580239 | Fuel pass on oc-base10: held-out confirm |
| `fc12-a` | 5120 | 910000-910019 | Fuel campaign 12, agent A (ocean) |
| `fc12-b` | 5120 | 910100-910119 | Fuel campaign 12, agent B (ocean) |
| `fc12-m` | 10240 | 910200-910239 | Fuel campaign 12, merge (ocean) |
| `oc5-panel2` | 2560 | 546300-546309 | SPSA run oc5's second panel set (astraeus, proteus) |
| `mc2-screen` | 10240 | 546400-546439 | oc-mapcond2 screen at 2x fuel (ocean) |

## suites/inv2/

Mild mutations of ladder maps for the reopened invade idea (`mapgen mutate` with 1-2 of walls/bushes/holes +-1-2, picks=3/4/5 on 40%; the source map included):

- `sunfam` (80 maps): 04sunburst and 79 mutations (seeds 900000-900078).
- `sunfam2` (320 maps): 04sunburst and 319 mutations (seeds 521500000-521500318), for the mirror pull.
- `sunfam3` (319 maps): 319 mutations of 04sunburst (seeds 521600000-521600318, the source map left out), the mirror pull's confirm family.
- `sungrad/` (6,448 maps): the mirror pull's mutation gradient on 04sunburst (`ops.json` has each arm's ops; mutation seeds 522200000+): `L1`-`L5` (800 each, rising strength), `walls` (448), `bushes`, `camppos`, `econ`, `campcount`, `picks` (500 each).
- `sunlike` (10,000 maps): the fresh ladder-mix maps nearest 04sunburst on 40 round-1 features, out of 59,904 (seeds 522300-522533, generated in scratch; only these were moved here).
- `lab-e`, `lab-c` (1,920 maps each): copies of late-e and late-c maps, for the mirror pull's traced situation labels.
- `realfam` (304 maps): 16 each of 04fault-lines, 00swirl, 01corridors, 00crater, 01the-farm, 04standing-stones, 02treasure-box, 00oasis, 03honeycomb, 04bowls, 02gift-wrapping, 00packs, 00the-line, 01boss-battle, 01elk-arena, 01hooks, 01starfish, 02the-pond, 04spiral-moat (seeds 910000 + 1000 i + k).

## suites/mp3/

The mirror pull's third pass (research/ideas-2026-11-05/invade-cycle.md): families of a base map and mild mutations (1-2 of walls/bushes/holes +-1-2, picks unchanged; `<id>-m0` is the base map itself), `families.json` gives each family's source, CV group and class.

- `pilot` (3,185 maps): 200 families x 16 (mutation seeds 527000000+): 50 sungrad, 50 ladder, 70 fresh-527000, 30 varied-527100.
- `full` (9,095 maps): 1,138 families x 8 (seeds 527100000+): 140 sungrad, 20 sunfam2, 120 sunlike, 78 ladder, 600 fresh 527000-527009, 200 varied 527100-527104.
- `sel-ab` (2,048 maps): the GBM gate's top 20% of fresh 527500-527539 (named `<seed>-<map>`), its pre-registered subset test.
- `labels-pilot.json`, `labels-full.json`, `labels-selab.json`: per-game paired diffs (c = 1 minus off) by family.

## suites/sets/

Hand-assembled sets of real map files (copies, no index.json).

- `fresh-ladder86` (86 maps): copies of 86 ladder maps.
- `osc3-confirm` (5120 maps): oscillation stream 3 confirm set: mapgen seeds 3391-3410 (file suffix `-s<seed>`).
- `osc4-mono` (538 maps): stream 4 Monolith test set (from fresh-92001..).
- `osc4-mono2` (803 maps): stream 4 Monolith set 2 (copies named `fresh-<seed>-<map>`).
- `osc4-sg-dev` (214 maps): stream 4 shared-gems dev set.
- `osc4-sg-known` (10 maps): stream 4 shared-gems known maps (ladder and gen picks).
- `p5-a` (10240 maps): phase 5 set, copies of fresh seeds 150481-150520.
- `p5-b` (10240 maps): phase 5 set, copies of fresh seeds 150521-150560.
- `p5-c` (10240 maps): phase 5 set, copies of fresh seeds 150561-150600.

## Paths not updated

The draft and emblem labs' `config.json` and `maps.jsonl` were rewritten to the `maps/suites/...` paths when the dirs moved, except `replays/draftlab/draft2` and `draft2-noctr`, whose `maps/fresh-*` glob names suites of the generator before 2026-10-30 (e.g. `fresh-6177`) that no longer exist. Notes in `research/*.md` keep the old paths as history.

## Teacher benchmark (2026-11-06)

`teacher-20261106/` contains 20 fresh ladder-mix suites, seeds 861001–861020,
256 maps each. `astraeus-teacher-v1-10k` samples 5,000 of their 5,120 maps with
seed 861000 and plays both sides. Its exact selection and hashes are in
`replays/ab/astraeus-teacher-v1-10k/teacher.json`.

`teacher-confirm-20261106/` contains 20 new ladder-mix suites, seeds
862001–862020, 256 maps each. The corrected teacher confirmation samples 5,000
with seed 862000, both sides (10,000 games). Three selected layout hashes repeat
from the diagnostic suite; excluding those six games leaves 9,994 held-out games.
Manifest: `replays/ab/astraeus-teacher-crew-index-confirm-10k/teacher.json`.

## Pool round 2 (2026-11-06)

Ladder-mix suites (`fresh-{seed}`) merged by symlink into `maps/suites/merged/`:
- `pool2-dev`: 610000-610039, 10,240 maps.
- `pool2-held`: 610100-610139, 10,240 maps.
- `pool2-varied`: 610200-610209, `--mix varied`, 2,560 maps.
- `pool2-panel2`: 610300-610309, 2,560 maps.
- `pool2-bis`: 610000-610003, a slice of dev used for diagnosis.
- `pool2-diag`: 610400-610409, 2,560 maps.

Used by research/ideas-2026-11-06/pool2.md; `pool2-varied` and `pool2-panel2` are still unused.

## astraeus's ocean port (2026-11-07)

`merged/astport-oc-40k`: ladder-mix suites 880000-880078 (`fresh-{seed}`), 20,224 maps, symlinked. Used by CHANGES 451's
A/B of astraeus-ocport (oc-base13) against oc-base12.

## Draft7 on ocean (2026-11-07)

`merged/d7port-655`: ladder-mix suites 655000-655079 (`fresh-{seed}`), 20,480 maps, symlinked. Used by CHANGES 454's
A/B of oc-base14 against oc-base13-453; fresh-655000..655007 also by its firstturn headroom check.

## Draft first-turn bound (2026-11-07)

Used by oc-draftfix (draft precompute bounded by map structure) against oc-base14. All symlinked into `merged/`:
- `merged/draftfix-held`: ladder-mix 941000-941059 plus `--mix varied` 942000-942029, 23,040 maps; held-out firstturn and plan-identity checks.
- `merged/draftfix-vtrain`: `--mix varied` 944000-944039, 10,240 maps; used to fit the work bound (training, not held out).
- `merged/draftfix-943`: ladder-mix 943000-943079, 20,480 maps; the 40,960-game A/B.

## Willow arms (2026-11-07)

Ladder-mix unless noted, all symlinked into `merged/`:
- `willow-pool-771`: 771000-771039, 10,240 maps. `willow-771` is its 5,187 maps where ocean's draft takes Willow
  (both sides or neither), used for the screens (dev). `willow-771-mech` is 300 of those.
- `willow-held-772`: 772000-772079, 20,480 maps, held out (40,960 games).
- `willow-varied-773`: 773000-773019, `--mix varied`, 5,120 maps.
- `willow-panel-774`: 774000-774039, 10,240 maps, the panel at 20,480 games a member.
- `willow-port-780`: 780000-780079, 20,480 maps, held out for CHANGES 457's port A/B (40,960 games).
- `willow-port-varied-781`: 781000-781019, `--mix varied`, 5,119 maps (10,238 games).
