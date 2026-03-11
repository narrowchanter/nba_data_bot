"""
ESPN-backed tennis schedule scraper.
"""

import pandas as pd

from .tennis_common import DEFAULT_TOURS, SITE_API_BASE, TOUR_LABELS, fetch_json, normalize_tours, tour_slug


SCHEDULE_COLUMNS = [
    "TOUR",
    "TOURNAMENT",
    "MATCH_ID",
    "DRAW",
    "ROUND",
    "START_TIME_UTC",
    "STATUS",
    "STATUS_DETAIL",
    "BEST_OF_SETS",
    "IS_MAJOR",
    "VENUE",
    "COURT",
    "PLAYER_1_ID",
    "PLAYER_1",
    "PLAYER_1_COUNTRY",
    "PLAYER_1_SCORE",
    "PLAYER_1_WINNER",
    "PLAYER_2_ID",
    "PLAYER_2",
    "PLAYER_2_COUNTRY",
    "PLAYER_2_SCORE",
    "PLAYER_2_WINNER",
    "NOTE",
]


def _score_line(competitor: dict) -> str:
    """Format a competitor's line scores as a simple set string."""
    values = []

    for line in competitor.get("linescores", []):
        score = line.get("value")
        if score is None:
            continue
        if float(score).is_integer():
            values.append(str(int(score)))
        else:
            values.append(str(score))

    return "-".join(values)


def _infer_tour(endpoint_tour: str, draw_name: str) -> str:
    """Infer ATP or WTA from the draw name when ESPN mixes events."""
    lower_draw = draw_name.lower()
    if "women" in lower_draw:
        return "WTA"
    if "men" in lower_draw:
        return "ATP"
    return TOUR_LABELS.get(endpoint_tour, endpoint_tour)


def get_tennis_schedule(
    tours: tuple[str, ...] = DEFAULT_TOURS,
    include_completed: bool = True,
) -> pd.DataFrame:
    """
    Fetch the current ESPN tennis scoreboard as a flattened singles schedule table.

    Returns match rows for active tournaments and de-duplicates overlapping feeds.
    """
    rows = []
    seen_match_ids = set()

    for endpoint_tour in normalize_tours(tours):
        scoreboard_url = f"{SITE_API_BASE}/{tour_slug(endpoint_tour)}/scoreboard"
        payload = fetch_json(scoreboard_url)

        for event in payload.get("events", []):
            tournament_name = event.get("shortName") or event.get("name")
            is_major = event.get("major", False)

            for grouping in event.get("groupings", []):
                draw_name = grouping.get("grouping", {}).get("displayName", "")
                if "singles" not in draw_name.lower():
                    continue
                inferred_tour = _infer_tour(endpoint_tour, draw_name)

                for competition in grouping.get("competitions", []):
                    status_state = competition.get("status", {}).get("type", {}).get("state")
                    if not include_completed and status_state == "post":
                        continue

                    match_id = competition.get("id")
                    if match_id in seen_match_ids:
                        continue

                    seen_match_ids.add(match_id)
                    competitors = sorted(
                        competition.get("competitors", []),
                        key=lambda item: item.get("order", 99),
                    )
                    player_1 = competitors[0] if len(competitors) > 0 else {}
                    player_2 = competitors[1] if len(competitors) > 1 else {}
                    player_1_athlete = player_1.get("athlete", {})
                    player_2_athlete = player_2.get("athlete", {})
                    note = "; ".join(item.get("text", "") for item in competition.get("notes", []))

                    rows.append(
                        {
                            "TOUR": inferred_tour,
                            "TOURNAMENT": tournament_name,
                            "MATCH_ID": match_id,
                            "DRAW": draw_name,
                            "ROUND": competition.get("round", {}).get("displayName"),
                            "START_TIME_UTC": competition.get("startDate") or competition.get("date"),
                            "STATUS": status_state,
                            "STATUS_DETAIL": competition.get("status", {}).get("type", {}).get("detail"),
                            "BEST_OF_SETS": competition.get("format", {}).get("regulation", {}).get("periods"),
                            "IS_MAJOR": is_major,
                            "VENUE": competition.get("venue", {}).get("fullName"),
                            "COURT": competition.get("venue", {}).get("court"),
                            "PLAYER_1_ID": str(player_1.get("id")) if player_1.get("id") is not None else None,
                            "PLAYER_1": player_1_athlete.get("displayName"),
                            "PLAYER_1_COUNTRY": player_1_athlete.get("flag", {}).get("alt"),
                            "PLAYER_1_SCORE": _score_line(player_1),
                            "PLAYER_1_WINNER": player_1.get("winner"),
                            "PLAYER_2_ID": str(player_2.get("id")) if player_2.get("id") is not None else None,
                            "PLAYER_2": player_2_athlete.get("displayName"),
                            "PLAYER_2_COUNTRY": player_2_athlete.get("flag", {}).get("alt"),
                            "PLAYER_2_SCORE": _score_line(player_2),
                            "PLAYER_2_WINNER": player_2.get("winner"),
                            "NOTE": note,
                        }
                    )

    if not rows:
        return pd.DataFrame(columns=SCHEDULE_COLUMNS)

    df = pd.DataFrame(rows)
    return df.sort_values(["START_TIME_UTC", "TOUR", "TOURNAMENT", "ROUND"]).reset_index(drop=True)
