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

NO_PIS = 4
RANDOM_TEST = False

if __name__ == '__main__':
    init_bench_path = './tmp/init.bench'
    init_aig_path = './tmp/init.aig'
    cnf_path = './tmp/init.cnf'
    output_bench_path = './tmp/output.bench'
    output_aig_path = './tmp/output.aig'
    
    for loop_idx in range(2 ** (2 ** NO_PIS)):
        if loop_idx < 3006:
            continue
        if RANDOM_TEST:
            tt_idx = np.random.randint(0, 2 ** (2 ** NO_PIS))
            print('Start TT: {}'.format(tt_idx))
        else:
            tt_idx = loop_idx 
        tt = simulator.dec2list(tt_idx, (2 ** NO_PIS))
        tt_hex = simulator.list2hex(tt, 2 ** (NO_PIS-2))
        cmd = 'abc -c \'read_truth {}; strash; write_bench {}; write_aiger {}; print_stats; \''.format(
            tt_hex, init_bench_path, init_aig_path
        )
        stdout_info, _ = run_command(cmd)
        if not 'and' in stdout_info[-2]:
            print('[INFO] Skip: {}\n'.format(tt_hex))
            continue
        
        x_data, edge_index = aiger_utils.aig_to_xdata(init_aig_path)
        fanin_list, fanout_list = circuit_utils.get_fanin_fanout(x_data, edge_index)
        PO_indexs = []
        PI_indexs = []
        for i in range(len(x_data)):
            if len(fanout_list[i]) == 0 and len(fanin_list[i]) > 0:
                PO_indexs.append(i)
            if len(fanin_list[i]) == 0 and len(fanout_list[i]) > 0:
                PI_indexs.append(i)
        if len(PO_indexs) != 1:
            continue
        if len(PI_indexs) != NO_PIS:
            continue
        
        cnf = aiger_utils.aig_to_cnf(x_data, fanin_list, const_1=PO_indexs)
        cnf_utils.save_cnf(cnf, len(x_data), cnf_path)
        
        # Convert to LUT
        cnf2lut(cnf_path, output_bench_path)
        
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
        for i in range(len(bench_x_data)):
            bench_node_name = int(bench_x_data[i][0].replace('N', ''))
            map_bench_init[i] = bench_node_name
                    
        # Reindex bench CNF
        assert len(bench_cnf[-1]) == 1 and bench_cnf[-1][0] == bench_PO_indexs[0] + 1
        assert len(cnf[-1]) == 1 and cnf[-1][0] == PO_indexs[0] + 1
        new_bench_cnf = copy.deepcopy(bench_cnf)
        for clause_k in range(len(new_bench_cnf)):
            for ele_k in range(len(new_bench_cnf[clause_k])):
                literal = new_bench_cnf[clause_k][ele_k]
                if literal > 0:
                    new_bench_cnf[clause_k][ele_k] = map_bench_init[abs(literal)-1] + 1
                else:
                    new_bench_cnf[clause_k][ele_k] = -1 * (map_bench_init[abs(literal)-1] + 1)
        
        # Solve bench cnf
        sat_status, asg, _ = cnf_utils.kissat_solve(new_bench_cnf, len(bench_x_data))
        os.remove(init_bench_path)
        os.remove(init_aig_path)
        os.remove(cnf_path)
        os.remove(output_bench_path)
        
        # BCP
        bcp_cnf = copy.deepcopy(cnf)
        remove_flag = [False] * len(bcp_cnf)
        check_cnf_res = True
        for var in range(1, len(x_data)+1):
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
            
        print('TT: {}, Check: {}'.format(tt_idx, check_cnf_res))
        assert len(remove_flag) == np.sum(remove_flag)
        assert check_cnf_res
        print()