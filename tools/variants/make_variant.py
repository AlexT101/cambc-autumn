"""Copy a bot to bots/variants/<name>/ with a forced draft compiled into its draft_preference array.

    py tools/variants/make_variant.py varg,willow,ryth,stellar,tavi
    py tools/variants/make_variant.py tavi --source baselines/v0 --name v0-tavi

Names are enum names from sdk/cpp/cambc.h or unique prefixes (vesper, cassi). Drafts shorter
than 5 are padded with the unused champions in enum order (the bots' own fallback order), since
maps set 3-5 picks; the variant name then ends in -pad and manifest.json records both lists.
Rerunning rewrites only changed files, so the variant's build cache stays incremental."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
VARIANTS = ROOT / "bots" / "variants"
HEADER = ROOT / "sdk" / "cpp" / "cambc.h"
MAX_PICKS = 5
COPIED = (".clangd", ".gitignore")
ARRAY = re.compile(r"(\bdraft_preference\s*\[\s*\]\s*=\s*\{)(.*?)(\};)", re.S)


def champions():
    """champion_draft enumerators in value order."""
    body = re.search(r"enum class champion_draft\b[^{]*\{(.*?)\};", HEADER.read_text(encoding="utf-8"), re.S)
    if not body:
        raise ValueError(f"champion_draft enum not found in {HEADER}")
    text = re.sub(r"//[^\n]*", "", body.group(1))
    names = [re.match(r"\s*(\w+)", item).group(1) for item in text.split(",") if item.strip()]
    return names


def short(name):
    return name[:4]


def resolve(token, names):
    token = token.strip().lower().replace("-", "_")
    if token in names:
        return token
    matches = [n for n in names if n.startswith(token)]
    if len(matches) != 1:
        raise ValueError(f"Unknown or ambiguous champion {token!r}; choose from {', '.join(names)}")
    return matches[0]


def parse_draft(text):
    names = champions()
    draft = [resolve(t, names) for t in (text.split(",") if isinstance(text, str) else text) if t.strip()]
    if not draft:
        raise ValueError("Empty draft")
    if len(set(draft)) != len(draft):
        raise ValueError(f"Draft repeats a champion: {','.join(draft)}")
    return draft


def padded(draft):
    return draft + [n for n in champions() if n not in draft][:max(0, MAX_PICKS - len(draft))]


def bot_dir(value):
    for path in (Path(value), ROOT / "bots" / value):
        if (path / "src").is_dir():
            return path.resolve()
    raise ValueError(f"Bot not found: {value}")


def default_name(source, draft):
    return "-".join([source.name, *map(short, draft)]) + ("-pad" if len(draft) < MAX_PICKS else "")


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def source_state(source):
    digest = hashlib.sha256()
    for path in sorted((source / "src").rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(source).as_posix().encode() + b"\0" + path.read_bytes())
    try:
        rel = source.relative_to(ROOT).as_posix()
    except ValueError:
        rel = None
    status = git("status", "--porcelain", "--untracked-files=all", "--", rel) if rel else None
    return {"source": rel or source.as_posix(), "git_commit": git("rev-parse", "HEAD"),
            "git_dirty": None if status is None else bool(status),
            "git_untracked": None if status is None else bool(status) and all(
                line.startswith("??") for line in status.splitlines()),
            "src_sha256": digest.hexdigest()}


def replace_draft(files, draft):
    hits = [(path, m) for path, text in files.items() for m in [ARRAY.search(text)] if m]
    if len(hits) != 1:
        where = ", ".join(p for p, _ in hits) or "no file"
        raise ValueError(f"Expected one draft_preference array definition, found it in {where}")
    path, match = hits[0]
    body = "".join(f"\n    cambc::champion_draft::{name}," for name in draft) + "\n"
    text = files[path]
    files[path] = text[:match.start(2)] + body + text[match.end(2):]
    return path


def write_if_changed(path, data):
    if path.is_file() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


def make_variant(source="aphelios", draft=None, name=None):
    """Create or refresh the variant; return (directory, manifest)."""
    source = bot_dir(source)
    given = parse_draft(draft)
    full = padded(given)
    name = name or default_name(source, given)
    if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        raise ValueError(f"Variant names may only use letters, digits, '.', '_' and '-': {name!r}")
    target = VARIANTS / name
    if target.resolve() == source:
        raise ValueError("Source and variant are the same directory")

    texts = {}
    blobs = {}
    for path in (source / "src").rglob("*"):
        if path.is_file():
            rel = path.relative_to(source).as_posix()
            if path.suffix in (".h", ".hpp", ".cpp", ".cc"):
                texts[rel] = path.read_bytes().decode("utf-8")
            else:
                blobs[rel] = path.read_bytes()
    edited = replace_draft(texts, full)
    for rel, text in texts.items():
        blobs[rel] = text.encode("utf-8")
    for rel in COPIED:
        if (source / rel).is_file():
            blobs[rel] = (source / rel).read_bytes()

    changed = [rel for rel, data in sorted(blobs.items()) if write_if_changed(target / rel, data)]
    for path in sorted((target / "src").rglob("*"), reverse=True):
        rel = path.relative_to(target).as_posix()
        if path.is_file() and rel not in blobs:
            path.unlink()
            changed.append(rel)
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()

    manifest = {"name": name, **source_state(source), "draft": full, "given": given,
                "padded": full[len(given):], "edited": edited}
    old = target / "manifest.json"
    previous = json.loads(old.read_text(encoding="utf-8")) if old.is_file() else None
    if previous and previous.get("source") != manifest["source"]:
        print(f"warning: {name} was made from {previous.get('source')}; now from {manifest['source']}",
              file=sys.stderr)
    write_if_changed(old, (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    return target, manifest, changed


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("draft", help="Comma-separated champions in pick order, e.g. varg,willow,ryth")
    parser.add_argument("--source", default="aphelios", help="Bot name under bots/, or a path (default: aphelios)")
    parser.add_argument("--name", help="Variant directory name (default: <source>-<champions>[-pad])")
    args = parser.parse_args()
    try:
        target, manifest, changed = make_variant(args.source, args.draft, args.name)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    pad = f" (padded with {','.join(manifest['padded'])})" if manifest["padded"] else ""
    print(f"{target.relative_to(ROOT).as_posix()}: {','.join(manifest['draft'])}{pad}; "
          f"{len(changed)} file(s) written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
