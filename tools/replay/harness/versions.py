"""The live submissions the replay harness can re-run: source, bot, data directory and trace bot per version.

Every pipeline script takes `--version NAME` (default: the newest version found).
Generated data goes under `dir` (gitignored): ws/, inputs/, runs/batch/, extract/.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
VERSIONS = {}

# Live versions (v87 on) are rebuilt from the scheduler's frozen build workspace: `src` is the source exactly as
# uploaded. The scheduler's gates.jsonl names each version's workspace (a label can have
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
        rec = json.loads(line); e = rec.get("entry") or {}
        if e.get("workspace") and e.get("version") is not None:
            seen.setdefault(e["version"], set()).add(e["workspace"])
        elif rec.get("version") is not None and rec.get("label") and not e:
            # A batch-mode record (live_batches.py) names no workspace: its label's one build dir, if exactly one.
            ws = [str(d) for d in (SCHED / "build").glob(f'{rec["label"]}-[0-9]*') if d.is_dir()]
            if len(ws) == 1: seen.setdefault(rec["version"], set()).add(ws[0])
    for num, wss in sorted(seen.items()):
        src = Path(next(iter(wss))) / "bots/ocean/src"
        if len(wss) > 1 or not src.is_dir():
            continue  # an ambiguous record is left out rather than guessed
        VERSIONS[f"v{num}"] = {"src": str(src), "bot": "bots/ocean", "dir": f"replays/v{num}",
                               "manifest": f"replays/v{num}/manifest.json", "trace_bot": f"replays/v{num}/trace-bot"}


_live_versions()


def _baseline_versions():
    # A live upload frozen in bots/baselines/v<N> (its masked source, model/prio_stream.h included) before the scheduler
    # has written its gates.jsonl record. A gates.jsonl row wins: its workspace is the one uploaded.
    for d in sorted((REPO / "bots/baselines").glob("v[0-9]*")):
        if d.name not in VERSIONS and (d / "src/model/prio_stream.h").is_file():
            VERSIONS[d.name] = {"src": str(d / "src"), "bot": "bots/ocean", "dir": f"replays/{d.name}",
                                "manifest": f"replays/{d.name}/manifest.json", "trace_bot": f"replays/{d.name}/trace-bot"}


_baseline_versions()
VERSIONS = dict(sorted(VERSIONS.items(), key=lambda kv: int(kv[0].lstrip("v"))))
DEFAULT = next(reversed(VERSIONS), None)

class Version:
    def __init__(self, name):
        if name not in VERSIONS:
            raise SystemExit(f"unknown version {name}; one of {', '.join(VERSIONS) or 'none (no scheduler gates.jsonl or bots/baselines/v<N>)'}")
        v = VERSIONS[name]
        self.name = name
        self.number = int(name.lstrip("v"))
        self.src = Path(v["src"])
        self.bot = v["bot"]
        self.dir = REPO / v["dir"]
        self.manifest = REPO / v["manifest"]
        self.trace_bot = REPO / v["trace_bot"]
        self.ws = self.dir / "ws"
        self.batch = self.dir / "runs" / "batch"
        self.inputs = self.dir / "inputs" / "ladder"
        self.extract = self.dir / "extract"
        self.release = self.ws / "bots" / f"{name}-release"
        self.direct = self.dir / "runs" / "direct"


def get(name=None):
    return Version(name or DEFAULT)


def add_arg(ap):
    ap.add_argument("--version", default=DEFAULT, required=DEFAULT is None, choices=list(VERSIONS),
                    help="the submission to work on (default %(default)s, the newest)")
