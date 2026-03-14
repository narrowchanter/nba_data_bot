import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

import main


def make_nba_frames() -> dict[str, pd.DataFrame]:
    return {
        "last5": pd.DataFrame(
            [
                {
                    "TEAM": "Boston Celtics",
                    "L5_WINS": 4,
                    "L5_LOSSES": 1,
                    "L5_RATING": 8.7,
                }
            ]
        ),
        "advanced": pd.DataFrame(
            [
                {
                    "TEAM_NAME": "Boston Celtics",
                    "W": 52,
                    "L": 18,
                    "NET_RATING": 9.8,
                    "OFF_RATING": 121.3,
                    "DEF_RATING": 111.5,
                    "PACE": 99.4,
                }
            ]
        ),
        "fourfactors": pd.DataFrame(
            [
                {
                    "TEAM_NAME": "Boston Celtics",
                    "EFG_PCT": 58.2,
                    "TOV_PCT": 12.5,
                    "OREB_PCT": 27.4,
                    "FT_RATE": 0.214,
                }
            ]
        ),
        "defense": pd.DataFrame(
            [
                {
                    "TEAM_NAME": "Boston Celtics",
                    "OPP_FG_PCT": 45.1,
                    "OPP_FG3_PCT": 34.8,
                    "OPP_PTS": 108.2,
                }
            ]
        ),
        "injuries": pd.DataFrame(
            [
                {
                    "TEAM": "Boston Celtics",
                    "PLAYER_NAME": "Jayson Tatum",
                    "CURRENT_STATUS": "QUESTIONABLE",
                    "REASON": "Ankle soreness",
                }
            ]
        ),
    }


class MainDispatchTests(unittest.TestCase):
    def test_main_dispatches_supported_commands_with_default_args(self):
        command_map = {
            "all": "cmd_all",
            "last5": "cmd_last5",
            "advanced": "cmd_advanced",
            "fourfactors": "cmd_fourfactors",
            "defense": "cmd_defense",
            "injuries": "cmd_injuries",
            "markdown": "cmd_markdown",
        }

        for command_name, function_name in command_map.items():
            with self.subTest(command=command_name):
                with patch.object(main, function_name, return_value={}) as command_mock:
                    with patch.object(sys, "argv", ["main.py", command_name]):
                        result = main.main()

                self.assertIsNone(result)
                command_mock.assert_called_once()
                parsed_args = command_mock.call_args.args[0]
                self.assertEqual(parsed_args.command, command_name)
                self.assertEqual(parsed_args.output, "./output")
                self.assertEqual(parsed_args.format, "csv")


class MainMarkdownSmokeTests(unittest.TestCase):
    def test_cmd_markdown_writes_expected_nba_sections(self):
        frames = make_nba_frames()

        with tempfile.TemporaryDirectory() as tmpdir:
            args = SimpleNamespace(output=tmpdir)

            with patch.object(main, "get_last5_form", return_value=frames["last5"]):
                with patch.object(main, "get_advanced_stats", return_value=frames["advanced"]):
                    with patch.object(main, "get_four_factors", return_value=frames["fourfactors"]):
                        with patch.object(main, "get_defense_stats", return_value=frames["defense"]):
                            with patch.object(main, "get_injury_report", return_value=frames["injuries"]):
                                results = main.cmd_markdown(args)

            self.assertEqual(set(results.keys()), {"last5", "advanced", "fourfactors", "defense", "injuries"})

            markdown_path = Path(tmpdir) / "nba_data.md"
            self.assertTrue(markdown_path.exists())

            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn("# NBA Stats & Injury Report", markdown)
            self.assertIn("## Team Standings & Ratings", markdown)
            self.assertIn("## Last 5 Games Form", markdown)
            self.assertIn("## Four Factors", markdown)
            self.assertIn("## Defense Stats", markdown)
            self.assertIn("## Injury Report", markdown)
            self.assertIn("### Boston Celtics", markdown)
            self.assertIn("Jayson Tatum", markdown)
            self.assertIn("QUESTIONABLE", markdown)


if __name__ == "__main__":
    unittest.main()
