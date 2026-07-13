import os
import re
import sys
import argparse
from cyvcf2 import VCF


def to_float(value):
    """Safely convert a value to float, returning np.nan on failure."""
    if not value:
        return None
    try:
        return round(float(value), 4)
    except (ValueError, TypeError):
        return None


def ms_vis_parse_variant_record(variant, gene_symbol, refseq):
    """
    Helper function to parse a single variant record (from cyvcf2 or a dictionary).
    Returns a list of variant data dictionaries (one for each relevant transcript).
    code copied from https://github.com/JMdeSteAgathe/missense_visual/blob/main/app.py function parse_variant_record
    """
    parsed_variants = []
    info_dict = variant.INFO
    chrom, pos, ref, alt = variant.CHROM, variant.POS, variant.REF, ','.join(variant.ALT)
    variant_id = str(variant.ID) if variant.ID else None
    bcsq_string = info_dict.get('BCSQ')
    if bcsq_string is None:
        return []
    for entry in bcsq_string.split(','):
        fields = entry.split('|')
        if len(fields) < 6:
            continue
        consequence, entry_gene, entry_transcript, biotype, strand, aa_change = fields[0:6]
        if consequence != 'missense' or entry_gene != gene_symbol or not aa_change:
            continue
        
        match = re.match(r'(\d+)', aa_change)
        if not match:
            continue
        
        aa_position = int(match.group(1))
        variant_data = {
            'chrom': chrom, 'pos': pos, 'ref': ref, 'alt': alt,
            'variant_id': variant_id,
            'gene': entry_gene, 'transcript': refseq, 'biotype': biotype,
            'aa_position': aa_position, 'aa_change': aa_change,
            'AC_joint': info_dict.get('AC_joint', 0),
            'AC_genomes': info_dict.get('AC_genomes', 0),
            'nhomalt_joint': info_dict.get('nhomalt_joint', 0),
            'nhomalt_genomes': info_dict.get('nhomalt_genomes', 0),
            # Convert all scores to float
            'revel': to_float(info_dict.get('REVEL')),
            'alphamissense': to_float(info_dict.get('am_pathogenicity')),
            'cadd': to_float(info_dict.get('cadd_v1.7')),
            'MPC': to_float(info_dict.get('MPC')),
            'mistic': to_float(info_dict.get('MISTIC_score')),
            'mistic_pred': info_dict.get('MISTIC_pred'),  # Keep as string
            'popEVE': to_float(info_dict.get('popEVE')),
            'bayesdel': to_float(info_dict.get('BayesDel_nsfp33a_noAF')),
            'VARITY_R_LOO': to_float(info_dict.get('VARITY_R_LOO')),
            # === CLINVAR SPECIFIC FIELDS ===
            'CLNDN': info_dict.get('CLNDN'),
            'CLNREVSTAT': info_dict.get('CLNREVSTAT'),
            'CLNSIG': info_dict.get('CLNSIG')
        }
        parsed_variants.append(variant_data)
    return parsed_variants


def main():
    """
    Parse VCF file for a specific gene using coordinates.
    """
    parser = argparse.ArgumentParser(usage='python run_spliceai.py [--seq ATGCATCAGC --context 10000]', description='Compute spliceai raw predictions for a given DNA sequence.')
    parser.add_argument('-f', '--file', default=None, required=True, help='annotated gnomAD or ClinVar file.')
    parser.add_argument('-c', '--chrom', default=None, required=True, help='Chromosome (without "chr").')
    parser.add_argument('-s', '--start', default=None, type=int, required=True, help='Genomic coordinate of gene start')
    parser.add_argument('-e', '--end', default=None, type=int, required=True, help='Genomic coordinate of gene end')
    parser.add_argument('-g', '--gene-symbol', default=None, required=True, help='HGNC Gene symbol')
    parser.add_argument('-r', '--refseq', default=None, required=True, help='NCBI RefSeq id')
    args = parser.parse_args()

    file_match = re.search(r'(clinvar_plp_ms.fully_annotated.vcf.gz|gnomad_ms.fully_annotated.vcf.gz)$', args.file)
    chrom_match = re.match(r'([\dXY]{1,2})$', args.chrom)
    refseq_match = re.match(r'(NM_\d+\.\d{1,2})$', args.refseq)
    gene_match = re.match(r'([\w\d-]+)$', args.gene_symbol)
    if file_match and \
            chrom_match and \
            refseq_match and \
            gene_match:
        chrom = chrom_match.group(1)
        refseq = refseq_match.group(1)
        gene_symbol = gene_match.group(1)
        variants = []
        vcf = VCF(args.file)
        region = "{0}:{1}-{2}".format(chrom, args.start, args.end)
        for variant in vcf(region):
            variants.extend(ms_vis_parse_variant_record(variant, gene_symbol, refseq))
        # to STDOUT
        print(variants)
    else:
        print('Bad parameters')


if __name__ == "__main__":
    main()
