"""Splice wa_memo_new.txt over farm.cc's WorkArrival struct and work_arrival lambda."""
from pathlib import Path

here = Path(__file__).resolve().parent
p = here.parents[1] / "bots/astraeus/src/economy/farm.cc"
s = p.read_text()
start = s.index("    struct WorkArrival {")
tail = "        arrival.earliest = std::min(arrival.direct, arrival.recall_route);\n        return arrival;\n    };\n"
end = s.index(tail) + len(tail)
s = s[:start] + (here / "wa_memo_new.txt").read_text() + s[end:]
p.write_text(s)
