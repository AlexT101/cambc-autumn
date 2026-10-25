// probe-suspend-memory: what shared memory a turn that runs out of fuel sees and writes.
// Run at the default fuel (the suspender must run out):
//   cambc run tools/probes/probe-suspend-memory tools/probes/probe-suspend-memory --map 00ambush --rounds 20 -o DIR
// The ally with the lowest id is S (suspends), the next is R (acts after S each round). Each logs
// "PROBE <engine round> <S|R> <what> smem=b0,..,b7" (team-a.stdout). Bytes:
//   r3  S writes b7=17 (control: R should see it in r3)
//   r4  S prints the fuel price of an 8-byte read, write, round_number() and fuel_remaining()
//   r5  S writes b0=165, runs out, resumes in r6, reads, writes b1=182; R writes b3=199 in r5
//   r10 S runs out without writing, resumes in r11, reads, writes nothing; R writes b4=216 in r10
//   r15 S runs out without writing, resumes in r16, writes b5=233; R writes b6=250 in r15
#include <cambc.h>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <vector>

static void log(const char* who, const char* what) {
    std::uint8_t m[8];
    cambc::shared_memory.read(0, std::span{m, 8});
    std::printf("PROBE %u %s %s smem=%d,%d,%d,%d,%d,%d,%d,%d\n", cambc::round_number(), who, what, m[0], m[1], m[2], m[3],
                m[4], m[5], m[6], m[7]);
}

static void put(int at, int v) { cambc::shared_memory[at] = static_cast<std::uint8_t>(v); }

static void burn() {
    const auto r0 = cambc::round_number();
    volatile std::uint64_t x = 0;
    for (std::uint64_t i = 0;; ++i) {
        x = x * 6364136223846793005ULL + 1;
        if (i % 256 == 0 && cambc::round_number() != r0) return;
    }
}

static void play() {
    auto& me = cambc::self();
    std::vector<unsigned> ids;
    for (auto& c : cambc::champions(cambc::team::ally)) ids.push_back(static_cast<unsigned>(static_cast<cambc::handle_champion_t>(c)));
    std::sort(ids.begin(), ids.end());
    const unsigned id = static_cast<unsigned>(static_cast<cambc::handle_champion_t>(me));
    const int k = static_cast<int>(std::find(ids.begin(), ids.end(), id) - ids.begin());
    if (k > 1) return;
    const char* who = k == 0 ? "S" : "R";
    const auto r = cambc::round_number();
    log(who, "start");
    if (k == 0) {
        if (r == 3) put(7, 17), log(who, "wrote_b7");
        if (r == 4) {
            // Host prices: an 8-byte read and write, and round_number().
            std::uint64_t w = 0;
            const auto f0 = cambc::detail::sdk_fuel_remaining();
            cambc::detail::sdk_read_shared_memory(0, &w, sizeof w);
            const auto f1 = cambc::detail::sdk_fuel_remaining();
            cambc::detail::sdk_write_shared_memory(0, &w, sizeof w);
            const auto f2 = cambc::detail::sdk_fuel_remaining();
            std::uint32_t rr = 0;
            cambc::detail::sdk_bc_round_number(&rr);
            const auto f3 = cambc::detail::sdk_fuel_remaining();
            cambc::detail::sdk_fuel_remaining();
            const auto f4 = cambc::detail::sdk_fuel_remaining();
            std::printf("PROBE 4 S cost read=%lld write=%lld round=%lld fuel_call=%lld\n", (long long)(f0 - f1), (long long)(f1 - f2), (long long)(f2 - f3), (long long)(f3 - f4));
        }
        if (r == 5 || r == 10 || r == 15) {
            if (r == 5) put(0, 165), log(who, "wrote_b0");
            burn();
            log(who, "resumed");
            if (r == 5) put(1, 182), log(who, "wrote_b1");
            if (r == 15) put(5, 233), log(who, "wrote_b5");
        }
    } else {
        if (r == 5) put(3, 199), log(who, "wrote_b3");
        if (r == 10) put(4, 216), log(who, "wrote_b4");
        if (r == 15) put(6, 250), log(who, "wrote_b6");
    }
}

int main() {
    while (true) {
        if (!cambc::is_draft()) {
            try {
                play();
            } catch (const cambc::error&) {
                std::printf("PROBE error\n");
            }
        }
        cambc::end_turn();
    }
}
