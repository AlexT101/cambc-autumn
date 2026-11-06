#!/bin/bash
# mksuites.sh: the fuel-budgeting suites. dev 533000-533039, confirm 533100-533139 (ladder mix), varied 533200-533209.
cd /home/ubuntu/cambc-autumn
mk() { # FIRST LAST NAME [MIX]
  node tools/mapgen/mapgen.mjs suite --out "maps/suites/fresh/fresh-{seed}" --seed $1-$2 ${4:+--mix $4}
  mkdir -p maps/suites/merged/$3
  for s in $(seq $1 $2); do for f in maps/suites/fresh/fresh-$s/*.map26a; do b=$(basename $f .map26a); ln -sf ../../fresh/fresh-$s/$b.map26a maps/suites/merged/$3/$b-$s.map26a; done; done
  ls maps/suites/merged/$3 | wc -l
}
mk 533000 533039 fuelbud-dev
mk 533100 533139 fuelbud-conf
mk 533200 533209 fuelbud-varied varied
mk 533300 533319 fuelbud-oracle  # (run separately: the oracle suite)
