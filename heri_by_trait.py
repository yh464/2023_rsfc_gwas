#!/usr/bin/env python3
'''
This script constitutes the LDSC heritability pipeline for any incoming fastGWA file
'''

import argparse
parser = argparse.ArgumentParser(description = 
  'This script computes heritability analysis for any incoming fastGWA file')
parser.add_argument('--ldsc', dest = 'ldsc', help = 'LDSC executable directory',
  default = '/rds/user/yh464/hpc-work/ldsc/')
parser.add_argument('-i', '--in', dest = '_in', help = 'input fastGWA file')
parser.add_argument('-o','--out', dest = 'out', help = 'output directory (ABSOLUTE)')
parser.add_argument('-f','--force',dest = 'force', help = 'force output',
  default = False, action = 'store_true')
args = parser.parse_args()

import os

args.out = os.path.realpath(args.out)
prefix = os.path.basename(args._in).replace('.fastGWA', '')

scripts_path = os.path.realpath(__file__)
scripts_path = os.path.dirname(scripts_path)
if args.force or (not os.path.isfile(f'{args.out}/{prefix}.sumstats')):
  os.system(f'bash {scripts_path}/ldsc_master.sh '+ \
          f'munge_sumstats.py --sumstats {args._in} --out {args.out}/{prefix}')

# QC h2 log
h2log = f'{args.out}/{prefix}.h2.log'
tmp = open(h2log).read().splitlines()[-7].replace('(','').replace(')','').split()
try: h2 = float(tmp[-2])
except: os.remove(h2log)

if (not os.path.isfile(f'{args.out}/{prefix}.h2.log')) or args.force:
  os.system(f'bash {scripts_path}/ldsc_master.sh ldsc.py '+
    f'--ref-ld-chr {args.ldsc}/baseline/ --w-ld-chr {args.ldsc}/baseline/ '+
    f'--h2 {args.out}/{prefix}.sumstats '+
    f'--out {args.out}/{prefix}.h2')