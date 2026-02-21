from typing import Dict, List

# --- API-nøkler (sett disse før kjøring) ---
RAPIDAPI_KEY = "470be59979msh0fb6d549f7d2d17p1239dejsna3bdfcd1a1cf"  # API-Football (RapidAPI)
ODDS_API_KEY = "25618d8b600764e9cac5a16b2181262f"   # TheOddsAPI
FOOTBALLDATA_KEY = "6206bb1e67c34d418e7af72282d01b28"

# --- Ligaer (API-Football league IDs) ---
# Vanlige ID-er i API-Football:
#   Premier League = 39, LaLiga = 140, Serie A = 135, Bundesliga = 78, Ligue 1 = 61
LEAGUE_IDS: Dict[str, int] = {
    'EPL': 39,
    'LaLiga': 140,
    'SerieA': 135,
    'Bundesliga': 78,
}

SEASON = 2025  # 2025/26
HOME_ADV_ELO = 55.0
DRAW_NU = 0.95

# OddsAPI sports keys (TheOddsAPI). Juster ved behov.
ODDS_SPORT_KEYS: Dict[str, str] = {
    'EPL': 'soccer_epl',
    'LaLiga': 'soccer_spain_la_liga',
    'SerieA': 'soccer_italy_serie_a',
    'Bundesliga': 'soccer_germany_bundesliga',
}

# Bookmakere du ønsker (keys som TheOddsAPI bruker)
BOOKMAKERS: List[str] = [
    'bet365', 'pinnacle', 'williamhill'
]

