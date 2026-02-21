# bootstrap_create_project.py
# -----------------------------------------
# Oppretter komplett "Footy Pipeline"-skjelett lokalt:
# mapper, kodefiler, DB-skjema, enkel Elo (Davidson), fixtures/odds/xG-scrapers
# og Streamlit-dashboard. Kjør i en tom mappe.
import os
from pathlib import Path

def write(path: str, content: str):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

# --- README ---
write("README.md", """# Footy Pipeline (skjelett)

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
  