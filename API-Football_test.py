import requests

HEADERS = {
    "X-RapidAPI-Key": "<LIM INN DIN NØKKEL HER>",
    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
}

# (A) Ping status – krever bare gyldig abonnement
r = requests.get("https://api-football-v1.p.rapidapi.com/v3/status", headers=HEADERS, timeout=30)
print("Status:", r.status_code)
print(r.text[:350])

# (B) Ping leagues – også “ufarlig” kall
r2 = requests.get("https://api-football-v1.p.rapidapi.com/v3/leagues", headers=HEADERS, timeout=30)
print("Leagues:", r2.status_code)
print(r2.text[:350])
