# Marcella Treasure tribute probe

This source-only probe checks whether Treasure Strength's 20% gold bonus applies to gold earned from tributing gems. The tested Team A roster is Marcella, Ryth, and Varg; Team B uses the passive `probe-passive` bot included here.

The successful 2,000-round `00collision` run confirmed the result from native round snapshots: before Treasure, Marcella's 4-gem tribute changed balance and lifetime earned gold from 100 to 108 (+8); after she bought Treasure Strength, a 15-gem tribute changed both from 202/352 to 238/388 (+36). The exact event intervals contain no logged Marcella income or spending. See [evidence-v1.json](evidence-v1.json) for source, runtime, map, replay, and snapshot pins. Full logs and replay are preserved under `replays/willow-marcella-treasure-tribute-probe-20261023-v2/`.

The replay extractor reports event-derived earnedGold 344 versus native 388. Its current validator counts capture and kill rewards but omits all tribute income; the 44-gold difference equals the two observed tribute awards (8 + 36). This is an extractor accounting gap, not contrary native evidence.

## Reproduce

From the repository root, build these two bots with Cambc 3.0.5 and then run one match using an exclusive output directory:

```sh
CAMBC=/Users/yufan/Desktop/Development/CambridgeBattlecode2026/current-autumn/tools/runtime/cambc-3.0.5/cambc
nice -n 19 "$CAMBC" build tools/probes/probe-marcella-treasure/probe-marcella
nice -n 19 "$CAMBC" build tools/probes/probe-marcella-treasure/probe-passive
nice -n 19 "$CAMBC" run tools/probes/probe-marcella-treasure/probe-marcella tools/probes/probe-marcella-treasure/probe-passive \
  --map 00collision --rounds 2000 --fuel 50000000 --log-limit 8388608 \
  --statistics stats.json --json -o /absolute/path/to/a-new-exclusive-output-directory
```

The higher 50,000,000 per-turn fuel setting keeps the scripted probe sequence stable while logging. This is a mechanic verification, not a default-fuel or performance test. The successful run's native engine snapshots and complete run command are preserved in the replay checkpoint named above. No generated `.cambc` files or compiler command databases are included here.
