"""Unit tests for the pure file operations in reverb_files.py.

Run:  python3 -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import reverb_files as rf


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, text):
        path = os.path.join(self.root, rel)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path


class TestListDir(TempDirCase):
    def test_dirs_first_and_fields(self):
        os.mkdir(os.path.join(self.root, "adir"))
        self.write("bfile.txt", "hello")
        self.write("afile.txt", "hi")
        entries = rf.list_dir(self.root)
        names = [e["name"] for e in entries]
        self.assertEqual(names, ["adir", "afile.txt", "bfile.txt"])
        by_name = {e["name"]: e for e in entries}
        self.assertTrue(by_name["adir"]["is_dir"])
        self.assertFalse(by_name["bfile.txt"]["is_dir"])
        self.assertEqual(by_name["bfile.txt"]["size"], 5)
        self.assertGreater(by_name["bfile.txt"]["mtime"], 0)


class TestCopyMove(TempDirCase):
    def test_copy_file(self):
        src = self.write("a.txt", "data")
        dst = os.path.join(self.root, "b.txt")
        final = rf.copy_path(src, dst)
        self.assertEqual(final, dst)
        with open(dst) as fh:
            self.assertEqual(fh.read(), "data")
        self.assertTrue(os.path.exists(src))

    def test_copy_into_dir_uses_basename(self):
        src = self.write("a.txt", "x")
        dest_dir = os.path.join(self.root, "dest")
        os.mkdir(dest_dir)
        final = rf.copy_path(src, dest_dir)
        self.assertEqual(final, os.path.join(dest_dir, "a.txt"))
        self.assertTrue(os.path.isfile(final))

    def test_copy_tree(self):
        os.makedirs(os.path.join(self.root, "tree", "sub"))
        self.write(os.path.join("tree", "sub", "leaf.txt"), "leaf")
        dst = os.path.join(self.root, "tree2")
        rf.copy_path(os.path.join(self.root, "tree"), dst)
        with open(os.path.join(dst, "sub", "leaf.txt")) as fh:
            self.assertEqual(fh.read(), "leaf")

    def test_move_file(self):
        src = self.write("a.txt", "m")
        dst = os.path.join(self.root, "moved.txt")
        final = rf.move_path(src, dst)
        self.assertEqual(final, dst)
        self.assertFalse(os.path.exists(src))
        self.assertTrue(os.path.isfile(dst))


class TestRenameDeleteMkdir(TempDirCase):
    def test_rename(self):
        src = self.write("old.txt", "r")
        final = rf.rename_path(src, "new.txt")
        self.assertEqual(os.path.basename(final), "new.txt")
        self.assertFalse(os.path.exists(src))
        self.assertTrue(os.path.isfile(final))

    def test_rename_rejects_path(self):
        src = self.write("old.txt", "r")
        with self.assertRaises(ValueError):
            rf.rename_path(src, "sub/evil.txt")

    def test_delete_file_and_tree(self):
        f = self.write("gone.txt", "g")
        rf.delete_path(f)
        self.assertFalse(os.path.exists(f))
        os.makedirs(os.path.join(self.root, "tree", "sub"))
        self.write(os.path.join("tree", "sub", "x.txt"), "x")
        rf.delete_path(os.path.join(self.root, "tree"))
        self.assertFalse(os.path.exists(os.path.join(self.root, "tree")))

    def test_delete_root_refused(self):
        with self.assertRaises(ValueError):
            rf.delete_path("/")

    def test_make_dir(self):
        path = rf.make_dir(self.root, "fresh")
        self.assertTrue(os.path.isdir(path))
        with self.assertRaises(ValueError):
            rf.make_dir(self.root, "a/b")


class TestPreview(TempDirCase):
    def test_preview_lines_and_cap(self):
        body = "".join("line %d\n" % i for i in range(150))
        path = self.write("big.txt", body)
        lines = rf.preview_lines(path)
        self.assertEqual(len(lines), 100)
        self.assertEqual(lines[0], "line 0")
        lines5 = rf.preview_lines(path, max_lines=5)
        self.assertEqual(len(lines5), 5)

    def test_preview_binary(self):
        path = os.path.join(self.root, "bin.dat")
        with open(path, "wb") as fh:
            fh.write(b"\x00\x01\x02")
        self.assertEqual(rf.preview_lines(path),
                         ["[binary file - preview unavailable]"])


class TestFormat(TempDirCase):
    def test_format_size(self):
        self.assertEqual(rf.format_size(0), "0B")
        self.assertEqual(rf.format_size(512), "512B")
        self.assertEqual(rf.format_size(2048), "2.0K")

    def test_format_entry_marks_dirs(self):
        os.mkdir(os.path.join(self.root, "d"))
        entry = rf.list_dir(self.root)[0]
        text = rf.format_entry(entry)
        self.assertTrue(text.startswith("/"))
        self.assertIn("<DIR>", text)


if __name__ == "__main__":
    unittest.main()
