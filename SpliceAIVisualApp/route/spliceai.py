# flask imports
from flask_restful import Resource
from flask import request, jsonify, make_response
# others
import os.path
import subprocess
# spliceai imports
# from keras.models import load_model
# from pkg_resources import resource_filename
# from spliceai.utils import one_hot_encode
# import numpy as np


# def getParentDirectory(path, levels=1):
#     # from https://www.geeksforgeeks.org/get-parent-of-current-directory-using-python
#     common = path
#     # Using for loop for getting
#     # starting point required for
#     # os.path.relpath()
#     for i in range(1, levels + 1):
#         # Starting point
#         common = os.path.dirname(common)
#     # Parent directory upto specified level
#     return os.path.relpath(path, common)


def getAppRootDirectory():
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


class SpliceAi(Resource):
    def get(self):
        input = request.get_json()
        result = subprocess.run(
            [
                '/home/adminbioinfo/miniconda3/envs/spliceai-cpu/bin/python',
                '{}/run_spliceai.py'.format(getAppRootDirectory()),
                '--seq',
                input['wt_seq']
            ],
            stdout=subprocess.PIPE
        )
        print(result)
        return make_response(jsonify({
            'result': input
        }), 200)
        # context = 10000
        # paths = ('models/spliceai{}.h5'.format(x) for x in range(1, 6))
        # models = [load_model(resource_filename('spliceai', x)) for x in paths]
        # x = one_hot_encode('N'*(context//2) + input['wt_seq'] + 'N'*(context//2))[None, :]
        # y = np.mean([models[m].predict(x) for m in range(5)], axis=0)
        #
        # wt_acceptor_prob = y[0, :, 1]
        # wt_donor_prob = y[0, :, 2]
        # return make_response(jsonify({
        #     'wt_acceptor_prob': wt_acceptor_prob,
        # }), 200)
        #
        # return make_response(jsonify({
        #
        #     }), 404)
