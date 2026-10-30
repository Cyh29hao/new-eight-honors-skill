"""Behavioral checks for the optional read-only Codex quota adapter."""

import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_codex_quota as quota


def response(five_used=20, weekly_used=40):
    return {"rateLimits": {
        "primary": {"usedPercent": five_used, "windowDurationMins": 300,
                    "resetsAt": 1800000000},
        "secondary": {"usedPercent": weekly_used, "windowDurationMins": 10080,
                      "resetsAt": 1800500000},
    }}


class SnapshotTests(unittest.TestCase):
    def test_weekly_allowance_is_converted_before_reserve_decision(self):
        result = quota.build_snapshot(response(20, 98), 10)
        self.assertEqual(result['weekly_equivalent_percent'], 12)
        self.assertEqual(result['effective_remaining_percent'], 12)
        self.assertEqual(result['quota'], 'OK')
        self.assertEqual(quota.build_snapshot(response(20, 98), 12)['quota'], 'CLOSEOUT')
        self.assertEqual(quota.build_snapshot(response(20, 95))['quota'], 'CLOSEOUT')

    def test_effective_balance_keeps_original_windows_and_uses_lower_value(self):
        result = quota.build_snapshot(response(92, 98), 10)
        self.assertEqual(result['effective_remaining_percent'], 8)
        self.assertEqual(result['five_hour']['remaining_percent'], 8)
        self.assertEqual(result['weekly']['remaining_percent'], 2)
        self.assertEqual(result['quota'], 'CLOSEOUT')

    def test_five_hour_closeout_boundary(self):
        for used, expected in ((69.9, "OK"), (70, "CLOSEOUT"), (100, "CLOSEOUT")):
            with self.subTest(used=used):
                self.assertEqual(quota.build_snapshot(response(used))["quota"], expected)

    def test_custom_threshold(self):
        self.assertEqual(quota.build_snapshot(response(75), 20)["quota"], "OK")
        self.assertEqual(quota.build_snapshot(response(80), 20)["quota"], "CLOSEOUT")

    def test_weekly_low_is_informational(self):
        snapshot = quota.build_snapshot(response(20, 70))
        self.assertEqual(snapshot["quota"], "OK")
        self.assertEqual(snapshot["weekly_notice"], "LOW")

    def test_weekly_exhaustion_requires_closeout(self):
        snapshot = quota.build_snapshot(response(20, 100))
        self.assertEqual(snapshot["quota"], "CLOSEOUT")
        self.assertEqual(snapshot["weekly_notice"], "EXHAUSTED")

    def test_explicit_duration_wins_over_primary_secondary_position(self):
        payload = response(10, 80)
        limits = payload["rateLimits"]
        limits["primary"], limits["secondary"] = limits["secondary"], limits["primary"]
        snapshot = quota.build_snapshot(payload)
        self.assertEqual(snapshot["five_hour"]["remaining_percent"], 90)
        self.assertEqual(snapshot["weekly"]["remaining_percent"], 20)
        self.assertEqual(snapshot["quota"], "OK")

    def test_legacy_positions_work_only_without_duration_metadata(self):
        payload = response()
        for window in payload["rateLimits"].values():
            window.pop("windowDurationMins")
        self.assertEqual(quota.build_snapshot(payload)["quota"], "OK")

    def test_unknown_duration_and_duplicate_windows_are_unknown(self):
        for duration in (15, 10080, None, True):
            with self.subTest(duration=duration):
                payload = response()
                payload["rateLimits"]["primary"]["windowDurationMins"] = duration
                self.assertEqual(quota.build_snapshot(payload)["quota"], "UNKNOWN")

    def test_missing_weekly_window_is_unknown(self):
        payload = response()
        payload["rateLimits"]["secondary"] = None
        snapshot = quota.build_snapshot(payload)
        self.assertEqual(snapshot["quota"], "UNKNOWN")
        self.assertIsNone(snapshot["weekly"]["remaining_percent"])

    def test_known_closeout_still_applies_when_other_window_is_missing(self):
        payload = response(80)
        payload["rateLimits"]["secondary"] = None
        self.assertEqual(quota.build_snapshot(payload)["quota"], "CLOSEOUT")

    def test_invalid_usage_never_becomes_an_available_allowance(self):
        for invalid in (None, True, "20", -1, 101, float("nan"), float("inf")):
            with self.subTest(invalid=invalid):
                snapshot = quota.build_snapshot(response(invalid))
                self.assertEqual(snapshot["quota"], "UNKNOWN")
                self.assertIsNone(snapshot["five_hour"]["remaining_percent"])

    def test_invalid_resets_and_thresholds_are_unknown(self):
        for invalid in (True, "tomorrow", -1, float("inf")):
            with self.subTest(reset=invalid):
                payload = response()
                payload["rateLimits"]["primary"]["resetsAt"] = invalid
                self.assertEqual(quota.build_snapshot(payload)["quota"], "UNKNOWN")
        for invalid in (-1, 101, True, float("nan")):
            with self.subTest(threshold=invalid):
                self.assertEqual(quota.build_snapshot(response(), invalid)["quota"], "UNKNOWN")

    def test_multi_bucket_codex_fallback(self):
        payload = {"rateLimitsByLimitId": {"codex": response()["rateLimits"]}}
        self.assertEqual(quota.build_snapshot(payload)["quota"], "OK")

    def test_summary_discards_unknown_account_fields(self):
        payload = response()
        payload["accessToken"] = "synthetic-private-field"
        payload["rateLimits"]["planType"] = "synthetic-private-plan"
        result = quota.build_snapshot(payload)
        self.assertNotIn("synthetic-private", json.dumps(result))
        self.assertEqual(result["plan"], "unknown")

    def test_text_timestamp_uses_host_local_timezone(self):
        with patch.object(quota, "datetime") as clock:
            clock.fromtimestamp.return_value.astimezone.return_value.strftime.return_value = "LOCAL-TIME"
            formatted = quota.format_window({"remaining_percent": 80, "resets_at": 1800000000})
            clock.fromtimestamp.assert_called_once_with(1800000000)
            self.assertIn("LOCAL-TIME", formatted)

    def test_exit_codes_match_states(self):
        for state, code in (("OK", 0), ("CLOSEOUT", 10), ("UNKNOWN", 20)):
            with self.subTest(state=state), contextlib.redirect_stdout(io.StringIO()):
                snapshot = quota.build_snapshot(response())
                snapshot["quota"] = state
                self.assertEqual(quota.emit_snapshot(snapshot, as_json=True), code)


