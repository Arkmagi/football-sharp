
import requests
from utils.config import ODDS_API_KEY, ODDS_SPORT_KEYS

sport_key = ODDS_SPORT_KEYS["EPL"]

r = requests.get(
    f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds",
    params={
        "apiKey": ODDS_API_KEY,
        "markets": "h2h",
        "regions": "eu,uk",
        "dateFormat": "iso"
    }
)

print(r.status_code)
events = r.json()
print(events[0])         # første event (full JSON)
print(events[0].keys())  # hvilke keys har eventet?
