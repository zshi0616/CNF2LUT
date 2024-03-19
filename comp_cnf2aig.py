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
from main import cnf2lut
from main import main as cnf2lutbench
import time 

CASE_DIR = '/Users/zhengyuanshi/studio/dataset/SAT_Comp'
CASE_LIST = [
    # 'mchess16-mixed-35percent-blocked', 
    'brent_9_0', 'apx_2_DS-ST'
]

if __name__ == '__main__':
    if len(CASE_LIST) == 0:
        for case_path in glob.glob(os.path.join(CASE_DIR, '*.cnf')):
            case = os.path.basename(case_path)[:-4]
            CASE_LIST.append(case)
    
    for case in CASE_LIST:
        print('[INFO] Case: {:}'.format(case))
        ####################################################
        # CNF2LUT 
        ####################################################
        cnf_path = os.path.join(CASE_DIR, '{}.cnf'.format(case) )
        cnf, no_var = cnf_utils.read_cnf(cnf_path)
        tmp_bench_path = './tmp/{}.bench'.format(case)
        cnf2lutbench(cnf_path, tmp_bench_path)
        
        abc_cmd = 'abc -c \"read_bench {:}; print_stats; strash; print_stats;\"'.format(tmp_bench_path)
        abc_output, _ = run_command(abc_cmd)
        arr = abc_output[-3].replace(' ', '').replace('edge', '').replace('lev', '').split('=')
        bench_lut_nds = int(arr[-4])
        bench_lut_levs = int(arr[-1])
        arr = abc_output[-2].replace(' ', '').replace('and', '').replace('lev', '').split('=')
        bench_aig_nds = int(arr[-2])
        bench_aig_levs = int(arr[-1])

        ####################################################
        # CNF2AIG
        ####################################################
        cnf2aig_aigpath = './tmp/{}.aig'.format(case)
        cnf2aig_cmd = 'cnf2aig {:} {:}'.format(cnf_path, cnf2aig_aigpath)
        abc_cmd = 'abc -c \"read_aiger {:}; strash; print_stats;\"'.format(cnf2aig_aigpath)
        _, _ = run_command(cnf2aig_cmd)
        if not os.path.exists(cnf2aig_aigpath):
            print('[WARNING] {:} - CNF2AIG failed\n'.format(cnf2aig_aigpath))
            continue
        cnf2aig_cmd, _ = run_command(abc_cmd)
        arr = cnf2aig_cmd[-2].replace(' ', '').replace('and', '').replace('lev', '').split('=')
        cnf2aig_nds = int(arr[-2])
        cnf2aig_levs = int(arr[-1])
        
        ####################################################
        # Print
        ####################################################
        print('Init CNF # Vars: {:}, # Clauses: {:}'.format(no_var, len(cnf)))
        print('CNF2AIG AIG-Netlist # Nodes: {:}, # Levels: {:}'.format(cnf2aig_nds, cnf2aig_levs))
        print('CNF2LUT LUT-Netlist # Nodes: {:}, # Levels: {:}'.format(bench_lut_nds, bench_lut_levs))
        print('CNF2LUT AIG-Netlist # Nodes: {:}, # Levels: {:}'.format(bench_aig_nds, bench_aig_levs))
        print('Reduction # Nodes: {:.2f}%, # Levs: {:.2f}%'.format(
            (cnf2aig_nds - bench_aig_nds) / cnf2aig_nds * 100,
            (cnf2aig_levs - bench_aig_levs) / cnf2aig_levs * 100
        ))
        print()
        
        os.remove(tmp_bench_path)
        os.remove(cnf2aig_aigpath)    
    
    