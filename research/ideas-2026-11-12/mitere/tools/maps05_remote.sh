#!/bin/bash
cd ~/cambc-autumn/.oarena/capture
nice timeout 300 sqlite3 -readonly capture.db "select map, min(replay) from matches where created_at>='2026-11-11T23' and map like '05%' and replay is not null group by map" 
