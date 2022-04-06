import argparse
# spliceai import
from keras.models import load_model
from pkg_resources import resource_filename
from spliceai.utils import one_hot_encode
import numpy as np


def main():
    parser = argparse.ArgumentParser(usage='python run_spliceai.py [--seq ATGCATCAGC --context 10000]', description='Compute spliceai raw predictions for a given DNA sequence.')
    parser.add_argument('-s', '--seq', default='CGATCTGACGTGGGTGTCATCGCATTATCGATATTGCAT', required=False, help='Sequence to be computed.')
    parser.add_argument('-c', '--context', default=10000, required=False, help='Context nucleotide to be considered for computation. Default: 10000.')
    args = parser.parse_args()

    input_sequence = args.seq
    context = args.context
    paths = ('models/spliceai{}.h5'.format(x) for x in range(1, 6))
    models = [load_model(resource_filename('spliceai', x)) for x in paths]
    x = one_hot_encode('N'*(context//2) + input_sequence + 'N'*(context//2))[None, :]
    y = np.mean([models[m].predict(x) for m in range(5)], axis=0)

    acceptor_prob = y[0, :, 1]
    donor_prob = y[0, :, 2]
    return acceptor_prob, donor_prob


if __name__ == "__main__":
    main()
