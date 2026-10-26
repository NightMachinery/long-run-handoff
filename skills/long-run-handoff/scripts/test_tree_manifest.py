import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("tree-manifest.py")
SPEC = importlib.util.spec_from_file_location("tree_manifest", SCRIPT)
MANIFEST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MANIFEST)


class TreeManifestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.tree = self.root / "tree"
        self.tree.mkdir()
        (self.tree / "src").mkdir()
        (self.tree / "src" / "item.txt").write_bytes(b"first\n")
        self.manifest = self.root / "receipt.json"

    def invoke(self, *args):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = MANIFEST.main([str(arg) for arg in args])
        return status, output.getvalue(), errors.getvalue()

    def snapshot(self, *args):
        status, output, errors = self.invoke("snapshot", self.tree, "-o", self.manifest, *args)
        self.assertEqual(status, 0, errors)
        data = json.loads(self.manifest.read_text())
        self.assertEqual(output.strip(), data["root_hash"])
        return data

    def assert_difference(self, label, path):
        status, output, errors = self.invoke("check", self.tree, self.manifest)
        self.assertEqual(status, 1, errors)
        self.assertIn(label + " (1):", output)
        self.assertIn(json.dumps(path), output)
        self.assertIn('"src/"', output)
        self.assertIn("manifest root:", output)
        self.assertIn("current root:", output)

    def test_identical_and_canonical_root(self):
        data = self.snapshot()
        entry = data["entries"][0]
        self.assertEqual(entry["sha256"], hashlib.sha256(b"first\n").hexdigest())
        self.assertEqual(entry["size"], 6)
        self.assertFalse(entry["executable"])
        lines = "".join(json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
                        for item in sorted(data["entries"], key=lambda item: item["path"]))
        self.assertEqual(data["root_hash"], hashlib.sha256(lines.encode()).hexdigest())
        self.assertEqual(self.invoke("check", self.tree, self.manifest)[0], 0)

    def test_added(self):
        self.snapshot()
        (self.tree / "src" / "added.txt").write_text("added")
        self.assert_difference("added", "src/added.txt")

    def test_removed(self):
        self.snapshot()
        (self.tree / "src" / "item.txt").unlink()
        self.assert_difference("removed", "src/item.txt")

    def test_changed_content_same_size_and_time(self):
        self.snapshot()
        path = self.tree / "src" / "item.txt"
        before = path.stat()
        path.write_bytes(b"other\n")
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assert_difference("changed", "src/item.txt")

    def test_executable_change(self):
        self.snapshot()
        path = self.tree / "src" / "item.txt"
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        self.assert_difference("changed", "src/item.txt")

    def test_modification_times_are_ignored(self):
        self.snapshot()
        path = self.tree / "src" / "item.txt"
        before = path.stat()
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1000000000))
        self.assertEqual(self.invoke("check", self.tree, self.manifest)[0], 0)

    def test_symlinks_are_not_followed_and_retarget_is_changed(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "unread.txt").write_text("outside tree")
        link = self.tree / "src" / "link"
        link.symlink_to(outside, target_is_directory=True)
        data = self.snapshot()
        self.assertEqual(len(data["entries"]), 2)
        self.assertIn({"path": "src/link", "type": "symlink", "target": str(outside)}, data["entries"])
        (outside / "unread.txt").write_text("still not followed")
        self.assertEqual(self.invoke("check", self.tree, self.manifest)[0], 0)
        link.unlink()
        link.symlink_to("missing-target")
        self.assert_difference("changed", "src/link")

    def test_default_and_custom_excludes_are_reused(self):
        for directory in (".git", "src/__pycache__", "logs"):
            path = self.tree / directory
            path.mkdir(parents=True, exist_ok=True)
            (path / "ignored").write_text("excluded")
        (self.tree / "src" / "scratch.tmp").write_text("excluded")
        data = self.snapshot("--exclude", "*.tmp", "logs/**")
        self.assertEqual([entry["path"] for entry in data["entries"]], ["src/item.txt"])
        (self.tree / "src" / "later.tmp").write_text("also excluded")
        (self.tree / ".git" / "ignored").unlink()
        self.assertEqual(self.invoke("check", self.tree, self.manifest)[0], 0)

    def test_sorted_streamed_inventory_and_relocated_tree(self):
        (self.tree / "z.txt").write_bytes(b"z")
        (self.tree / "a.bin").write_bytes(b"a" * (2 * 1024 * 1024 + 7))
        data = self.snapshot()
        self.assertEqual([entry["path"] for entry in data["entries"]],
                         ["a.bin", "src/item.txt", "z.txt"])
        self.assertEqual(data["entries"][0]["sha256"],
                         hashlib.sha256(b"a" * (2 * 1024 * 1024 + 7)).hexdigest())
        moved = self.root / "moved"
        self.tree.rename(moved)
        self.assertEqual(self.invoke("check", moved, self.manifest)[0], 0)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires FIFO support")
    def test_special_file_is_an_error_without_opening_it(self):
        os.mkfifo(self.tree / "pipe")
        status, _, errors = self.invoke("snapshot", self.tree, "-o", self.manifest)
        self.assertEqual(status, 2)
        self.assertIn("unsupported file type", errors)
        self.assertFalse(self.manifest.exists())

    def test_snapshot_and_check_do_not_modify_tree(self):
        def state():
            return {str(path.relative_to(self.tree)): (path.lstat().st_mode, path.lstat().st_size,
                    path.lstat().st_mtime_ns, path.read_bytes() if path.is_file() else None)
                    for path in [self.tree, *self.tree.rglob("*")]}
        before = state()
        self.snapshot()
        self.assertEqual(self.invoke("check", self.tree, self.manifest)[0], 0)
        self.assertEqual(state(), before)

    def test_output_inside_tree_or_via_alias_is_refused(self):
        for output in (self.tree / "receipt.json", self.tree / "new" / "receipt.json"):
            self.assertEqual(self.invoke("snapshot", self.tree, "-o", output)[0], 2)
            self.assertFalse(output.exists())
        alias = self.root / "alias"
        alias.symlink_to(self.tree, target_is_directory=True)
        self.assertEqual(self.invoke("snapshot", self.tree, "-o", alias / "receipt.json")[0], 2)

    def test_default_output_and_existing_receipt_not_overwritten(self):
        self.assertEqual(self.invoke("snapshot", self.tree)[0], 0)
        output = self.root / "tree.manifest.json"
        before = output.read_bytes()
        self.assertEqual(self.invoke("snapshot", self.tree)[0], 2)
        self.assertEqual(output.read_bytes(), before)

    def test_unreadable_is_error_in_snapshot_and_check(self):
        self.snapshot()
        with mock.patch.object(MANIFEST, "file_entry", side_effect=PermissionError("unreadable")):
            self.assertEqual(self.invoke("snapshot", self.tree, "-o", self.root / "unreadable.json")[0], 2)
            self.assertEqual(self.invoke("check", self.tree, self.manifest)[0], 2)
        self.assertFalse((self.root / "unreadable.json").exists())

    def test_invalid_manifest_and_io_are_errors(self):
        self.snapshot()
        data = json.loads(self.manifest.read_text())
        data["entries"][0]["size"] += 1
        self.manifest.write_text(json.dumps(data))
        self.assertEqual(self.invoke("check", self.tree, self.manifest)[0], 2)
        self.manifest.write_text("not JSON")
        self.assertEqual(self.invoke("check", self.tree, self.manifest)[0], 2)
        self.assertEqual(self.invoke("snapshot", self.root / "missing")[0], 2)

    def test_groups_and_type_changes(self):
        self.snapshot()
        path = self.tree / "src" / "item.txt"
        path.unlink()
        path.symlink_to("absent")
        self.assert_difference("changed", "src/item.txt")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            MANIFEST.print_group("added", ["a.txt", "b/x", "z.txt", "b/y"])
        self.assertEqual(output.getvalue().count('"(root)"'), 1)
        self.assertEqual(output.getvalue().count('"b/"'), 1)

    def test_cli_exit_codes(self):
        self.snapshot()
        done = subprocess.run([sys.executable, "-B", str(SCRIPT), "check", str(self.tree), str(self.manifest)],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        (self.tree / "src" / "item.txt").write_text("different")
        self.assertEqual(subprocess.run([sys.executable, "-B", str(SCRIPT), "check", str(self.tree), str(self.manifest)],
                                       capture_output=True).returncode, 1)
        self.assertEqual(subprocess.run([sys.executable, "-B", str(SCRIPT), "check"], capture_output=True).returncode, 2)


if __name__ == "__main__":
    unittest.main()
