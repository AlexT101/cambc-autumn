"""Patched copies of a tunified bot (research/diana-2026-11-03/tunify.py) with no compile: the tune block is
rewritten in the built wasm and in the fast runner's cached native library and wasmtime module for that wasm,
which hold the wasm's data segment verbatim, saved under the patched wasm's cache keys."""
import json, os, struct
from pathlib import Path

CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "fastrunner"


def fnv_state(b: bytes, start=0, state=(0xcbf29ce484222325, 0x84222325cbf29ce4)):
    """The two lanes of tools/fastengine/runner/src/runtime.rs fnv128 after b, from `state` at offset `start`."""
    M = (1 << 64) - 1
    a, c = state
    for i, x in enumerate(b, start):
        a = ((a ^ x) * 0x100000001b3) & M
        c = ((c ^ ((x + i) & M)) * 0x100000001b3) & M
    return a, c


def fnv128(b: bytes) -> int:
    a, c = fnv_state(b)
    return ((a << 64) | c) ^ len(b)


def forget(h: str):
    """Deletes a patched candidate's cached native library and wasmtime module (the base's stay)."""
    for p in list((CACHE / "native").glob(h + "-*.so")) + list((CACHE / "modules").glob(h + "*.cwasm")):
        p.unlink(missing_ok=True)


class Base:
    """A built bot directory (release or debug build) with src/tune.json."""

    def __init__(self, bot: Path, release=True):
        self.bot = Path(bot)
        self.spec = json.loads((self.bot / "src" / "tune.json").read_text())
        self.sub = "build-release" if release else "build"
        self.wasm = (self.bot / ".cambc" / self.sub / "bot-injected.wasm").read_bytes()
        self.at = self._find(self.wasm, "wasm")
        # Candidates differ only from the block on: hash the shared prefix once.
        self.prefix = fnv_state(self.wasm[:self.at])
        self.hash = self._hash(self.wasm)
        self.cached = {}
        for p in list((CACHE / "native").glob(self.hash + "-*.so")) + list((CACHE / "modules").glob(self.hash + "*.cwasm")):
            b = p.read_bytes()
            self.cached[p.name[len(self.hash):]] = (p.parent, b, self._find(b, p.name))

    def _find(self, b, what):
        m = self.spec["magic"].encode() + b"\0"
        if b.count(m) != 1:
            raise ValueError(f"{what}: tune magic found {b.count(m)} times")
        return b.index(m) + 16

    def _hash(self, w):
        a, c = fnv_state(w[self.at:], self.at, self.prefix)
        return f"{((a << 64) | c) ^ len(w):032x}"

    def defaults(self):
        return {n: v for n, v in self.spec["floats"] + self.spec["ints"]}

    def block(self, values):
        f = [float(values.get(n, d)) for n, d in self.spec["floats"]]
        i = [int(round(values.get(n, d))) for n, d in self.spec["ints"]]
        return struct.pack(f"<{len(f)}f{len(i)}i", *f, *i)

    def write(self, values, out: Path):
        """A bot directory at `out` playing `values` (name -> value; missing names keep defaults); returns (out,
        the patched wasm's cache hash)."""
        blk = self.block(values)
        w = bytearray(self.wasm)
        w[self.at:self.at + len(blk)] = blk
        d = Path(out) / ".cambc" / self.sub
        d.mkdir(parents=True, exist_ok=True)
        (d / "bot-injected.wasm").write_bytes(w)
        h = self._hash(bytes(w))
        for suffix, (folder, b, at) in self.cached.items():
            dst = folder / (h + suffix)
            if dst.exists():
                continue
            c = bytearray(b)
            c[at:at + len(blk)] = blk
            tmp = folder / f".{h}{suffix}.{os.getpid()}.tmp"
            tmp.write_bytes(c)
            os.chmod(tmp, 0o775)
            tmp.rename(dst)
        return Path(out), h
