import unittest
from unittest.mock import patch

import requests

from scraper.epl_standings_form import STANDINGS_COLUMNS, get_epl_standings_form


SAMPLE_PAYLOAD = [
    {
        "MatchNumber": 2,
        "RoundNumber": 1,
        "DateUtc": "2025-08-16 11:30:00Z",
        "Location": "Bravo Park",
        "HomeTeam": "Bravo",
        "AwayTeam": "Charlie",
        "HomeTeamScore": 1,
        "AwayTeamScore": 1,
    },
    {
        "MatchNumber": 1,
        "RoundNumber": 1,
        "DateUtc": "2025-08-15 19:00:00Z",
        "Location": "Alpha Park",
        "HomeTeam": "Alpha",
        "AwayTeam": "Bravo",
        "HomeTeamScore": 2,
        "AwayTeamScore": 0,
    },
    {
        "MatchNumber": 4,
        "RoundNumber": 2,
        "DateUtc": "2025-08-23 14:00:00Z",
        "Location": "Charlie Park",
        "HomeTeam": "Charlie",
        "AwayTeam": "Alpha",
        "HomeTeamScore": 0,
        "AwayTeamScore": 3,
    },
    {
        "MatchNumber": 3,
        "RoundNumber": 2,
        "DateUtc": "2025-08-22 19:00:00Z",
        "Location": "Delta Park",
        "HomeTeam": "Bravo",
        "AwayTeam": "Delta",
        "HomeTeamScore": None,
        "AwayTeamScore": None,
    },
]


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class EplStandingsFormTests(unittest.TestCase):
    @patch("scraper.epl_common.requests.get", return_value=FakeResponse(SAMPLE_PAYLOAD))
    def test_get_epl_standings_form_builds_table_and_recent_form(self, mock_get):
        df = get_epl_standings_form(season_start_year=2025)

        self.assertEqual(list(df.columns), STANDINGS_COLUMNS)
        self.assertEqual(df["TEAM"].tolist(), ["Alpha", "Bravo", "Charlie", "Delta"])
        self.assertEqual(df["POSITION"].tolist(), [1, 2, 3, 4])

        alpha = df[df["TEAM"] == "Alpha"].iloc[0]
        self.assertEqual(alpha["PLAYED"], 2)
        self.assertEqual(alpha["WINS"], 2)
        self.assertEqual(alpha["POINTS"], 6)
        self.assertEqual(alpha["GOAL_DIFF"], 5)
        self.assertEqual(alpha["FORM"], "WW")
        self.assertEqual(alpha["FORM_POINTS"], 6)

        bravo = df[df["TEAM"] == "Bravo"].iloc[0]
        self.assertEqual(bravo["FORM"], "LD")
        self.assertEqual(bravo["POINTS"], 1)
        self.assertEqual(bravo["GOAL_DIFF"], -2)

        delta = df[df["TEAM"] == "Delta"].iloc[0]
        self.assertEqual(delta["PLAYED"], 0)
        self.assertEqual(delta["FORM"], "")
        self.assertEqual(delta["POINTS"], 0)
        mock_get.assert_called_once()

    @patch("scraper.epl_common.requests.get", side_effect=requests.RequestException("boom"))
    def test_errors_return_empty_standings_schema(self, mock_get):
        df = get_epl_standings_form(season_start_year=2025)

        self.assertTrue(df.empty)
        self.assertEqual(list(df.columns), STANDINGS_COLUMNS)
        mock_get.assert_called_once()


if __name__ == "__main__":
    unittest.main()
