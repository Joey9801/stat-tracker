import os
_basedir = os.path.abspath( os.path.dirname(__file__) )

DEBUG = True

SECRET_KEY = 'A super secret key'
CSRF_ENABLED = True
CSRF_SESSION_KEY = 'Another super secret key'

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(_basedir, 'app', 'testing.db')
DATABASE_CONNECT_OPTIONS = {}
