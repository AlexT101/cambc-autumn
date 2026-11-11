"""Replace only the replica's baked noise seed/draft salt with per-game native inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

HEADER = '''#pragma once
#include <cstdint>
// The experimental runner supplies immutable per-team values before any draft call.
extern "C" __attribute__((import_module("env"), import_name("experiment_config")))
std::uint64_t experiment_config(std::uint32_t key);
'''


def transform(files):
    out = dict(files)
    assert 'experiment_config.h' not in out, 'Already patched or unexpected source'
    noise = out['dvp_noise.h']
    noise, n = re.subn(r'inline constexpr std::uint64_t member_seed = \d+u;',
                      'inline std::uint64_t member_seed() { return experiment_config(0); }', noise)
    assert n == 1
    assert noise.count('mixw(member_seed,') == 1
    noise = noise.replace('mixw(member_seed,', 'mixw(member_seed(),')
    noise = noise.replace('#include "tune.h"', '#include "tune.h"\n#include "experiment_config.h"', 1)
    fm, n = re.subn(r'inline constexpr std::uint64_t salt = \d+ull;',
                   'inline std::uint64_t salt() { return experiment_config(1); }', out['draft/fm_draft.h'])
    assert n == 1
    fm = fm.replace('#include <cstdint>', '#include <cstdint>\n#include "../experiment_config.h"', 1)
    draft = out['draft/draft.cc']
    assert draft.count('fm::salt *') == 1
    out.update({'dvp_noise.h': noise, 'draft/fm_draft.h': fm,
                'draft/draft.cc': draft.replace('fm::salt *', 'fm::salt() *'), 'experiment_config.h': HEADER})
    return out


def source(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob('*')) if p.is_file()}


def prepare(src, dst):
    assert src.is_dir() and not dst.exists(), 'Require existing frozen body and new destination'
    before = source(src / 'src')
    files = {str(p.relative_to(src / 'src')): p.read_text()
             for p in sorted((src / 'src').rglob('*')) if p.is_file()}
    changed = transform(files)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('.cambc', 'build', 'target', '.cache'))
    for name, value in changed.items():
        if files.get(name) != value:
            (dst / 'src' / name).write_text(value)
    assert source(src / 'src') == before
    after = source(dst / 'src')
    assert {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)} == {
        'dvp_noise.h', 'draft/fm_draft.h', 'draft/draft.cc', 'experiment_config.h'}
    return {'source': str(src), 'destination': str(dst), 'before': before, 'after': after,
            'keys': {'0': 'noise member_seed', '1': 'draft salt'},
            'limitation': 'Existing Flp4/Mt3qro approximations; not current live opponent source.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--proof', type=Path, required=True)
    args = parser.parse_args()
    args.proof.write_text(json.dumps(prepare(args.source, args.destination), indent=2) + '\n')
