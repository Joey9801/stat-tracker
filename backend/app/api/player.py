from flask import Blueprint, jsonify, abort

from ..models import Player, Game, GamePlayer

player = Blueprint('player', __name__)

@player.route('/all', methods=['GET'])
def all():
    players = Player.query.all()
    if players:
        d = {'players' : [p.toDict() for p in players]}
        return jsonify(d)
    else:
        abort(500)

@player.route('/<int:player_id>', methods=['GET'])
def by_id(player_id):
    player = Player.query.get(player_id)
    if player:
        return jsonify( player.toDict() )
    else:
        abort(404)

@player.route('/<int:player_id>/last_n_games/<int:n>', methods=['GET'])
def last_n_games(player_id, n):

    #Prevent pulling whole table
    if n > 20:
        abort(403)

    games = (Game.query
            .join(Game.players)
            .filter( GamePlayer.player_id == player_id )
            .order_by( Game.timestamp.desc() )
            .limit(n)
            )

    d = {'games': [g.toDict() for g in games]}

    return jsonify(d)
