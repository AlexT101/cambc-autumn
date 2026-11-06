#!/bin/bash
D=/tmp/claude-1000/-home-ubuntu-cambc-autumn/3650a530-f591-417e-a0c5-31524a1e3260/scratchpad/df
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
R5=l_monoliths,l_golems,l_camps_side,walls,l_shared_groups
T8=pr_gems_side__big_share,pr_gems_side__gold_side,sq_gems_side,pr_area__gold_side,sq_big_share,sq_area,pr_altar_centre__dash_gain,pr_area__gems_side
T16=$T8,sq_cluster_share,pr_big_share__cluster_share,pr_gold_side__max_group,pr_big_share__max_group,pr_gold_side__contested_share,pr_gems_side__cluster_share,pr_cluster_share__max_group,pr_gold_side__big_camp_share
node --max-old-space-size=80000 $D/mx.mjs cvx --lab replays/draftlab/draft5 --out $D/cv2 --dump 7 --threads 32 --sets "base;base,l_monoliths,l_golems;base,$R5;base,$R5,one_altar;base,$R5,odd_altar;base,$R5,one_altar,odd_altar;base,$R5,one_altar,$T8;base,$R5,one_altar,$T16;base,one_altar,$T16"
