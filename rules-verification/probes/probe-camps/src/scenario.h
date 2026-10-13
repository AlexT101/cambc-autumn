#pragma once
// Scenario selection for probe-camps: set SCENARIO (and K_OUT), rebuild, run.
//   cambc build probe-camps && cambc run probe-camps probe-camps-b --map packs --rounds 40 --fuel 5000000 -o <dir>
// (--fuel avoids skipped turns from long move_towards searches; map per scenario is named in its comment).
// (scenarios marked "self-play" run probe-camps vs probe-camps so side 1 is scripted too).
// packs: wolf pair group 0 = A(8,2) id0 + B(8,3) id2; team A spawn (0..2,0..2).
#include <cambc.h>
#include <array>
#include <vector>
#include "bot.h"
#ifndef SCENARIO
#define SCENARIO 1
#endif
#ifndef K_OUT
#define K_OUT 1
#endif
#define DUMP_MAP (SCENARIO == 0)
#define LOG_ALL_CAMPS 0
#define LOG_FUEL 0
#define LOG_RADIUS 6
#define SIDE_FLIP (SCENARIO == 30)  // monolith map: team A spawns bottom-left
#define PRIO_REVERSE (SCENARIO == 16 || SCENARIO == 17)
#define LOG_PRIO (SCENARIO == 16 || SCENARIO == 17)
#define PRIORITY_BASE 50
// Team order by type. Scenarios < 20 (packs, 3 per team): vesper=idx0, ren=idx1, varg=idx2.
// Scenarios >= 20 (5 per team): vesper=idx0, stellar=idx1, prism=idx2, marcella=idx3, ren=idx4.
#if SCENARIO < 20
inline constexpr std::array PICKS{ cambc::champion_draft::vesper_vale, cambc::champion_draft::ren, cambc::champion_draft::varg };
#else
inline constexpr std::array PICKS{ cambc::champion_draft::vesper_vale, cambc::champion_draft::stellar, cambc::champion_draft::prism,
    cambc::champion_draft::marcella, cambc::champion_draft::ren };
#endif

