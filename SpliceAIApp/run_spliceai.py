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
    args = parser.parse_args()

    wt_sequence = args.wt_seq
    mt_sequence = args.mt_seq
    context = int(args.context)
    print(context)
    paths = ('models/spliceai{}.h5'.format(x) for x in range(1, 6))
    models = [load_model(resource_filename('spliceai', x)) for x in paths]
    if wt_sequence:
        x = one_hot_encode('N'*(context//2) + wt_sequence + 'N'*(context//2))[None, :]
        y = np.mean([models[m].predict(x) for m in range(5)], axis=0)
        wt_acceptor_prob = y[0, :, 1]
        wt_donor_prob = y[0, :, 2]
    else:
        wt_acceptor_prob = '[no_wt]'
        wt_donor_prob = '[no_wt]'
    x = one_hot_encode('N'*(context//2) + mt_sequence + 'N'*(context//2))[None, :]
    y = np.mean([models[m].predict(x) for m in range(5)], axis=0)
    mt_acceptor_prob = y[0, :, 1]
    mt_donor_prob = y[0, :, 2]

    print(wt_acceptor_prob)
    print(wt_donor_prob)
    print(mt_acceptor_prob)
    print(mt_donor_prob)
    # with open('ref.bedGraph', mode='w') as bedgraph:
    #     bedgraph.write("browser position chr{}:{}-{}\ntrack name=\"    REF allele\" type=bedGraph description=\"spliceAI_REF     acceptor_sites = positive_values       donor_sites = negative_values\" visibility=full windowingFunction=maximum color=200,100,0 altColor=0,100,200 priority=20 autoScale=off viewLimits=-1:1 darkerLabels=on\n".format(chrom, pos-100, pos+100))
    #     for i, (i1, i2) in enumerate(zip(np.around(wt_acceptor_prob, 2), np.around(wt_donor_prob, 2))):
    #         bedgraph.write('chr{}\t{}\t{}\t{}\n'.format(chrom, cstart + strand*i-1, cstart + strand*i, i1 if i1>i2 else i2*(-1)))


if __name__ == "__main__":
    main()
