#!/bin/bash
D=/tmp/claude-1000/-home-ubuntu-cambc-autumn/3650a530-f591-417e-a0c5-31524a1e3260/scratchpad/df
cd /home/ubuntu/cambc-autumn
source /home/ubuntu/venv/bin/activate
R5=l_monoliths,l_golems,l_camps_side,walls,l_shared_groups
T16=pr_gems_side__big_share,pr_gems_side__gold_side,sq_gems_side,pr_area__gold_side,sq_big_share,sq_area,pr_altar_centre__dash_gain,pr_area__gems_side,sq_cluster_share,pr_big_share__cluster_share,pr_gold_side__max_group,pr_big_share__max_group,pr_gold_side__contested_share,pr_gems_side__cluster_share,pr_cluster_share__max_group,pr_gold_side__big_camp_share
SQ=$(python3 -c "print(','.join('sq_'+n for n in 'area reach_frac spawn_dist detour choke_rel openness bushes holes altars altar_ratio altar_centre gems_side gold_side big_share cluster_share contested_share big_camp_share dash_short camp_near dash_gain narrow spawn_ring max_group camp_altar sight_gap'.split()))")
T24=$(cat $D/top24.txt)
S7=base,$R5,one_altar,$T16
L='{"b":64,"w":1280,"syn":320,"ctr":1000000000,"side":0.1}'
L4='{"b":64,"w":320,"syn":320,"ctr":1000000000,"side":0.1}'
LX='{"b":64,"w":5120,"syn":320,"ctr":1000000000,"side":0.1}'
C1='{"b":64,"w":1280,"syn":320,"ctr":1280,"side":0.1}'
C3='{"b":64,"w":1280,"syn":320,"ctr":320,"side":0.1}'
C8='{"b":64,"w":1280,"syn":320,"ctr":80,"side":0.1}'
node --max-old-space-size=90000 $D/mx.mjs cvx --lab replays/draftlab/draft5 --out $D/cv3 --dump 6 --threads ${THREADS:-32} \
  --sets "base;base;base;base;$S7;$S7,$SQ;$S7,$SQ,$T24;$S7,$SQ,$T24;$S7,$SQ,$T24;$S7,$SQ,$T24" --lams "$L;$C1;$C3;$C8;$L4;$L;$L;$L4;$LX;$C3"
