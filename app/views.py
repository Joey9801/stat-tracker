from flask import render_template, request, redirect, session, jsonify, url_for, abort
from app import app
import psycopg2, psycopg2.extras
import elo
from . import elo, config
from datetime import datetime, timedelta
from raven.flask_glue import AuthDecorator
auth_decorator = AuthDecorator(desc="Selwyn foosball tracker")
app.before_request(auth_decorator.before_request)

# Make datetimes Javascript friendly. Flask's default seems to break
# sporadically.
import flask.json

class JSONEncoder(flask.json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat("T")
        else:
            return super(JSONEncoder, self).default(o)

app.json_encoder = JSONEncoder


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/')
def index():
    return render_template('index.html')
    
@app.route('/new_game', methods = ['GET', 'POST'])
def new_game():
    if request.method == 'GET':
    
        conn = psycopg2.connect("dbname=foosball user=flask_foosball")
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("SELECT id, nickname FROM players ORDER BY nickname")
        playerlist = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return render_template('new_game.html', 
                               playerlist=playerlist)
                               
    elif request.method == 'POST':
        if auth_decorator.principal in config.authed_crsids:
            pass
        else:
            return jsonify(valid=False,
                           reasons=["hmmm, you are not Joe.."]), 400
        
        try:
            reds = map(int, request.form.getlist("reds[]"))
            blues = map(int, request.form.getlist("blues[]"))
            red_score = int(request.form.get("red_score"))
            blue_score = int(request.form.get("blue_score"))
            valid, reasons = validate_game(reds, blues, red_score, blue_score)
        except ValueError, TypeError:
            valid = False
            reasons = ["Error while processing game"]
            
        if not valid:
            return jsonify(valid=False, 
                           reasons=reasons), 400

        query_game = "INSERT INTO games (red_score, blue_score, added_by)" \
                     " VALUES (%s, %s, (SELECT id FROM players WHERE crsid=%s)) RETURNING *"
        query_player = "INSERT INTO games_players (game_id, player_id, team, win) VALUES (%s, %s, %s, %s)"

        conn = psycopg2.connect("dbname=foosball user=flask_foosball")
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute(query_game, (red_score, blue_score, auth_decorator.principal))
        game = cur.fetchone()
        
        for player in reds:
            cur.execute(query_player, (game['id'], player, 'red', red_score>blue_score))
        
        for player in blues:
            cur.execute(query_player, (game['id'], player, 'blue', blue_score>red_score))
        conn.commit()
        
        elo.update_score(cur, game=game)
        conn.commit()
        
        cur.close()
        conn.close()
        
        if 'added_games' not in session:
            session['added_games'] = list()
        session['added_games'].append(game['id'])
        
        return jsonify(valid=True,
                       game_id=game['id'],
                       redirect=url_for('view_game', game_id=game['id'])), 202

@app.route('/predict', methods=["POST"])
def predict():
    try:
        reds = map(int, request.form.getlist("reds[]"))
        blues = map(int, request.form.getlist("blues[]"))
        valid, reasons = validate_players(reds, blues)
    except ValueError, TypeError:
        valid = False
        reasons = ["Error while processing players"]

    if not valid:
        return jsonify(valid=False, reasons=reasons), 400

    conn = psycopg2.connect("dbname=foosball user=flask_foosball")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    s = elo.lookup_predict_score(cur, reds, blues)
    u = elo.lookup_predict_updates(cur, reds, blues)
    cur.close()
    conn.close()

    # in JSON, all keys must be strings.
    u = {"{0}:{1}".format(*k): v for k, v in u.items()}

    return jsonify(valid=True, score=s, updates=u)


@app.route('/stats')
@app.route('/stats/<page>')
def stats_handler(page=None):
    if not page:
        return redirect('/stats/index')
    try:
        return globals()["stats_" + page]()
    except KeyError:
        abort(404)

        
def stats_index():
    conn = psycopg2.connect("dbname=foosball user=flask_foosball")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute("SELECT COUNT(*) FROM games;")
    count = cur.fetchone()['count']

    cur.close()
    conn.close()
    
    return render_template('stats/index.html',
                           count = count)
                           
def stats_leaderboard():
    conn = psycopg2.connect("dbname=foosball user=flask_foosball")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    query = """
            SELECT
                p.nickname, p.id,
                round( (p.score*1000+1000)::numeric, 1 ) AS score,
                round( (count(CASE win WHEN true THEN 1 ELSE NULL END)*100/count(*)::float)::numeric, 3 ) as "winp",
                count(*) as "Games played"
            FROM players AS p
            JOIN games_players gp ON p.id=gp.player_id
            JOIN games g ON gp.game_id = g.id
            WHERE p.id NOT IN %s
            GROUP BY p.nickname, p.id
            HAVING max(g.timestamp) > current_timestamp - '1000 days'::interval
            ORDER BY score DESC;
            """

    cur.execute(query, (tuple(config.leaderboard_hide), ))
    playerlist = cur.fetchall()
    
    cur.close()
    conn.close()
    return render_template('stats/leaderboard.html',
                           playerlist = playerlist)
                           
def stats_recent_games():
    conn = psycopg2.connect("dbname=foosball user=flask_foosball")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute("SELECT * FROM games ORDER BY timestamp DESC LIMIT 10")
    games = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('stats/games.html',
                           title="Recent Games", games=games)

def stats_humiliation():
    conn = psycopg2.connect("dbname=foosball user=flask_foosball")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT * FROM games "
                "WHERE (red_score = 0 AND blue_score = 10) "
                "   OR (blue_score = 0 AND red_score = 10) "
                "ORDER BY timestamp DESC")
    games = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('stats/games.html',
                           title="10 : 0 Games", games=games)
                           
