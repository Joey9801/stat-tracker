from __future__ import division

import numpy as np
from scipy.stats import norm
import psycopg2, psycopg2.extras

# Handicaps for different team sizes
magic_K = [None, -0.6, 0, 0.2, -0.1]  # 1-indexed

# This should be on the scale of typical differences between skills
sigma = 1

def _tau_phi(reds, blues):
    """Probability that the red team wins a certain point"""

    assert set(reds.keys()) & set(blues.keys()) == set()
    assert 1 <= len(reds) <= 4
    assert 1 <= len(blues) <= 4

    absI = float(len(reds))
    absJ = float(len(blues))
    K_I = magic_K[len(reds)]
    K_J = magic_K[len(blues)]
    tau = sum(reds.values()) / absI - sum(blues.values()) / absJ + K_I - K_J
    phi = sigma * np.sqrt( 1 / absI + 1 / absJ )
    return tau, phi

def _pwp_tauphi(tau, phi):
    return norm.cdf( tau / phi )

def _point_win_probability(reds, blues):
    return _pwp_tauphi(*_tau_phi(reds, blues))

def no_points_condition(reds, blues):
    return (4 in reds or 4 in blues)

def skill_update(reds, blues, red_score, blue_score):
    """
    reds, blues should be dictionaries mapping player_id to current
    skill.
    
    Returns two floats:  delta_red, delta_blue
    """

    assert red_score >= 0 and blue_score >= 0
    assert red_score + blue_score > 0
    assert red_score != blue_score

    if no_points_condition(reds, blues):
        return 0., 0.

    tau, phi = _tau_phi(reds, blues)
    E = _pwp_tauphi(tau, phi)
    observed_E = red_score / (red_score + blue_score)
    # since E \in (0, 1), target_E \in (0, 1) and so the PPF
    # will hopefully not be +/- inf  :-)
    target_E = 0.8 * E + 0.2 * observed_E

    x = norm.ppf(target_E)
    delta = (x * phi - tau) * 0.5

    return delta, -delta

def predict_score(reds, blues, points=10):
    """
    Predict the score of a game; returns red_score, blue_score
    """

    E = _point_win_probability(reds, blues)

    if E > 0.5:
        return points, points * (1 - E) / E
    else:
        return points * E / (1 - E), points
        
def update_score(cur, game):
    """Updates players score for a single game_id"""
    
    query1 = "SELECT games_players.player_id, players.score, games_players.team FROM games_players " \
             "JOIN players ON games_players.player_id=players.id WHERE games_players.game_id=%s"
    query2 = "UPDATE players SET score=score+%s WHERE id IN %s"
    query3 = "UPDATE games_players SET score=players.score FROM players " \
             "WHERE players.id = games_players.player_id AND games_players.game_id=%s;"
    
    game_id, red_score, blue_score = game['id'], game['red_score'], game['blue_score']
    
    reds = dict()
    blues = dict()
    cur.execute(query1, (game_id,))
    for row in cur.fetchall():
        team, player, score = row['team'], row['player_id'], row['score']
        if team=='red':
            reds[player] = score
        else:
            blues[player] = score
    
    adj_red, adj_blue = skill_update(reds, blues, red_score, blue_score)
    
    cur.execute(query2, (adj_red, tuple(reds)))
    cur.execute(query2, (adj_blue, tuple(blues)))
    cur.execute(query3, (game_id,))
 
def _get_scores(cur, players):
    query1 = "SELECT id, score FROM players WHERE id IN %s"
    cur.execute(query1, (tuple(players), ))
    return {r["id"]: r["score"] for r in cur}

def lookup_predict_score(cur, reds, blues):
    """
    Predicts the scores from a list of team members
    
    Returns red_score, blue_score
    """

    reds = _get_scores(cur, reds)
    blues = _get_scores(cur, blues)
    return predict_score(reds, blues)

def lookup_predict_updates(cur, reds, blues):
    """
    Predicts the score updates for various potential final scores.

    Returns a dictionary mapping possible final scores (a pair of integers)
    to pairs (red_adjustment, blue_adjustment).
    """

    reds = _get_scores(cur, reds)
    blues = _get_scores(cur, blues)

    scores = [(10, i) for i in range(10)] + [(i, 10) for i in range(10)]
    return {(red_score, blue_score): skill_update(reds, blues, red_score, blue_score)
            for red_score, blue_score in scores}

def recalculate_scores():
    conn = psycopg2.connect("dbname=foosball")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("UPDATE players SET score=0");
    cur.execute("UPDATE games_players SET score=0");
    cur.execute("SELECT * FROM games order by \"timestamp\" asc");
    for game in cur.fetchall():
        update_score(cur, game)
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    recalculate_scores()
