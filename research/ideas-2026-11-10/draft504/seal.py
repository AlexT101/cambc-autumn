"""Explicitly reseal owned draft17 preparation while the unstarted job is held."""
import argparse
import hashlib
import json
from pathlib import Path

from run import D, T, sha, source


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--expected-manifest',required=True);a=ap.parse_args()
    manifest=D/'manifest.json'
    assert sha(manifest)==a.expected_manifest
    assert not (D/'first-heavy-start.json').exists(), 'Started experiments cannot be resealed'
    m=json.loads(manifest.read_text())
    for bot,files in m['sources'].items():assert source(bot)==files,bot
    allowed={D/'protocol.json',D/'config.json'}
    for name,h in m['files'].items():
        p=Path(name)
        if sha(p)!=h:assert p.is_relative_to(T) or p.is_relative_to(D/'inputs/preferences') or p in allowed,p
    paths={Path(p) for p in m['files']}
    paths.update(p for p in T.iterdir() if p.is_file() and p.suffix in ('.py','.mjs','.md'))
    paths.update(p for p in (D/'inputs/preferences').iterdir() if p.is_file())
    paths.update([D/'protocol.json',D/'preference-seed-reservation.json',D/'preference-replacement-seed-reservation.json'])
    m['files']={str(p):sha(p) for p in sorted(paths)}
    m['preference_amendment']={'from_manifest':a.expected_manifest,'unstarted':True,
                              'scope':'One800kcollection; threefixedapproaches; noqueue release orresult admission'}
    temp=manifest.with_suffix('.json.tmp');temp.write_text(json.dumps(m,indent=2)+'\n');temp.replace(manifest)
    print(json.dumps({'old_manifest':a.expected_manifest,'manifest_sha256':sha(manifest),'files':len(paths)}))


if __name__=='__main__':main()
