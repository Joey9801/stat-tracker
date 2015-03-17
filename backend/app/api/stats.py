from flask import Blueprint, jsonify, abort
from sqlalchemy.sql import func

from ..models import Player, Game, GamePlayer

stats = Blueprint('stats', __name__)

@stats.route('/sums', methods=['GET'])
def sums():
    d = {
            'total_score' : Game.sum_score(),
            'wins' : Game.sum_wins()
        }
    
    return jsonify(d)


