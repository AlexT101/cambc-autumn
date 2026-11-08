set -e
cd /home/ubuntu/cambc-autumn
export PYTHONPATH=tools/fish OMP_NUM_THREADS=2
S=replays/fish-scorecard/mite-1107/manifest-all.json; C=replays/fish-scorecard/mite-1107/actor-all; D=replays/fish-farm3/mite1107
python3 tools/fish/decision_data.py $S $C $D/decisions-v2.jsonl.gz
python3 tools/fish/routes_data.py $S $C $D/decisions-v2.jsonl.gz $D/routes-v3.jsonl.gz
python3 tools/fish/choice_data.py $C $D/routes-v3.jsonl.gz $D/choice-v1.jsonl.gz
python3 tools/fish/farm2_data.py $D/choice-v1.jsonl.gz $C $D/farm2-v3.jsonl.gz
echo PIPELINE-DONE
