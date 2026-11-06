// Ablation switches for A/B diagnosis of the Fish chunks (research/fish-bot-2026-11-06/LOG.md).
#pragma once
#ifndef FISH_PRIORITY
#define FISH_PRIORITY 1
#endif
namespace aph::fish {
inline constexpr bool use_draft = true, use_shop = true, use_locks = true, use_recall = true, use_tribute = true;
} // namespace aph::fish
