import math

def elo_3way(home_elo: float, away_elo: float, home_adv: float = 55.0, nu: float = 0.95):
    """Davidson-modell for 3-veis sannsynligheter basert på Elo-diff.
    Returnerer (p_home, p_draw, p_away) som summerer til 1.
    """
    elo_diff = (home_elo + home_adv) - away_elo
    s = 10 ** (elo_diff / 400.0)
    root = math.sqrt(s)
    Z = s + 1.0 + 2.0 * nu * root
    pH = s / Z
    pD = (2.0 * nu * root) / Z
    pA = 1.0 / Z
    return pH, pD, pA