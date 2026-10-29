"""Read the signed-in Codex account's quota through the official App Server API.

Exit codes: 0 = enough allowance, 10 = closeout, 20 = quota unavailable.
This script never reads credentials or invokes a reset-consuming method.
"""

import argparse
import json
import math
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path


CLOSEOUT_REMAINING_PERCENT = 30.0
WEEKLY_NOTICE_REMAINING_PERCENT = 30.0
TIMEOUT_SECONDS = 20


def find_codex():
    bundled = os.environ.get("CODEX_CLI_PATH")
    if bundled and Path(bundled).is_file():
        return bundled
    return shutil.which("codex.exe") or shutil.which("codex.cmd") or shutil.which("codex")


def read_rate_limits(executable):
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        [executable, "app-server", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=flags,
    )
    messages = queue.Queue()

    def read_stdout():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except json.JSONDecodeError:
                pass

    threading.Thread(target=read_stdout, daemon=True).start()

    def send(message):
        process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        process.stdin.flush()

    try:
        send({
            "method": "initialize",
            "id": 1,
            "params": {"clientInfo": {
                "name": "codex_quota_readonly_check",
                "title": "Codex Quota Read-Only Check",
                "version": "1.0.0",
            }},
        })
        deadline = time.monotonic() + TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            try:
                message = messages.get(timeout=min(1, max(0.01, deadline - time.monotonic())))
            except queue.Empty:
                if process.poll() is not None:
                    raise RuntimeError("App Server exited before returning quota")
                continue
            if message.get("id") == 1:
                if "error" in message:
                    raise RuntimeError("App Server initialization failed")
                send({"method": "initialized", "params": {}})
                send({"method": "account/rateLimits/read", "id": 2})
            elif message.get("id") == 2:
                if "error" in message:
                    raise RuntimeError("App Server could not read account rate limits")
                return message.get("result", {})
        raise TimeoutError("App Server quota read timed out")
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()


def finite_number(value, minimum=0, maximum=100):
    return (
        type(value) in (int, float)
        and minimum <= value <= maximum
        and math.isfinite(value)
    )


def window_snapshot(window):
    empty = {"remaining_percent": None, "resets_at": None}
    if not isinstance(window, dict) or not finite_number(window.get("usedPercent")):
        return empty
    reset = window.get("resetsAt")
    if reset is not None:
        # Limit to timestamps representable by datetime on supported systems.
        if not finite_number(reset, 0, 253402300799):
            return empty
    return {"remaining_percent": 100.0 - window["usedPercent"], "resets_at": reset}


def select_windows(limits):
    """Use explicit durations first; legacy positions only lack duration metadata."""
    selected = {300: [], 10080: []}
    for key, legacy_duration in (("primary", 300), ("secondary", 10080)):
        window = limits.get(key)
        if not isinstance(window, dict):
            continue
        duration = window.get("windowDurationMins", legacy_duration)
        if type(duration) in (int, float) and duration in selected:
            selected[duration].append(window)
    return tuple(
        selected[duration][0] if len(selected[duration]) == 1 else None
        for duration in (300, 10080)
    )


def unknown_snapshot(threshold, reason):
    return {
        "schema_version": 1, "checked_at": time.time(), "quota": "UNKNOWN",
        "five_hour": {"remaining_percent": None, "resets_at": None},
        "weekly": {"remaining_percent": None, "resets_at": None},
        "weekly_notice": "UNKNOWN", "five_hour_closeout_percent": threshold,
        "plan": "unknown", "banked_resets": "unknown", "reason": reason,
    }


