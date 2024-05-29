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

# Change here !!! (default: main_deloop.py)
from main_deloop import cnf2lut
from main_deloop import main as cnf2lut_bench


import time 

import sys 
sys.setrecursionlimit(100000)

TIMEOUT = 1000 
syn_recipe = 'strash; rewrite -lz; balance; rewrite -lz; balance; rewrite -lz; balance; refactor -lz; balance; refactor -lz; balance; '
mapper_path = './tools/mockturtle/build/examples/my_mapper'
cnf2aig_path = 'cnf2aig'

def cnf2lut_solve(cnf_path, verify=True):
    cnf, no_var = cnf_utils.read_cnf(cnf_path)
    cnf = cnf_utils.sort_cnf(cnf)
    start_time = time.time()
    bench_x_data, bench_fanin_list, const_1_list = cnf2lut(cnf, no_var)
    trans_time = time.time() - start_time
    
    # return 0, None, (trans_time, 0)

    # Parse Bench
    for idx in range(len(bench_x_data)):
        bench_x_data[idx] = ['N{:}'.format(idx), bench_x_data[idx][2]]
    bench_cnf = lut_utils.convert_cnf(bench_x_data, bench_fanin_list, const_1_list=const_1_list)
    
    # Solve without verification 
    if not verify:
        sat_status, asg, bench_solvetime = cnf_utils.kissat_solve(bench_cnf, len(bench_x_data), args='--time={}'.format(TIMEOUT))
        return sat_status, asg, (trans_time, bench_solvetime)
    
    # Matching 
    map_bench_init = {}
    max_bench_index = 0
    for i in range(len(bench_x_data)):
        bench_node_name = int(bench_x_data[i][0].replace('N', ''))
        map_bench_init[i] = bench_node_name
        if bench_node_name > max_bench_index:
            max_bench_index = bench_node_name
                
    # Reindex bench CNF
    # assert len(bench_cnf[-1]) == 1 and bench_cnf[-1][0] == bench_PO_indexs[0] + 1
    new_bench_cnf = copy.deepcopy(bench_cnf)
    for clause_k in range(len(new_bench_cnf)):
        for ele_k in range(len(new_bench_cnf[clause_k])):
            literal = new_bench_cnf[clause_k][ele_k]
            if literal > 0:
                new_bench_cnf[clause_k][ele_k] = map_bench_init[abs(literal)-1] + 1
            else:
                new_bench_cnf[clause_k][ele_k] = -1 * (map_bench_init[abs(literal)-1] + 1)
    
    # Solve bench cnf
    check_cnf_res = True
    print('Size: ', len(new_bench_cnf), len(bench_x_data))
    sat_status, asg, bench_solvetime = cnf_utils.kissat_solve(new_bench_cnf, max_bench_index+1, args='--time={}'.format(TIMEOUT))
    
    if sat_status == -1:
        return -1, None, (trans_time, bench_solvetime)
    
    elif sat_status == 1:
        # BCP 
        sat_flag = [0] * len(cnf)
        for clause_k, clause in enumerate(cnf):
            for var in clause:
                if var > 0 and asg[abs(var)-1] == 1:
                    sat_flag[clause_k] = 1
                    break
                elif var < 0 and asg[abs(var)-1] == 0:
                    sat_flag[clause_k] = 1
                    break
        if np.sum(sat_flag) != len(cnf):
            check_cnf_res = False
        
        assert check_cnf_res
        return 1, asg, (trans_time, bench_solvetime)
    
    else:
        return 0, None, (trans_time, bench_solvetime)
    
