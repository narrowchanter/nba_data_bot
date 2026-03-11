"""
ESPN-backed tennis rankings scraper.
"""

import pandas as pd

from .tennis_common import (
    CORE_API_BASE,
    DEFAULT_TOURS,
    TOUR_LABELS,
    fetch_json,
    normalize_ref,
    normalize_tours,
    tour_slug,
)


RANKING_COLUMNS = [
    "TOUR",
    "RANK",
    "PREVIOUS_RANK",
    "RANK_POINTS",
    "TREND",
    "PLAYER_ID",
    "PLAYER",
    "SHORT_NAME",
    "COUNTRY",
    "AGE",
    "HAND",
    "ACTIVE",
    "PLAYER_URL",
    "LAST_UPDATED",
]


def _get_ranking_payload(tour: str) -> dict:
    """Fetch the latest ranking payload for a tour."""
    index_url = f"{CORE_API_BASE}/leagues/{tour}/rankings"
    index_payload = fetch_json(index_url)
    ranking_ref = normalize_ref(index_payload["items"][0]["$ref"])
    return fetch_json(ranking_ref)


def _get_athlete_payload(ref: str) -> dict:
    """Fetch a player payload from an ESPN ref."""
    return fetch_json(normalize_ref(ref))


def get_tennis_rankings(
    tours: tuple[str, ...] = DEFAULT_TOURS,
    top_n: int | None = 20,
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Fetch the latest ATP and WTA rankings from ESPN.

    Returns a DataFrame with player identity, ranking points, and basic bio fields.
    """
    rows = []
    row_limit = limit if limit is not None else top_n

    for tour in normalize_tours(tours):
        ranking_payload = _get_ranking_payload(tour_slug(tour))
        last_updated = ranking_payload.get("lastUpdated")

        ranks = ranking_payload.get("ranks", [])
        if row_limit is not None:
            ranks = ranks[:row_limit]

        for rank_entry in ranks:
            athlete = _get_athlete_payload(rank_entry["athlete"]["$ref"])
            links = athlete.get("links", [])
            player_url = next(
                (link["href"] for link in links if "playercard" in link.get("rel", [])),
                "",
            )
            country = athlete.get("citizenshipCountry", {}).get("abbreviation")
            hand = athlete.get("hand", {}).get("displayValue")
            status = athlete.get("status", {}).get("type")

            rows.append(
                {
                    "TOUR": TOUR_LABELS.get(tour, tour),
                    "RANK": rank_entry.get("current"),
                    "PREVIOUS_RANK": rank_entry.get("previous"),
                    "RANK_POINTS": rank_entry.get("points"),
                    "TREND": rank_entry.get("trend"),
                    "PLAYER_ID": str(athlete.get("id")) if athlete.get("id") is not None else None,
                    "PLAYER": athlete.get("displayName"),
                    "SHORT_NAME": athlete.get("shortName"),
                    "COUNTRY": country,
                    "AGE": athlete.get("age"),
                    "HAND": hand,
                    "ACTIVE": status == "active",
                    "PLAYER_URL": player_url,
                    "LAST_UPDATED": last_updated,
                }
            )

    if not rows:
        return pd.DataFrame(columns=RANKING_COLUMNS)

    df = pd.DataFrame(rows)
    return df.sort_values(["TOUR", "RANK", "PLAYER"]).reset_index(drop=True)
