# general imports
import os
import re
import subprocess
import json
# from collections import OrderedDict
# flask imports
from flask_restful import Resource
from flask import request, jsonify, make_response, current_app
import hashlib
import redis
from .spliceai import getAppRootDirectory, get_data_from_cache, run_spliceai


def return_json(message, return_code=1, http_code=200, result=None):
    # prepare flask response
    return make_response(jsonify({
        'ms_visual_return_code': return_code,
        'result': result,
        'error': message
    }), http_code)


class MissenseVisual(Resource):
    """
    Endpoint to get annotations for all missense of a given gene
    Takes as input a chrom position,  genomic start/end of a gene,
    gene symbol, NCBI Refseq
    Then runs a dedicated script twice
    calling Clivar and gnomad data
    Also uses a redis cache
    """
    def post(self):
        # instatiate redis object
        r = redis.Redis(
            host=current_app.config['CACHE_REDIS_HOST'],
            port=current_app.config['CACHE_REDIS_PORT'],
            socket_timeout=current_app.config['CACHE_DEFAULT_TIMEOUT'],
            db=3
        )
        input = request.get_json()
        # input should be:
        #  {
        #       dataset: "clinvar|gnomad"
        #       chromosome: "[\dXY]'1,2",
        #       start: int
        #       end: int
        #       gene_symbol: "\w\d-",
        #       ncbi_refseq: "NM_\d+\.\d{1,2}"
        #   }
        if 'dataset' in input and \
                'chromosome' in input and \
                'start' in input and \
                'end' in input and \
                'gene_symbol' in input and \
                'ncbi_refseq' in input:
            dataset_match = re.match(r'(clinvar|gnomad)$', input['dataset'])
            chrom_match = re.match(r'([\dXY]{1,2})$', input['chromosome'])
            refseq_match = re.match(r'(NM_\d+\.\d{1,2})$', input['ncbi_refseq'])
            gene_match = re.match(r'([\w\d-]+)$', input['gene_symbol'])
            start_match = re.match(r'(\d+)$', input['start'])
            end_match = re.match(r'(\d+)$', input['end'])
            if dataset_match and \
                    chrom_match and \
                    refseq_match and \
                    gene_match and \
                    start_match and \
                    end_match:
                dataset = dataset_match.group(1)
                chrom = chrom_match.group(1)
                refseq = refseq_match.group(1)
                gene = gene_match.group(1)
                start = start_match.group(1)
                end = end_match.group(1)
                # convert dataset into file
                vcf_file = current_app.config['GNOMAD'] if dataset == 'gnomad' else current_app.config['CLINVAR']

                # computes hash to uniquely identify the query for the redis cache
                raw_input_hash = hashlib.md5('{0}-{1}'.format(dataset, refseq).encode()).hexdigest()
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
                partition = 'spliceaiheavy'
                args_list = []
                if 'SRUN' in current_app.config:
                    args_list = [current_app.config['SRUN'], '-N', '1', '-c', '1', '-J', 'ms_visual','-p', partition]
                args_list.extend([
                    current_app.config['MS_VISUAL_PYTHON'],
                    '{0}/get_ms_visual_data.py'.format(getAppRootDirectory()),
                    '--file',
                    '{0}/hidden/ms_visual/{1}'.format(getAppRootDirectory(), vcf_file),
                    '--chrom',
                    chrom,
                    '--start',
                    start,
                    '--end',
                    end,
                    '--gene-symbol',
                    gene,
                    '--refseq',
                    refseq
                ])
                result = run_spliceai(args_list)
                if result.returncode == 0:
                    # success
                    # treat result to return them as json
                    if (result.stdout == 'Bad parameters'):
                        return return_json('Bad Missense-visual parameters submitted to the script', 1)
                    # results = json.loads(result.stdout)
                    ms_visual_results = {
                        'dataset': dataset,
                        'ms_visual': json.loads(result.stdout)
                    }

                    r.set(raw_input_hash, json.dumps(ms_visual_results))
                    return return_json(
                        None,
                        result.returncode,
                        200,
                        ms_visual_results
                    )
            else:
                return return_json('Bad Missense-visual input submitted', 1)
        else:
            return return_json('Bad Missense-visual parameters received', 1)