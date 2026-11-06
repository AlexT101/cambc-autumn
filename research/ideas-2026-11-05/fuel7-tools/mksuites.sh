#!/bin/bash
# mksuites.sh: fuel round 7 suites. dev 537000-537039, confirm 537100-537139 (ladder mix), merged in maps/suites/merged/.
cd /home/ubuntu/cambc-autumn
mk() { # FIRST LAST NAME [MIX]
  node tools/mapgen/mapgen.mjs suite --out "maps/suites/fresh/fresh-{seed}" --seed $1-$2 ${4:+--mix $4}
  mkdir -p maps/suites/merged/$3
  for s in $(seq $1 $2); do for f in maps/suites/fresh/fresh-$s/*.map26a; do b=$(basename $f .map26a); ln -sf ../../fresh/fresh-$s/$b.map26a maps/suites/merged/$3/$b-$s.map26a; done; done
  ls maps/suites/merged/$3 | wc -l
}
mk 537000 537039 fuel7-dev
mk 537100 537139 fuel7-conf
