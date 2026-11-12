"""Mechanism suite: map copies (run_batched keys the run-time body config by the file's stem, so no symlinks) with a
noise seed each. usage: mksuite.py OUTDIR SEED0 MAP:N|PATH... ; writes OUTDIR/maps and OUTDIR/cfg.json."""
import json, os, shutil, sys
out, k = sys.argv[1], int(sys.argv[2])
D = out + '/maps'; os.makedirs(D, exist_ok=True)
cfg = {}
for spec in sys.argv[3:]:
    if ':' in spec:
        m, n = spec.rsplit(':', 1)
        src = m if m.endswith('.map26a') else f'maps/{m}.map26a'; m = os.path.basename(m).removesuffix('.map26a')
        names = [(f'{m}-n{i:02d}', src) for i in range(int(n))]
    else:
        names = [(os.path.basename(spec)[:-len('.map26a')], spec)]
    for name, src in names:
        shutil.copyfile(src, f'{D}/{name}.map26a'); k += 1
        cfg[name] = {'seed': k, 'salt': k, 'unmetered': True}
json.dump({'schema': 1, 'opponent_index': 1, 'maps': cfg}, open(out + '/cfg.json', 'w'))
print(len(cfg))
