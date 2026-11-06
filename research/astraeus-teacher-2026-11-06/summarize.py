"""Audit both teams' runtime logs and teacher fuel in a completed teacher A/B batch."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import struct
import zipfile


def inspect(match):
    result = {"teacher": {}, "opponent": {}}
    with zipfile.ZipFile(match["replay"]) as z:
        for role, bot in (("teacher", 0), ("opponent", 1)):
            side = "ab"[match["order"].index(bot)]
            log = z.read(f"team-{side}.stdout").replace(b"\0", b"")
            errors = re.findall(rb"^.*(?:error:|SRCH-LEAVES-FULL|DRAFT-BAD).*", log, re.M)
            shortcuts = Counter(m.decode() for m in re.findall(rb"SHORTCUT \d+ \d+ ([^\s]+)", log))
            result[role] = {"errors": [e.decode(errors="replace") for e in errors[:5]],
                            "shortcuts": shortcuts, "stdout_capped": len(log) >= 1 << 20}
            if role == "teacher":
                fuel = z.read(f"team-{side}.fuel")[77:]
                values = [v[0] for v in struct.iter_unpack("<Q", fuel)]
                result[role]["max_fuel"] = max(values, default=0)
                result[role]["turns"] = len(values)
                result[role]["over_100k"] = sum(v > 100_000 for v in values)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    matches = json.loads((args.batch / "results.json").read_text())["matches"]
    out = {role: {"error_games": [], "shortcuts": Counter(), "stdout_capped_games": 0}
           for role in ("teacher", "opponent")}
    out["teacher"].update(max_fuel=0, turns=0, over_100k=0)
    with ThreadPoolExecutor(4) as pool:
        for index, (match, row) in enumerate(zip(matches, pool.map(inspect, matches)), 1):
            if index % 1000 == 0:
                print(f"Audited {index}/{len(matches)} games", flush=True)
            for role in out:
                total, game = out[role], row[role]
                if game["errors"]:
                    total["error_games"].append({"replay": match["replay"], "errors": game["errors"]})
                total["shortcuts"].update(game["shortcuts"])
                total["stdout_capped_games"] += game["stdout_capped"]
                if role == "teacher":
                    total["max_fuel"] = max(total["max_fuel"], game["max_fuel"])
                    total["turns"] += game["turns"]
                    total["over_100k"] += game["over_100k"]
    out["games"] = len(matches)
    out["fuel_scope"] = "all recorded turns, including drafts and first champion turns"
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
