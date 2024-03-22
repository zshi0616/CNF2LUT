import numpy as np 
import os 
import copy
import glob
import utils.lut_utils as lut_utils
import utils.cnf_utils as cnf_utils
import utils.circuit_utils as circuit_utils
import utils.aiger_utils as aiger_utils
import utils.simulator as simulator
from utils.utils import run_command
from main_exp import subcnf_simulation

from itertools import combinations

if __name__ == '__main__':
    CASE_LIST = [
        'velev-pipe-o-uns-1-7', 
        'brent_15_0_25', 
    ]
    CNF_DIR = './case'
    
    if len(CASE_LIST) == 0:
        for case_path in glob.glob(os.path.join(CNF_DIR, '*.cnf')):
            case = os.path.basename(case_path)[:-4]
            CASE_LIST.append(case)
    
    for case_name in CASE_LIST:
        cnf_path = os.path.join(CNF_DIR, '{}.cnf'.format(case_name))
        if not os.path.exists(cnf_path):
            print('[WARNING] {:} not exists'.format(cnf_path))
            continue
        
        cnf, no_vars = cnf_utils.read_cnf(cnf_path)
        cnf = cnf_utils.sort_cnf(cnf)[::-1]
        
        max_var_len = 4 
        var_comb_map = {}
        for clause_idx, clause in enumerate(cnf):
            if len(clause) > max_var_len:
                continue
            var_comb = []
            for var in clause:
                var_comb.append(abs(var))
            var_comb = tuple(sorted(var_comb))
            if var_comb not in var_comb_map:
                var_comb_map[var_comb] = [clause_idx]
            else:
                var_comb_map[var_comb].append(clause_idx)
        
        # Find sub var_comb
        for var_comb in var_comb_map.keys():
            for sub_var_len in range(1, len(var_comb)):
                sub_var_comb_list = list(combinations(var_comb, sub_var_len))
                for sub_var_comb in sub_var_comb_list:
                    if sub_var_comb in var_comb_map:
                        var_comb_map[var_comb] += var_comb_map[sub_var_comb]
        
        # Sort by the number of clauses
        var_comb_map = {k: v for k, v in sorted(var_comb_map.items(), key=lambda item: len(item[1]), reverse=True)}
        
        # Simulation 
        for var_comb in var_comb_map.keys():
            print('var_comb: {:}'.format(var_comb))
            sub_cnf = []
            for clause_idx in var_comb_map[var_comb]:
                sub_cnf.append(cnf[clause_idx])
            var_list = list(var_comb)[:-1]
            fanout_var = list(var_comb)[-1]
            
            tt = subcnf_simulation(sub_cnf, var_list, fanout_var)
        
        
        print()
        