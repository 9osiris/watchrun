#!/usr/bin/env python3
"""watchrun - rerun a command whenever files under the given paths change."""

import argparse
import os
import subprocess
import sys
import time


def is_hidden(path):
    return any(part.startswith(".") for part in path.split(os.sep))


def snapshot(paths, include_hidden):
    snap = {}
    for path in paths:
        if os.path.isfile(path):
            if include_hidden or not is_hidden(path):
                snap[path] = os.path.getmtime(path)
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    files = [f for f in files if not f.startswith(".")]
                for name in files:
                    full = os.path.join(root, name)
                    try:
                        snap[full] = os.path.getmtime(full)
                    except OSError:
                        pass
        else:
            print(f"watchrun: {path}: no such file or directory, skipping", file=sys.stderr)
    return snap


def run(cmd, clear):
    if clear:
        os.system("clear")
    print(f"$ {' '.join(cmd)}", flush=True)
    try:
        subprocess.run(cmd)
    except FileNotFoundError:
        print(f"watchrun: {cmd[0]}: command not found", file=sys.stderr)
        sys.exit(127)


def main():
    p = argparse.ArgumentParser(
        prog="watchrun",
        description="rerun a command whenever files under the given paths change",
    )
    p.add_argument("paths", nargs="+", help="files or dirs to watch")
    p.add_argument("--clear", action="store_true", help="clear the screen between runs")
    p.add_argument("--debounce", type=float, default=0.5,
                   help="seconds to wait after a change before rerunning (default 0.5)")
    p.add_argument("--interval", type=float, default=1.0,
                   help="seconds between change checks (default 1.0)")
    p.add_argument("--all", action="store_true",
                   help="watch hidden files and dirs too (skipped by default)")

    # everything after -- is the command, parsed by hand so commands
    # starting with dashes don't confuse argparse
    argv = sys.argv[1:]
    if "--" in argv:
        i = argv.index("--")
        watch_argv, cmd = argv[:i], argv[i + 1:]
    else:
        watch_argv, cmd = argv, []
    args = p.parse_args(watch_argv)
    if not cmd:
        p.error("no command given (put it after --)")

    prev = snapshot(args.paths, args.all)
    run(cmd, args.clear)
    try:
        while True:
            time.sleep(args.interval)
            cur = snapshot(args.paths, args.all)
            if cur != prev:
                # debounce: keep waiting until a full window passes with no change
                while True:
                    time.sleep(args.debounce)
                    new = snapshot(args.paths, args.all)
                    if new == cur:
                        break
                    cur = new
                prev = cur
                run(cmd, args.clear)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
