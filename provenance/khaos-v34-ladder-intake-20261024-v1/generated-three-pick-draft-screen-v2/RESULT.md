# Fixed-three native screen results

All 192 approved cells completed with normal native drafts. This fixed first-slot screen compares four candidates on 12 outcome-blind selected generated development maps against frozen f475 and v33 controls. These are development maps, not untouched holdout. Aggregation uses the explicit source identities in `ROWS.tsv`; controls are reported separately.

|Arm|Opponent|Games|Wins|A candidate-side wins|B candidate-side wins|Mean rounds|Candidate submitted gems|Control submitted gems|Draft order matches|Faults|
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|P|f475|24|12|6|6|1210.92|18081|18081|24/24|0|
|P|v33|24|11|3|8|1162.96|16243|17454|24/24|0|
|S|f475|24|5|3|2|1193.83|17597|19573|24/24|0|
|S|v33|24|4|2|2|1197.67|17422|20999|24/24|0|
|C|f475|24|12|8|4|1197.5|20231|17334|24/24|0|
|C|v33|24|14|7|7|1205.58|19684|17745|24/24|0|
|M|f475|24|16|8|8|1238.54|20512|14983|24/24|0|
|M|v33|24|14|7|7|1204.25|20181|16292|24/24|0|

## Matched P versus other-role cells

|Compared arm|Opponent|Matched map/side cells|Both win|Both lose|P only|Other arm only|
|---|---|---:|---:|---:|---:|---:|
|P vs S|f475|24|4|11|8|1|
|P vs S|v33|24|2|11|9|2|
|P vs C|f475|24|8|8|4|4|
|P vs C|v33|24|7|6|4|7|
|P vs M|f475|24|8|4|4|8|
|P vs M|v33|24|7|6|4|7|

## Outcome-blind sample strata

|Ramp band|Openness band|Arm|Opponent|Cells|Wins|A-side wins|B-side wins|
|---|---|---|---|---:|---:|---:|---:|
|high|above-or-equal-median|C|f475|4|3|2|1|
|high|above-or-equal-median|C|v33|4|2|1|1|
|high|above-or-equal-median|M|f475|4|2|1|1|
|high|above-or-equal-median|M|v33|4|1|1|0|
|high|above-or-equal-median|P|f475|4|2|2|0|
|high|above-or-equal-median|P|v33|4|1|0|1|
|high|above-or-equal-median|S|f475|4|0|0|0|
|high|above-or-equal-median|S|v33|4|0|0|0|
|high|below-median|C|f475|4|1|1|0|
|high|below-median|C|v33|4|3|2|1|
|high|below-median|M|f475|4|1|0|1|
|high|below-median|M|v33|4|1|0|1|
|high|below-median|P|f475|4|2|1|1|
|high|below-median|P|v33|4|2|0|2|
|high|below-median|S|f475|4|1|1|0|
|high|below-median|S|v33|4|0|0|0|
|low|above-or-equal-median|C|f475|4|3|2|1|
|low|above-or-equal-median|C|v33|4|3|1|2|
|low|above-or-equal-median|M|f475|4|3|2|1|
|low|above-or-equal-median|M|v33|4|3|2|1|
|low|above-or-equal-median|P|f475|4|2|1|1|
|low|above-or-equal-median|P|v33|4|1|0|1|
|low|above-or-equal-median|S|f475|4|1|1|0|
|low|above-or-equal-median|S|v33|4|1|1|0|
|low|below-median|C|f475|4|0|0|0|
|low|below-median|C|v33|4|0|0|0|
|low|below-median|M|f475|4|4|2|2|
|low|below-median|M|v33|4|4|2|2|
|low|below-median|P|f475|4|2|1|1|
|low|below-median|P|v33|4|2|1|1|
|low|below-median|S|f475|4|0|0|0|
|low|below-median|S|v33|4|1|0|1|
|middle|above-or-equal-median|C|f475|4|4|2|2|
|middle|above-or-equal-median|C|v33|4|4|2|2|
|middle|above-or-equal-median|M|f475|4|2|1|1|
|middle|above-or-equal-median|M|v33|4|1|0|1|
|middle|above-or-equal-median|P|f475|4|2|0|2|
|middle|above-or-equal-median|P|v33|4|3|1|2|
|middle|above-or-equal-median|S|f475|4|1|0|1|
|middle|above-or-equal-median|S|v33|4|1|0|1|
|middle|below-median|C|f475|4|1|1|0|
|middle|below-median|C|v33|4|2|1|1|
|middle|below-median|M|f475|4|4|2|2|
|middle|below-median|M|v33|4|4|2|2|
|middle|below-median|P|f475|4|2|1|1|
|middle|below-median|P|v33|4|2|1|1|
|middle|below-median|S|f475|4|2|1|1|
|middle|below-median|S|v33|4|1|1|0|

The per-map × candidate-side × opponent × arm outcomes and native draft/body facts are in `RESULT.json`. The pinned v1_0_3 replay phase audit completed across all 192 cells. It found zero native Bot error steps in play, draft, or other phases, and zero draft/other rollover steps. Play rollover counts by source are below. These counts are native rollover/fuel steps, not Bot errors. Full source and physical-side counts are in `NATIVE-PHASE-RESULT.json`. No selector threshold was derived from this screen.

|Arm|Opponent|Candidate play rollovers|Control play rollovers|Bot errors, all phases|
|---|---|---:|---:|---:|
|P|f475|35|35|0|
|P|v33|32|36|0|
|S|f475|38|37|0|
|S|v33|41|48|0|
|C|f475|55|54|0|
|C|v33|57|51|0|
|M|f475|37|35|0|
|M|v33|36|43|0|
