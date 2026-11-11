#pragma once
#include "../common/common.h"
#include "radix.h"

// The team's 8 bytes of shared memory: every channel's fields in one radix::product.
namespace comms {
    inline radix::product layout;
    inline u64 fields[radix::max_parts];

    inline void read() {
        using namespace cambc::detail;
        u64 word;
        check(sdk_read_shared_memory(0, &word, sizeof word));
        layout.unpack(word, fields);
    }

    inline void write() {
        using namespace cambc::detail;
        const u64 word = layout.pack(fields);
        check(sdk_write_shared_memory(0, &word, sizeof word));
    }
} // namespace comms
