import numpy as np 
import os 
import time
import copy
import utils.lut_utils as lut_utils
import utils.cnf_utils as cnf_utils
import utils.circuit_utils as circuit_utils
import utils.aiger_utils as aiger_utils
import utils.simulator as simulator
from utils.utils import run_command
from main import main as cnf2lut

np.random.seed(6666)
NO_PIS = 4
RANDOM_TEST = False
AIG_DIR = '/Users/zhengyuanshi/studio/dataset/LEC/all_case'
AIG_PATH_LIST = [
    # 'aa16', 'mult_op_DEMO1_13_13_TOP1', 'mult_op_DEMO1_9_9_TOP4', 'ab21', 'mult_op_DEMO1_5_5_TOP4', 'mult_op_DEMO1_9_9_TOP5', 'mult_op_DEMO1_3_3_TOP4', 'f14', 'b15', 'mult_op_DEMO1_5_5_TOP5', 'c12', 'mult_op_DEMO1_4_4_TOP5', 'd13', 'ac37', 'mult_op_DEMO1_10_10_TOP5', 'mult_op_DEMO1_11_11_TOP4', 'mult_op_DEMO1_8_8_TOP3', 'ad38', 'mult_op_DEMO1_12_12_TOP4', 'mult_op_DEMO1_4_4_TOP8', 'mult_op_DEMO1_9_9_TOP3', 'd27', 'mult_op_DEMO1_7_7_TOP3', 'e13', 'mult_op_DEMO1_10_10_TOP4', 'aa34', 'h33', 'mult_op_DEMO1_3_3_TOP6'
    'ad8'
]

if __name__ == '__main__':
    for aig_name in AIG_PATH_LIST:
        init_aig_path = os.path.join(AIG_DIR, '{}.aiger'.format(aig_name))
        if not os.path.exists(init_aig_path):
            init_aig_path = os.path.join(AIG_DIR, '{}.blif.aiger'.format(aig_name))
            if not os.path.exists(init_aig_path):
                print('File not found: {}'.format(init_aig_path))
                continue
        print('Read: {}'.format(init_aig_path))
        cnf_path = './tmp/init.cnf'
        output_bench_path = './tmp/output.bench'
        
        # x_data = [[0, 0], [1, 0], [2, 0], [3, 1], [4, 2], [5, 2], [6, 1], [7, 1]]
        # edge_index = [[0, 3], [1, 3], [3, 4], [3, 6], [4, 6], [6, 7], [2, 5], [5, 7]]
        x_data, edge_index = aiger_utils.aig_to_xdata(init_aig_path)
        fanin_list, fanout_list = circuit_utils.get_fanin_fanout(x_data, edge_index)
        PO_indexs = []
        PI_indexs = []
        for i in range(len(x_data)):
            if len(fanout_list[i]) == 0 and len(fanin_list[i]) > 0:
                PO_indexs.append(i)
            if len(fanin_list[i]) == 0 and len(fanout_list[i]) > 0:
                PI_indexs.append(i)
        
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
        max_lut_index = 0
        for i in range(len(bench_x_data)):
            bench_node_name = int(bench_x_data[i][0].replace('N', ''))
            map_bench_init[i] = bench_node_name
            if bench_node_name > max_lut_index:
                max_lut_index = bench_node_name
                    
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
        sat_status, asg, _ = cnf_utils.kissat_solve(new_bench_cnf, max_lut_index+1)
        os.remove(cnf_path)
        os.remove(output_bench_path)
        check_cnf_res = True
        if sat_status == 0:
            init_sat_status, _, _ = cnf_utils.kissat_solve(cnf, len(x_data))
            assert init_sat_status == 0
        else:
            # BCP
            bcp_cnf = copy.deepcopy(cnf)
            remove_flag = [False] * len(bcp_cnf)
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
            assert len(remove_flag) == np.sum(remove_flag)
            assert check_cnf_res
                
        print('AIG Name: {}, Check: {}'.format(aig_name, check_cnf_res))
        print()