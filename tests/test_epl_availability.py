import unittest
from unittest.mock import patch

import requests

from scraper.epl_availability import (
    AVAILABILITY_COLUMNS,
    BOOTSTRAP_URLS,
    get_epl_availability_report,
    normalize_status_bucket,
    summarize_availability_by_team,
)


SAMPLE_PAYLOAD = {
    "teams": [
        {"id": 1, "name": "Spurs"},
        {"id": 2, "name": "Nott'm Forest"},
        {"id": 3, "name": "Mystery FC"},
    ],
    "element_types": [
        {"id": 1, "singular_name_short": "GKP"},
        {"id": 2, "singular_name_short": "DEF"},
        {"id": 3, "singular_name_short": "MID"},
    ],
    "elements": [
        {
            "id": 101,
            "first_name": "Jamie",
            "second_name": "Doubt",
            "team": 1,
            "element_type": 3,
            "status": "d",
            "chance_of_playing_this_round": 50,
            "chance_of_playing_next_round": 75,
            "news": "Being assessed ahead of kickoff.",
            "news_updated": "2026-03-14T08:00:00Z",
        },
        {
            "id": 102,
            "first_name": "James",
            "second_name": "Available",
            "team": 1,
            "element_type": 2,
            "status": "a",
            "chance_of_playing_this_round": 100,
            "chance_of_playing_next_round": 100,
            "news": "Available after illness.",
            "news_added": "2026-03-14T09:15:00Z",
        },
        {
            "id": 103,
            "first_name": "Chris",
            "second_name": "Injured",
            "team": 2,
            "element_type": 1,
            "status": "i",
            "chance_of_playing_this_round": 0,
            "chance_of_playing_next_round": 25,
            "news": "Hamstring issue.",
            "news_added": "2026-03-13T10:00:00Z",
        },
        {
            "id": 104,
            "first_name": "Sam",
            "second_name": "Banned",
            "team": 2,
            "element_type": 2,
            "status": "a",
            "chance_of_playing_this_round": 0,
            "chance_of_playing_next_round": 0,
            "news": "Serving a suspension after a red card.",
            "news_added": "2026-03-12T11:00:00Z",
        },
        {
            "id": 105,
            "first_name": "Pat",
            "second_name": "Mystery",
            "team": 3,
            "element_type": 99,
            "status": "x",
            "chance_of_playing_this_round": None,
            "chance_of_playing_next_round": None,
            "news": "",
            "news_added": None,
        },
        {
            "id": 106,
            "first_name": "Skip",
            "second_name": "NoTeam",
            "team": 99,
            "element_type": 1,
            "status": "i",
            "chance_of_playing_this_round": 0,
            "chance_of_playing_next_round": 0,
            "news": "Should be skipped because the team is missing.",
        },
        "not-a-dict",
    ],
}


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class NormalizeStatusBucketTests(unittest.TestCase):
    def test_normalize_status_bucket_covers_required_buckets(self):
        cases = (
            ({"raw_status": "a", "chance_of_playing_this_round": 100}, "available"),
            ({"raw_status": "d", "chance_of_playing_this_round": 50}, "questionable"),
            ({"raw_status": "i", "chance_of_playing_this_round": 0}, "out"),
            ({"raw_status": "a", "reason": "Serving a suspension after a red card."}, "suspended"),
            ({"raw_status": "x"}, "unknown"),
        )

        for kwargs, expected in cases:
            with self.subTest(kwargs=kwargs):
                self.assertEqual(normalize_status_bucket(**kwargs), expected)


class EplAvailabilityTests(unittest.TestCase):
    @patch("scraper.epl_availability.requests.get", return_value=FakeResponse(SAMPLE_PAYLOAD))
    def test_get_epl_availability_report_normalizes_rows_and_team_names(self, mock_get):
        df = get_epl_availability_report(fetched_at="2026-03-14T10:30:00Z")

        self.assertEqual(list(df.columns), AVAILABILITY_COLUMNS)
        self.assertEqual(len(df), 5)
        self.assertEqual(df["TEAM"].tolist(), [
            "Mystery FC",
            "Nottingham Forest",
            "Nottingham Forest",
            "Tottenham Hotspur",
            "Tottenham Hotspur",
        ])
        self.assertEqual(df["STATUS_BUCKET"].tolist(), [
            "unknown",
            "suspended",
            "questionable",
            "questionable",
            "available",
        ])
        self.assertEqual(df["POSITION"].tolist(), ["", "DEF", "GKP", "MID", "DEF"])
        self.assertTrue((df["SOURCE"] == BOOTSTRAP_URLS[0]).all())
        self.assertTrue((df["FETCHED_AT"] == "2026-03-14T10:30:00Z").all())

        doubtful_row = df.loc[df["PLAYER_NAME"] == "Jamie Doubt"].iloc[0]
        self.assertEqual(doubtful_row["STATUS_TIMESTAMP"], "2026-03-14T08:00:00Z")
        self.assertEqual(int(doubtful_row["CHANCE_OF_PLAYING_THIS_ROUND"]), 50)
        self.assertEqual(doubtful_row["TEAM"], "Tottenham Hotspur")

        injured_row = df.loc[df["PLAYER_NAME"] == "Chris Injured"].iloc[0]
        self.assertEqual(injured_row["STATUS_BUCKET"], "questionable")
        self.assertEqual(injured_row["TEAM"], "Nottingham Forest")

        mystery_row = df.loc[df["PLAYER_NAME"] == "Pat Mystery"].iloc[0]
        self.assertEqual(mystery_row["TEAM"], "Mystery FC")
        self.assertEqual(mystery_row["STATUS_BUCKET"], "unknown")

        mock_get.assert_called_once_with(BOOTSTRAP_URLS[0], headers=unittest.mock.ANY, timeout=30)

    @patch(
        "scraper.epl_availability.requests.get",
        side_effect=[requests.Timeout("boom"), FakeResponse(SAMPLE_PAYLOAD)],
    )
    def test_primary_feed_failure_falls_back_to_secondary_source(self, mock_get):
        df = get_epl_availability_report(fetched_at="2026-03-14T10:30:00Z")

        self.assertEqual(len(df), 5)
        self.assertTrue((df["SOURCE"] == BOOTSTRAP_URLS[1]).all())
        self.assertEqual(mock_get.call_count, 2)

    @patch(
        "scraper.epl_availability.requests.get",
        side_effect=[FakeResponse({"bad": "shape"}), FakeResponse({"still": "bad"})],
    )
    def test_malformed_payloads_return_empty_schema(self, mock_get):
        df = get_epl_availability_report(fetched_at="2026-03-14T10:30:00Z")

        self.assertTrue(df.empty)
        self.assertEqual(list(df.columns), AVAILABILITY_COLUMNS)
        self.assertEqual(mock_get.call_count, 2)

    @patch("scraper.epl_availability.requests.get", return_value=FakeResponse(SAMPLE_PAYLOAD))
    def test_summarize_availability_by_team_groups_players_by_bucket(self, mock_get):
        df = get_epl_availability_report(fetched_at="2026-03-14T10:30:00Z")

        summary = summarize_availability_by_team(df)

        self.assertEqual(summary["Nottingham Forest"]["suspended"], ["Sam Banned"])
        self.assertEqual(summary["Nottingham Forest"]["questionable"], ["Chris Injured"])
        self.assertEqual(summary["Tottenham Hotspur"]["available"], ["James Available"])


if __name__ == "__main__":
    unittest.main()
