# Baseline: astraeus 8ec2c4d (frozen bots/variants/astraeus-8ec2c4d), 2026-10-29

| Run | mean | p90 | p99 | >100k | round 1 mean | OOF turns | shortcuts |
|---|---|---|---|---|---|---|---|
| wide 100M (52, test drafts) | 50923 | 86081 | 106866 | 3615 | 197299 | - | - |
| wide real | 50693 | 85893 | - | - | 185711 | 1247 | 18883 |
| OOF set 100M (32, own drafts vs frozen) | 62520 | 88486 | 147280 | 11851 | 212725 | - | - |
| OOF set real | 62372 | 90985 | - | - | 187207 | 8339 | 46248 (step-guard-entry 16703, out-of-fuel 8167, prey-cut-short 5663) |
| A/B parts23v (= HEAD src) real, 1676 games, ladder + fresh-82801..3 | | | | | | 17282 (ladder 951, f1 6396, f2 7757, f3 2178) | |

Wide real shortcuts: step-guard-entry 4770, farm-partial-evaluation 4661, prey-cut-short 2465, ward-no-bushes-fuel 1896,
turn-order 1339, out-of-fuel 1269, comms-stale-vision 974, crow-flies-farm 378, static-descend 272, ...
A/B command for merges: py tools/ab.py <cand dir under bots/, e.g. variants/astraeus-merge1> variants/astraeus-8ec2c4d --suites ladder,maps/fresh-82801,maps/fresh-82802,maps/fresh-82803 --no-test-draft --name <name>
