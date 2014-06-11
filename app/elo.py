from scipy.stats import norm
import numpy as np

update_constant = 1
magic_K = [None, 0.6, 0.5, 0.4, 0.1]  # 1-indexed
sigma = 1

def _point_win_probability(reds, blues):
    K_I = magic_K[len(reds)]
    K_J = magic_K[len(blues)]
    tau = K_I * sum(reds.values()) - K_J * sum(blues.values())
    phi = sigma * np.sqrt( K_I ** 2 * len(reds) + K_J ** 2 * len(blues) )
    E = norm.cdf( - tau / phi )
    return E

def skill_update(reds, blues, red_score, blue_score):
    """
    Return the new skills for players.

    reds, blues should be dictionaries mapping player_id to current
    skill; a (single) dictionary in the same form is returned.
    """

    assert set(reds.keys()) & set(blues.keys()) == set([])
    assert 1 <= len(reds) <= 4
    assert 1 <= len(blues) <= 4
    assert red_score >= 0 and blue_score >= 0
    assert red_score + blue_score > 0

    E = _point_win_probability(reds, blues)

    points = red_score + blue_score
    delta_I = red_score * (1 - E) - blue_score
    delta_J = red_score * (E - 1) + blue_score 

    updated = {}
    for key, skill in reds.items():
        updated[key] = skill + update_constant * delta_I
    for key, skill in blues.items():
        updated[key] = skill + update_constant * delta_J

    return updated

def predict_score(reds, blues, points=10):
    """
    Predict the score of a game; returns red_score, blue_score
    """

    E = _point_win_probability(reds, blues)

    if E > 0.5:
        return points, points * (1 - E) / E
    else:
        return points * E / (1 - E), points
