//! Facts read back from a finished game.

/// Winning team from the replay; filled in by game.rs from the engine's summary instead.
pub fn winner(_replay: &[u8]) -> Option<u32> {
    None
}
