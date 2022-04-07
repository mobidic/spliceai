# general imports
import os
import re
import subprocess
# flask imports
from flask_restful import Resource
from flask import request, jsonify, make_response, current_app
from flask_caching import Cache

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


def return_json(message, spliecai_return_code=1, http_code=200, result=None):
    return make_response(jsonify({
        'spliecai_return_code': spliecai_return_code,
        'result': result,
        'error': message
    }), http_code)


class SpliceAi(Resource):
    def get(self):
        input = request.get_json()
        # print(input)
        context = '10000'
        cache = Cache(current_app)
        wt_acceptor = wt_donor = mt_acceptor = mt_donor = None
        if 'context' in input and \
                re.search(r'^\d+$', str(input['context'])):
            context = str(input['context'])
        if 'wt_seq' in input and \
                'mt_seq' in input:
            wt_acceptor = cache.get('{}{}_acceptor'.format(current_app.config['CACHE_KEY_PREFIX'], input['wt_seq']))
            wt_donor = cache.get('{}{}_donor'.format(current_app.config['CACHE_KEY_PREFIX'], input['wt_seq']))
            mt_acceptor = cache.get('{}{}_acceptor'.format(current_app.config['CACHE_KEY_PREFIX'], input['mt_seq']))
            mt_donor = cache.get('{}{}_donor'.format(current_app.config['CACHE_KEY_PREFIX'], input['mt_seq']))
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
                result = subprocess.run(
                    [
                        current_app.config['PYTHON'],
                        '{}/run_spliceai.py'.format(getAppRootDirectory()),
                        '--wt-seq',
                        input['wt_seq'],
                        '--mt-seq',
                        input['mt_seq'],
                        '--context',
                        context
                    ],
                    stdout=subprocess.PIPE
                )
            else:
                return return_json('Bad wt or mt sequences submitted')
        elif 'mt_seq' in input:
            mt_acceptor = cache.get('{}{}_acceptor'.format(current_app.config['CACHE_KEY_PREFIX'], input['mt_seq']))
            mt_donor = cache.get('{}{}_donor'.format(current_app.config['CACHE_KEY_PREFIX'], input['mt_seq']))
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
            else:
                return return_json('Bad mt sequence submitted')
        else:
            return return_json('Bad parameters received')
        if result.returncode == 0:
            # success
            results = re.split(r'\[', str(result.stdout, 'utf-8').replace('\n', ''))
            # print(results)
            # print(results[1])
            if not re.search(r']', results[1]):
                # print(results)
                # wt and mutant results
                wt_acceptor = [list(t) for t in zip((input['wt_seq']), re.split(' ', results[1].replace(r']', '')))]
                wt_donor = [list(t) for t in zip((input['wt_seq']), re.split(' ', results[2].replace(r']', '')))]
                mt_acceptor = [list(t) for t in zip((input['mt_seq']), re.split(' ', results[3].replace(r']', '')))]
                mt_donor = [list(t) for t in zip((input['mt_seq']), re.split(' ', results[4].replace(r']', '')))]
                # populate redis
                cache.set('{}_acceptor'.format(input['wt_seq']), wt_acceptor)
                cache.set('{}_donor'.format(input['wt_seq']), wt_donor)
                cache.set('{}_acceptor'.format(input['mt_seq']), mt_acceptor)
                cache.set('{}_donor'.format(input['mt_seq']), mt_donor)
            else:
                # mutant only
                mt_acceptor = [list(t) for t in zip((input['mt_seq']), re.split(' ', results[3].replace(r']', '')))]
                mt_donor = [list(t) for t in zip((input['mt_seq']), re.split(' ', results[4].replace(r']', '')))]
                # populate redis
                print(result.stdout)
                cache.set('{}_acceptor'.format(input['mt_seq']), mt_acceptor)
                cache.set('{}_donor'.format(input['mt_seq']), mt_donor)
            return return_json(
                None,
                result.returncode,
                200,
                {
                    'spliceai_context': results[0],
                    'wt_sequence': input['wt_seq'],
                    'wt_acceptor_scores': wt_acceptor,
                    'wt_donor_scores': wt_donor,
                    'mt_sequence': input['mt_seq'],
                    'mt_acceptor_scores': mt_acceptor,
                    'mt_donor_scores': mt_donor,
                }
            )
        return return_json('Bad parameters received', result.returncode, 500)