class ProtocolTests(unittest.TestCase):
    def run_protocol(self, account, config=None, limits=None):
        class FakeProcess:
            def __init__(self):
                self.stdin = io.StringIO()
                replies = [{"id": 1, "result": {}}, {"id": 2, "result": account}]
                if config is not None:
                    replies.append({"id": 3, "result": config})
                if limits is not None:
                    replies.append({"id": 4, "result": limits})
                self.stdout = io.StringIO("\n".join(json.dumps(r) for r in replies) + "\n")
                self.stopped = False

            def poll(self):
                return 0 if self.stopped else None

            def terminate(self):
                self.stopped = True

            def wait(self, timeout):
                return 0

        process = FakeProcess()
        with patch.object(quota.subprocess, "Popen", return_value=process) as launch:
            result = quota.read_rate_limits("codex-fixture")
        requests = [json.loads(line) for line in process.stdin.getvalue().splitlines()]
        self.assertEqual(launch.call_args.args[0], ["codex-fixture", "app-server", "--stdio"])
        self.assertTrue(process.stopped)
        return result, requests

    def test_app_server_confirms_account_and_route_before_reading_limits(self):
        result, requests = self.run_protocol(
            {"account": {"type": "chatgpt", "email": "synthetic@example.invalid"}, "requiresOpenaiAuth": True},
            {"config": {"model_provider": "openai"}}, response())
        self.assertEqual(quota.build_snapshot(result)["quota"], "OK")
        self.assertEqual([r["method"] for r in requests], ["initialize", "initialized", "account/read", "config/read", "account/rateLimits/read"])
        self.assertEqual(requests[2]["params"], {"refreshToken": False})
        self.assertNotIn("synthetic@example.invalid", json.dumps(result))

    def test_api_account_never_queries_plan_even_when_plan_data_is_queued(self):
        result, requests = self.run_protocol({"account": {"type": "apiKey"}, "requiresOpenaiAuth": True},
                                             {"config": {}}, response(100, 100))
        summary = quota.build_snapshot(result)
        self.assertEqual(summary["quota"], "NOT_APPLICABLE")
        self.assertIsNone(summary["five_hour"]["remaining_percent"])
        self.assertEqual([r["method"] for r in requests], ["initialize", "initialized", "account/read"])

    def test_stale_chatgpt_login_does_not_authorize_custom_provider_plan_read(self):
        result, requests = self.run_protocol(
            {"account": {"type": "chatgpt"}, "requiresOpenaiAuth": True},
            {"config": {"model_provider": "relay", "model_providers": {"relay": {"base_url": "https://relay.invalid", "api_key": "synthetic-secret"}}}}, response())
        summary = quota.build_snapshot(result)
        self.assertEqual(summary["quota"], "UNKNOWN")
        self.assertNotIn("account/rateLimits/read", [r["method"] for r in requests])
        self.assertNotIn("synthetic-secret", json.dumps(summary))

    def test_provider_without_openai_auth_ignores_stale_chatgpt_account(self):
        result, requests = self.run_protocol({"account": {"type": "chatgpt"}, "requiresOpenaiAuth": False})
        self.assertEqual(quota.build_snapshot(result)["quota"], "NOT_APPLICABLE")
        self.assertNotIn("account/rateLimits/read", [r["method"] for r in requests])

    def test_null_account_cannot_turn_a_rate_limit_fixture_into_a_plan(self):
        result, requests = self.run_protocol({"account": None, "requiresOpenaiAuth": True}, {"config": {}}, response())
        self.assertEqual(quota.build_snapshot(result)["quota"], "UNKNOWN")
        self.assertNotIn("account/rateLimits/read", [r["method"] for r in requests])

    def test_missing_provider_config_is_unknown_not_a_plan_guess(self):
        self.assertEqual(quota.classify_connection({"account": {"type": "chatgpt"}, "requiresOpenaiAuth": True}, {})[0], "UNKNOWN")
        self.assertEqual(quota.classify_connection({"account": {"type": "chatgpt"}}, {"config": {}})[0], "UNKNOWN")

    def test_custom_endpoint_and_bedrock_are_not_plan_allowance(self):
        account = {"account": {"type": "chatgpt"}, "requiresOpenaiAuth": True}
        config = {"config": {"model_providers": {"openai": {"base_url": "https://relay.invalid"}}}}
        self.assertEqual(quota.classify_connection(account, config)[0], "UNKNOWN")
        config["config"]["model_providers"]["openai"]["base_url"] = "https://api.openai.com/v1"
        self.assertEqual(quota.classify_connection(account, config)[0], "UNKNOWN")
        with patch.dict(quota.os.environ, {"OPENAI_BASE_URL": "https://relay.invalid"}):
            self.assertEqual(quota.classify_connection(account, {"config": {}})[0], "UNKNOWN")
        self.assertEqual(quota.classify_connection({"account": {"type": "amazonBedrock"}}, None)[0], "NOT_APPLICABLE")

    def test_explicit_api_and_off_work_without_cli_and_never_query_accounts(self):
        for mode in ("api", "off"):
            with self.subTest(mode=mode), patch.object(quota, "find_codex") as find, patch.object(quota, "read_rate_limits") as read:
                value = quota.get_snapshot(quota_mode=mode)
                self.assertEqual(value["quota"], "NOT_APPLICABLE")
                self.assertIsNone(value["five_hour"]["remaining_percent"])
                find.assert_not_called()
                read.assert_not_called()
            output = io.StringIO()
            with patch.object(sys, "argv", ["check_codex_quota.py", "--json", "--quota-mode", mode]), contextlib.redirect_stdout(output):
                self.assertEqual(quota.main(), 0)
            self.assertEqual(json.loads(output.getvalue())["quota"], "NOT_APPLICABLE")

    def test_missing_cli_reports_unknown(self):
        output = io.StringIO()
        with patch.object(sys, "argv", ["check_codex_quota.py", "--json"]), \
             patch.object(quota, "find_codex", return_value=None), \
             contextlib.redirect_stdout(output):
            self.assertEqual(quota.main(), 20)
        self.assertEqual(json.loads(output.getvalue())["quota"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
