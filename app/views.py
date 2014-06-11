from flask import render_template, request, redirect, session, jsonify, url_for, abort
from app import app
import psycopg2, psycopg2.extras

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/')
def index():
    return render_template('index.html')
    
@app.route('/new_game', methods = ['GET', 'POST'])
def new_game():
    if request.method == 'GET':
    
        conn = psycopg2.connect("dbname=foosball")
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("SELECT id, nickname FROM players ORDER BY nickname")
        playerlist = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return render_template('new_game.html', 
                               playerlist=playerlist)
                               
    elif request.method == 'POST':
        try:
            reds = map(int, request.form.getlist("reds[]"))
            blues = map(int, request.form.getlist("blues[]"))
            red_score = int(request.form.get("red_score"))
            blue_score = int(request.form.get("blue_score"))
            valid, reasons = validate_game(reds, blues, red_score, blue_score)
        except ValueError:
            valid = False
            reasons = ["ValueError while processing game"]
            print "caught ValueError"
            
        if not valid:
            return jsonify(valid=False, 
                           reasons=reasons), 400
        
        print "no errors found with posted data"
        return jsonify(valid=True,
                       game_id=16,
                       redirect=url_for('view_game', game_id=16)), 202
        query_game = "INSERT INTO games (red_score, blue_score) VALUES (%s, %s) RETURNING id;"
        query_player = "INSERT INTO games_players (game_id, player_id, team) VALUES (%s, %s, %s);"
        
        conn = psycopg2.connect("dbname=foosball")
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute(query_game, (red_score, blue_score))
        game_id = cur.fetchone()['id']
        
        for player in reds:
            cur.execute(query_player, (game_id, player, 'red'))
        
        for player in blues:
            cur.execute(query_player, (game_id, player, 'blue'))
        conn.commit()
        cur.close()
        conn.close()
        
        session['last_added'] = game_id
        
        return "", 202

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
    conn = psycopg2.connect("dbname=foosball")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute("SELECT COUNT(*) FROM games;")
    count = cur.fetchone()['count']

    cur.close()
    conn.close()
    
    return render_template('stats/index.html',
                           count = count)
                           
def stats_leaderboard():
    conn = psycopg2.connect("dbname=foosball")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute("SELECT id, nickname FROM players ORDER BY score")
    playerlist = cur.fetchall()
    
    cur.close()
    conn.close()
    return render_template('stats/leaderboard.html',
                           playerlist = playerlist)
                           
def stats_recent_games():
    conn = psycopg2.connect("dbname=foosball")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute("SELECT * FROM games ORDER BY timestamp DESC LIMIT 10;")
    games = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('stats/recent_games.html',
                           games = games)
                           
@app.route('/view_game/<game_id>')
def view_game(game_id=None):
    try:
        game_id = int(game_id)
    except ValueError:
        abort(404)
    
    name_query = "SELECT players.nickname FROM games_players INNER JOIN players ON players.id=games_players.player_id WHERE game_id=%s AND team=%s;"
    
    class game: pass
    
    conn = psycopg2.connect("dbname=foosball")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute("SELECT * FROM games WHERE id=%s", (game_id,))
    
    line = cur.fetchone()
    if not line:
        abort(404)
    game.id = line['id']
    game.red_score = line['red_score']
    game.blue_score = line['blue_score']
    game.timestamp = line['timestamp']
    print game.timestamp
    
    cur.execute(name_query, (game_id, 'red'))
    game.reds = [x['nickname'] for x in cur.fetchall()]
    cur.execute(name_query, (game_id, 'blue'))
    game.blues = [x['nickname'] for x in cur.fetchall()]
    
    return render_template('view_game.html', game=game)
        
def validate_game(reds, blues, red_score, blue_score):
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
