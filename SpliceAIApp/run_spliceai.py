# import sys
import argparse
# spliceai import
from keras.models import load_model
from pkg_resources import resource_filename
from spliceai.utils import one_hot_encode
import numpy as np


def main():
    parser = argparse.ArgumentParser(usage='python run_spliceai.py [--seq ATGCATCAGC --context 10000]', description='Compute spliceai raw predictions for a given DNA sequence.')
    parser.add_argument('-wt', '--wt-seq', default=None, required=False, help='Wild type sequence to be computed.')
    parser.add_argument('-mt', '--mt-seq', default='CGATCTGACGTGGGTGTCATCGCATTATCGATATTGCAT', required=False, help='Mutant sequence to be computed.')
    parser.add_argument('-c', '--context', default=10000, required=False, help='Context nucleotide to be considered for computation. Default: 10000.')
    parser.add_argument('-t', '--tmp_folder', default='/var/www/tmp_res', required=False, help='Path to tmp folder to store spliceai results. Default: /var/www/tmp_res.')
    args = parser.parse_args()

    wt_sequence = args.wt_seq
    mt_sequence = args.mt_seq
    context = int(args.context)
    tmp_folder = args.tmp_folder
    # print('run_spliceai mt: {}'.format(len(mt_sequence)), file=sys.stderr)
    # print(context)
    paths = ('models/spliceai{}.h5'.format(x) for x in range(1, 6))
    models = [load_model(resource_filename('spliceai', x)) for x in paths]
    wt_result = 't'
    if wt_sequence:
        x = one_hot_encode('N'*(context//2) + wt_sequence + 'N'*(context//2))[None, :]
        y = np.mean([models[m].predict(x) for m in range(5)], axis=0)
        wt_acceptor_prob = y[0, :, 1]
        wt_donor_prob = y[0, :, 2]
    else:
        wt_result = 'f'
        wt_acceptor_prob = np.array([-1])
        wt_donor_prob = np.array([-1])
    x = one_hot_encode('N'*(context//2) + mt_sequence + 'N'*(context//2))[None, :]
    y = np.mean([models[m].predict(x) for m in range(5)], axis=0)
    mt_acceptor_prob = y[0, :, 1]
    mt_donor_prob = y[0, :, 2]

    # print(wt_acceptor_prob)
    # print(wt_donor_prob)
    # print(mt_acceptor_prob)
    np.savetxt('{0}/wt_acceptor_prob.txt'.format(tmp_folder), wt_acceptor_prob, fmt='%4.8f', delimiter=' ')
    np.savetxt('{0}/wt_donor_prob.txt'.format(tmp_folder), wt_donor_prob, fmt='%4.8f', delimiter=' ')
    np.savetxt('{0}/mt_acceptor_prob.txt'.format(tmp_folder), mt_acceptor_prob, fmt='%4.8f', delimiter=' ')
    np.savetxt('{0}/mt_donor_prob.txt'.format(tmp_folder), mt_donor_prob, fmt='%4.8f', delimiter=' ')
    print('{0};{1}'.format(context, wt_result))


if __name__ == "__main__":
    main()
