// Function bodies; src/unity.cpp includes this after every header.

namespace aph {
int Field::at(vec2 p) const
{ return steps_at(steps, p); }

FuelMeter::FuelMeter(const char* label) : label_{label}
{
        if constexpr (debug_fuel) {
            start_ = fuel();
            round_ = cambc::round_number();
        }
    }

FuelMeter::~FuelMeter()
{
        if constexpr (debug_fuel) {
            const auto now = fuel();
            const bool spilled = cambc::round_number() != round_;
            fuel_log().push_back({label_, round_, spilled ? 0 : start_ - now, spilled});
        }
    }

}
