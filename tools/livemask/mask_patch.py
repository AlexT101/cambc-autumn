#!/usr/bin/env python3
"""Patch a copied ocean bot so its priorities show coded per game in replays (prio_mask.h, next to this file).

    python3 mask_patch.py BOT_DIR [--key-file F] [--zero]

BOT_DIR is a scratch copy (never a frozen variant or a git-tracked dir): its src/model gets prio_mask.h with the
key from F (default ~/.config/cambc-secret/comms.key, 16 bytes) and seven edits at anchors that must each match
exactly once. Exits non-zero, changing nothing, if any anchor is missing. --zero writes a zero key (the code then
compiles out: for identity checks). Never prints the key.
"""
import argparse, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARK = 'inline constexpr std::uint64_t key[2] = {0x0ull, 0x0ull}; // PRIO_MASK_KEY'

SETUP = '''
} // namespace

// prio_mask's seed and rank range: packed_priority's rank is (rank_code - rank_code(0)) * 8 + 7 - index.
static_assert((rank_code(3 * band_width - 1) - rank_code(0)) * 8 + 7 < 32767 && rank_code(0) * 8 < 32768);
void prio_mask::setup(const World& world) {
    const auto& s = world.map();
    std::uint64_t picks = s.team_a ? 0x5a : 0xa5;
    for (const auto& b : world.allies) picks = picks * 0x100000001b3ull + static_cast<std::uint64_t>(b.type) + 1;
    const std::uint64_t place = static_cast<std::uint64_t>(s.width) << 48 ^ static_cast<std::uint64_t>(s.height) << 32
                                ^ static_cast<std::uint64_t>(s.groups.size()) << 16
                                ^ static_cast<std::uint64_t>(s.ally_spawn_centre.x * 256 + s.ally_spawn_centre.y);
    prio_mask::make(prio_mask::mix(place ^ prio_mask::key[1]) ^ picks, -rank_code(0) * 8,
                    (rank_code(3 * band_width - 1) - rank_code(0)) * 8 + 7);
}

namespace {
'''

EDITS = [
    ('model/turn_order.cc', '#include "world.h"\n', '#include "world.h"\n#include "prio_mask.h"\n'),
    ('model/turn_order.cc',
     '    return rank * (1 << priority_payload_bits) + static_cast<std::int32_t>(payload);\n',
     '    if constexpr (prio_mask::on) return prio_mask::packed(rank, payload);\n'
     '    return rank * (1 << priority_payload_bits) + static_cast<std::int32_t>(payload);\n'),
    ('model/turn_order.cc',
     'static_assert(((rank_code(3 * band_width - 1) - rank_code(0)) * 8 + 7) < 1 << (31 - priority_payload_bits));\n',
     'static_assert(((rank_code(3 * band_width - 1) - rank_code(0)) * 8 + 7) < 1 << (31 - priority_payload_bits));\n' + SETUP),
    ('model/world.cc', '#include "turn_order.h"\n', '#include "turn_order.h"\n#include "prio_mask.h"\n'),
    ('model/world.cc', '        try {\n            init_beliefs();\n',
     '        try {\n            init_beliefs();\n'
     '            if constexpr (prio_mask::on) prio_mask::setup(*this);\n'),
    ('model/comms.cc', '#include "turn_order.h"\n', '#include "turn_order.h"\n#include "prio_mask.h"\n'),
    ('model/comms.cc',
     '    return static_cast<std::uint32_t>(a.next_priority) & ((1u << priority_payload_bits) - 1);\n',
     '    if constexpr (prio_mask::on) return prio_mask::payload_of(a.next_priority);\n'
     '    return static_cast<std::uint32_t>(a.next_priority) & ((1u << priority_payload_bits) - 1);\n'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bot')
    ap.add_argument('--key-file', default=str(Path.home() / '.config/cambc-secret/comms.key'))
    ap.add_argument('--zero', action='store_true')
    a = ap.parse_args()
    src = Path(a.bot) / 'src'
    if (src / 'model/prio_mask.h').exists():
        sys.exit('mask_patch: already patched')
    texts = {}
    for f, old, _ in EDITS:
        p = src / f
        if not p.is_file():
            sys.exit(f'mask_patch: {f} missing')
        texts.setdefault(f, p.read_text())
        n = texts[f].count(old)
        if n != 1:
            sys.exit(f'mask_patch: anchor in {f} matches {n} times: {old.splitlines()[0].strip()[:60]}')
    if a.zero:
        words = (0, 0)
    else:
        kb = Path(a.key_file).read_bytes()
        if len(kb) < 16:
            sys.exit('mask_patch: key file too short')
        words = (int.from_bytes(kb[:8], 'little'), int.from_bytes(kb[8:16], 'little'))
        if words == (0, 0):
            sys.exit('mask_patch: zero key')
    header = (HERE / 'prio_mask.h').read_text()
    if header.count(MARK) != 1:
        sys.exit('mask_patch: key marker missing in prio_mask.h')
    header = header.replace(MARK, 'inline constexpr std::uint64_t key[2] = {0x%016xull, 0x%016xull};' % words)
    for f, old, new in EDITS:
        texts[f] = texts[f].replace(old, new, 1)
    for f, t in texts.items():
        (src / f).write_text(t)
    hp = src / 'model/prio_mask.h'
    hp.write_text(header)
    hp.chmod(0o600)
    print(f'mask_patch: patched {a.bot} ({"zero key" if a.zero else "keyed"})')


if __name__ == '__main__':
    main()
