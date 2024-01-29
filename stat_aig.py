import numpy as np 
import deepgate as dg 
import glob
import os 

from utils.utils import run_command
import utils.cnf_utils as cnf_utils

import sys
sys.setrecursionlimit(10000)

# cnf_dir = '../dataset/SAT_Comp'
# NAME_LIST = [
#     'mchess16-mixed-25percent-blocked', 'vlsat2_11_42'
# ]

cnf_dir = '../dataset/LEC/all_case_cnf'
NAME_LIST = [
    'mult_op_DEMO1_10_10_TOP13', 'aa9'
]

if __name__ == '__main__':
    aig_parser = dg.AigParser()
    for cnf_path in glob.glob(os.path.join(cnf_dir, '*.cnf')):
        cnf_name = cnf_path.split('/')[-1].split('.')[0]
        if cnf_name not in NAME_LIST:
            continue
        aig_path = './tmp/' + cnf_name + '.aig'
        
        # Convert CNF to AIG
        cmd = 'cnf2aig {} {}'.format(cnf_path, aig_path)
        stdout, _ = run_command(cmd)
        if 'error' in stdout:
            print('Error: {}'.format(stdout))
            continue
        
        # Read CNF 
        clauses, no_vars = cnf_utils.read_cnf(cnf_path)
        no_clauses = len(clauses)
        
        # Read AIG
        g = aig_parser.read_aiger(aig_path)
        os.remove(aig_path)
        no_nodes = len(g.x)
        no_levels = g.forward_level.max().item()
        
        print('=' * 20)
        print('CNF Case: {}, # Clauses: {:}, # Vars: {:}'.format(
            cnf_name, no_clauses, no_vars
        ))
        print('AIG Case: {}, # Nodes: {:}, # Levels: {:}'.format(
            cnf_name, no_nodes, no_levels
        ))
        
        # Original AIG
        original_aig_path = '../dataset/LEC/all_case/' + cnf_name + '.aiger'
        if not os.path.exists(original_aig_path):
            original_aig_path = '../dataset/LEC/all_case/' + cnf_name + '.blif.aiger'
            if not os.path.exists(original_aig_path):
                continue
        original_g = aig_parser.read_aiger(original_aig_path)
        original_no_nodes = len(original_g.x)
        original_no_levels = original_g.forward_level.max().item()
        print('Original AIG Case: {}, # Nodes: {:}, # Levels: {:}'.format(
            cnf_name, original_no_nodes, original_no_levels
        ))
        