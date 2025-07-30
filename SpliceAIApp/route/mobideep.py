# general imports
import os
import re
import subprocess
import json
from collections import OrderedDict
# flask imports
from flask_restful import Resource
from flask import request, jsonify, make_response, current_app
import hashlib
import redis
from .spliceai import getAppRootDirectory, run_spliceai, get_data_from_cache


def jsonify_spliceai(seq, hash, type):
    # from spliceai file result and input sequence build a dict
    # format: {'1': ('[ATCG]', 'spliceai_score'), ...}
    # returns a json from this dict
    spliceai_res = []
    with open('{0}/{1}_{2}.txt'.format(current_app.config['TMP_FOLDER'], hash, type), mode='r') as spliceai_file:
        spliceai_res = spliceai_file.read()
    json_dict = OrderedDict()
    i = 1
    for t in list(zip(seq, re.split('\n', spliceai_res))):
        json_dict[i] = t
        i += 1
    os.remove('{0}/{1}_{2}.txt'.format(current_app.config['TMP_FOLDER'], hash, type))
    return json.dumps(json_dict), json_dict


def return_json(message, mobideep_return_code=1, http_code=200, result=None):
    # prepare flask response
    return make_response(jsonify({
        'mobideep_return_code': mobideep_return_code,
        'result': result,
        'error': message
    }), http_code)


class MobiDeep(Resource):
    """
    Endpoint to compute MobiDeep scores
    Takes as input 5 scores: CADD1.7 GPNMSA ReMM Cactus241way PhyloP
    Then runs the MobiDeep model as an apptainer container through SLURM
    Also uses a redis cache
    """
    def post(self):
        # instatiate redis object
        r = redis.Redis(
            host=current_app.config['CACHE_REDIS_HOST'],
            port=current_app.config['CACHE_REDIS_PORT'],
            socket_timeout=current_app.config['CACHE_DEFAULT_TIMEOUT'],
            db=0
        )
        input = request.get_json()
        # input should be:
        #  {mobideep_input: "CADD1.7 GPNMSA ReMM Cactus241way PhyloP"}
        # format id: float or NaN
        score_sequence = None
        if 'mobideep_input' in input:
            raw_input = input['mobideep_input']
            # computes hash to uniquely identify the query for the redis cache
            raw_input_hash = hashlib.md5(raw_input.encode()).hexdigest()
            # check if the result is already known
            redis_result = get_data_from_cache(raw_input_hash, r)
            if redis_result:
                # return values from cache
                return return_json(
                    None,
                    0,
                    200,
                    redis_result
                )
            if re.search(r'^[\w\.]+\s[\w\.-]+\s[\w\.]+\s[\w\.]+\s[\w\.-]+$', raw_input):
                # otherwise runs MobiDeep through SLURM
                partition = 'spliceailight'
                args_list = []
                input_list = re.split('\s', raw_input)
                if 'SRUN' in current_app.config:
                    args_list = [current_app.config['SRUN'], '-N', '1', '-c', '1', '-J', 'mobideep','-p', partition]
                args_list.extend([
                    current_app.config['APPTAINER'],
                    'run',
                    '{}/mobideep_mobidetails.sif'.format(getAppRootDirectory()),
                    input_list[0],
                    input_list[1],
                    input_list[2],
                    input_list[3],
                    input_list[4],

                ])
                result = run_spliceai(args_list)
            else:
                return return_json('Bad mobideep input submitted', 1)
        else:
            return return_json('Bad parameters received', 1)
        if result.returncode == 0:
            # success
            # treat result to return them as json
            results = re.split(r'\n', str(result.stdout, 'utf-8'))
            mobideep_results = {
                'MobiDeepRawscore': None,
                'MobiDeepLogScore': None
            }
            for line in results:
                match_obj = re.search('MobiDeep_raw_score":\s([\d\.]+)', line)
                if match_obj:
                    mobideep_results['MobiDeepRawscore'] = "{:.6f}".format(float(match_obj.group(1)))
                match_obj = re.search('MobiDeep_log_score":\s([\d\.]+)', line)
                if match_obj:
                    mobideep_results['MobiDeepLogScore'] = "{:.6f}".format(float(match_obj.group(1)))
            if 'MobiDeepLogScore' in mobideep_results and \
                    'MobiDeepRawscore' in mobideep_results:
                r.set(raw_input_hash, json.dumps(mobideep_results))
                return return_json(
                    None,
                    result.returncode,
                    200,
                    mobideep_results
                )
            return return_json('MobiDeep result retrieval error', result.returncode, 500)
        return return_json('MobiDeep execution error', result.returncode, 500)