#pragma once

#include "../../../comms.h"

namespace aph {
struct Turn;
}

namespace cassi::states::assess {
inline constexpr int max_score = 15;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace cassi::states::bank {
inline constexpr int max_score = 7;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace cassi::states::capture {
inline constexpr int max_score = 10;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace cassi::states::channel {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace cassi::states::chase {
inline constexpr int max_score = 4;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace cassi::states::contest {
inline constexpr int max_score = 3;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace cassi::states::dead {
inline constexpr int max_score = 20;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace cassi::states::ender {
inline constexpr int max_score = 16;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace cassi::states::farm {
inline constexpr int max_score = 1;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace cassi::states::guard {
inline constexpr int max_score = 11;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace cassi::states::idle {
inline constexpr int max_score = 17;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace cassi::states::mend {
inline constexpr int max_score = 13;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace cassi::states::prepare {
inline constexpr int max_score = 18;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace cassi::states::retreat {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace cassi::states::siege {
inline constexpr int max_score = 2;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace cassi::states::spent {
inline constexpr int max_score = 6;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace cassi::states::strike {
inline constexpr int max_score = 9;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace cassi::states::tend {
inline constexpr int max_score = 14;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::assess {
inline constexpr int max_score = 15;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::bank {
inline constexpr int max_score = 7;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::capture {
inline constexpr int max_score = 10;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::channel {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::chase {
inline constexpr int max_score = 4;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::contest {
inline constexpr int max_score = 3;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::dead {
inline constexpr int max_score = 20;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::ender {
inline constexpr int max_score = 16;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::farm {
inline constexpr int max_score = 1;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::guard {
inline constexpr int max_score = 11;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::idle {
inline constexpr int max_score = 17;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::mend {
inline constexpr int max_score = 13;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::prepare {
inline constexpr int max_score = 18;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::retreat {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::siege {
inline constexpr int max_score = 2;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::spent {
inline constexpr int max_score = 6;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::strike {
inline constexpr int max_score = 9;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace heart_of_ruin::states::tend {
inline constexpr int max_score = 14;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::assess {
inline constexpr int max_score = 15;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::bank {
inline constexpr int max_score = 7;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::capture {
inline constexpr int max_score = 10;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::channel {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::chase {
inline constexpr int max_score = 4;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::contest {
inline constexpr int max_score = 3;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::dead {
inline constexpr int max_score = 20;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::ender {
inline constexpr int max_score = 16;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::farm {
inline constexpr int max_score = 1;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::guard {
inline constexpr int max_score = 11;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::idle {
inline constexpr int max_score = 17;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::mend {
inline constexpr int max_score = 13;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::prepare {
inline constexpr int max_score = 18;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::retreat {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::siege {
inline constexpr int max_score = 2;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::spent {
inline constexpr int max_score = 6;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::strike {
inline constexpr int max_score = 9;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace issac::states::tend {
inline constexpr int max_score = 14;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::assess {
inline constexpr int max_score = 15;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::bank {
inline constexpr int max_score = 7;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::capture {
inline constexpr int max_score = 10;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::channel {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::chase {
inline constexpr int max_score = 4;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::contest {
inline constexpr int max_score = 3;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::dead {
inline constexpr int max_score = 20;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::ender {
inline constexpr int max_score = 16;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::farm {
inline constexpr int max_score = 1;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::guard {
inline constexpr int max_score = 11;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::idle {
inline constexpr int max_score = 17;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::mend {
inline constexpr int max_score = 13;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::prepare {
inline constexpr int max_score = 18;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::retreat {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::siege {
inline constexpr int max_score = 2;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::spent {
inline constexpr int max_score = 6;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::strike {
inline constexpr int max_score = 9;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace marcella::states::tend {
inline constexpr int max_score = 14;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::assess {
inline constexpr int max_score = 16;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::bank {
inline constexpr int max_score = 7;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::capture {
inline constexpr int max_score = 10;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::channel {
inline constexpr int max_score = 20;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::chase {
inline constexpr int max_score = 4;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::contest {
inline constexpr int max_score = 3;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::dead {
inline constexpr int max_score = 21;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::ender {
inline constexpr int max_score = 17;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::farm {
inline constexpr int max_score = 1;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::guard {
inline constexpr int max_score = 11;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::idle {
inline constexpr int max_score = 18;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::mend {
inline constexpr int max_score = 13;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::prepare {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::retreat {
inline constexpr int max_score = 20;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::siege {
inline constexpr int max_score = 2;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::spent {
inline constexpr int max_score = 6;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::strike {
inline constexpr int max_score = 9;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::support {
inline constexpr int max_score = 15;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace prism::states::tend {
inline constexpr int max_score = 14;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::assess {
inline constexpr int max_score = 15;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::bank {
inline constexpr int max_score = 7;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::capture {
inline constexpr int max_score = 10;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::channel {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::chase {
inline constexpr int max_score = 4;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::contest {
inline constexpr int max_score = 3;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::dead {
inline constexpr int max_score = 20;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::ender {
inline constexpr int max_score = 16;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::farm {
inline constexpr int max_score = 1;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::guard {
inline constexpr int max_score = 11;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::idle {
inline constexpr int max_score = 17;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::mend {
inline constexpr int max_score = 13;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::prepare {
inline constexpr int max_score = 18;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::retreat {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::siege {
inline constexpr int max_score = 2;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::spent {
inline constexpr int max_score = 6;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::strike {
inline constexpr int max_score = 9;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ren::states::tend {
inline constexpr int max_score = 14;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::assess {
inline constexpr int max_score = 15;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::bank {
inline constexpr int max_score = 7;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::capture {
inline constexpr int max_score = 10;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::channel {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::chase {
inline constexpr int max_score = 4;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::contest {
inline constexpr int max_score = 3;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::dead {
inline constexpr int max_score = 20;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::ender {
inline constexpr int max_score = 16;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::farm {
inline constexpr int max_score = 1;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::guard {
inline constexpr int max_score = 11;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::idle {
inline constexpr int max_score = 17;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::mend {
inline constexpr int max_score = 13;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::prepare {
inline constexpr int max_score = 18;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::retreat {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::siege {
inline constexpr int max_score = 2;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::spent {
inline constexpr int max_score = 6;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::strike {
inline constexpr int max_score = 9;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace ryth::states::tend {
inline constexpr int max_score = 14;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::assess {
inline constexpr int max_score = 15;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::bank {
inline constexpr int max_score = 7;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::capture {
inline constexpr int max_score = 10;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::channel {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::chase {
inline constexpr int max_score = 4;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::contest {
inline constexpr int max_score = 3;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::dead {
inline constexpr int max_score = 20;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::ender {
inline constexpr int max_score = 16;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::farm {
inline constexpr int max_score = 1;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::guard {
inline constexpr int max_score = 11;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::idle {
inline constexpr int max_score = 17;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::mend {
inline constexpr int max_score = 13;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::prepare {
inline constexpr int max_score = 18;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::retreat {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::siege {
inline constexpr int max_score = 2;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::spent {
inline constexpr int max_score = 6;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::strike {
inline constexpr int max_score = 9;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace stellar::states::tend {
inline constexpr int max_score = 14;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::assess {
inline constexpr int max_score = 15;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::bank {
inline constexpr int max_score = 7;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::capture {
inline constexpr int max_score = 10;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::channel {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::chase {
inline constexpr int max_score = 4;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::contest {
inline constexpr int max_score = 3;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::dead {
inline constexpr int max_score = 20;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::ender {
inline constexpr int max_score = 16;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::farm {
inline constexpr int max_score = 1;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::guard {
inline constexpr int max_score = 11;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::idle {
inline constexpr int max_score = 17;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::mend {
inline constexpr int max_score = 13;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::prepare {
inline constexpr int max_score = 18;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::retreat {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::siege {
inline constexpr int max_score = 2;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::spent {
inline constexpr int max_score = 6;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::strike {
inline constexpr int max_score = 9;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace tavi::states::tend {
inline constexpr int max_score = 14;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::assess {
inline constexpr int max_score = 15;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::bank {
inline constexpr int max_score = 7;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::capture {
inline constexpr int max_score = 10;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::channel {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::chase {
inline constexpr int max_score = 4;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::contest {
inline constexpr int max_score = 3;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::dead {
inline constexpr int max_score = 20;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::ender {
inline constexpr int max_score = 16;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::farm {
inline constexpr int max_score = 1;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::guard {
inline constexpr int max_score = 11;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::idle {
inline constexpr int max_score = 17;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::mend {
inline constexpr int max_score = 13;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::prepare {
inline constexpr int max_score = 18;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::retreat {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::siege {
inline constexpr int max_score = 2;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::spent {
inline constexpr int max_score = 6;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::strike {
inline constexpr int max_score = 9;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace varg::states::tend {
inline constexpr int max_score = 14;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::assess {
inline constexpr int max_score = 15;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::bank {
inline constexpr int max_score = 7;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::capture {
inline constexpr int max_score = 10;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::channel {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::chase {
inline constexpr int max_score = 4;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::contest {
inline constexpr int max_score = 3;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::dead {
inline constexpr int max_score = 20;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::ender {
inline constexpr int max_score = 16;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::farm {
inline constexpr int max_score = 1;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::guard {
inline constexpr int max_score = 11;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::idle {
inline constexpr int max_score = 17;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::mend {
inline constexpr int max_score = 13;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::prepare {
inline constexpr int max_score = 18;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::retreat {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::siege {
inline constexpr int max_score = 2;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::spent {
inline constexpr int max_score = 6;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::strike {
inline constexpr int max_score = 9;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vendetta::states::tend {
inline constexpr int max_score = 14;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::assess {
inline constexpr int max_score = 15;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::bank {
inline constexpr int max_score = 7;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::capture {
inline constexpr int max_score = 10;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::channel {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::chase {
inline constexpr int max_score = 4;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::contest {
inline constexpr int max_score = 3;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::dead {
inline constexpr int max_score = 20;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::ender {
inline constexpr int max_score = 16;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::farm {
inline constexpr int max_score = 1;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::guard {
inline constexpr int max_score = 11;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::idle {
inline constexpr int max_score = 17;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::mend {
inline constexpr int max_score = 13;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::prepare {
inline constexpr int max_score = 18;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::retreat {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::siege {
inline constexpr int max_score = 2;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::spent {
inline constexpr int max_score = 6;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::strike {
inline constexpr int max_score = 9;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace vesper_vale::states::tend {
inline constexpr int max_score = 14;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::assess {
inline constexpr int max_score = 16;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::bank {
inline constexpr int max_score = 7;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::capture {
inline constexpr int max_score = 10;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::channel {
inline constexpr int max_score = 20;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::chase {
inline constexpr int max_score = 4;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::contest {
inline constexpr int max_score = 3;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::dead {
inline constexpr int max_score = 21;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::ender {
inline constexpr int max_score = 17;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::farm {
inline constexpr int max_score = 1;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::guard {
inline constexpr int max_score = 11;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::idle {
inline constexpr int max_score = 18;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::mend {
inline constexpr int max_score = 13;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::prepare {
inline constexpr int max_score = 19;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::retreat {
inline constexpr int max_score = 20;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::siege {
inline constexpr int max_score = 2;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::spent {
inline constexpr int max_score = 6;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::strike {
inline constexpr int max_score = 9;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::support {
inline constexpr int max_score = 15;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
namespace willow::states::tend {
inline constexpr int max_score = 14;

inline int score(aph::Turn& t);

inline bool run(aph::Turn& t);

}
