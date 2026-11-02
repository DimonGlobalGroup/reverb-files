# Reverb Files

A keyboard-driven terminal file manager in a single Python file.
No dependencies — Python 3 and its standard library (curses) only.

```bash
python3 reverb_files.py            # browse the current directory
python3 reverb_files.py ~/projects # start somewhere else
```

## Why it exists

The two-keystroke file manager is one of the oldest, best ideas in
personal computing: see everything, touch the mouse never, and let
confirmation prompts — not luck — stand between you and a mistake.
Modern desktops buried that workflow under right-click menus and
cloud sync dialogs. Reverb Files brings it back as one readable,
hackable file you can drop on any machine with Python 3.

## Features

- Single-pane curses browser with file sizes and modification dates;
  directories marked and listed first
- Fast keyboard navigation: arrows or `j`/`k`, PageUp/PageDown, `g`/`G`
- Built-in text preview (first 100 lines) with scrolling — binary
  files are detected and reported instead of dumped to the screen
- Copy, move, rename, delete, and new-directory operations from the
  keyboard, with prompts prefilled so the common case is one Enter
- Delete always asks for confirmation first; the filesystem root is
  refused outright
- Hidden-file toggle (`.` files) on the `.` key
- Permission and I/O errors appear as status-line messages — the
  program does not crash on a locked file or an unreadable directory

## Key map

| Key | Action |
| --- | --- |
| `↑` `↓` or `j` `k` | Move selection |
| `PgUp` `PgDn` | Move by a page |
| `g` / `G` | First / last entry |
| `Enter` or `l` | Open directory, or preview file |
| `Backspace` or `h` | Parent directory |
| `v` | Preview selected file |
| `c` | Copy (prompts for destination) |
| `m` | Move (prompts for destination) |
| `r` | Rename |
| `d` | Delete (confirmation prompt) |
| `n` | New directory |
| `.` | Toggle hidden files |
| `q` | Quit (in preview: back to browser) |
| `Esc` | Cancel a prompt |

Copy and move accept either a full destination path or an existing
directory (the item is placed inside it, keeping its name).

## Testing

The file operations are pure functions, separate from the curses UI,
and unit-tested:

```bash
python3 -m unittest discover -s tests -v
```

## Lineage

Reverb Files is part of the **Reverb** line: clean-room revivals of
classic software ideas, rebuilt from scratch for current machines.
It is an original implementation inspired by the keyboard
file-manager genre — no code, name, or text was taken from any
existing file manager.

## License

MIT — see `LICENSE`.

By Dimon Global Group