def build_snapshot(result, threshold=CLOSEOUT_REMAINING_PERCENT):
    """Build a safe quota summary without I/O or retaining the account response."""
    if not finite_number(threshold):
        return unknown_snapshot(CLOSEOUT_REMAINING_PERCENT, "Invalid closeout threshold")
    snapshot = unknown_snapshot(threshold, "Invalid quota response")
    if not isinstance(result, dict):
        return snapshot
    limits = result.get("rateLimits")
    if not limits:
        by_id = result.get("rateLimitsByLimitId")
        limits = by_id.get("codex") if isinstance(by_id, dict) else None
    if not isinstance(limits, dict):
        snapshot["reason"] = "No Codex rate-limit bucket returned"
        return snapshot
    five, week = select_windows(limits)
    snapshot["five_hour"] = window_snapshot(five)
    snapshot["weekly"] = window_snapshot(week)
    five_remaining = snapshot["five_hour"]["remaining_percent"]
    week_remaining = snapshot["weekly"]["remaining_percent"]
    five_hour_low = five_remaining is not None and five_remaining <= threshold
    weekly_exhausted = week_remaining is not None and week_remaining <= 0
    snapshot["quota"] = (
        "CLOSEOUT" if five_hour_low or weekly_exhausted
        else "UNKNOWN" if five_remaining is None or week_remaining is None
        else "OK"
    )
    snapshot["weekly_notice"] = (
        "UNKNOWN" if week_remaining is None
        else "EXHAUSTED" if weekly_exhausted
        else "LOW" if week_remaining <= WEEKLY_NOTICE_REMAINING_PERCENT
        else "NORMAL"
    )
    plan = limits.get("planType")
    allowed_plans = {"free", "go", "plus", "pro", "team", "business", "enterprise", "edu", "unknown"}
    snapshot["plan"] = plan if isinstance(plan, str) and plan in allowed_plans else "unknown"
    credits = result.get("rateLimitResetCredits")
    count = credits.get("availableCount") if isinstance(credits, dict) else None
    snapshot["banked_resets"] = count if type(count) is int and 0 <= count <= 2147483647 else "unknown"
    if snapshot["quota"] == "UNKNOWN":
        snapshot["reason"] = "Quota windows unavailable or invalid"
    else:
        snapshot.pop("reason", None)
    return snapshot


def format_window(window):
    remaining = window["remaining_percent"]
    if remaining is None:
        return "unknown"
    reset = window["resets_at"]
    try:
        # Convert each timestamp using the host timezone, including its DST rules.
        reset_text = datetime.fromtimestamp(reset).astimezone().strftime("%Y-%m-%d %H:%M %Z") if reset is not None else "unknown"
    except (OSError, OverflowError, ValueError):
        reset_text = "unknown"
    return f"{remaining:g}% left; resets {reset_text}"


def window_summary(window):
    """Retain the original helper interface for existing callers."""
    snapshot = window_snapshot(window)
    return format_window(snapshot), snapshot["remaining_percent"]


def emit_snapshot(snapshot, as_json=False):
    if as_json:
        print(json.dumps(snapshot, allow_nan=False, separators=(",", ":")))
    elif snapshot.get("reason") in {"Invalid closeout threshold", "Codex CLI not found", "Invalid quota response", "No Codex rate-limit bucket returned", "App Server quota read failed"}:
        print(f"quota=UNKNOWN reason={snapshot['reason']}")
    else:
        print(
            f"quota={snapshot['quota']} plan={snapshot['plan']} "
            f"five_hour=[{format_window(snapshot['five_hour'])}] weekly=[{format_window(snapshot['weekly'])}] "
            f"banked_resets={snapshot['banked_resets']} weekly_notice={snapshot['weekly_notice']} "
            f"five_hour_closeout_percent={snapshot['five_hour_closeout_percent']:g}"
        )
    return {"OK": 0, "CLOSEOUT": 10, "UNKNOWN": 20}[snapshot["quota"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='Emit one safe schema-versioned JSON snapshot.')
    parser.add_argument(
        '--five-hour-closeout-percent', type=float,
        default=CLOSEOUT_REMAINING_PERCENT,
        help='Five-hour remaining percentage that triggers closeout (default: 30).',
    )
    options = parser.parse_args()
    if not finite_number(options.five_hour_closeout_percent):
        return emit_snapshot(unknown_snapshot(CLOSEOUT_REMAINING_PERCENT, "Invalid closeout threshold"), options.json)
    executable = find_codex()
    if not executable:
        return emit_snapshot(unknown_snapshot(options.five_hour_closeout_percent, "Codex CLI not found"), options.json)
    try:
        result = read_rate_limits(executable)
        return emit_snapshot(build_snapshot(result, options.five_hour_closeout_percent), options.json)
    except (OSError, RuntimeError, TimeoutError, ValueError, KeyError, TypeError, OverflowError):
        # Never print raw exception text: it may contain an upstream account payload.
        return emit_snapshot(unknown_snapshot(options.five_hour_closeout_percent, "App Server quota read failed"), options.json)


if __name__ == "__main__":
    sys.exit(main())
