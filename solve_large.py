import numpy as np 
import os 
import copy
import glob
import time 
import argparse
from wrapper import *

CASE_DIR = './case'
CASE_LIST = [
    # 'a26', 'a28', 'b30'
    # 'ham3_28_5_2', 'c17_5_-1', 
    'brent_9_0', 'brent_13_0_1', 'brent_15_0_25'
]

if __name__ == '__main__':
    tot_bl_time = 0
    tot_our_solvetime = 0
    tot_our_transtime = 0
    
    for case in CASE_LIST:
        print('[INFO] Case: {:}'.format(case))
        cnf_path = os.path.join(CASE_DIR, '{}.cnf'.format(case) )
        ####################################################################
        # C2L: CNF -> LUT -> CNF -> SAT
        ####################################################################
        c2l_res, _, c2l_timelist = cnf2lut_solve(cnf_path, verify=False)
        c2l_time = c2l_timelist[0] + c2l_timelist[1]
        if c2l_res == -1:
            print('[WARNING] c2l Timeout')
        print('[INFO] C2L Trans. {:.2f}s, Solve: {:.2f}s, Tot: {:.2f}s'.format(
            c2l_timelist[0], c2l_timelist[1], c2l_time, 
        ))
        
        # ####################################################################
        # # C2LSAM: CNF -> LUT -> SAM -> CNF -> SAT
        # ####################################################################
        # c2lsam_res, _, c2lsam_timelist = cnf2lut_samsat_solve(cnf_path)
        # c2lsam_time = c2lsam_timelist[0] + c2lsam_timelist[1]
        # if c2lsam_res == -1:
        #     print('[WARNING] c2lsam Timeout')
        # print('[INFO] C2LSAM Trans. {:.2f}s, Solve: {:.2f}s, Tot: {:.2f}s'.format(
        #     c2lsam_timelist[0], c2lsam_timelist[1], c2lsam_time, 
        # ))
        
        print()
    
    print()
    print('=' * 10 + ' PASS ' + '=' * 10)
    print('Total Baseline Time: {:.2f}s'.format(tot_bl_time))
    print('Our Total Trans. Time: {:.2f}s, Solve Time: {:.2f}s'.format(
        tot_our_transtime, tot_our_solvetime
    ))