"""Lay out a run_batched batch for tools/fuel/census/census.py, one bot only: symlinks DIR/<game>-<side>/x.repl26a
with the side bot N played (-12: bot 1 is team A).

    python3 split_sides.py BATCH OUT BOT   # BOT 1 or 2
"""
import sys
from pathlib import Path

batch, out, bot = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
for p in batch.glob("*.repl26a"):
    tag = p.stem.rsplit("-", 1)[1]
    side = "a" if (tag == "12") == (bot == 1) else "b"
    d = out / f"{p.stem}-{side}"
    d.mkdir(parents=True, exist_ok=True)
    (d / p.name).unlink(missing_ok=True)
    (d / p.name).symlink_to(p.resolve())
