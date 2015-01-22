CREATE TYPE team AS ENUM ('red', 'blue');

CREATE TABLE games (
    id SERIAL PRIMARY KEY,
    red_score integer NOT NULL,
    blue_score integer NOT NULL,
    "timestamp" timestamp with time zone NOT NULL DEFAULT now(),
    added_by integer REFERENCES players(id),
    CONSTRAINT games_blue_score_check CHECK (((blue_score >= 0) AND (blue_score <= 10))),
    CONSTRAINT games_red_score_check CHECK (((red_score >= 0) AND (red_score <= 10)))
);

CREATE TABLE games_players (
    game_id integer NOT NULL REFERENCES games(id),
    player_id integer NOT NULL REFERENCES players(id),
    team team NOT NULL,
    win boolean NOT NULL,
    score real NOT NULL,
    PRIMARY KEY (game_id, player_id)
);

CREATE TABLE players (
    id SERIAL PRIMARY KEY,
    first_name character varying(50) NOT NULL,
    last_name character varying(50) NOT NULL,
    score real DEFAULT 0 NOT NULL,
    nickname character varying(50) NOT NULL,
    crsid character varying(10)
);

GRANT ALL ON TABLE games TO joe;
GRANT ALL ON SEQUENCE games_id_seq TO joe;
GRANT ALL ON TABLE games_players TO joe;
GRANT ALL ON TABLE players TO joe;
GRANT ALL ON SEQUENCE players_id_seq TO joe;

GRANT ALL ON TABLE games TO flask_foosball;
GRANT USAGE ON SEQUENCE games_id_seq TO flask_foosball;
GRANT ALL ON TABLE games_players TO flask_foosball;
GRANT SELECT ON TABLE players TO flask_foosball;
