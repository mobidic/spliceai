import os
import argparse
# spliceai import
from keras.models import load_model
from pkg_resources import resource_filename
from spliceai.utils import one_hot_encode
import numpy as np


def main():
    parser = argparse.ArgumentParser(usage='python run_spliceai.py [--seq ATGCATCAGC --context 10000]', description='Compute spliceai raw predictions for a given DNA sequence.')
    # parser.add_argument('-wt', '--wt-seq', default=None, required=False, help='Wild type sequence to be computed.')
    # parser.add_argument('-mt', '--mt-seq', default='CGATCTGACGTGGGTGTCATCGCATTATCGATATTGCAT', required=False, help='Mutant sequence to be computed.')
    parser.add_argument('-wth', '--wt-hash', default=None, required=False, help='Wild type sequence hash.')
    parser.add_argument('-mth', '--mt-hash', default='4e8dc438ea52c410caabb1a0774494c6', required=False, help='Mutant sequence hash.')
    parser.add_argument('-c', '--context', default=10000, required=False, help='Context nucleotide to be considered for computation. Default: 10000.')
    parser.add_argument('-t', '--tmp_folder', default='/var/www/tmp_res', required=False, help='Path to tmp folder to store spliceai results. Default: /var/www/tmp_res.')
    args = parser.parse_args()

    # wt_sequence = args.wt_seq
    wt_hash = args.wt_hash
    # mt_sequence = args.mt_seq
    mt_hash = args.mt_hash
    context = int(args.context)
    tmp_folder = args.tmp_folder
    # print('run_spliceai mt: {}'.format(len(mt_sequence)), file=sys.stderr)
    # print(context)
    paths = ('models/spliceai{}.h5'.format(x) for x in range(1, 6))
    # models = [load_model(resource_filename('spliceai', x)) for x in paths]
    models = [load_model(resource_filename('spliceai', x), compile=False) for x in paths]
    wt_result = 't'
    # if wt_sequence:
    if wt_hash:
        with open('{0}/{1}_wt_sequence.txt'.format(tmp_folder, wt_hash), 'r') as wt_seq_file:
            wt_sequence = wt_seq_file.read()
        wt_seq_file.close()
        os.remove('{0}/{1}_wt_sequence.txt'.format(tmp_folder, wt_hash))
        x = one_hot_encode('N'*(context//2) + wt_sequence + 'N'*(context//2))[None, :]
        y = np.mean([models[m].predict(x) for m in range(5)], axis=0)
        wt_acceptor_prob = y[0, :, 1]
        wt_donor_prob = y[0, :, 2]
    else:
        wt_result = 'f'
        wt_acceptor_prob = np.array([-1])
        wt_donor_prob = np.array([-1])
    with open('{0}/{1}_mt_sequence.txt'.format(tmp_folder, mt_hash), 'r') as mt_seq_file:
        mt_sequence = mt_seq_file.read()
    mt_seq_file.close()
    os.remove('{0}/{1}_mt_sequence.txt'.format(tmp_folder, mt_hash))
    x = one_hot_encode('N'*(context//2) + mt_sequence + 'N'*(context//2))[None, :]
    y = np.mean([models[m].predict(x) for m in range(5)], axis=0)
    mt_acceptor_prob = y[0, :, 1]
    mt_donor_prob = y[0, :, 2]

    # print(wt_acceptor_prob)
    # print(wt_donor_prob)
    # print(mt_acceptor_prob)
    np.savetxt('{0}/{1}_wt_acceptor_prob.txt'.format(tmp_folder, wt_hash), wt_acceptor_prob, fmt='%4.8f', delimiter=' ')
    np.savetxt('{0}/{1}_wt_donor_prob.txt'.format(tmp_folder, wt_hash), wt_donor_prob, fmt='%4.8f', delimiter=' ')
    np.savetxt('{0}/{1}_mt_acceptor_prob.txt'.format(tmp_folder, mt_hash), mt_acceptor_prob, fmt='%4.8f', delimiter=' ')
    np.savetxt('{0}/{1}_mt_donor_prob.txt'.format(tmp_folder, mt_hash), mt_donor_prob, fmt='%4.8f', delimiter=' ')

    print('{0};{1}'.format(context, wt_result))


if __name__ == "__main__":
    main()
