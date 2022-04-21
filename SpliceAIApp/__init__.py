import os
from flask import Flask
from flask_restful import Api
from SpliceAIApp.route.spliceai import SpliceAi
from SpliceAIApp.route.hello import Hello


def create_app(test_config=None):
    app = Flask(__name__, static_folder='static')
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('hidden/spliceaiapp.cfg', silent=False)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)
    api = Api(app)
    api.add_resource(SpliceAi, "/spliceai")
    api.add_resource(Hello, "/hello")
    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    if app.debug:
        print(app.config)
    return app
