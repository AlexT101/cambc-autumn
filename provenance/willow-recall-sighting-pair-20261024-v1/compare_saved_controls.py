#!/usr/bin/env python3
"""Compare already-saved combined/control replay payloads; does not run games."""
from pathlib import Path
import subprocess, sys
root=Path.cwd()
base=Path('provenance/willow-recall-sighting-pair-20261024-v1')
combined_bw=base/'outputs/corrected-v33-A-combined-B-big-world.repl26a'
combined_bw_a=base/'outputs/combined-B-v33-A-big-world.repl26a' # actual A, despite historical filename
combined_pil=base/'outputs/combined-A-v33-B-pilgrimage.repl26a'
pairs={
 'corrected-bigworld-vs-parent-B':(combined_bw,Path('provenance/willow-phased-solo-boss-4d08241-v1/outputs/latest-parent-B-vs-v33-big-world.repl26a')),
 'corrected-bigworld-vs-recall-B':(combined_bw,Path('provenance/willow-finishing-recall-bigworld-20261024-v1/outputs/finishing-recall-B-vs-v33-big-world.repl26a')),
 'pilgrimage-vs-parent-A':(combined_pil,Path('provenance/willow-sighting-arbitration-pilgrimage-pair-20261024-v1/outputs/parent-A-vs-v33-pilgrimage.repl26a')),
 'pilgrimage-vs-sighting-A':(combined_pil,Path('provenance/willow-sighting-arbitration-pilgrimage-pair-20261024-v1/outputs/sighting-A-vs-v33-pilgrimage.repl26a')),
 'misoriented-bigworld-A-vs-parent-A':(combined_bw_a,base/'outputs/parent-A-v33-B-big-world.repl26a'),
 'misoriented-bigworld-A-vs-recall-A':(combined_bw_a,base/'outputs/finishing-recall-A-v33-B-big-world.repl26a'),
}
for name,(left,right) in pairs.items():
    out=base/f'comparison-{name}.json'
    cmd=['node','tools/replay/harness/compare.mjs',str(left),str(right)]
    with out.open('wb') as f:
        proc=subprocess.run(cmd,stdout=f,stderr=subprocess.PIPE)
    if proc.returncode:
        print(f'{name}: comparator exit {proc.returncode}: {proc.stderr.decode(errors="replace")}',file=sys.stderr)
        sys.exit(proc.returncode)
    print(name)
