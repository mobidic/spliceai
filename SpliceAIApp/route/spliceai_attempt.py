# general imports
import os
import re
import subprocess
import json
# flask imports
from flask_restful import Resource
from flask import request, jsonify, make_response, current_app
import redis
# spliceai imports
from keras.models import load_model
from pkg_resources import resource_filename
from spliceai.utils import one_hot_encode
import numpy as np

paths = ('models/spliceai{}.h5'.format(x) for x in range(1, 6))
models = [load_model(resource_filename('spliceai', x)) for x in paths]


def getAppRootDirectory():
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def jsonify_spliceai(seq, spliceai_results):
    # from spliceai string result and input sequence build a dict
    # format: {'1': ('[ATCG]', 'spliceai_score'), ...}
    # returns a json from this dict
    # [list(t) for t in zip((input['wt_seq']), re.split(' ', results[1].replace(r']', '')))]
    json_dict = {}
    i = 1
    for t in list(zip(seq, re.split(' ', spliceai_results.replace(r']', '')))):
        json_dict[i] = t
        i += 1
    return json.dumps(json_dict), json_dict


def get_data_form_cache(key, r):
    # get data from redis cache and returns as json
    data = r.get(key)
    if data:
        return json.loads(data)
    else:
        return None


def return_json(message, spliceai_return_code=1, http_code=200, result=None):
    # prepare flask response
    return make_response(jsonify({
        'spliceai_return_code': spliceai_return_code,
        'result': result,
        'error': message
    }), http_code)


