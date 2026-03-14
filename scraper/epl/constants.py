"""
Constants for EPL team identifiers and aliases.
"""

from .types import TeamAliasGroups, TeamIdMap

MATCH_KEY_PREFIX = "epl"

TEAM_IDS: TeamIdMap = {
    "Arsenal": "arsenal",
    "Aston Villa": "aston-villa",
    "Bournemouth": "bournemouth",
    "Brentford": "brentford",
    "Brighton and Hove Albion": "brighton",
    "Burnley": "burnley",
    "Chelsea": "chelsea",
    "Crystal Palace": "crystal-palace",
    "Everton": "everton",
    "Fulham": "fulham",
    "Ipswich Town": "ipswich",
    "Leeds United": "leeds",
    "Leicester City": "leicester",
    "Liverpool": "liverpool",
    "Luton Town": "luton",
    "Manchester City": "man-city",
    "Manchester United": "man-united",
    "Newcastle United": "newcastle",
    "Norwich City": "norwich",
    "Nottingham Forest": "nottingham-forest",
    "Sheffield United": "sheffield-united",
    "Southampton": "southampton",
    "Sunderland": "sunderland",
    "Tottenham Hotspur": "tottenham",
    "Watford": "watford",
    "West Ham United": "west-ham",
    "Wolverhampton Wanderers": "wolves",
}

TEAM_ALIASES: TeamAliasGroups = {
    "Arsenal": ("arsenal", "arsenal fc"),
    "Aston Villa": ("aston villa", "aston villa fc", "villa"),
    "Bournemouth": ("bournemouth", "afc bournemouth", "a.f.c. bournemouth"),
    "Brentford": ("brentford", "brentford fc"),
    "Brighton and Hove Albion": (
        "brighton and hove albion",
        "brighton & hove albion",
        "brighton",
    ),
    "Burnley": ("burnley", "burnley fc"),
    "Chelsea": ("chelsea", "chelsea fc"),
    "Crystal Palace": ("crystal palace", "palace"),
    "Everton": ("everton", "everton fc"),
    "Fulham": ("fulham", "fulham fc"),
    "Ipswich Town": ("ipswich town", "ipswich"),
    "Leeds United": ("leeds united", "leeds", "leeds utd"),
    "Leicester City": ("leicester city", "leicester"),
    "Liverpool": ("liverpool", "liverpool fc"),
    "Luton Town": ("luton town", "luton"),
    "Manchester City": ("manchester city", "man city", "manchester city fc"),
    "Manchester United": (
        "manchester united",
        "man united",
        "man utd",
        "manchester utd",
        "manchester united fc",
    ),
    "Newcastle United": ("newcastle united", "newcastle", "newcastle utd"),
    "Norwich City": ("norwich city", "norwich"),
    "Nottingham Forest": ("nottingham forest", "forest", "nottm forest", "nott'm forest"),
    "Sheffield United": ("sheffield united", "sheffield utd", "sheff utd"),
    "Southampton": ("southampton", "southampton fc", "saints"),
    "Sunderland": ("sunderland", "sunderland afc"),
    "Tottenham Hotspur": ("tottenham hotspur", "tottenham", "spurs"),
    "Watford": ("watford", "watford fc"),
    "West Ham United": ("west ham united", "west ham"),
    "Wolverhampton Wanderers": (
        "wolverhampton wanderers",
        "wolverhampton",
        "wolves",
    ),
}

CANONICAL_TEAMS = tuple(TEAM_IDS.keys())
