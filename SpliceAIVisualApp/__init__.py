import os
from flask import Flask, render_template
from flask_cors import CORS
# https://flask-wtf.readthedocs.io/en/stable/csrf.html
from flask_wtf.csrf import CSRFProtect
from flask_restful import Api


csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__, static_folder='static')

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('hidden/spliceaiapp.cfg', silent=False)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)
    csrf.init_app(app)
    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    if app.debug:
        print(app.config)
    return app
