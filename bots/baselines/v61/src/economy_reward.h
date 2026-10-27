#pragma once

namespace aph {

struct CaptureReward { int gold = 0, gems = 0; };

constexpr int reward_share(int amount, int holders, bool lowest) {
    return holders > 0 ? amount / holders + (lowest ? amount % holders : 0) : 0;
}

constexpr CaptureReward capture_reward(int gold, int gems, int cluster_gold, int cluster_gems,
                                       int holders, bool lowest, bool prospector) {
    return {reward_share(gold, holders, lowest) + (prospector ? reward_share(cluster_gold, holders, lowest) / 4 : 0),
            reward_share(gems, holders, lowest) + (prospector ? reward_share(cluster_gems, holders, lowest) / 4 : 0)};
}

} // namespace aph