def cnf2lut_samsat_solve(cnf_path):     # TODO
    tmp_bench_path = './tmp/tmp_cases.bench'
    start_time = time.time()
    cnf2lut_bench(cnf_path, tmp_bench_path)
    trans_time = time.time() - start_time
    
    # ABC 
    tmp_aig_path = './tmp/tmp_cases.aig'
    tmp_mapped_bench_path = './tmp/tmp_cases_mapped.bench'
    abc_cmd = 'abc -c "read_bench {}; {} write_aiger {};"'.format(tmp_bench_path, syn_recipe, tmp_aig_path)
    abc_out, abc_time = run_command(abc_cmd)
    for line in abc_out:
        assert 'Network contains a combinational loop' not in line
    trans_time += abc_time
    
    # Map 
    map_cmd = '{} {} {}'.format(mapper_path, tmp_aig_path, tmp_mapped_bench_path)
    _, map_time = run_command(map_cmd)
    trans_time += map_time
    
    # Solve 
    x_data, fanin_list, fanout_list, PI_list, PO_list = lut_utils.parse_bench(tmp_mapped_bench_path)
    f = open(tmp_bench_path, 'r')
    lines = f.readlines()
    f.close()
    const_1_list = []
    po_k = 0
    for line in lines: 
        if 'OUTPUT' in line:
            if 'Const_1' in line:
                const_1_list.append(PO_list[po_k])
            po_k += 1
    assert len(PO_list) == po_k 
    bench_cnf = lut_utils.convert_cnf(x_data, fanin_list, const_1_list=const_1_list)
    sat_status, asg, bench_solvetime = cnf_utils.kissat_solve(bench_cnf, len(x_data), args='--time={}'.format(TIMEOUT))
    
    # Remove 
    os.remove(tmp_bench_path)
    os.remove(tmp_aig_path)
    os.remove(tmp_mapped_bench_path)
    
    return sat_status, asg, (trans_time, bench_solvetime)

def cnf2aig_solve(cnf_path):
    tmp_aig_path = './tmp/tmp_cases.aig'
    cnf2aig_cmd = '{} {} {}'.format(cnf2aig_path, cnf_path, tmp_aig_path)
    _, trans_time = run_command(cnf2aig_cmd)
    
    # Parse AIG 
    x_data, edge_index = aiger_utils.aig_to_xdata(tmp_aig_path)
    fanin_list, fanout_list = circuit_utils.get_fanin_fanout(x_data, edge_index)
    PO_list = []
    for idx in range(len(fanout_list)):
        if len(fanout_list[idx]) == 0:
            PO_list.append(idx) 
    assert len(PO_list) == 1
    cnf = aiger_utils.aig_to_cnf(x_data, fanin_list, const_1=PO_list)
    no_vars = len(x_data)
    
    # solve 
    sat_status, asg, aig_solvetime = cnf_utils.kissat_solve(cnf, no_vars, args='--time={}'.format(TIMEOUT))
    
    # Remove
    os.remove(tmp_aig_path)
    
    return sat_status, asg, (trans_time, aig_solvetime)
    
def cnf2aig_samsat_solve(cnf_path):
    tmp_aig_path = './tmp/tmp_cases.aig'
    cnf2aig_cmd = '{} {} {}'.format(cnf2aig_path, cnf_path, tmp_aig_path)
    _, trans_time = run_command(cnf2aig_cmd)
    
    # ABC 
    tmp_mapped_bench_path = './tmp/tmp_cases_mapped.bench'
    abc_cmd = 'abc -c "read_aiger {}; {} write_aiger {};"'.format(tmp_aig_path, syn_recipe, tmp_aig_path)
    _, abc_time = run_command(abc_cmd)
    trans_time += abc_time
    
    # Map 
    map_cmd = '{} {} {}'.format(mapper_path, tmp_aig_path, tmp_mapped_bench_path)
    _, map_time = run_command(map_cmd)
    trans_time += map_time
    
    # Solve 
    x_data, fanin_list, fanout_list, PI_list, PO_list = lut_utils.parse_bench(tmp_mapped_bench_path)
    assert len(PO_list) == 1
    bench_cnf = lut_utils.convert_cnf(x_data, fanin_list, const_1_list=PO_list)
    sat_status, asg, bench_solvetime = cnf_utils.kissat_solve(bench_cnf, len(x_data), args='--time={}'.format(TIMEOUT))
    
    # Remove
    os.remove(tmp_aig_path)
    os.remove(tmp_mapped_bench_path)
    
    return sat_status, asg, (trans_time, bench_solvetime)

def baseline_solve(cnf_path):
    res, _, st = cnf_utils.kissat_solve_file(cnf_path, args='--time={}'.format(TIMEOUT))
    return res, None, (0, st)
    
if __name__ == '__main__':
    print('[INFO] Debug wrapper.py ...')
    
    CASE_LIST = [
        'large_benchmark', 
        # 'mult_op_DEMO1_3_3_TOP6', 
        # 'a28', 
        # 'velev-pipe-o-uns-1-7', 
        # 'brent_15_0_25', 
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
    
        res, asg, time_list = cnf2lut_solve(cnf_path)
        # res, asg, time_list = cnf2lut_samsat_solve(cnf_path)
        
        print('[INFO] Case: {:}, Result: {:}'.format(case_name, res))
        print('Trans.: {:.2f}s, Solve: {:.2f}s'.format(time_list[0], time_list[1]))
        print()