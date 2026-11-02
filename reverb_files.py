#!/usr/bin/env python3
"""Reverb Files - a keyboard-driven terminal file manager.

A clean-room revival of the classic keyboard file-manager genre,
written from scratch on the Python 3 standard library only (curses).

Run:  python3 reverb_files.py [starting-directory]

Keys:
  Up/Down or j/k   move selection        Enter   open dir / preview file
  Backspace or h   parent directory      v       preview file
  c copy   m move   r rename   d delete (asks first)   n new directory
  . toggle hidden files                  q       quit (in preview: back)
"""

import curses
import os
import shutil
import sys
import time

PREVIEW_LINES = 100


# ---------------------------------------------------------------------------
# Pure file operations (no curses here -- these are unit-tested directly)
# ---------------------------------------------------------------------------

def list_dir(path):
    """Return entries of *path* as dicts, directories first, then by name.

    Each entry: {"name", "path", "is_dir", "size", "mtime"}.
    Unreadable entries are skipped rather than raising.
    """
    entries = []
    with os.scandir(path) as it:
        for entry in it:
            try:
                st = entry.stat()
                is_dir = entry.is_dir()
            except OSError:
                continue
            entries.append({
                "name": entry.name,
                "path": entry.path,
                "is_dir": is_dir,
                "size": st.st_size,
                "mtime": st.st_mtime,
            })
    entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
    return entries


def _resolve_dest(src, dst):
    """If *dst* is an existing directory, the target is dst/basename(src)."""
    if os.path.isdir(dst):
        return os.path.join(dst, os.path.basename(src.rstrip(os.sep)))
    return dst


def copy_path(src, dst):
    """Copy file or directory tree *src* to *dst*. Returns the final path."""
    target = _resolve_dest(src, dst)
    if os.path.isdir(src):
        shutil.copytree(src, target)
    else:
        shutil.copy2(src, target)
    return target


def move_path(src, dst):
    """Move file or directory *src* to *dst*. Returns the final path."""
    target = _resolve_dest(src, dst)
    shutil.move(src, target)
    return target


def rename_path(src, new_name):
    """Rename *src* to *new_name* (a bare name, not a path) in place."""
    if not new_name or os.sep in new_name or (os.altsep and os.altsep in new_name):
        raise ValueError("rename target must be a plain file name")
    target = os.path.join(os.path.dirname(os.path.abspath(src)), new_name)
    os.rename(src, target)
    return target


def delete_path(path):
    """Delete a file, or a directory tree. Refuses to delete '/'."""
    if os.path.abspath(path) == os.path.abspath(os.sep):
        raise ValueError("refusing to delete the filesystem root")
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    else:
        os.remove(path)


def make_dir(parent, name):
    """Create directory *name* inside *parent*. Returns the new path."""
    if not name or os.sep in name or (os.altsep and os.altsep in name):
        raise ValueError("directory name must be a plain name")
    target = os.path.join(parent, name)
    os.mkdir(target)
    return target


def preview_lines(path, max_lines=PREVIEW_LINES):
    """Return up to *max_lines* text lines of *path* for the viewer.

    Binary-looking content is reported as a single explanatory line
    instead of dumping raw bytes to the terminal.
    """
    lines = []
    with open(path, "rb") as fh:
        for _ in range(max_lines):
            raw = fh.readline()
            if not raw:
                break
            if b"\x00" in raw:
                return ["[binary file - preview unavailable]"]
            lines.append(raw.decode("utf-8", errors="replace").rstrip("\n").rstrip("\r"))
    return lines


def format_size(num):
    """Human-readable byte size."""
    size = float(num)
    for unit in ("B", "K", "M", "G", "T"):
        if size < 1024 or unit == "T":
            return "%d%s" % (size, unit) if unit == "B" else "%.1f%s" % (size, unit)
        size /= 1024


def format_entry(entry):
    """One-line display string for a listing entry."""
    marker = "/" if entry["is_dir"] else " "
    size = "<DIR>" if entry["is_dir"] else format_size(entry["size"])
    date = time.strftime("%Y-%m-%d %H:%M", time.localtime(entry["mtime"]))
    return "%s%-40s %8s  %s" % (marker, entry["name"], size, date)


# ---------------------------------------------------------------------------
# Curses interface
# ---------------------------------------------------------------------------

