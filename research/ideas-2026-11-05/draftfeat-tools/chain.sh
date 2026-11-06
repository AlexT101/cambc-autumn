#!/bin/bash
D=/tmp/claude-1000/-home-ubuntu-cambc-autumn/3650a530-f591-417e-a0c5-31524a1e3260/scratchpad/df
cd $D; source /home/ubuntu/venv/bin/activate
while pgrep -f cv3.sh >/dev/null; do sleep 5; done
for g in all mapD comp; do OMP_NUM_THREADS=32 python -I gbm.py resid $D/gbm_res6_$g $D/cv3 --set 6 --group $g > $D/gbm_res6_$g.log 2>&1; done
cd /home/ubuntu/cambc-autumn
R5=l_monoliths,l_golems,l_camps_side,walls,l_shared_groups
T16=pr_gems_side__big_share,pr_gems_side__gold_side,sq_gems_side,pr_area__gold_side,sq_big_share,sq_area,pr_altar_centre__dash_gain,pr_area__gems_side,sq_cluster_share,pr_big_share__cluster_share,pr_gold_side__max_group,pr_big_share__max_group,pr_gold_side__contested_share,pr_gems_side__cluster_share,pr_cluster_share__max_group,pr_gold_side__big_camp_share
SQ=$(python3 -c "print(','.join('sq_'+n for n in 'area reach_frac spawn_dist detour choke_rel openness bushes holes altars altar_ratio altar_centre gems_side gold_side big_share cluster_share contested_share big_camp_share dash_short camp_near dash_gain narrow spawn_ring max_group camp_altar sight_gap'.split()))")
F92=base,$R5,one_altar,$T16,$SQ,$(cat $D/top24.txt)
N24=$(cat $D/next24.txt)
L='{"b":64,"w":1280,"syn":320,"ctr":1000000000,"side":0.1}'
W3='{"b":64,"w":320,"syn":320,"ctr":1000000000,"side":0.1}'
W8='{"b":64,"w":80,"syn":320,"ctr":1000000000,"side":0.1}'
S8='{"b":64,"w":320,"syn":80,"ctr":1000000000,"side":0.1}'
B16='{"b":16,"w":320,"syn":320,"ctr":1000000000,"side":0.1}'
node --max-old-space-size=90000 $D/mx.mjs cvx --lab replays/draftlab/draft5 --out $D/cv4 --dump 1 --threads 32 \
  --sets "base;$F92;$F92;$F92;$F92;$F92,$N24;$F92,$N24" --lams "$L;$W3;$W8;$S8;$B16;$W3;$W8"
echo chain-done
