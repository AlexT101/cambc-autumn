// Native check of the bot's token function against the offline one: reads
// "v n rank res0 tank hp max_hp shield gems" lines, prints one token per line.
#include <cstdio>

#include "opp_token.h"

int main() {
    long long v;
    int n, rank, res0, tank, gems;
    double hp, max_hp, shield;
    while (std::scanf("%lld %d %d %d %d %lf %lf %lf %d", &v, &n, &rank, &res0, &tank, &hp, &max_hp, &shield, &gems) == 9)
        std::printf("%d\n", static_cast<int>(aph::opp::token(static_cast<int>(v), n, rank, res0, tank != 0, hp, max_hp, shield, gems)));
}
