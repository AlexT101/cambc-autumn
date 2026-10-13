# Fuel

*Bots have a computation limit enforced via Wasmtime fuel. Fuel roughly corresponds to CPU instructions, though it isn't perfectly 1:1. Using fuel rather than time means that execution is deterministic and machine-independent. Since some languages are more instruction efficient than others, there are different fuel limits for different languages.*

Bots have a computation limit enforced via Wasmtime fuel. Fuel roughly corresponds to CPU instructions, though it isn't perfectly 1:1. Using fuel rather than time means that execution is deterministic and machine-independent. Since some languages are more instruction efficient than others, there are different fuel limits for different languages.

By default, a C++ or Rust bot gets 100k fuel per turn. OCaml gets 5 times the C++ limit, and Python gets 25 times the C++ limit.

When a bot runs out of fuel, its execution is suspended and the next bot in the turn order gets to go. The next round, this bot's turn will resume from the point of suspension and continues.

We provide bots with 10x fuel for the first turn of draft, to facilitate precomputation, and 2x fuel for the first turn of play, giving bots room to initialise and precompute. Unused fuel at the end of a turn is not added to the next turn's fuel budget.

---

**See also:** [Drafting](./02-draft.md) · [A champion turn](./03-your-first-turn.md) · [Distance Fields](../guides/cpp/distance-fields.md)

<sub>Engine sources cited by the handbook: `game/cli/wasm-runtime/src/lib.rs`, `game/cli/runner/src/lib.rs`, `game/cli/runner/src/primitives.rs`, `game/cli/src/main.rs`</sub>
