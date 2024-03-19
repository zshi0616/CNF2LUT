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
import time 

CASE_DIR = './case/'
CASE_LIST = [
    # 'fail_04'
]

# CASE_DIR = '/Users/zhengyuanshi/studio/dataset/LEC/all_case_cnf/'
# CASE_LIST = [
#     'mult_op_DEMO1_9_9_TOP11', 'c8', 'b31'
# ]

# CASE_DIR = '/Users/zhengyuanshi/studio/dataset/SAT_Comp'
# CASE_LIST = [
#     # 'mchess16-mixed-35percent-blocked', 
#     'brent_9_0', 'apx_2_DS-ST'
# ]

TIMEOUT = 1000

def solve(cnf_path):
    cnf, no_var = cnf_utils.read_cnf(cnf_path)
    cnf = cnf_utils.sort_cnf(cnf)
    start_time = time.time()
    bench_x_data, bench_fanin_list, const_1_list = cnf2lut(cnf, no_var)
    trans_time = time.time() - start_time

    # Parse Bench
    for idx in range(len(bench_x_data)):
        bench_x_data[idx] = ['N{:}'.format(idx), bench_x_data[idx][2]]
    bench_cnf = lut_utils.convert_cnf(bench_x_data, bench_fanin_list, const_1_list=const_1_list)

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
    sat_status, asg, bench_solvetime = cnf_utils.kissat_solve(new_bench_cnf, max_bench_index+1, args='--time={}'.format(TIMEOUT))
    assert sat_status != -1     # Not UNKNOWN
    if sat_status == 1:
        # BCP
        bcp_cnf = copy.deepcopy(cnf)
        remove_flag = [False] * len(bcp_cnf)
        for var in range(1, no_var+1):
            var_value = asg[var-1]
            for clause_k, clause in enumerate(bcp_cnf):
                if remove_flag[clause_k]:
                    continue
                if var_value == 1:
                    if var in clause:
                        remove_flag[clause_k] = True
                        continue
                    if -var in clause:
                        clause.remove(-var)
                else:
                    if -var in clause:
                        remove_flag[clause_k] = True
                        continue
                    if var in clause:
                        clause.remove(var)
        
            for clause_k, clause in enumerate(bcp_cnf):
                if len(clause) == 0:
                    print('{:}, UNSAT'.format(var))
                    check_cnf_res = False
                    break
            if check_cnf_res == False:
                break
        
        assert check_cnf_res

    # sat_res = 'SAT' if sat_status == 1 else 'UNSAT'
    # print('Init CNF # Vars: {:}, # Clauses: {:}'.format(no_var, len(cnf)))
    # print('Results: {}, Check: {}'.format(sat_res, check_cnf_res))
    # print()
    
    # Return result
    if sat_status == 1:
        return 1, asg, (trans_time, bench_solvetime)
    
    return 0, None, (trans_time, bench_solvetime)

if __name__ == '__main__':
    if len(CASE_LIST) == 0:
        for case_path in glob.glob(os.path.join(CASE_DIR, '*.cnf')):
            case = os.path.basename(case_path)[:-4]
            CASE_LIST.append(case)
    
    for case in CASE_LIST:
        print('[INFO] Case: {:}'.format(case))
        # CNF2LUT: CNF -> LUT -> CNF -> SAT
        cnf_path = os.path.join(CASE_DIR, '{}.cnf'.format(case) )
        res, asg, time_list = solve(cnf_path)
        trans_time, solve_time = time_list
        all_time = solve_time + trans_time
        sat_res = 'SAT' if res else 'UNSAT'
        
        # Baseline: CNF -> SAT
        bl_res, _, bl_st = cnf_utils.kissat_solve_file(cnf_path, args='--time={}'.format(TIMEOUT))
        if bl_res == -1:
            print('[WARNING] Baseline TO')
        else:
            assert bl_res == res
        
        print('[INFO] Result: {:}'.format(sat_res))
        print('Baseline Time: {:.2f}s'.format(bl_st))
        print('CNF2LUT Trans. {:.2f}s, Solve: {:.2f}s, Tot: {:.2f}s'.format(
            trans_time, solve_time, all_time
        ))
        print('Solve Time Reduction: {:.2f}%'.format(
            (bl_st - all_time) / bl_st * 100
        ))
        print()
        
    