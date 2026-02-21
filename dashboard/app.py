import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title='Footy Dashboard', layout='wide')

conn = sqlite3.connect('data/footy.sqlite')

st.title('Dagens og kommende kamper')

df = pd.read_sql_query(
    """
    SELECT f.league, f.season, f.utc_kickoff, f.home_team_id, f.away_team_id,
           p.p_home, p.p_draw, p.p_away, p.model
    FROM fixtures f
    LEFT JOIN probs p ON p.fixture_id = f.fixture_id
    WHERE date(f.utc_kickoff) >= date('now')
    ORDER BY f.utc_kickoff
    """,
    conn,
)

st.caption('Alle tider i UTC. Sannsynligheter fra Elo (Davidson).')

if df.empty:
    st.info('Ingen data enda. Kjør pipeline først: `python -m pipeline.run_daily --init --days 2 --leagues EPL`')
else:
    st.dataframe(df.style.format({'p_home': '{:.3f}', 'p_draw': '{:.3f}', 'p_away': '{:.3f}'}))