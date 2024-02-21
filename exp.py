import os
import numpy as np 
import copy

import utils.aiger_utils as aiger_utils
import utils.circuit_utils as circuit_utils
import utils.cnf_utils as cnf_utils
import utils.lut_utils as lut_utils
from main import main as cnf2lut

# CASE_NAME = 'mchess16-mixed-45percent-blocked'
CASE_NAME = 'h5'

if __name__ == '__main__':
    cnf_path = './case/{}.cnf'.format(CASE_NAME)
    bench_path = './output/{}.bench'.format(CASE_NAME)
    cnf, no_var = cnf_utils.read_cnf(cnf_path)
    
    cnf2lut(cnf_path, bench_path)
    
    # Parse Bench 
    bench_x_data, bench_fanin_list, bench_fanout_list = lut_utils.parse_bench(bench_path)
    bench_PI_indexs = []
    bench_PO_indexs = []
    for i in range(len(bench_x_data)):
        if len(bench_fanout_list[i]) == 0 and len(bench_fanin_list[i]) > 0:
            bench_PO_indexs.append(i)
        if len(bench_fanin_list[i]) == 0 and len(bench_fanout_list[i]) > 0:
            bench_PI_indexs.append(i)
    assert len(bench_PO_indexs) == 1
    bench_cnf = lut_utils.convert_cnf(bench_x_data, bench_fanin_list, po_idx=bench_PO_indexs[0], use_node_name=True)
    bench_no_var = max(abs(var) for clause in bench_cnf for var in clause)
    
    tmp_filename = './tmp/exp.cnf'
    sat_status, asg, _ = cnf_utils.kissat_solve(bench_cnf, bench_no_var, tmp_filename=tmp_filename)
    cnf_utils.save_cnf(bench_cnf, bench_no_var, tmp_filename)
    
    print(sat_status)
    
    # BCP 
    bcp_cnf = copy.deepcopy(cnf)
    remove_flag = [False] * len(bcp_cnf)
    for var in range(1, len(asg)+1):
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
                break
        
    print()