import numpy as np 
import os 
import copy
import glob
import utils.lut_utils as lut_utils
import utils.cnf_utils as cnf_utils
import utils.circuit_utils as circuit_utils
# import utils.aiger_utils as aiger_utils
import utils.simulator as simulator
from utils.utils import run_command
from main import select_cnf
import time 

LUT_MAX_FANIN = 5
gate_to_index={'PI': 0, 'LUT': 1}
CASE_DIR = './testcase/'
CASE_LIST = [
    # 'a28'
    # 'tt_7'
    # 'mchess16-mixed-45percent-blocked',
    # 'mchess16-mixed-35percent-blocked',
    # 'php15-mixed-15percent-blocked','php16-mixed-35percent-blocked','php17-mixed-15percent-blocked',
    # '10pipe_q0_k',
    # 'brent_9_0',
    # # '46bits_11',
    # '138_apx_2_DS-ST',
    # 'apx_0','apx_2_DC-AD','apx_2_DS-ST',
    # 'brent_13_0_1','brent_15_0.25','brent_15_0_25','brent_69_0_3','mchess16-mixed-25percent-blocked',
    # 'mrpp_6x6_18_20',
    # 'php17-mixed-35percent-blocked','sat05-2534','SE_apx_0','velev-pipe-o-uns-1-7','vlsat2_11_42',
    # 'vmpc_28.shuffled-as.sat05-1957','WS_400_24_70_10_apx_1_DC-ST','WS_400_24_70_10_apx_2_DC-AD',
    # 'WS_400_24_70_10_apx_2_DC-ST'
]

# CASE_DIR = '/Users/zhengyuanshi/studio/dataset/LEC/all_case_cn
# CASE_LIST = [
#     'mult_op_DEMO1_9_9_TOP11', 'c8', 'b31'
# ]

# CASE_DIR = '/Users/zhengyuanshi/studio/dataset/SAT_Comp'
# CASE_LIST = [
#     # 'mchess16-mixed-35percent-blocked', 
#     'brent_9_0', 'apx_2_DS-ST'
# ]

TIMEOUT = 1000

