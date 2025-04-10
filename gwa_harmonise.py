#!/usr/bin/env python3
'''
Author: Yuankai He
Correspondence: yh464@cam.ac.uk
Version 1: 2025-01-07

Harmonises GWAS to fill in missing info from UKB genetics data

Requires following inputs: 
    GWAS summary statistics (scans directory)
    require the following columns: SNP, A1, A2, BETA or OR (manually edit if necessary)
'''

def main(args):
    import os
    import pandas as pd
    from fnmatch import fnmatch
    from time import perf_counter as t
    tic = t()
    # reference SNP info: CHR, SNP, POS, A1, A2, AF1
    ref = pd.read_table(args.ref)
    toc = t() - tic
    print(f'Read reference, time = {toc:.3f}')
    for p in args.pheno:
        flist = []
        for x in os.listdir(f'{args._in}/{p}'):
            if fnmatch(f'{args._in}/{p}/{x}', '*.fastGWA') or fnmatch (x,'*.txt'):
                flist.append(f'{args._in}/{p}/{x}')
        
        for x in flist:
            # first line to skip irrelevant files
            l = open(x).readline()
            if not 'BETA' in l and not 'OR' in l: continue
            print(f'Harmonising {x}')
            
            # read df
            df = pd.read_table(x, sep = '\s+')
            for col in ['CHR','POS','BP']: # erase CHR and BP information in case of different GRCh builds
                if col in df.columns: df.drop(col, axis = 1, inplace = True)
            for col in ['A1','A2']:
                df[col] = df[col].str.upper()
                
            # construct df with flipped alleles
            df_rev = df.copy()
            df_rev.loc[:,'A2'] = df.loc[:,'A1'].copy() # intentional
            df_rev.loc[:,'A1'] = df.loc[:,'A2'].copy()
            if 'OR' in df.columns: df_rev['OR'] = df_rev['OR'] ^ -1
            if 'BETA' in df.columns: df_rev['BETA'] *= -1
            
            if 'AF1' in df.columns:
                tmpref = ref.drop('AF1', axis = 1)
                df_rev.loc[:,'AF1'] *= -1
                df_rev.loc[:,'AF1'] += 1
            else: tmpref = ref
            
            merge = pd.merge(tmpref, df, on = ['SNP','A1','A2'])
            merge_rev = pd.merge(tmpref, df_rev, on = ['SNP','A1','A2'])
            
            df = pd.concat([merge, merge_rev], axis = 0).sort_values(by = ['CHR','POS'])
            df.to_csv(x, sep = '\t', index = False)
            toc = t() - tic
            print(f'Finished harmonising {x}, time = {toc:.3f}')
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='This script harmonises GWAS summary stats to align with UKB genetics data')
    parser.add_argument('pheno', help = 'Phenotypes', nargs = '*')
    parser.add_argument('-i','--in', dest = '_in', help = 'Input directory',
        default = '../gwa/')
    parser.add_argument('-r','--ref', dest = 'ref', help = 'reference UKB genetics data',
        default = '/rds/project/rb643/rds-rb643-ukbiobank2/Data_Users/yh464/params/ukb_snp_info.txt')
    args = parser.parse_args()
    import os
    args._in = os.path.realpath(args._in)
    
    from _utils import cmdhistory, logger
    logger.splash(args)
    cmdhistory.log()
    try: main(args)
    except: cmdhistory.errlog()