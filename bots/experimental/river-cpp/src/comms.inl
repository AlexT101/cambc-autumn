// Function bodies; src/unity.cpp includes this after every header.

namespace comms {
void Coder::symbol(int ctx, int s)
{
        const auto q = range >> frequency_bits;
        if (q == 0) {
            ok = false;
            return;
        }
        low += q * static_cast<std::uint64_t>(cumulative(ctx, s));
        range = q * static_cast<std::uint64_t>(frequency(ctx, s));
    }

int Coder::read_symbol(std::uint64_t word, int ctx)
{
        const auto q = range >> frequency_bits;
        if (q == 0) {
            ok = false;
            return stay;
        }
        const auto v = (word - low) / q;
        const int t = v < (1u << frequency_bits) ? static_cast<int>(v) : (1 << frequency_bits) - 1;
        const auto& c = cumulative_table[ctx];
        // The last of the 10 entries at or below t (c[0] is 0): stay, the likeliest, first.
        int s = 0;
        if (t >= c[1])
            for (int step = 8; step > 0; step >>= 1)
                if (s + step <= 9 && t >= c[s + step]) s += step;
        int f = frequency_table[ctx][s], at = c[s];
        if (s == 9) {
            const int u = (t - at) / f;
            if (u < dashes) s += u, at += u * f;
            else if (u < dashes + arrival_weight) s = arrival_symbol, at += dashes * f, f *= arrival_weight;
            else {
                const int k = std::min(u - dashes - arrival_weight, symbol_count - arrival_symbol - 2);
                s = arrival_symbol + 1 + k, at += (dashes + arrival_weight + k) * f;
            }
        }
        low += q * static_cast<std::uint64_t>(at);
        range = q * static_cast<std::uint64_t>(f);
        return s;
    }

void Coder::field(std::uint64_t f, std::uint64_t c, std::uint64_t n)
{
        const auto q = range / n;
        if (q == 0) {
            ok = false;
            return;
        }
        low += q * c, range = q * f;
    }

std::uint64_t Coder::peek(std::uint64_t word, std::uint64_t n)
{
        const auto q = range / n;
        if (q == 0) {
            ok = false;
            return 0;
        }
        const auto v = (word - low) / q;
        return v < n ? v : n - 1;
    }

int Coder::read_field(std::uint64_t word, int n)
{
        const int v = static_cast<int>(peek(word, static_cast<std::uint64_t>(n)));
        field(1, static_cast<std::uint64_t>(v), static_cast<std::uint64_t>(n));
        return v;
    }

int Coder::bits() const
{ return 64 - (63 - __builtin_clzll(range)); }

int History::context() const
{ return c1 * 10 + c2; }

void History::read(const Slot& s)
{
        if (s.mode == window_mode || s.mode == absolute_mode) c1 = 9, c2 = 0;
        else if (s.mode == single_mode) c2 = c1, c1 = symbol_class(s.a);
    }

void Fields::put(Coder& c) const
{
        for (int k = 0; k < n; ++k) c.field(v[k][0], v[k][1], v[k][2]);
    }

}
