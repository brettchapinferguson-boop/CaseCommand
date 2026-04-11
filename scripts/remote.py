#!/usr/bin/env python3
"""Laptop-side CLI for running shell commands against a CaseCommand server.

Usage:
    export CASECOMMAND_URL=https://casecommand.onrender.com
    export CASECOMMAND_TOKEN=your-auth-token
    python scripts/remote.py "git status"
    python scripts/remote.py --cwd /tmp "ls -la"
    python scripts/remote.py --timeout 120 "pytest"

Or install as a shortcut:
    alias remote='python /path/to/CaseCommand/scripts/remote.py'
    remote "uname -a"

Relies only on the Python standard library so it works on a fresh laptop.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a command on a remote CaseCommand server.")
    parser.add_argument("command", help="Command to run, e.g. 'git status'")
    parser.add_argument("--url", default=os.environ.get("CASECOMMAND_URL"),
                        help="Server base URL (or set CASECOMMAND_URL)")
    parser.add_argument("--token", default=os.environ.get("CASECOMMAND_TOKEN"),
                        help="Bearer token (or set CASECOMMAND_TOKEN)")
    parser.add_argument("--cwd", default=None, help="Working directory on the server")
    parser.add_argument("--timeout", type=int, default=None, help="Command timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Print raw JSON response")
    args = parser.parse_args()

    if not args.url:
        print("error: --url or CASECOMMAND_URL is required", file=sys.stderr)
        return 2
    if not args.token:
        print("error: --token or CASECOMMAND_TOKEN is required", file=sys.stderr)
        return 2

    payload = {"command": args.command}
    if args.cwd:
        payload["cwd"] = args.cwd
    if args.timeout:
        payload["timeout"] = args.timeout

    req = urllib.request.Request(
        args.url.rstrip("/") + "/api/terminal",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {args.token}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=(args.timeout or 60) + 30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {detail}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"Network error: {e.reason}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(body, indent=2))
        return 0 if body.get("exit_code") == 0 else 1

    if body.get("stdout"):
        sys.stdout.write(body["stdout"])
        if not body["stdout"].endswith("\n"):
            sys.stdout.write("\n")
    if body.get("stderr"):
        sys.stderr.write(body["stderr"])
        if not body["stderr"].endswith("\n"):
            sys.stderr.write("\n")
    if body.get("timed_out"):
        print(f"[timed out after {body.get('timeout')}s]", file=sys.stderr)
        return 124
    if body.get("truncated"):
        print("[output truncated]", file=sys.stderr)

    exit_code = body.get("exit_code")
    return int(exit_code) if isinstance(exit_code, int) else 1


if __name__ == "__main__":
    sys.exit(main())
