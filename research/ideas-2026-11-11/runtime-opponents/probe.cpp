#include <cstdint>
extern "C" __attribute__((import_module("env"), import_name("experiment_config"))) std::uint64_t config(std::uint32_t);
extern "C" __attribute__((import_module("env"), import_name("fuel_remaining"))) std::int64_t fuel_remaining();
volatile std::uint64_t work = 0;
int main() {
    if (config(0) == 99) for (;;) work = work + 1;
    if (config(0) == 98 && fuel_remaining() != INT64_MAX) __builtin_trap();
    return 0;
}
