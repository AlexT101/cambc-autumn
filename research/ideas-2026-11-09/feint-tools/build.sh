#!/bin/bash
# Rebuilds the feint variants (bots/variants is gitignored): oc-base25 + patch_mite --v3 (m3), minus the first-turn
# contact cancel (k), one-turn channels only (1); w and b were made from k by hand (bank.cc banking_here, see EXPERIMENTS).
cd /home/ubuntu/cambc-autumn; T=research/ideas-2026-11-09; F=$T/feint-tools
for v in m3 k 1; do ./copybot -f variants/oc-base25 variants/v87-ft-$v >/dev/null && python3 $T/oppfidelity-tools/patch_mite.py bots/variants/v87-ft-$v --v3; done
python3 $F/patch_ft.py bots/variants/v87-ft-k && python3 $F/patch_ft.py bots/variants/v87-ft-1 --one
