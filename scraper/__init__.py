"""
Public scraper package exports.
"""


def get_last5_form():
    from .teamrankings import get_last5_form as _get_last5_form

    return _get_last5_form()


def get_advanced_stats():
    from .nba_stats import get_advanced_stats as _get_advanced_stats

    return _get_advanced_stats()


def get_four_factors():
    from .nba_stats import get_four_factors as _get_four_factors

    return _get_four_factors()


def get_defense_stats():
    from .nba_stats import get_defense_stats as _get_defense_stats

    return _get_defense_stats()


def get_injury_report():
    from .injury_report import get_injury_report as _get_injury_report

    return _get_injury_report()


__all__ = [
    "get_last5_form",
    "get_advanced_stats",
    "get_four_factors",
    "get_defense_stats",
    "get_injury_report",
]
