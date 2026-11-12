## Win rates against both bodies on fresh maps (fgate batches at 100k fuel, bodies unmetered; 10,240 maps a pool, both sides)

| bot | v2 | v3 | v4 | v4 minus v3 |
|---|---|---|---|---|
| c520-ps | 77.1% (76.7-77.5) of 40,960 | 77.4% (77.0-77.8) of 40,960 | 77.7% (77.3-78.1) of 40,960 | +0.3 ±0.6 |
| chy-life | 77.0% (76.6-77.5) of 40,960 | 77.5% (77.1-77.9) of 40,960 | 77.5% (77.1-77.9) of 40,960 | +0.0 ±0.6 |
| dfuel-506 | 68.9% (68.4-69.3) of 40,960 | 69.4% (68.9-69.8) of 40,960 | 69.3% (68.8-69.7) of 40,960 | -0.1 ±0.6 |

## Paired differences between bots on fresh maps (same map, side and body; units are maps, 95% CI)

| pair | v2 | v3 | v4 |
|---|---|---|---|
| c520-ps - chy-life | +0.05 ±0.32 | -0.08 ±0.32 | +0.19 ±0.32 |
| c520-ps - dfuel-506 | +8.21 ±0.58 | +8.07 ±0.58 | +8.44 ±0.58 |
| chy-life - dfuel-506 | +8.15 ±0.58 | +8.15 ±0.58 | +8.25 ±0.58 |

## Win rates by feature, both bodies (every fresh map, by the metrics its suite index records)

| bucket | pool | share of fresh maps | c520-ps | chy-life | dfuel-506 |
|---|---|---|---|---|---|
| close spawns (spawn_rel < 0.5) | v3 | 4.5% | 76.9% (74.9-78.8) of 1,844 | 76.8% (74.8-78.7) of 1,844 | 69.8% (67.7-71.9) of 1,844 |
| close spawns (spawn_rel < 0.5) | v4 | 14.1% | 76.3% (75.2-77.4) of 5,784 | 76.0% (74.8-77.0) of 5,784 | 68.2% (67.0-69.4) of 5,784 |
| other spawns | v3 | 95.5% | 77.4% (77.0-77.9) of 39,116 | 77.5% (77.1-77.9) of 39,116 | 69.3% (68.9-69.8) of 39,116 |
| other spawns | v4 | 85.9% | 78.0% (77.5-78.4) of 35,176 | 77.8% (77.4-78.2) of 35,176 | 69.5% (69.0-69.9) of 35,176 |
| open frame (fill_edge 1) | v3 | 18.5% | 79.4% (78.4-80.3) of 7,588 | 79.0% (78.0-79.9) of 7,588 | 70.4% (69.4-71.4) of 7,588 |
| open frame (fill_edge 1) | v4 | 39.4% | 79.1% (78.4-79.7) of 16,156 | 78.4% (77.7-79.0) of 16,156 | 69.8% (69.1-70.5) of 16,156 |
| arena (fill_edge < 0.5) | v3 | 7.0% | 75.8% (74.2-77.3) of 2,860 | 75.8% (74.2-77.3) of 2,860 | 69.2% (67.5-70.9) of 2,860 |
| arena (fill_edge < 0.5) | v4 | 10.2% | 77.0% (75.7-78.3) of 4,160 | 77.0% (75.7-78.3) of 4,160 | 69.3% (67.9-70.7) of 4,160 |
| partly blocked frame | v3 | 74.5% | 77.1% (76.6-77.6) of 30,512 | 77.3% (76.8-77.8) of 30,512 | 69.1% (68.6-69.6) of 30,512 |
| partly blocked frame | v4 | 50.4% | 76.8% (76.3-77.4) of 20,644 | 77.0% (76.4-77.6) of 20,644 | 68.9% (68.2-69.5) of 20,644 |
