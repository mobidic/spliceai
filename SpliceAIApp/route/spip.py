# general imports
import os
import re
import subprocess
import json
import tempfile
# from collections import OrderedDict
# flask imports
from flask_restful import Resource
from flask import request, jsonify, make_response, current_app
import hashlib
import redis
from .spliceai import getAppRootDirectory, run_spliceai, get_data_from_cache, writeSeqInTmpFile


def return_json(message, spip_return_code=1, http_code=200, result=None):
    # prepare flask response
    return make_response(jsonify({
        'spip_return_code': spip_return_code,
        'result': result,
        'error': message
    }), http_code)


def run_spip(args_list):
    return subprocess.run(
        args_list,
        # stdout=subprocess.DEVNULL,
        # stderr=subprocess.STDOUT
    )


class Spip(Resource):
    """
    Endpoint to compute SPiP predictions
    Takes as input a tempfile like
    gene    varID
    USH2A   NM_206933.4:c.7595-2144A>G
    Then runs Spip  as an apptainer container through SLURM
    Also uses a redis cache
    """
    def post(self):
        # instatiate redis object
        r = redis.Redis(
            host=current_app.config['CACHE_REDIS_HOST'],
            port=current_app.config['CACHE_REDIS_PORT'],
            socket_timeout=current_app.config['CACHE_DEFAULT_TIMEOUT'],
            db=2
        )
        input = request.get_json()
        # input should be:
        #  {spip_input: "GeneSymbol\tRefSeq:c.hgvs"}
        # Ex: {spip_input: "USH2A\tNM_206933.4:c.7595-2144A>G"}
        # format id: String
        score_sequence = None
        if 'spip_input' in input:
            raw_input = input['spip_input']
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

            if re.search(r'^\w+\tNM_\d+\.\d{1,2}:c\.[\w\*\+_>-]+$', raw_input):
                spip_input = "gene\tvarID\n{0}\n".format(raw_input)
                # create temp file for variant
                # file is created in temp dir, named {hash}_spip.txt, and contains raw_input
                writeSeqInTmpFile(raw_input_hash, spip_input, 'spip')
                # runs SPiP through SLURM
                partition = 'spliceailight'
                args_list = []
                if 'SRUN' in current_app.config:
                    args_list = [current_app.config['SRUN'], '-N', '1', '-c', '1', '-J', 'spip','-p', partition]
                args_list.extend([
                    current_app.config['APPTAINER'],
                    'run',
                    '--bind',
                    '{0}/hidden:/hidden'.format(getAppRootDirectory()),
                     '--bind',
                    '{0}:{0}'.format(current_app.config['TMP_FOLDER']),
                    '{0}/spiptainer.sif'.format(getAppRootDirectory()),
                    '-I',
                    '{0}/{1}_{2}_sequence.txt'.format(current_app.config['TMP_FOLDER'], raw_input_hash, 'spip'),
                    '-O',
                    '{0}/{1}_{2}.txt'.format(current_app.config['TMP_FOLDER'], raw_input_hash, 'spip_results'),
                    '-g',
                    'hg38',
                    '--transcriptome',
                    '/hidden/RefFiles/transcriptome_hg38.RData'
                ])
                result = run_spip(args_list)
                print(args_list)
            else:
                return return_json('Bad spip input submitted', 1)
        else:
            return return_json('Bad parameters received', 1)
        if result.returncode == 0:
            # success
            # treat result to return them as json
            with open('{0}/{1}_{2}.txt'.format(current_app.config['TMP_FOLDER'], raw_input_hash, 'spip_results'), "r") as spip_out:
                result_file = spip_out.read()
            os.remove('{0}/{1}_{2}.txt'.format(current_app.config['TMP_FOLDER'], raw_input_hash, 'spip_sequence'))
            os.remove('{0}/{1}_{2}.txt'.format(current_app.config['TMP_FOLDER'], raw_input_hash, 'spip_results'))
            # populate redis cache
            r.set(raw_input_hash, json.dumps(result_file))
            return return_json(
                None,
                result.returncode,
                200,
                result_file
            )
        return return_json('SPiP execution error', result.returncode, 500)