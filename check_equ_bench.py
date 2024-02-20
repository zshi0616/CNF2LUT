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

if __name__ == '__main__':
    init_bench_path = './tmp/init.bench'
    init_aig_path = './tmp/init.aig'
    cnf_path = './tmp/init.cnf'
    output_bench_path = './tmp/output.bench'
    output_aig_path = './tmp/output.aig'
    
    for tt_idx in range(2 ** (2 ** NO_PIS)):
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
            if bench_node_name < len(x_data):
                map_bench_init[i] = bench_node_name
                    
        # Reindex bench CNF
        assert len(bench_cnf[-1]) == 1 and bench_cnf[-1][0] == bench_PO_indexs[0] + 1
        assert len(cnf[-1]) == 1 and cnf[-1][0] == PO_indexs[0] + 1
        new_bench_cnf = copy.deepcopy(bench_cnf)
        max_init_var = len(x_data) - len(map_bench_init)
        for clause_k in range(len(new_bench_cnf)):
            for ele_k in range(len(new_bench_cnf[clause_k])):
                literal = new_bench_cnf[clause_k][ele_k]
                if abs(literal)-1 in map_bench_init:
                    if literal > 0:
                        new_bench_cnf[clause_k][ele_k] = map_bench_init[abs(literal)-1] + 1
                    else:
                        new_bench_cnf[clause_k][ele_k] = -1 * (map_bench_init[abs(literal)-1] + 1)
                else:
                    if literal > 0:
                        new_bench_cnf[clause_k][ele_k] = literal + max_init_var
                    else:
                        new_bench_cnf[clause_k][ele_k] = literal - max_init_var
        
        # Create Miter 
        init_po_var = cnf[-1][0]
        output_po_var = new_bench_cnf[-1][0]
        po_var = len(x_data) + len(bench_x_data) - len(PI_indexs) + 2
        miter_cnf = [[-init_po_var, -output_po_var, -po_var], 
                     [init_po_var, output_po_var, -po_var], 
                     [init_po_var, -output_po_var, po_var], 
                     [-init_po_var, output_po_var, po_var]]
        final_check_cnf = cnf[:-1] + new_bench_cnf[:-1] + miter_cnf + [[po_var]]
        
        # !!! transformed cnf (bench cnf) must be SAT
        # Logic-1 in truth table of LUT bench should be same as initial AIG
        # Otherwise, AIG may be 1 but bench is 0 due to the deloop variable enforces XNOR to be 0
        final_check_cnf += new_bench_cnf[-1:]
        
        sat_status, asg, _ = cnf_utils.kissat_solve(final_check_cnf, po_var)
        
        assert sat_status == 0
        print('TT: {}, Pass '.format(tt_idx))
        print()

        os.remove(init_bench_path)
        os.remove(init_aig_path)
        os.remove(cnf_path)
        os.remove(output_bench_path)