def append_cnf(cnf, no_vars):
    cnf = cnf_utils.sort_cnf(cnf)
    po_var = abs(cnf[0][0])
    x_data = []     # [name, is_lut, tt]
    fanin_list = []
    fanout_list = []
    has_lut = [0] * no_vars
    clause_visited = [0] * len(cnf)
    extra_po = []
    extra_pi = []
    po_idx = po_var - 1
    map_inv_idx = {}
    new_cnf = []
    
    # Consider the unit clause as PO, generate LUT for po_var at first
    lut_queue = []
    lut_queue.append(po_idx)
    has_lut[po_idx] = 1
    
    # Create gate 
    for k in range(1, no_vars + 1):
        x_data.append([k-1, gate_to_index['PI'], ''])
        fanin_list.append([])
        fanout_list.append([])
    
    while len(lut_queue) > 0:
        lut_idx = lut_queue.pop(0)
        # Select clauses for LUT generation
        var_comb, cover_clauses, tt = select_cnf(cnf, clause_visited, lut_idx)
        if len(var_comb) == 0:
            # print('[DEBUG] LUT %d has no clauses, consider as PI' % lut_idx)
            continue
        lut_fanin_list = []
        # print('LUT %d: %s' % (lut_idx, var_comb))
        
        for clause_idx in cover_clauses:
            clause_visited[clause_idx] = 1
        
        for var in var_comb:
            lut_fanin_list.append(var-1)
        
        for idx in lut_fanin_list:
            if not has_lut[idx]:
                lut_queue.append(idx)
                has_lut[idx] = 1
                
        # Parse 3-lut tt: 2 - Don't Care / -1 - Not Available State 
        # if 2 in tt:
        #     new_fanin_idx = len(x_data)
        #     extra_pi.append(len(x_data))
        #     x_data.append([new_fanin_idx, gate_to_index['PI'], ''])
        #     fanin_list.append([])
        #     fanout_list.append([])
        #     lut_fanin_list.append(new_fanin_idx)
        #     new_tt = []
        #     for k in range(len(tt)):
        #         if tt[k] == 2:
        #             new_tt.append(0)
        #             new_tt.append(1)
        #         else:
        #             new_tt.append(tt[k])
        #             new_tt.append(tt[k])
        #     tt = new_tt
            
        add_fanout_tt = [1] * len(tt)
        new_fanout_idx = len(x_data)
        if -1 in tt:
            # add_fanout_tt = [1] * len(tt)
            for k in range(len(tt)):
                if tt[k] == -1:
                    add_fanout_tt[k] = 0
                    tt[k] = 0       # 2 means don't care, if unsupport in LUT parser, use 0 
            # new_fanout_idx = len(x_data)
            x_data.append([new_fanout_idx, 0, 0])
            extra_po.append(new_fanout_idx)
            # add_fanout_tt_hex, ordered_lut_fanin_idx = create_lut(add_fanout_tt, lut_fanin_list)
            # tt_hex, ordered_lut_fanin_idx = create_lut(tt, lut_fanin_list)
            
        subcnf_tt = []
        for tt_idx, tt_value in enumerate(tt): 
            if tt_value == 2:
                continue
            tt_bin = bin(tt_idx)[2:]
            padded_binary_string = tt_bin.zfill(len(lut_fanin_list))
            binary_array = [int(bit) for bit in padded_binary_string]
            tt_array = [1 if x == 0 else -x for x in binary_array]      #[0,1]转换成[1,-1]
            clause = [x * (y+1) for x, y in zip(tt_array, lut_fanin_list)]
            clause.append(lut_idx+1 if tt_value==1 else -1*(lut_idx+1) )
            subcnf_tt.append(clause)
        subcnf_tt_addfo = []
        for tt_idx, tt_value in enumerate(add_fanout_tt): 
            if tt_value == 2:
                continue
            tt_bin = bin(tt_idx)[2:]
            padded_binary_string = tt_bin.zfill(len(lut_fanin_list))
            binary_array = [int(bit) for bit in padded_binary_string]
            tt_array = [1 if x == 0 else -x for x in binary_array]      #[0,1]转换成[1,-1]
            clause = [x * (y+1) for x, y in zip(tt_array, lut_fanin_list)]
            clause.append(new_fanout_idx+1 if tt_value==1 else -1*(new_fanout_idx+1) )
            subcnf_tt_addfo.append(clause)
        
        subcnf = subcnf_tt + subcnf_tt_addfo
        # BCP
        remove_flag = [False] * len(subcnf)
        for clause_k, clause in enumerate(subcnf):
            if new_fanout_idx+1 in clause:
                remove_flag[clause_k] = True
            elif -(new_fanout_idx+1) in clause:    
                clause.remove(-(new_fanout_idx+1))
        bcp_subcnf = []
        for clause_k, clause in enumerate(subcnf):
            if remove_flag[clause_k] == False:
                bcp_subcnf.append(subcnf[clause_k])
        # print()
        # replace
        # cover_clauses.sort(reverse=True)
        # for cover_idx, clause_idx in enumerate(cover_clauses):
        #     cnf.pop(clause_idx)
        #     clause_visited.pop(clause_idx)
        # cnf+=bcp_subcnf
        # clause_visited += len(bcp_subcnf)*[1]
        new_cnf += bcp_subcnf
        # has_lut += len(bcp_subcnf)*[0]
        # print()
        
    
    for clause_idx in range(len(cnf)):
        if clause_visited[clause_idx] == 0:
            new_cnf.append(cnf[clause_idx])
    return new_cnf

def solve(cnf_path):
    cnf, no_var = cnf_utils.read_cnf(cnf_path)
    cnf = cnf_utils.sort_cnf(cnf)
    start_time = time.time()
    # new_cnf= replace_cnf(cnf, no_var)
    appended_cnf= append_cnf(cnf, no_var)
    trans_time = time.time() - start_time

    
    # Solve new cnf
    check_cnf_res = True
    sat_status, asg, bench_solvetime = cnf_utils.kissat_solve(appended_cnf, no_var, args='--time={}'.format(TIMEOUT)) 
    # sat_status, asg, bench_solvetime = cnf_utils.kissat_solve(new_cnf, no_var) 
    # 可以保证变量数量no_var不变吗  会不会在归约过程中消掉了一些
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
        
    