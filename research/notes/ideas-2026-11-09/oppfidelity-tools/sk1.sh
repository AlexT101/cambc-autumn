#!/bin/bash
# soup-k's three knobs one at a time against the -Mt3 bodies (block 0 and seeds 1-16).
T=/home/ubuntu/cambc-autumn/research/notes/ideas-2026-11-09/oppfidelity-tools
for k in fw tb cc; do $T/runs.sh sk$k variants/v87-sk-$k spar-o25-Mt3 spar-oc29-Mt3 spar-dvn1-Mt3 spar-dvn2-Mt3 spar-dvn3-Mt3 spar-dvn4-Mt3 spar-dvn5-Mt3 spar-dvn6-Mt3 spar-dvn7-Mt3 spar-dvn8-Mt3 spar-dvn9-Mt3 spar-dvn10-Mt3 spar-dvn11-Mt3 spar-dvn12-Mt3 spar-dvn13-Mt3 spar-dvn14-Mt3 spar-dvn15-Mt3 spar-dvn16-Mt3  & done; wait
touch ~/tmp-offload/oppfidelity/logs/sk1.alldone
