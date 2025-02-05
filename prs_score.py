#!/usr/bin/env python3
'''
Author: Yuankai He
Correspondence: yh464@cam.ac.uk
Version 1: 2023-07-22
Version 2: 2025-01-23

Batch runs PRS scoring from PRS effect sizes and genotype PLINK binary

Upstream workflow:
    prs_from_gwa_batch.py
'''
    
def main(args):
    import os
    import numpy as np
    from fnmatch import fnmatch
    
    from _utils import array_submitter
    submitter = array_submitter.array_submitter(
        name = 'prs_score', n_cpu = 1,
        timeout = 20, mode = 'long')
    
    # parse input
    flist = np.loadtxt(args._list, dtype = 'U')
    if fnmatch(args.bed, '*.bed'):
        bed_list = [args.bed[:-4]]
    elif os.path.isfile(f'{args.bed}.bed'):
        bed_list = [args.bed]
    elif os.path.isfile(args.bed):
        bed_list = open(args.bed).read().splitlines()
    elif os.path.isdir(args.bed):
        bed_list = []
        for j in range(22):
            for y in os.listdir(args.bed):
                if fnmatch(y.lower(), f'*chr{j+1}.bed'): 
                    bed_list.append(f'{args.bed}/{y[:-4]}')
                    print(bed_list[-1])
    else: raise ValueError('Please supply a valid BED file prefix')
    if len(bed_list) == 1: bed_list *= 22
    if not os.path.isdir(args.out): os.mkdir(args.out)
    
    for i in range(flist.shape[0]):
      f = flist[i,0]
      prefix = f.split('/')[-1].replace('.txt','')
      in_dir = args._in + '/'+ prefix + '/'
      out_dir = args.out +'/'+ prefix +'/'                                     # scores by chr in args.out/prefix/
      if not os.path.isdir(out_dir): os.mkdir(out_dir)
      
      # Score by chromosome
      for j in range(22):
        effsz = in_dir + f'chr{j+1}_pst_eff_a1_b0.5_phi{args.phi:.0e}_chr{j+1}.txt'
        out_fname = f'{out_dir}/{prefix}.chr{j+1}'
        if not os.path.isfile(out_fname+'.sscore') or args.force:
          submitter.add(f'{args.plink} --bfile {bed_list[j]} --chr {j+1} --score {effsz} 2 4 6 center '+
                  f'cols=fid,denom,dosagesum,scoresums --out {out_fname}')
    submitter.submit()
     
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description = 
      'This script concatenates the PRS-cs output to produce individual level PRS scores')
    parser.add_argument('--list', dest = '_list',
      help = 'list of GWA files to generate PRS. FORMAT: ${absolute path} \t ${sample size}',
      default = '../params/gwa_for_prs.list')
    parser.add_argument('-i','--in', dest = '_in', help = 'input directory',
      default = '../prs/prs_effsize/')
    parser.add_argument('--plink', dest = 'plink', help = 'Location of plink2 executable',
      default = '/rds/project/rb643/rds-rb643-ukbiobank2/Data_Genetics/plink2')
    parser.add_argument('--bed', dest = 'bed', help = 'PLINK binaries for target sample, list or directory or prefix',
      default = '../params/bed')
    parser.add_argument('-o','--out', dest = 'out', help = 'output directory',
      default = '../prs/prs_score/')
    parser.add_argument('--phi', dest = 'phi', help = 'shrinkage parameter used for prscs',
      type = float, default = 0.01)
    parser.add_argument('--force','-f', dest = 'force', action = 'store_true',
                        default = False, help = 'force overwrite')
    args = parser.parse_args()
    import os
    for arg in ['_in','out','plink','bed','_list']:
        exec(f'args.{arg} = os.path.realpath(args.{arg})')
    
    from _utils import cmdhistory, path, logger
    logger.splash(args)
    cmdhistory.log()
    proj = path.project()
    proj.add_input(args._in+'/%pheno.txt', __file__)
    proj.add_output(args.out+'/%pheno.txt', __file__)
    try: main(args)
    except: cmdhistory.errlog()