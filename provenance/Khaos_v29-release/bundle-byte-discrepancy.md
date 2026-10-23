# Khaos_v29 submission byte-count investigation

The successful `cambc submit` response records version 39 and prints `Uploading .../bots/Khaos_v29 (210730 bytes)`. The separately prepared local ZIP is 209803 bytes (SHA-256 `15a535d6d37083c5ff64997f272d6991898e3b4fe6f1fa30b48107a8284543ea`).

Using the installed cambc 3.0.5 CLI's read-only `bundle` command with a distinct output path reproduced the reported count exactly: 210730 bytes. The preserved CLI bundle `Khaos_v29-cli-3.0.5.bundle.zip` contains 29 `src/` entries, 748379 uncompressed bytes. Its names/order and every uncompressed member byte match the prepared ZIP and current `bots/Khaos_v29/src`. The CLI ZIP has 207670 bytes of compressed member payload; the prepared ZIP has 206743, a 927-byte difference. Both use ZIP deflate, but their per-file compressed output differs; CLI entries use 1980-01-01 timestamps while the prepared ZIP uses 2026-10-23 source timestamps.

This makes the CLI's ZIP bundling step the evidenced explanation for the 210730-byte message. The actual remote upload payload was not retrieved, so it is not asserted byte-identical to the preserved CLI ZIP or the prepared ZIP. The source tree aggregate remains `f71154064f1b2073ffa17391be4519d33f1a0af17710cf19e60f1942b3fcda9b`. No resubmission was attempted.
