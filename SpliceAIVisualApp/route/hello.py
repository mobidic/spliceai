from flask_restful import Resource
from flask import jsonify, make_response


class Hello(Resource):
    def get(self):
        return make_response(jsonify({
                'spliceaivisual_status': 'running'
            }), 200)
