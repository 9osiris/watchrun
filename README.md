# watchrun

rerun a command whenever files under the given paths change. polls mtimes,
no dependencies, works anywhere python does.

## usage

```bash
# rerun the test suite when anything under src/ or tests/ changes
python watchrun.py src tests -- pytest

# rebuild when the markdown changes
python watchrun.py docs -- make site

# clear the screen between runs so output doesn't pile up
python watchrun.py --clear src -- python main.py

# run once at startup and exit, don't watch
python watchrun.py --once src -- pytest

# stop watching the moment a run fails, exit with its code
python watchrun.py --fail-fast src -- pytest
```

runs the command once at startup, then watches. ctrl-c to stop.

hidden files and dirs (anything starting with `.`) are ignored by default;
pass `--all` to watch them too.

skip noisy paths with `--ignore` (repeatable, glob patterns):

```bash
# don't rerun when logs change or anything under build/ moves
python watchrun.py --ignore "*.log" --ignore "build/*" src -- pytest
```

## flags

- `--clear` - clear the screen between runs
- `--debounce SEC` - wait this long after a change before rerunning (default 0.5)
- `--interval SEC` - seconds between change checks (default 1.0)
- `--all` - also watch hidden files and dirs
- `--ignore GLOB` - never watch matching paths (repeatable)
- `--once` - run once at startup and exit, don't watch
- `--fail-fast` - stop watching after a failing run, exit with its code

## notes

- single file, stdlib only, no install
- new files, deleted files, and content changes all trigger a rerun

## license

do whatever you want with it