inline std::vector<Step> script(int side, int idx) {
    using V = cambc::vec2;
    const V A{ 8, 2 };
    (void)A;
#if SCENARIO == 1
    // packs: vesper stands at Chebyshev 3 from the wolf pair for 4 rounds without attacking (does it wake?),
    // then attacks A once and stays in range forever (does it keep attacking without further damage?).
    if (side == 0 && idx == 0) return { { V{ 5, 2 }, 0, {}, 4 }, { V{ 5, 2 }, 1, A, -1 } };
#elif SCENARIO == 2
    // packs: vesper hits A once from (5,2), next turn steps out to (4,2) (Chebyshev 4), waits K_OUT rounds,
    // then returns to (5,2) and idles. Does the group still attack on return?
    if (side == 0 && idx == 0) return { { V{ 5, 2 }, 0, {}, 1 }, { V{ 5, 2 }, 1, A, 0 }, { V{ 4, 2 }, 0, {}, K_OUT }, { V{ 5, 2 }, 0, {}, -1 } };
#elif SCENARIO == 3
    // packs: attacker vs nearer bystander. Ren idles at (9,1) (Chebyshev 1 to A, 2 to B); vesper hits A once
    // from (5,2) at round 12 and stays. Who takes the wolves' damage?
    if (side == 0 && idx == 0) return { { V{ 5, 2 }, 1, A, -1, 12 } };
    if (side == 0 && idx == 1) return { { V{ 9, 1 }, 0, {}, -1 } };
#elif SCENARIO == 4
    // packs: independent picks. vesper (6,0): A C2, B C3. ren (8,5): A C3, B C2. vesper hits A at round 12.
    if (side == 0 && idx == 0) return { { V{ 6, 0 }, 1, A, -1, 12 } };
    if (side == 0 && idx == 1) return { { V{ 8, 5 }, 0, {}, -1 } };
#elif SCENARIO == 5
    // packs: Chebyshev tie, straight vs diagonal. vesper (5,2): A(3,0) B(3,1); ren (11,5): A(3,3) B(3,2).
    if (side == 0 && idx == 0) return { { V{ 5, 2 }, 1, A, -1, 14 } };
    if (side == 0 && idx == 1) return { { V{ 11, 5 }, 0, {}, -1 } };
#elif SCENARIO == 6
    // packs: as 5 with roles swapped: vesper diagonal (11,5) attacks, ren straight (5,2).
    if (side == 0 && idx == 0) return { { V{ 11, 5 }, 1, A, -1, 14 } };
    if (side == 0 && idx == 1) return { { V{ 5, 2 }, 0, {}, -1 } };
#elif SCENARIO == 7
    // packs: exact tie. vesper (5,2) and ren (11,2) are mirror images about x=8 for both wolves.
    if (side == 0 && idx == 0) return { { V{ 5, 2 }, 1, A, -1, 14 } };
    if (side == 0 && idx == 1) return { { V{ 11, 2 }, 0, {}, -1 } };
#elif SCENARIO == 8
    // packs: exact tie with the attacker on the right: vesper (11,2) attacks, ren (5,2).
    if (side == 0 && idx == 0) return { { V{ 11, 2 }, 1, A, -1, 14 } };
    if (side == 0 && idx == 1) return { { V{ 5, 2 }, 0, {}, -1 } };
#elif SCENARIO == 9
    // packs: does a non-attacker in range keep the camp awake? ren idles at (11,2) (C3) from the start;
    // vesper hits A from (5,2) at round 14, then walks back to (2,2) out of range and idles.
    if (side == 0 && idx == 0) return { { V{ 5, 2 }, 1, A, 0, 14 }, { V{ 1, 2 }, 0, {}, -1 } };
    if (side == 0 && idx == 1) return { { V{ 11, 2 }, 0, {}, -1 } };
#elif SCENARIO == 10
    // packs: tie where the bystander has the lower id. vesper (id0) idles at (7,1); ren (id1) at (9,1) hits A
    // at round 14. A: both C1; B: both C2.
    if (side == 0 && idx == 0) return { { V{ 7, 1 }, 0, {}, -1 } };
    if (side == 0 && idx == 1) return { { V{ 9, 1 }, 1, A, -1, 14 } };
#elif SCENARIO == 11
    // packs, self-play: team-0 vesper hits A from (5,2) at round 40; team-1 vesper idles at (9,1) (C1 to A,
    // C2 to B) having never damaged the camp. Who is attacked?
    if (side == 0 && idx == 0) return { { V{ 5, 2 }, 1, A, -1, 40 } };
    if (side == 1 && idx == 0) return { { V{ 9, 1 }, 0, {}, -1 } };
#elif SCENARIO == 12
    // packs, self-play: cross-team exact tie, team-0 vesper attacks from (5,2), team-1 vesper idles at (11,2).
    if (side == 0 && idx == 0) return { { V{ 5, 2 }, 1, A, -1, 40 } };
    if (side == 1 && idx == 0) return { { V{ 11, 2 }, 0, {}, -1 } };
#elif SCENARIO == 13
    // packs, self-play: cross-team exact tie, team-1 vesper attacks from (11,2), team-0 vesper idles at (5,2).
    if (side == 0 && idx == 0) return { { V{ 5, 2 }, 0, {}, -1 } };
    if (side == 1 && idx == 0) return { { V{ 11, 2 }, 1, A, -1, 40 } };
#elif SCENARIO == 14
    // packs: strength-0 group (gold 12,18 / 11,17, gems 11,18 / 12,17). vesper hits gold (12,18) from (12,15)
    // every turn; ren idles adjacent at (13,18). Any camp damage?
    if (side == 0 && idx == 0) return { { V{ 12, 15 }, 2, V{ 12, 18 }, -1, 25 } };
    if (side == 0 && idx == 1) return { { V{ 13, 18 }, 0, {}, -1 } };
#elif SCENARIO == 15
    // packs: health vs id tie-break. ren (id1) hits A from (9,1) at round 14 and takes hits alone (vesper waits at
    // (7,0): C2 to A, C3 to B); at round 17 vesper steps to (7,1), tying ren (A: C1 both, B: C2 both).
    if (side == 0 && idx == 0) return { { V{ 7, 0 }, 0, {}, 0, 17 }, { V{ 7, 1 }, 0, {}, -1 } };
    if (side == 0 && idx == 1) return { { V{ 9, 1 }, 1, A, -1, 14 } };
#elif SCENARIO == 16
    // = scenario 7 (exact tie, vesper id0 attacks) with turn priorities reversed (ren scheduled first).
    if (side == 0 && idx == 0) return { { V{ 5, 2 }, 1, A, -1, 14 } };
    if (side == 0 && idx == 1) return { { V{ 11, 2 }, 0, {}, -1 } };
#elif SCENARIO == 17
    // = scenario 10 (tie, ren id1 attacks, vesper bystander) with turn priorities reversed.
    if (side == 0 && idx == 0) return { { V{ 7, 1 }, 0, {}, -1 } };
    if (side == 0 && idx == 1) return { { V{ 9, 1 }, 1, A, -1, 14 } };
#elif SCENARIO == 20
    // elkring: elk (9,2) + gold cluster (10,2) group. vesper hits elk from (6,2) at round 12 and stays.
    if (side == 0 && idx == 0) return { { V{ 6, 2 }, 1, V{ 9, 2 }, -1, 12 } };
#elif SCENARIO == 21
    // elkring: vesper hits only the gold cluster (10,2) from (7,2) (C2 to elk) at round 12. Does the elk wake?
    if (side == 0 && idx == 0) return { { V{ 7, 2 }, 1, V{ 10, 2 }, -1, 12 } };
#elif SCENARIO == 22
    // elkring: does damage keep an un-attended camp awake? vesper hits elk from (6,2) at round 12, steps out to
    // (5,2) (C4) at 13, returns to (6,2) at round K_OUT+13. stellar (5,1) and prism (5,3) (C4 to elk, C5 to gold)
    // cast range-4 damage spells at rounds 13 and 14 respectively (K_OUT>=2). Control: K_OUT=-K disables casts.
    if (side == 0 && idx == 0) return { { V{ 6, 2 }, 1, V{ 9, 2 }, 0, 12 }, { V{ 5, 2 }, 0, {}, 0, 13 }, { V{ 5, 2 }, 0, {}, 0, 13 + (K_OUT < 0 ? -K_OUT : K_OUT) }, { V{ 6, 2 }, 0, {}, -1 } };
    if (K_OUT > 0 && side == 0 && idx == 1) { Step s{ V{ 5, 1 }, 1, V{ 9, 2 }, -1, 13 }; s.cast = true; return { s }; }
    if (K_OUT > 0 && side == 0 && idx == 2) { Step s{ V{ 5, 3 }, 1, V{ 9, 2 }, -1, 14 }; s.cast = true; return { s }; }
#elif SCENARIO == 23
    // elkring: does spell damage wake a sleeping camp? vesper idles at (6,2) (C3 to elk) never attacking;
    // stellar casts its range-4 damage spell on the elk from (5,1) at round 14.
    if (side == 0 && idx == 0) return { { V{ 6, 2 }, 0, {}, -1 } };
    if (side == 0 && idx == 1) { Step s{ V{ 5, 1 }, 1, V{ 9, 2 }, -1, 14 }; s.cast = true; return { s }; }
#elif SCENARIO == 24
    // lanes: bush test. vesper stands in the bush row at (43,9) (C2 to single wolf (43,11)) and hits it at
    // round 50, then idles there. Does the wolf attack a champion hidden in a bush?
    if (side == 0 && idx == 0) return { { V{ 43, 9 }, 1, V{ 43, 11 }, -1, 50 } };
    if (side == 0 && idx >= 1 && idx <= 3) return { { V{ 2 + idx, 17 }, 0, {}, -1 } };
#elif SCENARIO == 30
    // monolith map: monolith (1,1) in a group with 8 gem clusters. vesper hits it from (4,4) (C3; C2 to gem 2,2)
    // at round 60, then steps east one tile per round to (5,4) C4, (6,4) C5, (7,4) C6. Monolith range?
    if (side == 0 && idx == 0) return { { V{ 4, 4 }, 1, V{ 1, 1 }, 0, 60 }, { V{ 5, 4 }, 0, {}, 0, 61 }, { V{ 6, 4 }, 0, {}, 0, 62 }, { V{ 7, 4 }, 0, {}, -1 } };
#endif
#if SCENARIO >= 20 && SCENARIO < 30
    // elkring: park unscripted champions off the 3x3 spawn (out of every camp's range) so others can leave.
    if (side == 0 && idx >= 1 && idx <= 3) return { { V{ 2 + idx, 0 }, 0, {}, -1 } };
#endif
#if SCENARIO == 30
    if (side == 0 && idx >= 1 && idx <= 3) return { { V{ 5 + idx, 43 }, 0, {}, -1 } };
#endif
    return {};
}
