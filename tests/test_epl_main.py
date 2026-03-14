import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import epl_main


class EPLMainDispatchTests(unittest.TestCase):
    def test_main_dispatches_supported_commands_with_default_args(self):
        command_map = {
            "markdown": "cmd_markdown",
            "data": "cmd_data",
            "matches_today": "cmd_matches_today",
            "quality_report": "cmd_quality_report",
        }

        for command_name, function_name in command_map.items():
            with self.subTest(command=command_name):
                with patch.object(epl_main, function_name, return_value=0) as command_mock:
                    with patch.object(sys, "argv", ["epl_main.py", command_name]):
                        exit_code = epl_main.main()

                self.assertEqual(exit_code, 0)
                command_mock.assert_called_once()
                parsed_args = command_mock.call_args.args[0]
                self.assertEqual(parsed_args.command, command_name)
                self.assertEqual(parsed_args.output, "./data")


class EPLMainRenderTests(unittest.TestCase):
    def test_render_epl_data_includes_player_stats_injuries_and_sanity_sections(self):
        content = epl_main.render_epl_data(epl_main.LAST_UPDATED)

        self.assertIn("# EPL Match Data", content)
        self.assertIn("## Match Features", content)
        self.assertIn("## Player Stats Snapshot", content)
        self.assertIn("## Injury Watch", content)
        self.assertIn("## Sanity Checks", content)
        self.assertIn("Bukayo Saka", content)
        self.assertIn("Reece James", content)
        self.assertIn("| team | player | window | goals | assists | shots_on_target | chances_created | note |", content)

    def test_render_epl_matches_today_includes_injury_watch_and_refresh_fields(self):
        content = epl_main.render_epl_matches_today(epl_main.LAST_UPDATED)

        self.assertIn("# EPL Matches Today", content)
        self.assertIn("## Injury Watch", content)
        self.assertIn("## Pre-Kickoff Watchlist", content)
        self.assertIn("player_stats_refresh", content)
        self.assertIn("injury_refresh", content)

    def test_render_epl_quality_report_includes_new_quality_metrics(self):
        content = epl_main.render_epl_quality_report(epl_main.LAST_UPDATED)

        self.assertIn("# EPL Quality Report", content)
        self.assertIn("## Run Summary", content)
        self.assertIn("## Coverage", content)
        self.assertIn("## Guardrails", content)
        self.assertIn("## Sanity Checks", content)
        self.assertIn("| player_stats_rows | 4 |", content)
        self.assertIn("| injury_rows | 3 |", content)
        self.assertIn("| matches_with_player_stats | 1 |", content)
        self.assertIn("| matches_with_injury_data | 1 |", content)
        self.assertIn("| candidate_row_schema | PASS |", content)
        self.assertIn("| player_stats_shape | PASS |", content)


class EPLMainSmokeTests(unittest.TestCase):
    def test_cmd_markdown_writes_expected_epl_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            args = SimpleNamespace(output=tmpdir)

            exit_code = epl_main.cmd_markdown(args)

            self.assertEqual(exit_code, 0)

            data_path = Path(tmpdir) / "epl_data.md"
            matches_path = Path(tmpdir) / "epl_matches_today.md"
            quality_path = Path(tmpdir) / "epl_quality_report.md"

            self.assertTrue(data_path.exists())
            self.assertTrue(matches_path.exists())
            self.assertTrue(quality_path.exists())

            data_content = data_path.read_text(encoding="utf-8")
            matches_content = matches_path.read_text(encoding="utf-8")
            quality_content = quality_path.read_text(encoding="utf-8")

            self.assertIn("## Player Stats Snapshot", data_content)
            self.assertIn("## Injury Watch", data_content)
            self.assertIn("## Sanity Checks", data_content)
            self.assertIn("## Injury Watch", matches_content)
            self.assertIn("player_stats_refresh", matches_content)
            self.assertIn("## Coverage", quality_content)
            self.assertIn("| player_stats_rows | 4 |", quality_content)
            self.assertIn("| injury_rows | 3 |", quality_content)


if __name__ == "__main__":
    unittest.main()
