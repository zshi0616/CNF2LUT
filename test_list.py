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
    # 'c17_5_-1'
    'brent_9_0', 'brent_13_0_1', 'brent_15_0_25'
    # 'mult_op_DEMO1_3_3_TOP6'
]

if __name__ == '__main__':
    tot_bl_time = 0
    tot_our_solvetime = 0
    tot_our_transtime = 0
    
    for case in CASE_LIST:
        print('[INFO] Case: {:}'.format(case))
        cnf_path = os.path.join(CASE_DIR, '{}.cnf'.format(case) )
        ####################################################################
        # Baseline: CNF -> SAT
        ####################################################################
        # bl_res, _, bl_timelist = baseline_solve(cnf_path)
        # bl_time = bl_timelist[1]
        # if bl_res == -1:
        #     print('[WARNING] Baseline Timeout')
        # print('[INFO] Result: {:}'.format(bl_res))
        # print('Baseline Time: {:.2f}s'.format(bl_timelist[1]))
        # tot_bl_time += bl_time
        bl_time = 1
        bl_res = 0
        
        ####################################################################
        # C2L: CNF -> LUT -> CNF -> SAT
        ####################################################################
        c2l_res, _, c2l_timelist = cnf2lut_solve(cnf_path)
        c2l_time = c2l_timelist[0] + c2l_timelist[1]
        if c2l_res == -1:
            print('[WARNING] c2l Timeout')
        assert c2l_res == bl_res
        print('[INFO] C2L Trans. {:.2f}s, Solve: {:.2f}s, Tot: {:.2f}s | Red.: {:.2f}%'.format(
            c2l_timelist[0], c2l_timelist[1], c2l_time, 
            (bl_time - c2l_time) / bl_time * 100
        ))
        tot_our_solvetime += c2l_timelist[1]
        tot_our_transtime += c2l_timelist[0]
        
        # ####################################################################
        # # C2LSAM: CNF -> LUT -> SAM -> CNF -> SAT
        # ####################################################################
        # c2lsam_res, _, c2lsam_timelist = cnf2lut_samsat_solve(cnf_path)
        # c2lsam_time = c2lsam_timelist[0] + c2lsam_timelist[1]
        # if c2lsam_res == -1:
        #     print('[WARNING] c2lsam Timeout')
        # assert c2lsam_res == bl_res
        # print('[INFO] C2LSAM Trans. {:.2f}s, Solve: {:.2f}s, Tot: {:.2f}s | Red.: {:.2f}%'.format(
        #     c2lsam_timelist[0], c2lsam_timelist[1], c2lsam_time, 
        #     (bl_time - c2lsam_time) / bl_time * 100
        # ))
        
        # ####################################################################
        # # C2A: CNF -> AIG -> CNF -> SAT
        # ####################################################################
        # c2a_res, _, c2a_timelist = cnf2aig_solve(cnf_path)
        # c2a_time = c2a_timelist[0] + c2a_timelist[1]
        # if c2a_res == -1:
        #     print('[WARNING] c2a Timeout')
        # assert c2a_res == bl_res
        # print('[INFO] C2A Trans. {:.2f}s, Solve: {:.2f}s, Tot: {:.2f}s | Red.: {:.2f}%'.format(
        #     c2a_timelist[0], c2a_timelist[1], c2a_time, 
        #     (bl_time - c2a_time) / bl_time * 100
        # ))
        
        
        print()
    
    print()
    print('=' * 10 + ' PASS ' + '=' * 10)
    print('Total Baseline Time: {:.2f}s'.format(tot_bl_time))
    print('Our Total Trans. Time: {:.2f}s, Solve Time: {:.2f}s'.format(
        tot_our_transtime, tot_our_solvetime
    ))