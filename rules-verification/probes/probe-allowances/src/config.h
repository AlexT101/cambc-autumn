#pragma once
#include <cambc.h>
#include <array>
// Experiment configuration. Both runs use map interlock (4 picks) vs probe-allowances-b:
//   cambc run probe-allowances probe-allowances-b --map interlock --rounds 330 --fuel 50000000 -o <dir>
// (--fuel is raised so heavy logging never suspends a bot mid-turn; suspension splits a turn's actions
//  across rounds and invalidates same-turn results.)
inline constexpr bool kDumpMap = false;
#ifndef PROBE_RUN
#define PROBE_RUN 1
#endif
inline constexpr int kRun = PROBE_RUN;
// Run 1: Vesper Vale, Stellar, Cassi&Issac, Willow.   Run 2: Tavi, Vendetta, Ryth, Varg.
inline constexpr std::array kPicks = kRun == 1
    ? std::array{ cambc::champion_draft::vesper_vale, cambc::champion_draft::stellar, cambc::champion_draft::cassi_and_issac,
          cambc::champion_draft::willow, cambc::champion_draft::prism }
    : std::array{ cambc::champion_draft::tavi, cambc::champion_draft::vendetta, cambc::champion_draft::ryth,
          cambc::champion_draft::varg, cambc::champion_draft::prism };
// Round after which the enemy Varg (probe-allowances-b) is parked in the bush at (13,22).
inline constexpr int kHiddenRound = 120;
