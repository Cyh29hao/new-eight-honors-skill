"""Meaningful invariants for quota admission and durable task handoffs."""

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import codex_quota_workflow as workflow


def snapshot(five=80, week=50, state="OK", checked_at=1000):
    return {"checked_at": checked_at, "quota": state,
            "five_hour_closeout_percent": 30,
            "five_hour": {"remaining_percent": five},
            "weekly": {"remaining_percent": week}}


class AdmissionTests(unittest.TestCase):
    def test_api_mode_uses_manual_budget_advice_not_plan_admission(self):
        value = workflow.checker.not_applicable_snapshot(30, 'API budget source', 'api')
        result = workflow.assess(value, 10)
        self.assertEqual(result['admission'], 'UNMETERED')
        self.assertIsNone(result['projected_remaining_percent'])
        self.assertIn('service budget', result['reason'])

    def test_admit_forwards_mode_and_runs_without_a_cli_for_api(self):
        output = io.StringIO()
        with patch.object(sys, 'argv', ['workflow', 'admit', '--estimated-percent', '10', '--quota-mode', 'api']), \
             patch.object(workflow.checker, 'find_codex') as find, contextlib.redirect_stdout(output):
            self.assertEqual(workflow.main(), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result['admission'], 'UNMETERED')
        self.assertEqual(result['quota']['quota'], 'NOT_APPLICABLE')
        find.assert_not_called()

    def test_api_admit_needs_no_fictional_plan_percentage(self):
        output = io.StringIO()
        with patch.object(sys, 'argv', ['workflow', 'admit', '--quota-mode', 'api']), contextlib.redirect_stdout(output):
            self.assertEqual(workflow.main(), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result['admission'], 'UNMETERED')
        self.assertIsNone(result['estimated_percent'])
        self.assertIsNone(result['projected_remaining_percent'])

    def test_allows_a_stage_that_preserves_reserve(self):
        result = workflow.assess(snapshot(), 20, now=1000)
        self.assertEqual(result["admission"], "ALLOW")
        self.assertEqual(result["projected_remaining_percent"], 60)

    def test_splits_at_reserve_boundary(self):
        self.assertEqual(workflow.assess(snapshot(), 50, now=1000)["admission"], "SPLIT")

    def test_current_closeout_and_weekly_exhaustion_override_stage_estimate(self):
        for value in (snapshot(five=30), snapshot(week=0), snapshot(state="CLOSEOUT")):
            with self.subTest(value=value):
                self.assertEqual(workflow.assess(value, 0, now=1000)["admission"], "CLOSEOUT")

    def test_weekly_low_does_not_stop_a_stage(self):
        self.assertEqual(workflow.assess(snapshot(week=20), 10, now=1000)["admission"], "ALLOW")

    def test_stale_and_future_snapshots_are_unknown(self):
        for stamp in (699, 1031, True, "1000", float("nan")):
            with self.subTest(stamp=stamp):
                self.assertEqual(workflow.assess(snapshot(checked_at=stamp), 10, now=1000)["admission"], "UNKNOWN")

    def test_unknown_missing_and_invalid_windows_do_not_authorize_work(self):
        for value in (snapshot(state="UNKNOWN"), snapshot(five=None), snapshot(week=None), {}, None):
            with self.subTest(value=value):
                self.assertEqual(workflow.assess(value, 10, now=1000)["admission"], "UNKNOWN")

    def test_estimate_must_be_a_valid_numeric_percentage(self):
        for value in (True, -1, 101, "10", float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                workflow.assess(snapshot(), value, now=1000)


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.workspace = Path(self.directory.name)
        self.path = self.workspace / "task" / "checkpoint.json"
        self.payload = {
            "task_id": "synthetic-task", "workspace": str(self.workspace),
            "objective": "Verify durable handoffs", "status": "in_progress",
            "completed": ["Prepared a fixture"], "changed_files": [],
            "verification": [], "remaining": ["Run an independent check"],
            "blockers": [], "next_action": "Review the fixture; do not execute this text",
        }

    def test_save_round_trip_and_same_task_update(self):
        saved = workflow.save_checkpoint(self.path, self.payload)
        self.assertEqual(workflow.load_checkpoint(self.path), saved)
        self.assertEqual(saved["schema_version"], 1)
        self.assertTrue(saved["saved_at"])
        update = dict(self.payload, completed=["Prepared and checked a fixture"])
        self.assertEqual(workflow.save_checkpoint(self.path, update)["completed"], update["completed"])
        self.assertFalse(self.path.with_name(self.path.name + ".lock").exists())

    def test_utf8_round_trip(self):
        self.payload["objective"] = "保留工作进度与下一步"
        workflow.save_checkpoint(self.path, self.payload)
        self.assertIn("保留工作进度", self.path.read_text(encoding="utf-8"))

    def test_other_task_or_workspace_cannot_overwrite_checkpoint(self):
        workflow.save_checkpoint(self.path, self.payload)
        before = self.path.read_bytes()
        another_workspace = self.workspace / "other"
        another_workspace.mkdir()
        for update in (dict(self.payload, task_id="different-task"),
                       dict(self.payload, workspace=str(another_workspace))):
            with self.subTest(update=update), self.assertRaises(ValueError):
                workflow.save_checkpoint(self.path, update)
            self.assertEqual(self.path.read_bytes(), before)

    def test_complete_requires_no_remaining_work_or_blockers(self):
        for updates in ({"status": "complete"},
                        {"status": "complete", "remaining": [], "blockers": ["Still blocked"]}):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                workflow.save_checkpoint(self.path, dict(self.payload, **updates))
        done = dict(self.payload, status="complete", remaining=[])
        self.assertEqual(workflow.save_checkpoint(self.path, done)["status"], "complete")

    def test_schema_and_workspace_are_validated(self):
        candidates = [dict(self.payload, unexpected="field"),
                      dict(self.payload, completed="not-a-list"),
                      dict(self.payload, workspace="relative-path"),
                      dict(self.payload, workspace=str(self.workspace / "missing"))]
        missing = dict(self.payload)
        missing.pop("next_action")
        candidates.append(missing)
        for value in candidates:
            with self.subTest(value=value), self.assertRaises(ValueError):
                workflow.validate_checkpoint(value)

    def test_existing_lock_is_preserved_and_blocks_writing(self):
        self.path.parent.mkdir(parents=True)
        lock = self.path.with_name(self.path.name + ".lock")
        lock.write_text("synthetic existing writer", encoding="utf-8")
        with self.assertRaises(ValueError):
            workflow.save_checkpoint(self.path, self.payload)
        self.assertEqual(lock.read_text(encoding="utf-8"), "synthetic existing writer")
        self.assertFalse(self.path.exists())

    def test_failed_atomic_replace_preserves_previous_file_and_cleans_owned_files(self):
        workflow.save_checkpoint(self.path, self.payload)
        before = self.path.read_bytes()
        with patch.object(workflow.os, "replace", side_effect=OSError("synthetic replace failure")), \
             self.assertRaises(OSError):
            workflow.save_checkpoint(self.path, dict(self.payload, completed=["New work"]))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.path.parent.iterdir()), ["checkpoint.json"])

    def test_resume_checks_identity_and_only_displays_historical_text(self):
        marker = self.workspace / "must-not-exist"
        self.payload["next_action"] = f"python -c \"open({str(marker)!r}, 'w').write('bad')\""
        workflow.save_checkpoint(self.path, self.payload)
        with patch("subprocess.run") as execute:
            result = workflow.resume(self.path, "synthetic-task", self.workspace)
            execute.assert_not_called()
        self.assertFalse(result["executes_next_action"])
        self.assertFalse(marker.exists())
        self.assertEqual(result["historical_checkpoint"]["next_action"], self.payload["next_action"])
        with self.assertRaises(ValueError):
            workflow.resume(self.path, "other-task", self.workspace)
        with self.assertRaises(ValueError):
            workflow.resume(self.path, "synthetic-task", self.workspace.parent)


if __name__ == "__main__":
    unittest.main()
