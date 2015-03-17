from flask import Blueprint, jsonify, abort

from ..models import Game, GamePlayer

game = Blueprint('game', __name__)

@game.route('/<int:game_id>', methods=['GET'])
def by_id(game_id):
    game = Game.query.get(game_id)
    if game:
        return jsonify( game.toDict() )
    else:
        abort(404)

@game.route('/last_n/<int:n>', methods=['GET'])
def last_n(n):

    #Prevent pulling whole table
    if n > 20:
        abort(403)

    games = (Game.query
            .order_by( Game.timestamp.desc() )
            .limit(n)
            )

    d = {'games': [g.toDict() for g in games] }
    
    return jsonify( d )
