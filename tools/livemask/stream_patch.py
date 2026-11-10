#!/usr/bin/env python3
"""Patch a copied ocean bot so its priorities show coded per round in replays (prio_stream.h, next to this file).
A successor to mask_patch.py: apply one or the other, never both.

    python3 stream_patch.py BOT_DIR [--key-file F] [--zero]

BOT_DIR is a scratch copy (never a frozen variant or a git-tracked dir): its src/model gets prio_stream.h with the
key from F (default tools/livemask/livemask.key, 16 bytes; v87-v105 used the old secret key in ~/.config/cambc-secret/comms.key) and edits at anchors that must each match exactly
once. Exits non-zero, changing nothing, if any anchor is missing. --zero writes a zero key (the code then compiles
out: for identity checks). Never prints the key.
"""
import argparse, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARK = 'inline constexpr std::uint64_t key[2] = {0x0ull, 0x0ull}; // PRIO_MASK_KEY'

SETUP = '''
} // namespace

// prio_stream's seed and rank range (make()'s limits): packed_priority's rank is (rank_code - rank_code(0)) * 8 + 7 - index.
static_assert(rank_code(0) <= 64 && rank_code(band_width) - rank_code(0) <= 63
              && (rank_code(3 * band_width - 1) - rank_code(band_width) + 1) * 8 <= 32000);
void prio_stream::setup(const World& world) {
    const auto& s = world.map();
    std::uint64_t picks = s.team_a ? 0x5a : 0xa5;
    for (const auto& b : world.allies) picks = picks * 0x100000001b3ull + static_cast<std::uint64_t>(b.type) + 1;
    const std::uint64_t place = static_cast<std::uint64_t>(s.width) << 48 ^ static_cast<std::uint64_t>(s.height) << 32
                                ^ static_cast<std::uint64_t>(s.groups.size()) << 16
                                ^ static_cast<std::uint64_t>(s.ally_spawn_centre.x * 256 + s.ally_spawn_centre.y);
    (void)prio_stream::make(prio_stream::mix(place ^ prio_stream::key[1]) ^ picks, -rank_code(0) * 8,
                      (rank_code(3 * band_width - 1) - rank_code(0)) * 8 + 7, (rank_code(band_width) - rank_code(0)) * 8,
                      static_cast<int>(world.allies.size()));
}

namespace {
'''

EDITS = [
    ('model/turn_order.cc', '#include "world.h"\n', '#include "world.h"\n#include "prio_stream.h"\n'),
    ('model/turn_order.cc',
     '    return rank * (1 << priority_payload_bits) + static_cast<std::int32_t>(payload);\n',
     '    if constexpr (prio_stream::on) return prio_stream::packed(rank, payload);\n'
     '    return rank * (1 << priority_payload_bits) + static_cast<std::int32_t>(payload);\n'),
    ('model/turn_order.cc',
     '    const std::int32_t priority = packed_priority(turn_rank, world.me().index, payload);\n',
     '    std::int32_t priority = packed_priority(turn_rank, world.me().index, payload);\n'
     '    if constexpr (prio_stream::on) priority = prio_stream::publish(priority, world.round, world.me().index);\n'),
    ('model/turn_order.cc',
     'static_assert(((rank_code(3 * band_width - 1) - rank_code(0)) * 8 + 7) < 1 << (31 - priority_payload_bits));\n',
     'static_assert(((rank_code(3 * band_width - 1) - rank_code(0)) * 8 + 7) < 1 << (31 - priority_payload_bits));\n' + SETUP),
    ('model/world.cc', '#include "turn_order.h"\n', '#include "turn_order.h"\n#include "prio_stream.h"\n'),
    ('model/world.cc', '        try {\n            init_beliefs();\n',
     '        try {\n            init_beliefs();\n'
     '            if constexpr (prio_stream::on) prio_stream::setup(*this);\n'),
    ('model/comms.cc', '#include "turn_order.h"\n', '#include "turn_order.h"\n#include "prio_stream.h"\n'),
    ('model/comms.cc',
     '    return static_cast<std::uint32_t>(a.next_priority) & ((1u << priority_payload_bits) - 1);\n',
     '    if constexpr (prio_stream::on) return prio_stream::payload_of(a.next_priority, world.round, a.index);\n'
     '    return static_cast<std::uint32_t>(a.next_priority) & ((1u << priority_payload_bits) - 1);\n'),
]
# The round tag takes the payload's top 2 bits: the first anchor found (bots with the chase bit, then before it).
TAG_ROOM = [
    ('model/comms.cc',
     'static_assert(support_mailbox::payload_shift + 3 <= chase_shift && chase_shift + 3 <= priority_payload_bits);\n',
     'static_assert(support_mailbox::payload_shift + 3 <= chase_shift && chase_shift + 3 <= priority_payload_bits);\n'
     'static_assert(chase_shift + 3 <= 14);\n'),
    ('model/comms.cc',
     "static_assert(support_mailbox::protected_mate == 0 && support_mailbox::healer == 1); // support_pair's order\n",
     "static_assert(support_mailbox::protected_mate == 0 && support_mailbox::healer == 1); // support_pair's order\n"
     'static_assert(support_mailbox::payload_shift + 3 <= 14);\n'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bot')
    ap.add_argument('--key-file', default='/home/ubuntu/cambc-autumn/tools/livemask/livemask.key')
    ap.add_argument('--zero', action='store_true')
    a = ap.parse_args()
    src = Path(a.bot) / 'src'
    if (src / 'model/prio_stream.h').exists() or (src / 'model/prio_mask.h').exists():
        sys.exit('stream_patch: already patched')
    comms = (src / 'model/comms.cc').read_text() if (src / 'model/comms.cc').is_file() else ''
    room = [e for e in TAG_ROOM if 'chase_shift' in comms] [:1] if 'chase_shift' in comms else TAG_ROOM[1:]
    edits = EDITS + room
    texts = {}
    for f, old, _ in edits:
        p = src / f
        if not p.is_file():
            sys.exit(f'stream_patch: {f} missing')
        texts.setdefault(f, p.read_text())
        n = texts[f].count(old)
        if n != 1:
            sys.exit(f'stream_patch: anchor in {f} matches {n} times: {old.splitlines()[0].strip()[:60]}')
    if a.zero:
        words = (0, 0)
    else:
        kb = Path(a.key_file).read_bytes()
        if len(kb) < 16:
            sys.exit('stream_patch: key file too short')
        words = (int.from_bytes(kb[:8], 'little'), int.from_bytes(kb[8:16], 'little'))
        if words == (0, 0):
            sys.exit('stream_patch: zero key')
    header = (HERE / 'prio_stream.h').read_text()
    if header.count(MARK) != 1:
        sys.exit('stream_patch: key marker missing in prio_stream.h')
    header = header.replace(MARK, 'inline constexpr std::uint64_t key[2] = {0x%016xull, 0x%016xull};' % words)
    for f, old, new in edits:
        texts[f] = texts[f].replace(old, new, 1)
    for f, t in texts.items():
        (src / f).write_text(t)
    hp = src / 'model/prio_stream.h'
    hp.write_text(header)
    hp.chmod(0o600)
    print(f'stream_patch: patched {a.bot} ({"zero key" if a.zero else "keyed"})')


if __name__ == '__main__':
    main()
