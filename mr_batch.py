#!/usr/bin/env python3
'''
Author: Yuankai He
Correspondence: yh464@cam.ac.uk
2024-11-05

Batch submits jobs for Mendelian Randomisation for all GWAS files in a directory
(usually the same group of phenotypes). Scans the entire directory for GWAS summary
stats of the same data extension.
'''

def main(args):
    import os
    from fnmatch import fnmatch
    import numpy as np
    import pandas as pd
    
    # array submitter
    from _utils import array_submitter
    submitter_main = array_submitter.array_submitter(
        name = 'mr_'+'_'.join(args.p2), env = 'gentoolsr',
        timeout = 20,
        debug = False
        )
    submitter_cause = array_submitter.array_submitter(
        name = 'mr_cause_'+'_'.join(args.p2), env = 'gentoolsr',
        n_cpu = 3, timeout = 20,
        debug = False
        )
    
    # output directory
    if not os.path.isdir(args.out): os.mkdir(args.out)
    
    force = '-f' if args.force else ''
    
    for p2 in args.p2:
      # make output directory wrt p2
      if not os.path.isdir(f'{args.out}/{p2}'): os.mkdir(f'{args.out}/{p2}')
        
      # input processing by scanning directories
      prefix2 = []
      for f in os.listdir(f'{args._in}/{p2}'):
          if fnmatch(f, '*_X*') or fnmatch(f,'*_all_chrs*'): continue # exclude x-chr sum stats
          if fnmatch(f,f'*.{args.ext2}'): prefix2.append(f.replace(f'.{args.ext2}',''))
      
      # parse n2 table
      if os.path.isfile(args.n2):
          n2_tbl = pd.read_table(args.n2)
          if n2_tbl.shape[1] == 2:
              n2_tbl.columns = ['pheno','n']
              n2_tbl['nca'] = np.nan
              n2_tbl['nco'] = np.nan
          elif n2_tbl.shape[1] == 4:
              n2_tbl.columns = ['pheno','n','nca','nco']
          else: raise ValueError('N2 should specify either both NCa and NCo or neither')
      else:
          if type(args.nca) != type(None):
              nca = args.nca; nco = args.n2 - args.nca
          else: nca = np.nan; nco = np.nan
          n2_tbl = pd.DataFrame(dict(pheno = prefix2, n = args.n2, nca = nca, nco = nco))
      n2_tbl.index = n2_tbl.pheno
      
      for p1 in args.p1:
        # input processing by scanning directories
        prefix1 = []
        for f in os.listdir(f'{args._in}/{p1}'):
            if fnmatch(f, '*_X*') or fnmatch(f,'*_all_chrs*'): continue # exclude x-chr sum stats
            if fnmatch(f, f'*.{args.ext1}'): prefix1.append(f.replace(f'.{args.ext1}',''))
        
        # parse n1 table
        if os.path.isfile(args.n1):
            n1_tbl = pd.read_table(args.n1)
            n1_tbl.columns = ['pheno','n']
        else:
            n1_tbl = pd.DataFrame(dict(pheno = prefix1, n = args.n1))
        n1_tbl.index = n1_tbl.pheno
        
        for f1 in prefix1:
          for f2 in prefix2:
            if not os.path.isdir(f'{args.out}/{p2}/{f2}'): os.mkdir(f'{args.out}/{p2}/{f2}')  
            
            # sample size for p2
            n2 = n2_tbl.loc[f2,'n']
            nca = n2_tbl.loc[f2,'nca']
            nca = '' if np.isnan(nca) else f'--nca {nca}'
            nco = n2_tbl.loc[f2,'nco']
            nco = '' if np.isnan(nco) else f'--nco {nco}'
                  
            # sample size for p1
            n1 = n1_tbl.loc[f1, 'n']
            
            # check progress
            out_prefix = f'{args.out}/{p2}/{f2}/{p1}_{f1}_{f2}'
            
            # input file name specification
            gwa1 = f'{args._in}/{p1}/{f1}.{args.ext1}'
            clump1 = f'{args.clump}/{p1}/{f1}_{args.pval:.0e}.clumped' # does not matter if does not exist
            gwa2 = f'{args._in}/{p2}/{f2}.{args.ext2}'
            clump2 = f'{args.clump}/{p2}/{f2}_{args.pval:.0e}.clumped' # also does not matter if does not exist
            
            if not os.path.isfile(f'{out_prefix}_mr_forward_results.txt') or \
                not os.path.isfile(f'{out_prefix}_mr_reverse_results.txt') or \
                not os.path.isfile(f'{out_prefix}_mr_forward_presso_results.txt') or \
                not os.path.isfile(f'{out_prefix}_mr_reverse_presso_results.txt') or args.force:
                submitter_main.add(
                    f'Rscript mr_master.r --g1 {gwa1} --c1 {clump1} --n1 {n1} '+
                    f'--g2 {gwa2} --c2 {clump2} --n2 {n2} {nca} {nco} -o {args.out}/{p2}/{f2} {force}')
            
            if not os.path.isfile(f'{out_prefix}_mr_lcv_results.txt') or args.force: # bidirectional
                submitter_main.add(
                    f'Rscript mr_lcv.r --g1 {gwa1} --g2 {gwa2} --n1 {n1} --n2 {n2} '+
                    f'-o {args.out}/{p2}/{f2} --ldsc {args.ldsc} {force}')
            
            if not os.path.isfile(f'{out_prefix}_mr_forward_cause_results.txt') or \
                not os.path.isfile(f'{out_prefix}_mr_reverse_cause_results.txt') or args.force:
                submitter_cause.add(
                    f'Rscript mr_cause.r --g1 {gwa1} --c1 {clump1} '+
                    f'--g2 {gwa2} --c2 {clump2} -o {args.out}/{p2}/{f2} {force}')
    
    submitter_main.submit()
    submitter_cause.submit()
    
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description = 
      'This script batch runs MR for groups of phenotypes')
    parser.add_argument('-i','--in', dest = '_in', 
                        help = 'input GWA directory, assumes both groups of pheno to be in the same dir',
                        default = '../gwa')
    parser.add_argument('-p1','--pheno1', dest = 'p1', 
                        help = 'Phenotypes group 1 (reserved for IDPs)', nargs = '*',
                        default=['deg_local','degi_local','degc_local',
                                 'clu_local','eff_local','mpl_local'])
    parser.add_argument('-e1','--ext1', dest = 'ext1', help = 'Extension for phenotype group 1',
                        default = 'fastGWA')
    parser.add_argument('-n1', help = 'Sample size for phenotype group 1, number or tabular (two columns, prefix and n, with header)',
                        default = 54030)
    parser.add_argument('-p2','--pheno2', dest = 'p2', 
                        help = 'Phenotypes group 2 (reserved for correlates)', nargs = '*', 
                        default = ['disorders_for_mr']) # require manual fiddling, so create new dir
    parser.add_argument('-e2','--ext2', dest = 'ext2', help = 'Extension for phenotype group 2',
                        default = 'txt')
    parser.add_argument('-n2', help = 'Sample size for phenotype group 2, number or tabular',
                        default = '../params/disorder_sample_size.txt')
    parser.add_argument('-nca', help = 'Sample size for cases in phenotype group 2, number',
                        default = None)
    parser.add_argument('-c','--clump', dest = 'clump', help = 'Directory of clumping files',
                        default = '../clump')
    parser.add_argument('--ldsc', help = 'LD scores, for LCV regression', # intentionally absolute
                        default = '/rds/project/rb643/rds-rb643-ukbiobank2/Data_Users/yh464/params/ldsc_for_gsem/uk10k.l2.ldscore')
    parser.add_argument('--pval', help = 'Clumping p-value threshold', default = 1e-3, type = float)
    parser.add_argument('-o','--out', dest = 'out', help = 'Output directory',
                        default = '../mr')
    parser.add_argument('-f','--force', dest = 'force', action = 'store_true',
                        default = False, help = 'Force overwrite')
    args = parser.parse_args()
    
    import os
    for arg in ['_in','out','clump']:
        exec(f'args.{arg} = os.path.realpath(args.{arg})')
    try: args.n1 = int(args.n1)
    except: args.n1 = os.path.realpath(args.n1)
    try: args.n2 = int(args.n2)
    except: args.n2 = os.path.realpath(args.n2)
    
    from _utils import cmdhistory, path, logger
    logger.splash(args)
    cmdhistory.log()
    proj = path.project()
    proj.add_input(f'{args._in}/{args.p1}/*.{args.ext1}', __file__)
    proj.add_input(f'{args._in}/{args.p2}/*.{args.ext2}', __file__)
    proj.add_input(f'{args.clump}/{args.p1}/*.clumped',__file__)
    proj.add_input(f'{args.clump}/{args.p2}/*.clumped',__file__)
    proj.add_output(f'{args.out}/{args.p2}/*',__file__)
    
    try: main(args)
    except: cmdhistory.errlog()