# Shared memory

*Your team’s two scratchpads: 1,024 bytes saved in the draft, and 8 bytes shared all match.*

Each champion has its own bot instance, but there is a team memory buffer that is shared by your team, which cannot be read by the opponent.

Each team has 8 bytes of shared memory, that is readable and writable throughout the match.

In addition, there is the 1024 bytes of draft memory, that is writable during the draft phase, that becomes read-only for your champions during the match itself.

---

**See also:** [Bot API reference](../api/cpp.md) · [Champion roster](../champions/README.md)

<sub>Engine sources cited by the handbook: `game/Engine/include/private_cpp/Engine/Balance/GameSettings.h`, `game/Engine/src/Game/Memory.cpp`, `game/cli/sdk/cpp/cambc.h`, `game/cli/runner/src/api.rs`, `game/cli/runner/src/primitives.rs`</sub>
