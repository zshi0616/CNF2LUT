import numpy as np 
import os 
import copy
import random
import utils.lut_utils as lut_utils
import utils.cnf_utils as cnf_utils
import utils.circuit_utils as circuit_utils
import utils.aiger_utils as aiger_utils
import utils.simulator as simulator
from utils.utils import run_command
from main import main as cnf2lut

NO_PIS = 5

if __name__ == '__main__':
    init_bench_path = './tmp/init.bench'
    init_aig_path = './tmp/init.aig'
    cnf_path = './tmp/init.cnf'
    output_bench_path = './tmp/output.bench'
    output_aig_path = './tmp/output.aig'
    
    for tt_idx in range(2 ** (2 ** NO_PIS)):
        tt_val = random.randint(0, 2 ** (2 ** NO_PIS) - 1)
        tt = simulator.dec2list(tt_val, (2 ** NO_PIS))
        tt_hex = simulator.list2hex(tt, 2)
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
        if len(PI_indexs) != NO_PIS or len(PO_indexs) != 1:
            continue
        
        cnf = aiger_utils.aig_to_cnf(x_data, fanin_list, const_1=PO_indexs)
        cnf_utils.save_cnf(cnf, len(x_data), cnf_path)
        
        # Convert to LUT
        print('[INFO] Convert to LUT: {}'.format(tt_hex))
        cnf2lut(cnf_path, output_bench_path)
        
        # Parse Bench
        bench_x_data, bench_fanin_list, bench_fanout_list, bench_PI_indexs, bench_PO_indexs = lut_utils.parse_bench(output_bench_path)
        bench_cnf = lut_utils.convert_cnf(bench_x_data, bench_fanin_list, const_1_list=bench_PO_indexs[1:])
        
        # Check loop
        bench_aig_path = './tmp/output.aig'
        cmd = 'abc -c \'read {}; strash; write_aiger {}; print_stats; \''.format(
            output_bench_path, bench_aig_path
        )
        stdout_info, _ = run_command(cmd)
        for line in stdout_info:
            if 'Network contains a combinational loop' in line:
                raise
        
        os.remove(init_bench_path)
        os.remove(init_aig_path)
        os.remove(cnf_path)
        os.remove(output_bench_path)
        os.remove(output_aig_path)