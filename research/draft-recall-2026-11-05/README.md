# Shared draft recall threshold

Candidate: `bots/variants/astraeus-shared-draft-recall` (CHANGES 412).
Reference: `bots/variants/astraeus-before-draft-recall-29cd092`, frozen from
29cd0921b6b62b34593b55843f30ad8f549c67f7. `change.diff` is the candidate's source
change; `manifest.json` lists the 5,000 selected maps and sampling seed.

10,000 games, both sides, own drafts, cambc 5.0.0, native fast runner and real
fuel: 5,002-4,998, 50.02% (95% Wilson CI 49.04-51.00), no failed games.
Out-of-fuel turns: candidate 67,219, reference 67,224. Level; keep the simpler
parameter set. `summary.json` preserves the runner's result.

Generate the fresh suites:

```sh
node tools/mapgen/mapgen.mjs suite --seed 731001-731020 --mix ladder --out 'maps/suites/fresh/fresh-{seed}'
```

The merged directory `maps/suites/merged/astraeus-draft-recall-10k` contains
symlinks to the maps listed in `manifest.json`. Run:

```sh
XDG_CACHE_HOME=/tmp/astraeus-draft-recall-cache CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native py tools/ab.py variants/astraeus-shared-draft-recall variants/astraeus-before-draft-recall-29cd092 --no-test-draft --suites maps/suites/merged/astraeus-draft-recall-10k --name astraeus-shared-draft-recall-10k-r2
```

The writable XDG cache contains a `cambc` symlink to the installed SDK cache at
`/home/ubuntu/.cache/cambc`; the successful run used unsandboxed access to the
existing shared CPU-slot lock files under `.git`.
