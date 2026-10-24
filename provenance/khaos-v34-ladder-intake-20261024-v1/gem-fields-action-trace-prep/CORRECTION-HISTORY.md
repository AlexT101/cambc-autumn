# Action trace correction history

- Initial patch-generation attempt stopped at an incorrect unique-text anchor before producing its review patch.
- Superseded patch `action-realization-instrumentation-v1-incorrect.patch` accidentally renamed the existing `enemy_tribute_wins` function to an overloaded `cast_at_camp`; it was not used for the accepted trace build.
- `action-realization-instrumentation-v2-intermediate.patch` briefly used `world.me().handle` in the actor filter. This is equivalent, but was superseded to keep the source change minimal; `my_handle()` is cached in `util.h`.
- The final v2 patch restores the original `enemy_tribute_wins` declaration and body, retains `my_handle()` actor scoping, and is AR-only against f475. The reviewed row metadata says AR-only. This exact source was copied into `gem-fields-action-trace`, built, and run.
