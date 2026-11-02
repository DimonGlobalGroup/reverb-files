# Changelog

## v1.0.0 — 2026-11-01

Initial release.

- Single-file curses file browser (`reverb_files.py`), Python 3
  standard library only
- Directory navigation with arrows/`j`/`k`, `Enter` to open,
  `Backspace`/`h` to go to the parent directory
- Listing with file sizes, modification dates, directories marked
  and sorted first
- Copy (`c`), move (`m`), rename (`r`), delete (`d`, with a
  confirmation prompt), and new directory (`n`)
- Text preview of the first 100 lines (`v` or `Enter` on a file),
  with scrolling; binary files are detected and reported
- Hidden-file toggle (`.`)
- Status/help line; I/O and permission errors reported on screen
  instead of crashing
- Unit tests for the pure file-operation functions
