"""Run a tools/replay/harness script (or import the harness) with an extra version "v118b": bots/baselines/v118's
source (the masked upload) with its own data directory replays/v118b, without editing the shared versions.py.

    py research/ideas-2026-11-12/v118-fish-b/h.py batch.py --version v118b --jobs 16 ...
    import h; h.register()        # then `import v38lib as L; L.use("v118b")`
"""
import runpy, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HARNESS = REPO / "tools/replay/harness"
NAME = "v118b"


def register():
    if str(HARNESS) not in sys.path:
        sys.path.insert(0, str(HARNESS))
    import versions
    versions.VERSIONS[NAME] = {"commit": None, "src": str(REPO / "bots/baselines/v118/src"), "bot": "bots/ocean",
                               "dir": f"replays/{NAME}", "live": True, "manifest": f"replays/{NAME}/manifest.json",
                               "trace_bot": f"replays/{NAME}/trace-bot"}
    init = versions.Version.__init__

    def patched(self, name):
        if name != NAME:
            return init(self, name)
        # Version.__init__ parses the number from the name; v118b is submission 118.
        versions.VERSIONS["v118000"] = versions.VERSIONS[NAME]
        init(self, "v118000")
        del versions.VERSIONS["v118000"]
        v = versions.VERSIONS[NAME]
        self.name, self.number = NAME, 118
        self.release = self.ws / "bots" / f"{NAME}-release"
        self.rec = self.ws / "bots" / f"{NAME}-rec"
        self.slot_prefix = f"{NAME}-trace-s"

    versions.Version.__init__ = patched
    return versions


if __name__ == "__main__":
    register()
    script = HARNESS / sys.argv[1]
    sys.argv = [str(script)] + sys.argv[2:]
    runpy.run_path(str(script), run_name="__main__")
