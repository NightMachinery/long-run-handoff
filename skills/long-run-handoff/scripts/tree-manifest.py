#!/usr/bin/env python3
"""Snapshot and compare a flat inventory without modifying the inspected tree."""

import argparse
import datetime
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys


FORMAT_VERSION = 1
TOOL_VERSION = "1.0"
DEFAULT_EXCLUDES = (".git", "__pycache__")


def root_hash(entries):
    digest = hashlib.sha256()
    for entry in sorted(entries, key=lambda item: item["path"]):
        line = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        digest.update((line + "\n").encode("utf-8"))
    return digest.hexdigest()


def excluded(relative, patterns):
    parts = PurePosixPath(relative).parts
    return any(
        any(fnmatch.fnmatchcase(part, pattern) for part in parts)
        if "/" not in pattern
        else fnmatch.fnmatchcase(relative, pattern)
        or fnmatch.fnmatchcase(relative + "/", pattern)
        for pattern in patterns
    )


def file_entry(path, relative):
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"not a regular file: {relative}")
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
        after = os.fstat(stream.fileno())
    current = path.lstat()
    identity = lambda info: (
        info.st_dev, info.st_ino, info.st_size, info.st_mode,
        info.st_mtime_ns, info.st_ctime_ns,
    )
    if (identity(before) != identity(after)
            or identity(after) != identity(current) or size != after.st_size):
        raise OSError(f"file changed while hashing: {relative}")
    return {
        "path": relative,
        "type": "file",
        "sha256": digest.hexdigest(),
        "size": size,
        "executable": bool(before.st_mode & 0o111),
    }


def inventory(base, patterns):
    entries = []
    pending = [base]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as children:
            for child in children:
                path = Path(child.path)
                relative = path.relative_to(base).as_posix()
                if excluded(relative, patterns):
                    continue
                mode = child.stat(follow_symlinks=False).st_mode
                if stat.S_ISLNK(mode):
                    entries.append({"path": relative, "type": "symlink", "target": os.readlink(path)})
                elif stat.S_ISDIR(mode):
                    pending.append(path)
                elif stat.S_ISREG(mode):
                    entries.append(file_entry(path, relative))
                else:
                    raise ValueError(f"unsupported file type: {relative}")
    return sorted(entries, key=lambda item: item["path"])


def read_manifest(path):
    with path.open(encoding="utf-8") as stream:
        manifest = json.load(stream)
    if (not isinstance(manifest, dict)
            or type(manifest.get("format_version")) is not int
            or manifest["format_version"] != FORMAT_VERSION):
        raise ValueError("unsupported manifest format")
    for name in ("tool_version", "base_dir", "created_at"):
        if not isinstance(manifest.get(name), str):
            raise ValueError(f"invalid manifest {name}")
    patterns = manifest.get("excludes")
    entries = manifest.get("entries")
    if (not isinstance(patterns, list)
            or any(not isinstance(item, str) or not item for item in patterns)):
        raise ValueError("invalid manifest excludes")
    if not isinstance(entries, list):
        raise ValueError("invalid manifest entries")
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("invalid manifest entry")
        relative = entry.get("path")
        if (not isinstance(relative, str) or not relative or "\x00" in relative
                or relative.startswith("/")
                or any(part in ("", ".", "..") for part in relative.split("/"))
                or relative in seen):
            raise ValueError("invalid or duplicate manifest path")
        seen.add(relative)
        if entry.get("type") == "file":
            digest = entry.get("sha256")
            valid = (
                set(entry) == {"path", "type", "sha256", "size", "executable"}
                and isinstance(digest, str) and len(digest) == 64
                and all(character in "0123456789abcdef" for character in digest)
                and type(entry.get("size")) is int and entry["size"] >= 0
                and type(entry.get("executable")) is bool
            )
        else:
            valid = (
                set(entry) == {"path", "type", "target"}
                and entry.get("type") == "symlink" and isinstance(entry.get("target"), str)
            )
        if not valid:
            raise ValueError(f"invalid manifest entry: {relative}")
    if manifest.get("root_hash") != root_hash(entries):
        raise ValueError("manifest root hash does not match its entries")
    return manifest


def snapshot(base, output, patterns):
    output = output.expanduser().resolve()
    if output == base or base in output.parents:
        raise ValueError("manifest output must be outside DIR")
    entries = inventory(base, patterns)
    manifest = {
        "format_version": FORMAT_VERSION,
        "tool_version": TOOL_VERSION,
        "base_dir": str(base),
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "excludes": patterns,
        "entries": entries,
        "root_hash": root_hash(entries),
    }
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=True)
        stream.write("\n")
    print(manifest["root_hash"])
    return 0


def print_group(label, paths):
    print(f"{label} ({len(paths)}):")
    groups = {}
    for path in paths:
        group = path.split("/", 1)[0] + "/" if "/" in path else "(root)"
        groups.setdefault(group, []).append(path)
    for group in sorted(groups):
        print("  " + json.dumps(group))
        for path in groups[group]:
            print("    " + json.dumps(path))


def check(base, path):
    manifest = read_manifest(path)
    current = inventory(base, manifest["excludes"])
    before = {entry["path"]: entry for entry in manifest["entries"]}
    after = {entry["path"]: entry for entry in current}
    added = sorted(after.keys() - before.keys())
    removed = sorted(before.keys() - after.keys())
    changed = sorted(path for path in before.keys() & after.keys() if before[path] != after[path])
    for label, paths in (("added", added), ("removed", removed), ("changed", changed)):
        print_group(label, paths)
    print(f"counts: added={len(added)} removed={len(removed)} changed={len(changed)}")
    print("manifest root: " + manifest["root_hash"])
    print("current root:  " + root_hash(current))
    return int(bool(added or removed or changed))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=TOOL_VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("snapshot", help="write a new manifest outside DIR")
    create.add_argument("directory", type=Path)
    create.add_argument("-o", "--output", type=Path, help="default: sibling DIR.manifest.json; never overwrite")
    create.add_argument("--exclude", nargs="+", action="append", default=[], metavar="GLOB")
    compare = commands.add_parser("check", help="compare DIR with a saved manifest")
    compare.add_argument("directory", type=Path)
    compare.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        base = args.directory.expanduser().resolve(strict=True)
        if not base.is_dir():
            raise ValueError("DIR must be a directory")
        if args.command == "snapshot":
            patterns = list(dict.fromkeys(DEFAULT_EXCLUDES + tuple(pattern for group in args.exclude for pattern in group)))
            if any(not pattern for pattern in patterns):
                raise ValueError("exclude patterns must not be empty")
            return snapshot(base, args.output or base.with_name(base.name + ".manifest.json"), patterns)
        return check(base, args.manifest.expanduser())
    except (OSError, ValueError, RuntimeError) as error:
        print(f"tree-manifest: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
