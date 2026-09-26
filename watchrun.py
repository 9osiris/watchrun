#!/usr/bin/env python3
"""watchrun - rerun a command whenever files under the given paths change."""

import argparse
import fnmatch
import os
import subprocess
import sys
import time


def is_hidden(path):
    return any(part.startswith(".") for part in path.split(os.sep))


def make_ignorer(patterns):
    # match against the full path and every trailing suffix, so both
    # "*.log" and "build/*" work no matter how paths were passed in
    def ignored(path):
        parts = path.replace(os.sep, "/").split("/")
        tails = ["/".join(parts[i:]) for i in range(len(parts))]
        return any(fnmatch.fnmatch(t, p) for t in tails for p in patterns)
    return ignored


def snapshot(paths, include_hidden, ignored):
    snap = {}
    for path in paths:
        if ignored(path):
            continue
        if os.path.isfile(path):
            if include_hidden or not is_hidden(path):
                snap[path] = os.path.getmtime(path)
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs
                           if not ignored(os.path.join(root, d))]
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    files = [f for f in files if not f.startswith(".")]
                for name in files:
                    full = os.path.join(root, name)
                    if ignored(full):
                        continue
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
        return subprocess.run(cmd).returncode
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
    p.add_argument("--ignore", action="append", default=[], metavar="GLOB",
                   help="never watch paths matching glob, repeatable")
    p.add_argument("--once", action="store_true",
                   help="run the command once at startup and exit, don't watch")
    p.add_argument("--fail-fast", action="store_true",
                   help="stop watching after a failing run, exit with its code")

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

    ignored = make_ignorer(args.ignore)
    prev = snapshot(args.paths, args.all, ignored)
    rc = run(cmd, args.clear)
    if args.once or (args.fail_fast and rc != 0):
        # once: never watch; fail-fast: a failing first run stops us too
        sys.exit(rc)
    try:
        while True:
            time.sleep(args.interval)
            cur = snapshot(args.paths, args.all, ignored)
            if cur != prev:
                # debounce: keep waiting until a full window passes with no change
                while True:
                    time.sleep(args.debounce)
                    new = snapshot(args.paths, args.all, ignored)
                    if new == cur:
                        break
                    cur = new
                prev = cur
                rc = run(cmd, args.clear)
                if args.fail_fast and rc != 0:
                    sys.exit(rc)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
