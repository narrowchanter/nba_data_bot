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

            self.assertIn("# EPL Match Data", data_content)
            self.assertIn("## Candidate Matches", data_content)
            self.assertIn("Arsenal", data_content)
            self.assertIn("# EPL Matches Today", matches_content)
            self.assertIn("## Pre-Kickoff Watchlist", matches_content)
            self.assertIn("# EPL Quality Report", quality_content)
            self.assertIn("## Guardrails", quality_content)


if __name__ == "__main__":
    unittest.main()
