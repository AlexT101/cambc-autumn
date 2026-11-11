"""The badmaps mechanism suite: wheel at 24 noise seeds and 13 other weak ladder maps at 8, as map copies (run_batched
keys the experiment config by the resolved file's stem, so symlinks do not work), with a run-time body config.
Writes replays/gemprice/mech/maps and replays/gemprice/mech/cfg.json; mech.sh plays it."""
import json, os, shutil

D = 'replays/gemprice/mech/maps'
os.makedirs(D, exist_ok=True)
maps = {'04wheel': 24}
for m in ['03honeycomb', '02harvest', '00collision', '00interlock', '04courtyard', '04bowls', '03shrines', '00elkring',
          '04bullseye', '00ribs', '04waves', '04orchard', '02famine']:
    maps[m] = 8
cfg = {}; k = 880000
for m, n in maps.items():
    for i in range(n):
        name = f'{m}-n{i:02d}'
        shutil.copyfile(f'maps/{m}.map26a', f'{D}/{name}.map26a')
        k += 1
        cfg[name] = {'seed': 1310000 + k, 'salt': k, 'unmetered': True}
json.dump({'schema': 1, 'opponent_index': 1, 'maps': cfg}, open('replays/gemprice/mech/cfg.json', 'w'))
print(len(cfg))
