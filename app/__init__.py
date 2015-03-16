from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object('config')

db = SQLAlchemy(app)

from .api import game
app.register_blueprint(game.game, url_prefix='/api/game')