class FileManager:
    def __init__(self, stdscr, start):
        self.scr = stdscr
        self.cwd = os.path.abspath(start)
        self.show_hidden = False
        self.entries = []
        self.sel = 0
        self.offset = 0
        self.message = ""
        self.refresh()

    # -- data ------------------------------------------------------------
    def refresh(self, keep_name=None):
        try:
            all_entries = list_dir(self.cwd)
        except OSError as exc:
            self.entries = []
            self.message = "Cannot read directory: %s" % exc
            return
        if not self.show_hidden:
            all_entries = [e for e in all_entries if not e["name"].startswith(".")]
        self.entries = all_entries
        if keep_name:
            for i, e in enumerate(self.entries):
                if e["name"] == keep_name:
                    self.sel = i
                    break
            else:
                self.sel = 0
        self.sel = max(0, min(self.sel, len(self.entries) - 1)) if self.entries else 0

    def selected(self):
        if 0 <= self.sel < len(self.entries):
            return self.entries[self.sel]
        return None

    # -- drawing ---------------------------------------------------------
    def draw(self):
        self.scr.erase()
        height, width = self.scr.getmaxyx()
        header = " Reverb Files  %s" % self.cwd
        self.scr.addnstr(0, 0, header, width - 1, curses.A_REVERSE)
        list_h = max(1, height - 3)
        if self.sel < self.offset:
            self.offset = self.sel
        if self.sel >= self.offset + list_h:
            self.offset = self.sel - list_h + 1
        for row in range(list_h):
            idx = self.offset + row
            if idx >= len(self.entries):
                break
            entry = self.entries[idx]
            text = format_entry(entry)
            attr = curses.A_REVERSE if idx == self.sel else curses.A_NORMAL
            if entry["is_dir"]:
                attr |= curses.A_BOLD
            self.scr.addnstr(1 + row, 0, text, width - 1, attr)
        status_y = height - 2
        if self.message:
            self.scr.addnstr(status_y, 0, self.message, width - 1, curses.A_BOLD)
        elif self.entries:
            self.scr.addnstr(
                status_y, 0,
                "%d item(s) - selected: %s" % (len(self.entries),
                                                self.entries[self.sel]["name"]),
                width - 1)
        help_line = ("j/k move  Enter open  h parent  v preview  c copy  m move  "
                     "r rename  d delete  n new dir  . hidden  q quit")
        self.scr.addnstr(height - 1, 0, help_line, width - 1, curses.A_DIM)
        self.scr.refresh()

    # -- input helpers ---------------------------------------------------
    def prompt(self, label, initial=""):
        """Minimal line editor on the bottom line. None on cancel (Esc)."""
        height, width = self.scr.getmaxyx()
        y = height - 2
        text = initial
        curses.curs_set(1)
        while True:
            self.scr.addnstr(y, 0, " " * (width - 1), width - 1)
            self.scr.addnstr(y, 0, "%s%s" % (label, text), width - 1, curses.A_BOLD)
            self.scr.move(y, min(len(label) + len(text), width - 2))
            self.scr.refresh()
            key = self.scr.getch()
            if key in (10, 13, curses.KEY_ENTER):
                curses.curs_set(0)
                return text
            if key == 27:
                curses.curs_set(0)
                return None
            if key in (curses.KEY_BACKSPACE, 127, 8):
                text = text[:-1]
            elif 32 <= key < 127:
                text += chr(key)

    def confirm(self, question):
        height, width = self.scr.getmaxyx()
        y = height - 2
        self.scr.addnstr(y, 0, " " * (width - 1), width - 1)
        self.scr.addnstr(y, 0, "%s (y/n) " % question, width - 1,
                         curses.A_BOLD | curses.A_REVERSE)
        self.scr.refresh()
        while True:
            key = self.scr.getch()
            if key in (ord("y"), ord("Y")):
                return True
            if key in (ord("n"), ord("N"), 27):
                return False

    def show_message(self, text):
        self.message = text

    # -- actions ---------------------------------------------------------
    def do_preview(self, entry):
        try:
            lines = preview_lines(entry["path"])
        except OSError as exc:
            self.show_message("Cannot preview: %s" % exc)
            return
        top = 0
        while True:
            self.scr.erase()
            height, width = self.scr.getmaxyx()
            title = " Preview: %s (j/k scroll, q back)" % entry["path"]
            self.scr.addnstr(0, 0, title, width - 1, curses.A_REVERSE)
            view_h = height - 1
            for row in range(view_h):
                idx = top + row
                if idx >= len(lines):
                    break
                self.scr.addnstr(1 + row, 0, lines[idx], width - 1)
            self.scr.refresh()
            key = self.scr.getch()
            if key in (ord("q"), 27):
                return
            if key in (curses.KEY_DOWN, ord("j")):
                top = min(top + 1, max(0, len(lines) - view_h))
            elif key in (curses.KEY_UP, ord("k")):
                top = max(0, top - 1)
            elif key == curses.KEY_NPAGE:
                top = min(top + view_h, max(0, len(lines) - view_h))
            elif key == curses.KEY_PPAGE:
                top = max(0, top - view_h)

    def do_copy(self, entry):
        dst = self.prompt("Copy to: ", os.path.join(self.cwd, entry["name"]))
        if dst is None:
            return
        try:
            final = copy_path(entry["path"], dst)
            self.show_message("Copied to %s" % final)
            self.refresh(keep_name=entry["name"])
        except (OSError, shutil.Error) as exc:
            self.show_message("Copy failed: %s" % exc)

    def do_move(self, entry):
        dst = self.prompt("Move to: ", os.path.join(self.cwd, entry["name"]))
        if dst is None:
            return
        try:
            final = move_path(entry["path"], dst)
            self.show_message("Moved to %s" % final)
            self.refresh()
        except (OSError, shutil.Error) as exc:
            self.show_message("Move failed: %s" % exc)

    def do_rename(self, entry):
        new_name = self.prompt("Rename to: ", entry["name"])
        if new_name is None:
            return
        try:
            rename_path(entry["path"], new_name)
            self.show_message("Renamed to %s" % new_name)
            self.refresh(keep_name=new_name)
        except (OSError, ValueError) as exc:
            self.show_message("Rename failed: %s" % exc)

    def do_delete(self, entry):
        kind = "directory" if entry["is_dir"] else "file"
        if not self.confirm("Delete %s '%s'?" % (kind, entry["name"])):
            self.show_message("Delete cancelled")
            return
        try:
            delete_path(entry["path"])
            self.show_message("Deleted %s" % entry["name"])
            self.refresh()
        except (OSError, ValueError) as exc:
            self.show_message("Delete failed: %s" % exc)

    def do_new_dir(self):
        name = self.prompt("New directory name: ")
        if name is None:
            return
        try:
            path = make_dir(self.cwd, name)
            self.show_message("Created %s" % path)
            self.refresh(keep_name=name)
        except (OSError, ValueError) as exc:
            self.show_message("New directory failed: %s" % exc)

    def open_entry(self, entry):
        if entry["is_dir"]:
            self.cwd = entry["path"]
            self.sel = 0
            self.offset = 0
            self.message = ""
            self.refresh()
        else:
            self.do_preview(entry)

    def go_parent(self):
        parent = os.path.dirname(self.cwd)
        if parent != self.cwd:
            old = os.path.basename(self.cwd)
            self.cwd = parent
            self.message = ""
            self.refresh(keep_name=old)

    # -- main loop ---------------------------------------------------------
    def run(self):
        curses.curs_set(0)
        self.scr.keypad(True)
        while True:
            self.draw()
            key = self.scr.getch()
            self.message = ""
            height, _ = self.scr.getmaxyx()
            page = max(1, height - 3)
            entry = self.selected()
            if key in (curses.KEY_DOWN, ord("j")):
                if self.entries:
                    self.sel = min(self.sel + 1, len(self.entries) - 1)
            elif key in (curses.KEY_UP, ord("k")):
                self.sel = max(0, self.sel - 1)
            elif key == curses.KEY_NPAGE:
                if self.entries:
                    self.sel = min(self.sel + page, len(self.entries) - 1)
            elif key == curses.KEY_PPAGE:
                self.sel = max(0, self.sel - page)
            elif key == ord("g"):
                self.sel = 0
            elif key == ord("G"):
                if self.entries:
                    self.sel = len(self.entries) - 1
            elif key in (10, 13, curses.KEY_ENTER, curses.KEY_RIGHT, ord("l")):
                if entry:
                    self.open_entry(entry)
            elif key in (curses.KEY_BACKSPACE, 127, 8, curses.KEY_LEFT, ord("h")):
                self.go_parent()
            elif key == ord("v"):
                if entry and not entry["is_dir"]:
                    self.do_preview(entry)
            elif key == ord("c"):
                if entry:
                    self.do_copy(entry)
            elif key == ord("m"):
                if entry:
                    self.do_move(entry)
            elif key == ord("r"):
                if entry:
                    self.do_rename(entry)
            elif key == ord("d"):
                if entry:
                    self.do_delete(entry)
            elif key == ord("n"):
                self.do_new_dir()
            elif key == ord("."):
                self.show_hidden = not self.show_hidden
                self.refresh()
                self.show_message("Hidden files %s" %
                                  ("shown" if self.show_hidden else "hidden"))
            elif key == ord("q"):
                return


def main(argv):
    start = argv[1] if len(argv) > 1 else os.getcwd()
    if not os.path.isdir(start):
        sys.stderr.write("reverb_files: not a directory: %s\n" % start)
        return 2
    curses.wrapper(lambda stdscr: FileManager(stdscr, start).run())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
