"""The submissions the replay harness can re-run: commit, bot, workspace and trace bot per version.

Every pipeline script takes `--version NAME` (default v38) and the loader `v38lib.use(NAME)`.
Generated data goes under `dir` (gitignored): ws/, inputs/, runs/batch/, extract/.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DEFAULT = "v38"

VERSIONS = {
    # The 830 games against 2026-10-22's top 20; the committed manifest.
    "v38": {"commit": "5b02a02", "bot": "bots/hyperion", "dir": "replays/v38-top20",
            "manifest": "tools/replay/harness/manifest.json", "trace_bot": "tools/replay/harness/trace-bot"},
    # Ladder submission 47 (live 2026-10-24T05:29Z). Its manifest is built from the replay folders by
    # build_manifest.py, since the set grows as games are downloaded.
    "v47": {"commit": "f7d54e9e", "bot": "bots/astraeus", "dir": "replays/v47",
            "manifest": "replays/v47/manifest.json", "trace_bot": "tools/replay/harness/trace-bot-v47",
            "since": "2026-10-24T05:17:00Z"},
    # Submission 66 (bots/baselines/v66 = astraeus at 4a7c25f6), engine 2.0.0 and cambc 4.0.0: the 610
    # unranked games of replays/v66-farm against four opponents.
    "v66": {"commit": "4a7c25f6", "bot": "bots/astraeus", "dir": "replays/v66",
            "manifest": "replays/v66/manifest.json", "trace_bot": "tools/replay/harness/trace-bot-v66",
            "folders": ["replays/v66-farm/*"]},
}


class Version:
    def __init__(self, name):
        if name not in VERSIONS:
            raise SystemExit(f"unknown version {name}; one of {', '.join(VERSIONS)}")
        v = VERSIONS[name]
        self.name = name
        self.number = int(name.lstrip("v"))
        self.commit = v["commit"]
        self.bot = v["bot"]
        self.dir = REPO / v["dir"]
        self.manifest = REPO / v["manifest"]
        self.trace_bot = REPO / v["trace_bot"]
        self.ws = self.dir / "ws"
        self.batch = self.dir / "runs" / "batch"
        self.inputs = self.dir / "inputs" / "ladder"
        self.extract = self.dir / "extract"
        self.release = self.ws / "bots" / f"{name}-release"
        self.rec = self.ws / "bots" / f"{name}-rec"
        self.slot_prefix = f"{name}-trace-s"
        self.folders = v.get("folders")


def get(name=None):
    return Version(name or DEFAULT)


def add_arg(ap):
    ap.add_argument("--version", default=DEFAULT, choices=list(VERSIONS), help="the submission to work on (default %(default)s)")