class SpliceAi(Resource):
    def get(self):
        r = redis.Redis(
            host=current_app.config['CACHE_REDIS_HOST'],
            port=current_app.config['CACHE_REDIS_PORT'],
            socket_timeout=current_app.config['CACHE_DEFAULT_TIMEOUT'],
            db=0
        )
        input = request.get_json()
        # print(input)
        context = '10000'
        wt_acceptor = wt_donor = mt_acceptor = mt_donor = None
        if 'context' in input and \
                re.search(r'^\d+$', str(input['context'])):
            context = str(input['context'])
        if 'wt_seq' in input and \
                'mt_seq' in input:
            wt_acceptor = get_data_form_cache('{}_acceptor'.format(input['wt_seq']), r)
            wt_donor = get_data_form_cache('{}_donor'.format(input['wt_seq']), r)
            mt_acceptor = get_data_form_cache('{}_acceptor'.format(input['mt_seq']), r)
            mt_donor = get_data_form_cache('{}_donor'.format(input['mt_seq']), r)
            if (wt_acceptor and
                    wt_donor and
                    mt_acceptor and
                    mt_donor):
                # return values from cache
                return return_json(
                    None,
                    0,
                    200,
                    {
                        'spliceai_context': context,
                        'wt_sequence': input['wt_seq'],
                        'wt_acceptor_scores': wt_acceptor,
                        'wt_donor_scores': wt_donor,
                        'mt_sequence': input['mt_seq'],
                        'mt_acceptor_scores': mt_acceptor,
                        'mt_donor_scores': mt_donor,
                    }
                )
            if re.search('^[ATGC]+$', input['wt_seq']) and \
                    re.search('^[ATGC]+$', input['mt_seq']):
                # print(input['wt_seq'])
                # result = subprocess.run(
                #     [
                #         current_app.config['PYTHON'],
                #         '{}/run_spliceai.py'.format(getAppRootDirectory()),
                #         '--wt-seq',
                #         input['wt_seq'],
                #         '--mt-seq',
                #         input['mt_seq'],
                #         '--context',
                #         context
                #     ],
                #     stdout=subprocess.PIPE
                # )
                x = one_hot_encode('N'*(context//2) + input['wt_seq'] + 'N'*(context//2))[None, :]
                y = np.mean([models[m].predict(x) for m in range(5)], axis=0)
                wt_acceptor_prob = y[0, :, 1]
                wt_donor_prob = y[0, :, 2]
                x = one_hot_encode('N'*(context//2) + input['mt_seq'] + 'N'*(context//2))[None, :]
                y = np.mean([models[m].predict(x) for m in range(5)], axis=0)
                mt_acceptor_prob = y[0, :, 1]
                mt_donor_prob = y[0, :, 2]
            else:
                return return_json('Bad wt or mt sequences submitted')
        elif 'mt_seq' in input:
            mt_acceptor = get_data_form_cache('{}_acceptor'.format(input['mt_seq']), r)
            mt_donor = get_data_form_cache('{}_donor'.format(input['mt_seq']), r)
            if (mt_acceptor and
                    mt_donor):
                # return values from cache
                return return_json(
                    None,
                    0,
                    200,
                    {
                        'spliceai_context': context,
                        'wt_sequence': None,
                        'wt_acceptor_scores': wt_acceptor,
                        'wt_donor_scores': wt_donor,
                        'mt_sequence': input['mt_seq'],
                        'mt_acceptor_scores': mt_acceptor,
                        'mt_donor_scores': mt_donor,
                    }
                )
            if (not mt_acceptor or
                    not mt_donor) and \
                    re.search('^[ATGC]+$', input['mt_seq']):
                input['wt_seq'] = None
                result = subprocess.run(
                    [
                        current_app.config['PYTHON'],
                        '{}/run_spliceai.py'.format(getAppRootDirectory()),
                        '--mt-seq',
                        input['mt_seq'],
                        '--context',
                        context
                    ],
                    stdout=subprocess.PIPE
                )
                wt_acceptor_prob = '[no_wt]'
                wt_donor_prob = '[no_wt]'
                x = one_hot_encode('N'*(context//2) + input['mt_seq'] + 'N'*(context//2))[None, :]
                y = np.mean([models[m].predict(x) for m in range(5)], axis=0)
                mt_acceptor_prob = y[0, :, 1]
                mt_donor_prob = y[0, :, 2]
            else:
                return return_json('Bad mt sequence submitted')
        else:
            return return_json('Bad parameters received')
        # if result.returncode == 0:
        #     # success
        #     results = re.split(r'\[', str(result.stdout, 'utf-8').replace('\n', ''))
        #     print(results)
        #     if not re.search(r'no_wt', results[1]):
        #         # print(results)
        #         # wt and mutant results
        #         wt_acceptor_redis, wt_acceptor = jsonify_spliceai(input['wt_seq'], results[1])
        #         wt_donor_redis, wt_donor = jsonify_spliceai(input['wt_seq'], results[2])
        #         mt_acceptor_redis, mt_acceptor = jsonify_spliceai(input['mt_seq'], results[3])
        #         mt_donor_redis, mt_donor = jsonify_spliceai(input['mt_seq'], results[4])
        #         # populate redis
        #         r.set('{}_acceptor'.format(input['wt_seq']), wt_acceptor_redis)
        #         r.set('{}_donor'.format(input['wt_seq']), wt_donor_redis)
        #         r.set('{}_acceptor'.format(input['mt_seq']), mt_acceptor_redis)
        #         r.set('{}_donor'.format(input['mt_seq']), mt_donor_redis)
        #     else:
        #         # mutant only
        #         mt_acceptor_redis, mt_acceptor = jsonify_spliceai(input['mt_seq'], results[3])
        #         mt_donor_redis, mt_donor = jsonify_spliceai(input['mt_seq'], results[4])
        #         # populate redis
        #         r.set('{}_acceptor'.format(input['mt_seq']), mt_acceptor_redis)
        #         r.set('{}_donor'.format(input['mt_seq']), mt_donor_redis)
        #     return return_json(
        #         None,
        #         result.returncode,
        #         200,
        #         {
        #             'spliceai_context': results[0],
        #             'wt_sequence': input['wt_seq'],
        #             'wt_acceptor_scores': wt_acceptor,
        #             'wt_donor_scores': wt_donor,
        #             'mt_sequence': input['mt_seq'],
        #             'mt_acceptor_scores': mt_acceptor,
        #             'mt_donor_scores': mt_donor,
        #         }
        #     )
        return return_json('Bad parameters received', result.returncode, 500)
