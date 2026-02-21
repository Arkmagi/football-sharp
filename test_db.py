import sqlite3, pandas as pd
conn = sqlite3.connect('data/footy.sqlite')

# 1) Se hvilke fixtures som er lagt inn og hvilken STATUS de har
df_fix = pd.read_sql_query("SELECT fixture_id, league, utc_kickoff, home_team_id, away_team_id, status FROM fixtures ORDER BY utc_kickoff", conn)
print(df_fix)

# 2) Se hva som ligger i probs
df_probs = pd.read_sql_query("SELECT * FROM probs", conn)
print(df_probs)

# 3) Finn fixtures uten probs
df_join = pd.read_sql_query("""
SELECT f.fixture_id, f.league, f.utc_kickoff, f.home_team_id, f.away_team_id, f.status,
       p.p_home, p.p_draw, p.p_away
FROM fixtures f
LEFT JOIN probs p ON p.fixture_id = f.fixture_id
ORDER BY f.utc_kickoff
""", conn)
print(df_join)