@app.route('/view_game/<int:game_id>')
def view_game(game_id):
    
    name_query = "SELECT players.nickname, players.id FROM games_players INNER JOIN players ON players.id=games_players.player_id WHERE game_id=%s AND team=%s"
    
    conn = psycopg2.connect("dbname=foosball user=flask_foosball")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute("SELECT * FROM games WHERE id=%s", (game_id,))
    
    line = cur.fetchone()
    if not line:
        abort(404)
    game = dict(line)

    
    cur.execute(name_query, (game_id, 'red'))
    game['reds'] = cur.fetchall()
    cur.execute(name_query, (game_id, 'blue'))
    game['blues'] = cur.fetchall()
    
    return render_template('view_game.html', game=game)
    
@app.route('/delete_game/<int:game_id>')
def delete_game(game_id):
    success = True
    game_id = int(game_id)
    if 'added_games' not in session:
        msg = "You can only delete games that you put in"
        return jsonify(msg=msg), 403
    elif game_id not in session['added_games']:
        msg = "You can only delete games that you put in"
        return jsonify(msg=msg), 403

    max_time = timedelta(minutes=10)
    check_expired = "SELECT (now()-timestamp)<%s AS in_date FROM games WHERE id=%s"
    
    delete_game = "DELETE FROM games where id=%s"
    
    conn = psycopg2.connect("dbname=foosball")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(check_expired, (max_time,game_id))
    
    in_date = cur.fetchone()
    try:
        in_date = in_date['in_date']
    except TypeError:
        in_date = False
    
    if not in_date:
        cur.close()
        conn.close()
        return "You can only delete games from the last 10 minutes", 403
    else:
        cur.execute(delete_game, (game_id,))
        conn.commit()
        cur.close()
        conn.close()
        elo.recalculate_scores();
        session['added_games'].remove(game_id)
        return "Deleted that shit", 200
    
