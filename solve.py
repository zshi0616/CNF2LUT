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
from main import main as cnf2lut
import time 

# CASE_DIR = './case/'
# CASE_LIST = [
# ]

CASE_DIR = '/Users/zhengyuanshi/studio/dataset/LEC/all_case_cnf/'
CASE_LIST = [
    'mult_op_DEMO1_9_9_TOP11', 'c8', 'b31'
]

def solve(cnf_path, tmp_bench_path='./tmp/output.bench', tmp_cnf_path='./tmp/tmp.cnf'):
    init_cnf, no_var = cnf_utils.read_cnf(cnf_path)
    init_cnf = cnf_utils.sort_cnf(init_cnf)
    all_cnf = []
    if len(init_cnf[0]) == 1:       # Exist unit clause
        if init_cnf[0][0] < 0:
            reverse_var = abs(init_cnf[0][0])
            all_cnf.append((cnf_utils.reverse_cnf(init_cnf, reverse_var), reverse_var))
        else:
            all_cnf.append((init_cnf, -1))
    else:
        div_var = abs(init_cnf[0][0])
        cnf_pos = [[div_var]] + init_cnf
        cnf_neg = [[-div_var]] + init_cnf
        all_cnf.append((cnf_pos, -1))
        all_cnf.append((cnf_utils.reverse_cnf(cnf_neg, div_var), div_var))
    
    assert len(all_cnf) == 1 or len(all_cnf) == 2
    
    # Statistic
    trans_time = 0
    solve_time = 0
    bench_size = 0
    cnf_size = 0
    
    ########################################
    # Solve 
    ########################################
    for cnf, reverse_var in all_cnf:
        cnf_utils.save_cnf(cnf, no_var, tmp_cnf_path)
        start_time = time.time()
        cnf2lut(tmp_cnf_path, tmp_bench_path)
        trans_time += time.time() - start_time

        # Parse Bench
        bench_x_data, bench_fanin_list, bench_fanout_list = lut_utils.parse_bench(tmp_bench_path)
        bench_PI_indexs = []
        bench_PO_indexs = []
        for i in range(len(bench_x_data)):
            if len(bench_fanout_list[i]) == 0 and len(bench_fanin_list[i]) > 0:
                bench_PO_indexs.append(i)
            if len(bench_fanin_list[i]) == 0 and len(bench_fanout_list[i]) > 0:
                bench_PI_indexs.append(i)
        assert len(bench_PO_indexs) == 1
        bench_cnf = lut_utils.convert_cnf(bench_x_data, bench_fanin_list, bench_PO_indexs[0])
    
        # Matching 
        map_bench_init = {}
        max_bench_index = 0
        for i in range(len(bench_x_data)):
            bench_node_name = int(bench_x_data[i][0].replace('N', ''))
            map_bench_init[i] = bench_node_name
            if bench_node_name > max_bench_index:
                max_bench_index = bench_node_name
                    
        # Reindex bench CNF
        assert len(bench_cnf[-1]) == 1 and bench_cnf[-1][0] == bench_PO_indexs[0] + 1
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
        sat_status, asg, bench_solvetime = cnf_utils.kissat_solve(new_bench_cnf, max_bench_index+1)
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
        os.remove(tmp_bench_path)
        os.remove(tmp_cnf_path)
        solve_time += bench_solvetime
        bench_size += len(bench_x_data)
        cnf_size += len(bench_cnf)
        
        # Return result
        if sat_status == 1:
            if reverse_var != -1:
                asg[reverse_var-1] = 1 - asg[reverse_var-1]
            return 1, asg, (trans_time, solve_time)
    
    return 0, None, (trans_time, solve_time)

if __name__ == '__main__':
    if len(CASE_LIST) == 0:
        for case_path in glob.glob(os.path.join(CASE_DIR, '*.cnf')):
            case = os.path.basename(case_path)[:-4]
            CASE_LIST.append(case)
    
    for case in CASE_LIST:
        print('[INFO] Case: {:}'.format(case))
        # CNF2LUT
        cnf_path = os.path.join(CASE_DIR, '{}.cnf'.format(case) )
        res, asg, time_list = solve(cnf_path)
        trans_time, solve_time = time_list
        all_time = solve_time + trans_time
        sat_res = 'SAT' if res else 'UNSAT'
        
        # Baseline
        bl_res, _, bl_st = cnf_utils.kissat_solve_file(cnf_path, args='--time=100')
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
        
    