import numpy as np 
import os 
import copy
import utils.lut_utils as lut_utils
import utils.cnf_utils as cnf_utils
import utils.circuit_utils as circuit_utils
import utils.aiger_utils as aiger_utils
import utils.simulator as simulator
from utils.utils import run_command
from main import main as cnf2lut
import time 

NO_PIS = 4
RANDOM_TEST = False
CNF_PATH = './case/mchess16-mixed-45percent-blocked.cnf'
# CNF_PATH = './case/rand_5.cnf'

if __name__ == '__main__':
    output_bench_path = './tmp/output.bench'
    start_time = time.time()
    
    cnf, no_var = cnf_utils.read_cnf(CNF_PATH)
    # Convert to LUT
    cnf2lut(CNF_PATH, output_bench_path)
    
    # Parse Bench
    bench_x_data, bench_fanin_list, bench_fanout_list = lut_utils.parse_bench(output_bench_path)
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
    sat_status, asg, _ = cnf_utils.kissat_solve(new_bench_cnf, max_bench_index+1)
    os.remove(output_bench_path)
    end_time = time.time()
    assert sat_status != -1
    if sat_status == 0:
        init_sat_status, _, _ = cnf_utils.kissat_solve(cnf, no_var)
        assert init_sat_status == 0
    else:
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
        
        assert len(remove_flag) == np.sum(remove_flag)
        assert check_cnf_res
    
    sat_res = 'SAT' if sat_status == 1 else 'UNSAT'
    print('Results: {}, Check: {}'.format(sat_res, check_cnf_res))
    print('Time: {:.2f}s'.format(end_time - start_time))
    print()