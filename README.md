# Footy Pipeline (skjelett)

** This doesn't workyet :)


Et minimalt prosjektoppsett for henting (scraping/API), beregning og presentasjon av fotballdata.

## Innhold
- **scraping/** – moduler for å hente fixtures, odds og xG
- **models/** – Elo og sannsynlighetsberegning (3-veis Davidson)
- **pipeline/** – daglig kjøring, normalisering og limkode
- **dashboard/** – enkelt Streamlit-dashboard
- **utils/** – database, konfig, logging
- **data/** – rå- og prosesserte data samt SQLite-database

## Kom raskt i gang
1. Opprett og aktiver et Python-miljø (3.10+ anbefales).
2. Installer avhengigheter:
   ```bash
   pip install -r requirements.txt
   ```
3. Sett API-nøkler i `utils/config.py`.
4. Initialiser database og kjør en enkel pipeline:
   ```bash
   python -m pipeline.run_daily --init --days 2 --leagues EPL
   ```
5. Start dashboard:
   ```bash
   streamlit run dashboard/app.py
   ```

## Merk
- API-Football brukes som eksempel for fixtures. Odds hentes fra TheOddsAPI.
- xG fra Understat er uoffisielt og kan bryte hvis HTML endres. Koden er derfor modulær og lett å vedlikeholde.
- Alle tider lagres som UTC.

## Lisens og etikk
- Følg vilkårene til dataleverandørene. Ikke overdriv frekvens. Respekter robots.txt.