@app.route('/view_player/<int:player_id>')
def view_player(player_id=None):
    #player data
    query1 = "SELECT * from players WHERE id=%s"
             
    #Total num of games
    query2 = "SELECT COUNT(*) FROM games_players WHERE player_id=%s"
    
    #Are there any recent games (if not then they are unranked)
    query3 = "select count(g.timestamp) from games g " \
                "join games_players gp on g.id = gp.game_id " \
                "where gp.player_id = %s " \
                "and g.timestamp > now() - interval '1000 days'"

    #For calculating rank
    query4 = "select count(*) from (" \
                "select distinct players.* from games " \
                "join games_players on (games.id=games_players.game_id) " \
                "join players on (games_players.player_id=players.id) " \
                "where games.timestamp > now()- interval '1000 days' " \
                "and players.score > (SELECT score from players WHERE id=%s)" \
                "and players.id NOT IN %s " \
                "order by players.score desc" \
                ") as temp"

    #Total games won
    query5 = "SELECT COUNT(*) FROM games_players WHERE player_id=%s AND win"
    
    #Goals scored/conceded
    query6 = "SELECT COALESCE(SUM(red_score), 0)  AS red_goals, " \
             "       COALESCE(SUM(blue_score), 0) AS blue_goals " \
             "FROM games " \
             "JOIN games_players ON games_players.game_id = games.id " \
             "WHERE games_players.player_id = %s " \
             "AND games_players.team = %s"
     
    #Score over time
    query7 = "SELECT gp.score, g.timestamp FROM games_players gp " \
             "JOIN games g ON gp.game_id = g.id " \
             "WHERE gp.player_id=%s ORDER BY g.timestamp DESC LIMIT 100"
    
    conn = psycopg2.connect("dbname=foosball user=flask_foosball")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute(query1, (player_id,))
    player = cur.fetchone()
    
    player['score'] = int(player['score']*1000 + 1000)
     
    cur.execute(query2, (player_id,))
    player['games_total'] = total = int(cur.fetchone()['count'])
    
    #A player is only ranked if he has played a recent game
    cur.execute(query3, (player_id,))
    if cur.fetchone()['count'] > 0 and player['id'] not in config.leaderboard_hide:
        cur.execute(query4, (player_id, tuple(config.leaderboard_hide)))
        player['rank'] = int(cur.fetchone()['count']) + 1
        player['rank'] = '#' + str(player['rank'])
    else:
        player['rank'] = "Unranked"

    
    cur.execute(query5, (player_id,))
    player['games_won'] = won = int(cur.fetchone()['count'])

    scored, conceded = 0, 0
    for team, other_team in (('red', 'blue'), ('blue', 'red')):
        cur.execute(query6, (player_id, team))
        r = cur.fetchone()
        scored += r[team + "_goals"]
        conceded += r[other_team + "_goals"]
    
    player['goals_scored'] = scored
    player['goals_conceded'] = conceded
    
    cur.execute(query7, (player_id,))
    player['score_history'] = cur.fetchall()
    
    if won:
        player['win_percentage'] = float(won)/float(total)*100
    else:
        player['win_percentage'] = 0
    
    return render_template('view_player.html',
                           player = player)

def validate_players(reds, blues):
    reasons = list()
    valid = True
    if not len(reds):
        valid = False
        reasons.append("No red players")
    if not len(blues):
        valid = False
        reasons.append("No blue players")
    if any(i in reds for i in blues):
        valid = False
        reasons.append("Cannot have the same player on both sides")

    query = "SELECT COUNT(*) FROM players WHERE id IN %s"
    
    conn = psycopg2.connect("dbname=foosball user=flask_foosball")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    id_list = tuple(reds + blues)
    cur.execute(query, (id_list,))

    if int(cur.fetchone()['count']) != len(id_list):
        valid = False
        reasons.append("Not all players exist")
        
    return (valid, reasons)

def validate_scores(red_score, blue_score):
    reasons = list()
    valid = True
    if red_score < 0 or red_score > 10:
        valid = False
        reasons.append("Red score out of bounds")
    if blue_score < 0 or blue_score > 10:
        valid = False
        reasons.append("Blue score out of bounds")
    if red_score == blue_score:
        valid = False
        reasons.append("There's no such thing as a draw")
    
    return (valid, reasons)

def validate_game(reds, blues, red_score, blue_score):
    valid1, reasons1 = validate_scores(red_score, blue_score)
    valid2, reasons2 = validate_players(reds, blues)
    return (valid1 and valid2, reasons1 + reasons2)
