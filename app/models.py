from flask.ext.sqlalchemy import SQLAlchemy
from datetime import datetime

from . import db

class GamePlayer(db.Model):
    game_id = db.Column(db.Integer,
            db.ForeignKey('game.id'),
            primary_key=True,
            nullable=False)

    player_id = db.Column(db.Integer,
            db.ForeignKey('player.id'),
            primary_key=True,
            nullable=False)

    team = db.Column(db.Enum('red', 'blue', name='team'))

    player = db.relationship('Player', backref='games')
    game   = db.relationship('Game', backref='players')

    def score(self, team):
        return self.game.score(team)

    def toDict(self, which):
        if which=='player':
            return self.player.toDict()
        elif which=='game':
            return self.game.toDict()

    def __init__(self, team):
        self.team = team

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    red_score = db.Column(db.Integer, nullable=False)
    blue_score = db.Column(db.Integer, nullable=False)

    timestamp = db.Column(db.DateTime(timezone=True), nullable=False)

    def score(self, team=None):
        if team is 'red':
            return red_score
        elif team is 'blue':
            return blue_score
        else:
            return {'red_score'  : red_score,
                    'blue_score' : blue_score}

    def __init__(self,
            red_score, red_team,
            blue_score, blue_team,
            timestamp=None):
        """
        red_score, blue_score: integer
        red_team, blue_team: iterable of player id's
        """

        if timestamp:
            self.timestamp = timestamp
        else:
            self.timestamp = datetime.now()

        self.red_score = red_score
        self.blue_score = blue_score

        for pid in red_team:
            a = GamePlayer(team='red')
            a.player = Player.query.get(pid)
            self.players.append(a)

        for pid in blue_team:
            a = GamePlayer(team='blue')
            a.player = Player.query.get(pid)
            self.players.append(a)

    def toDict(self):
        return {
            'id'        : self.id,
            'red_score' : self.red_score,
            'blue_score': self.blue_score,
            'timestamp' : self.timestamp.isoformat(),
            'players'   : {
                    'reds'  : [a.player.toDict() for a in self.players if a.team=='red'],
                    'blues' : [a.player.toDict() for a in self.players if a.team=='blue'],
                    }
            }

    def __repr__(self):
        return '<Game {}, {}:{}>'.format(self.id, self.red_score, self.blue_score)

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    first_name = db.Column(db.String(100), nullable=False)
    last_name  = db.Column(db.String(100), nullable=False)
    nickname   = db.Column(db.String(100), nullable=False)
    crsid      = db.Column(db.String(10))

    @property
    def name(self):
        return self.first_name + ' ' + self.last_name + ' (' + self.nickname + ')'

    def toDict(self):
        return {
            'first_name': self.first_name,
            'last_name' : self.last_name,
            'nickname'  : self.nickname,
            'id'        : self.id
            }

    def __init__(self, first_name, last_name, nickname, crsid=None):
        self.first_name = first_name
        self.last_name  = last_name
        self.nickname   = nickname

        if crsid:
            self.crsid  = crsid

    def __repr__(self):
        return '<Player {}, \'{}\'>'.format(self.id, self.nickname)
