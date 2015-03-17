#!env/bin/python

from app import app

app.run(debug=app.config['DEBUG'], host='0.0.0.0')
