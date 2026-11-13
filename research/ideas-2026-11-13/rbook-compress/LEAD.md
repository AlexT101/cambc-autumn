# Lead from the book agent (relayed by the coordinator, 2026-11-13 ~02:55Z)

About half the book is the live mask's noise in our recorded priorities.

- Every turn of every body records one set-priority (169,355 in 40 entries, about 4,200 an entry). The mask xors the
  payload's low 14 bits with a fresh draw each round, plus a 2-bit round tag, so each costs about 2 incompressible
  bytes: roughly 8.5 KB of the ~18 KB an entry.
- The draw depends only on a per-game seed (prio_stream.h: `mask_of(mix(game.seed ^ w * 0x9e37...), index)`, tag
  `(w + game.tag) & 3`). The plain payload under it is the claim + 1 and three mailbox bits, which is highly
  compressible.
- Exact scheme: store the game seed per entry (8 bytes) and code `low16 ^ (tag << 14 | mask)`; the bot xors it back at
  play time. The round trip is exact whatever the seed, so a wrong seed only costs size, never correctness. Entries with
  seed 0 (foreign, unmasked) stay as they are.
- Getting each game's seed needs the key (via tools/livemask, never printed or committed) and World's setup facts. The
  safe way is a masked host with an empty book that prints `prio_stream::game.seed` at World init and resigns, played
  once on each entry's map and side against the opponent puppet.
- A turn that set its priority after a rollover may carry the previous round's mask; those just code badly.

Expected: about 40% off the blob, i.e. room for roughly 400 entries instead of 240.
The book agent will adopt the compression agent's patch; it is not doing this itself.

## Update 03:25Z: the final host is UNMASKED (user decision)

The final submission's host sends plain priorities (no live mask). On-book bodies still emit the recorded, masked
priorities verbatim. So if your scheme needs the mask stream at play time to rebuild those recorded values, the key
may be compiled in for the book's decoder only; the host's own comms stay plain. Never print or commit the key.
Design the decoder so it works in a build whose own comms are unmasked.
