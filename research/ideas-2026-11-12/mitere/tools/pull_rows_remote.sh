#!/bin/bash
cd ~/cambc-autumn/.oarena/capture
T=ee83f5e5-bcad-4923-86b4-b79ea6083d2e
COLS="match_id,created_at,kind,map,group_id,position,team_a,team_b,name_a,name_b,result_a,picks_a,picks_b,engine,rank_a,rank_b,rating_a,rating_b,replay,map_id"
for s in a b; do
  nice timeout 400 sqlite3 -readonly -separator $'\t' capture.db "select $COLS from matches where team_$s='$T' and created_at>='2026-11-09T12' and status='finished'"
done | gzip -1
