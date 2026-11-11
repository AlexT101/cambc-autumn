"""The submissions the replay harness can re-run: commit, bot, workspace and trace bot per version.

Every pipeline script takes `--version NAME` (default v38) and the loader `v38lib.use(NAME)`.
Generated data goes under `dir` (gitignored): ws/, inputs/, runs/batch/, extract/.
"""
import json
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
    # Submission 66 (astraeus at 4a7c25f6), engine 2.0.0 and cambc 4.0.0: the 610
    # unranked games of replays/v66-farm against four opponents.
    "v66": {"commit": "4a7c25f6", "bot": "bots/astraeus", "dir": "replays/v66",
            "manifest": "replays/v66/manifest.json", "trace_bot": "tools/replay/harness/trace-bot-v66",
            "folders": ["replays/v66-farm/*"]},
}

# Live versions (v87 on) are rebuilt from the scheduler's frozen build workspace rather than a commit: `src` is the
# masked source exactly as uploaded. The scheduler's gates.jsonl names each version's workspace (a label can have
# several), so every version it lists is registered here; batch.py's release re-runs then prove the attribution. Their
# games ran on cambc 5.0.1 and come from the scrim log (scrim_manifest.py). pipeline.py runs the live chain for them.
SCHED = Path.home() / "tmp-offload/handoff/sched"


def _live_versions():
    seen = {}
    try:
        lines = (SCHED / "gates.jsonl").read_text().splitlines()
    except OSError:
        return
    for line in lines:
        e = json.loads(line).get("entry") or {}
        if e.get("workspace") and e.get("version") is not None:
            seen.setdefault(e["version"], set()).add(e["workspace"])
    for num, wss in sorted(seen.items()):
        src = Path(next(iter(wss))) / "bots/ocean/src"
        if len(wss) > 1 or f"v{num}" in VERSIONS or not src.is_dir():
            continue  # an ambiguous record is left out rather than guessed
        VERSIONS[f"v{num}"] = {"commit": None, "src": str(src), "bot": "bots/ocean", "dir": f"replays/v{num}", "live": True,
                               "manifest": f"replays/v{num}/manifest.json", "trace_bot": f"replays/v{num}/trace-bot"}


_live_versions()

class Version:
    def __init__(self, name):
        if name not in VERSIONS:
            raise SystemExit(f"unknown version {name}; one of {', '.join(VERSIONS)}")
        v = VERSIONS[name]
        self.name = name
        self.number = int(name.lstrip("v"))
        self.commit = v["commit"]
        self.src = Path(v["src"]) if v.get("src") else None
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
        self.live = bool(v.get("live"))
        self.direct = self.dir / "runs" / "direct"


def get(name=None):
    return Version(name or DEFAULT)


def add_arg(ap):
    ap.add_argument("--version", default=DEFAULT, choices=list(VERSIONS), help="the submission to work on (default %(default)s)")
