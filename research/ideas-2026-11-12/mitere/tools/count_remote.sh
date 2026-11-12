#!/bin/bash
cd ~/cambc-autumn/.oarena/capture
T=ee83f5e5-bcad-4923-86b4-b79ea6083d2e
for s in a b; do
nice timeout 200 sqlite3 -readonly -separator $'\t' capture.db "select '$s', substr(created_at,1,13), kind, count(*), sum(replay is not null) from matches where team_$s='$T' and created_at>='2026-11-10T12' group by 2,3"
done
ls ~/cambc-autumn/.oarena/archive/ | tail -5
