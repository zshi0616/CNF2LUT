import numpy as np 
import os 
import copy
import glob
import time 
import argparse
import requests

from wrapper import *
from utils.logger import Logger

def get_parse_args():
    parser = argparse.ArgumentParser()
    
    # Required
    parser.add_argument('--log_path', type=str, default='./solve_benchmark.log', help='Path of the log')
    
    # Parse and Initialize
    args = parser.parse_args()
    if not os.path.exists('./tmp'):
        os.mkdir('./tmp')
        
    return args

if __name__ == '__main__':
    args = get_parse_args()
    log = Logger(args.log_path)
    
    # Get case list 
    url = 'https://benchmark-database.de/'
    response = requests.get(url).text
    key = '<td><a href="/file'
    
    pos = response.find(key)
    while pos != -1:
        hash_val = response[pos+19: pos+19+32]
        case_url = 'https://benchmark-database.de/file/{}?context=cnf'.format(hash_val)
        xz_path = './tmp/{}.cnf.xz'.format(hash_val)
        cnf_path = './tmp/{}.cnf'.format(hash_val)
        print('[INFO] Download: {} ... '.format(case_url))
        download_cmd = 'wget -O {} {}'.format(xz_path, case_url)
        _, _ = run_command(download_cmd)
        if os.path.exists(xz_path):
            xz_path = 'xz -d {}'.format(xz_path)
            _, _ = run_command(xz_path)
            if os.path.exists(cnf_path):
                # log.write('[INFO] Case Hash: {:}'.format(hash_val))
                # ####################################################################
                # # Baseline: CNF -> SAT
                # ####################################################################
                # bl_res, _, bl_timelist = baseline_solve(cnf_path)
                # bl_time = bl_timelist[1]
                # if bl_res == -1:
                #     log.write('[WARNING] Baseline Timeout')
                # log.write('[INFO] Result: {:}'.format(bl_res))
                # log.write('Baseline Time: {:.2f}s'.format(bl_timelist[1]))
                
                ####################################################################
                # C2L: CNF -> LUT -> CNF -> SAT
                ####################################################################
                c2l_res, _, c2l_timelist = cnf2lut_solve(cnf_path)
                c2l_time = c2l_timelist[0] + c2l_timelist[1]
                if c2l_res == -1:
                    log.write('[WARNING] c2l Timeout')
                assert bl_res == -1 or c2l_res == bl_res
                log.write('[INFO] C2L Trans. {:.2f}s, Solve: {:.2f}s, Tot: {:.2f}s | Red.: {:.2f}%'.format(
                    c2l_timelist[0], c2l_timelist[1], c2l_time, 
                    (bl_time - c2l_time) / bl_time * 100
                ))
                
                ####################################################################
                # C2LSAM: CNF -> LUT -> SAM -> CNF -> SAT
                ####################################################################
                c2lsam_res, _, c2lsam_timelist = cnf2lut_samsat_solve(cnf_path)
                c2lsam_time = c2lsam_timelist[0] + c2lsam_timelist[1]
                if c2lsam_res == -1:
                    log.write('[WARNING] c2lsam Timeout')
                assert bl_res == -1 or c2lsam_res == bl_res
                log.write('[INFO] C2LSAM Trans. {:.2f}s, Solve: {:.2f}s, Tot: {:.2f}s | Red.: {:.2f}%'.format(
                    c2lsam_timelist[0], c2lsam_timelist[1], c2lsam_time, 
                    (bl_time - c2lsam_time) / bl_time * 100
                ))
                
                log.write()
                os.remove(cnf_path)
    log.close()
        
    