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

CNF_PATH = './case/aa9.cnf'
# CNF_PATH = '/Users/zhengyuanshi/studio/dataset/SAT_Comp/php16-mixed-35percent-blocked.cnf'

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
    sat_status, asg, bench_solvetime = cnf_utils.kissat_solve(new_bench_cnf, max_bench_index+1)
    end_time = time.time()
    assert sat_status != -1     # Not UNKNOWN
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
        
        assert check_cnf_res
        
    # LUT bench to AIG
    abc_cmd = 'abc -c \"read_bench {:}; print_stats; strash; print_stats;\"'.format(output_bench_path)
    abc_output, _ = run_command(abc_cmd)
    arr = abc_output[-3].replace(' ', '').replace('lev', '').split('=')
    bench_levels = int(arr[-1])
    arr = abc_output[-2].replace(' ', '').replace('and', '').replace('lev', '').split('=')
    bench_aig_nodes = int(arr[-2])
    bench_aig_levels = int(arr[-1])
    
    # CNF2AIG
    cnf2aig_aigpath = './tmp/cnf2aig.aig'
    cnf2aig_cmd = 'cnf2aig {:} {:}'.format(CNF_PATH, cnf2aig_aigpath)
    abc_cmd = 'abc -c \"read_aiger {:}; print_stats;\"'.format(cnf2aig_aigpath)
    _, _ = run_command(cnf2aig_cmd)
    cnf2aig_cmd, _ = run_command(abc_cmd)
    arr = cnf2aig_cmd[-2].replace(' ', '').replace('and', '').replace('lev', '').split('=')
    cnf2aig_aig_nodes = int(arr[-2])
    cnf2aig_aig_levels = int(arr[-1])
    
    sat_res = 'SAT' if sat_status == 1 else 'UNSAT'
    print('Init CNF # Vars: {:}, # Clauses: {:}'.format(no_var, len(cnf)))
    print('CNF2AIG AIG-Netlist # Nodes: {:}, # Levels: {:}'.format(cnf2aig_aig_nodes, cnf2aig_aig_levels))
    print('CNF2LUT LUT-Netlist # Nodes: {:}, # Levels: {:}'.format(len(bench_x_data), bench_levels))
    print('CNF2LUT AIG-Netlist # Nodes: {:}, # Levels: {:}'.format(bench_aig_nodes, bench_aig_levels))
    print('Results: {}, Check: {}'.format(sat_res, check_cnf_res))
    all_time = end_time - start_time
    print('Time Trans. {:.2f}s / Solve {:.2f}s / All {:.2f}s'.format(
        all_time - bench_solvetime, bench_solvetime, all_time
    ))
    print()
    
    os.remove(output_bench_path)
    