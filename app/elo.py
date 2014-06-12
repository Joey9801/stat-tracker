import numpy as np
from scipy.stats import binom, norm
import psycopg2, psycopg2.extras

# Averaging & handicaps for different team sizes
magic_K = [None, 0.6, 0.5, 0.4, 0.1]  # 1-indexed

# Adjustments will be in [-update_magnitude, update_magnitude]
# sizes
update_magnitude = 0.025

# This should be on the scale of typical differences between skills
sigma = 1

def _point_win_probability(reds, blues):
    """Probability that the red team wins a certain point"""

    assert set(reds.keys()) & set(blues.keys()) == set()
    assert 1 <= len(reds) <= 4
    assert 1 <= len(blues) <= 4

    K_I = magic_K[len(reds)]
    K_J = magic_K[len(blues)]
    tau = K_I * sum(reds.values()) - K_J * sum(blues.values())
    phi = sigma * np.sqrt( K_I ** 2 * len(reds) + K_J ** 2 * len(blues) )
    E = norm.cdf( tau / phi )
    return E

def skill_update(reds, blues, red_score, blue_score):
    """
    reds, blues should be dictionaries mapping player_id to current
    skill.
    
    Returns
        update_amount, ups, downs
    where update_amount is a float, and ups & downs are sets of player IDs
    """

    assert red_score >= 0 and blue_score >= 0
    assert red_score + blue_score > 0
    assert red_score != blue_score

    E = _point_win_probability(reds, blues)

    points = red_score + blue_score

    if red_score > blue_score:
        delta = 0.5 - binom.sf(red_score - 1, points, E)
        ups, downs = reds, blues
    else:
        delta = 0.5 - binom.cdf(red_score, points, E)
        ups, downs = blues, reds

    return 2 * update_magnitude * delta, set(ups), set(downs)

def predict_score(reds, blues, points=10):
    """
    Predict the score of a game; returns red_score, blue_score
    """

    E = _point_win_probability(reds, blues)

    if E > 0.5:
        return points, points * (1 - E) / E
    else:
        return points * E / (1 - E), points
        
def update_score(cur, game=None):
    
    query1 = "SELECT games_players.player_id, players.score, games_players.team FROM games_players " \
             "JOIN players ON games_players.player_id=players.id WHERE games_players.game_id=%s"
    query2 = "UPDATE players SET score=score+%s WHERE id IN %s"
    
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
    
    adj, ups, downs = skill_update(reds, blues, red_score, blue_score)
    
    ups = tuple(ups)
    downs = tuple(downs)
    
    print "updating player skills for game {0}".format(game_id)
    print "adj, ups, downs = "
    print adj, ups, downs
    
    cur.execute(query2, (adj, ups))
    cur.execute(query2, (-adj, downs))
    
    
def recalculate_scores():

    conn = psycopg2.connect("dbname=foosball")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("UPDATE players SET score=0");
    cur.execute("SELECT * FROM games");
    for game in cur.fetchall():
        update_score(cur, game)
    conn.commit()
    cur.close()
    conn.close()
